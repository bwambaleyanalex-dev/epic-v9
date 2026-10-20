#!/usr/bin/env python3
"""Standalone historical backtest for the user's paper spot strategy.

Read-only with respect to the live dashboard: downloads public Binance 5m candles,
uses an in-memory $9.897851010245653 starting balance by default, and writes only
backtest_report.json and backtest_trades.csv in the current directory.
No orders are submitted. Standard library only.
"""
import argparse
import csv
import json
import math
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

SYMBOLS = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]
API = "https://api.binance.com/api/v3/klines"
INTERVAL = "5m"
FEE_RATE = 0.001
RISK_FRACTION = 0.01
MAX_ALLOCATION = 0.80
ATR_MULTIPLIER = 1.5
NET_TARGET = 0.05
MIN_NOTIONAL = 1.0


def ema(values, period):
    if len(values) < period:
        return None
    value = sum(values[:period]) / period
    alpha = 2.0 / (period + 1.0)
    for x in values[period:]:
        value = x * alpha + value * (1.0 - alpha)
    return value


def rsi(values, period=14):
    if len(values) < period + 1:
        return None
    changes = [values[i] - values[i - 1] for i in range(len(values) - period, len(values))]
    gains = sum(max(x, 0.0) for x in changes) / period
    losses = sum(max(-x, 0.0) for x in changes) / period
    if losses == 0:
        return 100.0 if gains else 50.0
    return 100.0 - 100.0 / (1.0 + gains / losses)


def atr(highs, lows, closes, period=14):
    if len(closes) < period + 1:
        return None
    trs = []
    for i in range(1, len(closes)):
        trs.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))
    return sum(trs[-period:]) / period


def get_candles(symbol, start_ms, end_ms):
    out, cursor = [], start_ms
    while cursor < end_ms:
        query = urllib.parse.urlencode({
            "symbol": symbol, "interval": INTERVAL, "startTime": cursor,
            "endTime": end_ms, "limit": 1000,
        })
        req = urllib.request.Request(API + "?" + query, headers={"User-Agent": "PaperBacktest/1.0"})
        with urllib.request.urlopen(req, timeout=15) as response:
            batch = json.loads(response.read().decode("utf-8"))
        if not batch:
            break
        out.extend(batch)
        next_cursor = int(batch[-1][0]) + 300_000
        if next_cursor <= cursor:
            break
        cursor = next_cursor
        if len(batch) < 1000:
            break
        time.sleep(0.15)
    # Exclude any still-forming candle and normalize to dicts.
    now_ms = int(time.time() * 1000)
    rows = []
    for k in out:
        if int(k[6]) >= now_ms:
            continue
        rows.append({
            "time": int(k[0]), "open": float(k[1]), "high": float(k[2]),
            "low": float(k[3]), "close": float(k[4]), "close_time": int(k[6]),
        })
    unique = {r["time"]: r for r in rows}
    return [unique[t] for t in sorted(unique)]


def build_features(candles):
    result = []
    closes, highs, lows = [], [], []
    for i, c in enumerate(candles):
        closes.append(c["close"]); highs.append(c["high"]); lows.append(c["low"])
        if i < 30:
            result.append({**c, "signal": "WAIT", "score": None, "atr": None})
            continue
        e9 = ema(closes, 9)
        e21 = ema(closes, 21)
        prev9 = ema(closes[:-1], 9)
        prev21 = ema(closes[:-1], 21)
        strength = rsi(closes)
        volatility = atr(highs, lows, closes)
        # Approximate the corrected engine's entry confirmation and candidate ranking.
        # EMA21 slope is measured against the prior candle; normalized by ATR.
        prev_closes = closes[:-1]
        prev_e21 = ema(prev_closes, 21)
        signal, score = "WAIT", None
        if all(v is not None for v in (e9, e21, prev9, prev21, strength, volatility, prev_e21)) and volatility > 0:
            cross = prev9 <= prev21 and e9 > e21
            rising_e21 = e21 > prev_e21
            above_e9 = c["close"] > e9
            gap_atr = (e9 - e21) / volatility
            slope_atr = (e21 - prev_e21) / volatility
            if cross and rising_e21 and above_e9 and 50 <= strength <= 68:
                score = (2.0 * gap_atr) + (3.0 * slope_atr) - (abs(strength - 58.0) / 20.0)
                signal = "BUY"
        result.append({**c, "ema9": e9, "ema21": e21, "rsi": strength,
                       "atr": volatility, "signal": signal, "score": score})
    return result


def run_backtest(data, start_balance):
    # Merge by timestamp; signals are known only after candle close, entries at next candle open.
    by_symbol = {s: {r["time"]: r for r in rows} for s, rows in data.items()}
    all_times = sorted(set().union(*(set(x.keys()) for x in by_symbol.values())))
    feature_by_symbol = {s: {r["time"]: r for r in rows} for s, rows in data.items()}
    cash, realized = start_balance, 0.0
    position, trades = None, []
    equity_peak, max_drawdown = start_balance, 0.0
    for idx, t in enumerate(all_times):
        # Current candle OHLC for all symbols, and prior candle's signal for entry.
        current = {s: by_symbol[s].get(t) for s in SYMBOLS}
        if position:
            bar = current.get(position["symbol"])
            if bar:
                # Check the stop that was active before this candle.
                # If stop and target are both touched, conservatively choose the stop.
                target_price = position["entry"] * (1.0 + FEE_RATE + NET_TARGET) / (1.0 - FEE_RATE)
                exit_price, reason = None, None
                if bar["low"] <= position["stop"]:
                    exit_price, reason = min(position["stop"], bar["open"]), "ATR_TRAILING_STOP"
                elif bar["high"] >= target_price:
                    exit_price, reason = target_price, "NET_5_PERCENT_TARGET"
                if exit_price is None:
                    # Update the trailing stop for subsequent candles only.
                    position["high_water"] = max(position["high_water"], bar["high"])
                    position["stop"] = max(position["stop"], position["high_water"] - position["atr"] * ATR_MULTIPLIER)
                if exit_price is not None:
                    qty = position["qty"]
                    net = (exit_price - position["entry"]) * qty - (position["entry"] + exit_price) * qty * FEE_RATE
                    cash += exit_price * qty * (1.0 - FEE_RATE)
                    realized += net
                    trades.append({"symbol": position["symbol"], "entry_time": datetime.fromtimestamp(position["entry_time"]/1000, timezone.utc).isoformat(),
                                   "exit_time": datetime.fromtimestamp(t/1000, timezone.utc).isoformat(),
                                   "entry": position["entry"], "exit": exit_price, "qty": qty,
                                   "net_pnl": net, "reason": reason})
                    position = None
        # Entry uses signal from previous completed candle and next candle open to avoid look-ahead.
        if position is None and idx > 0:
            candidates = []
            prev_t = all_times[idx - 1]
            for s in SYMBOLS:
                signal_row = feature_by_symbol[s].get(prev_t)
                bar = current.get(s)
                if signal_row and bar and signal_row.get("signal") == "BUY" and signal_row.get("atr") and signal_row["atr"] > 0:
                    candidates.append((float(signal_row["score"]), s, signal_row, bar))
            if candidates:
                candidates.sort(key=lambda x: x[1])
                candidates.sort(key=lambda x: x[0], reverse=True)
                score, symbol, sig, bar = candidates[0]
                price, volatility = bar["open"], sig["atr"]
                stop = price - ATR_MULTIPLIER * volatility
                risk_cash = (cash + (position["qty"] * price if position else 0)) * RISK_FRACTION
                risk_per_unit = (price - stop) + FEE_RATE * (price + stop)
                if price > 0 and risk_per_unit > 0:
                    qty = risk_cash / risk_per_unit
                    qty = min(qty, min(cash / (1 + FEE_RATE), cash * MAX_ALLOCATION) / price)
                    notional = qty * price
                    cost = notional * (1 + FEE_RATE)
                    if qty > 0 and notional >= MIN_NOTIONAL and cost <= cash:
                        cash -= cost
                        position = {"symbol": symbol, "entry": price, "qty": qty, "stop": stop,
                                    "atr": volatility, "high_water": price, "entry_time": t, "score": score}
        # Track conservative equity mark to close, after estimated liquidation fee.
        marked = cash
        if position:
            bar = current.get(position["symbol"])
            if bar:
                marked += position["qty"] * bar["close"] * (1.0 - FEE_RATE)
        equity_peak = max(equity_peak, marked)
        if equity_peak > 0:
            max_drawdown = max(max_drawdown, (equity_peak - marked) / equity_peak)
    # Mark any remaining position to the final close, but do not force-close it.
    final_equity = cash
    if position:
        last = by_symbol[position["symbol"]].get(all_times[-1])
        if last:
            final_equity += position["qty"] * last["close"] * (1.0 - FEE_RATE)
    wins = sum(1 for tr in trades if tr["net_pnl"] > 0)
    losses = sum(1 for tr in trades if tr["net_pnl"] <= 0)
    report = {
        "symbols": SYMBOLS, "interval": INTERVAL, "starting_balance": start_balance,
        "final_equity": final_equity, "net_pnl": final_equity - start_balance,
        "return_percent": (final_equity / start_balance - 1.0) * 100 if start_balance else 0,
        "closed_trades": len(trades), "wins": wins, "losses": losses,
        "win_rate_percent": (wins / len(trades) * 100) if trades else 0,
        "max_drawdown_percent": max_drawdown * 100,
        "realized_net_pnl_closed_trades": realized,
        "open_position_at_end": position is not None,
        "open_position_symbol": position["symbol"] if position else None,
        "fees_rate_each_side": FEE_RATE, "net_target_percent": NET_TARGET * 100,
        "note": "Historical simulation only. Approximate signal/ranking reconstruction; stop-first when stop and target touch the same candle. Results do not predict future performance."
    }
    return report, trades


def main():
    parser = argparse.ArgumentParser(description="Standalone paper-strategy historical backtest; does not touch live account files.")
    parser.add_argument("--days", type=int, default=30, help="Historical days to test (default: 30; maximum 90).")
    parser.add_argument("--balance", type=float, default=9.897851010245653, help="Starting test balance (default: current paper cash; not linked to account file).")
    args = parser.parse_args()
    if not 1 <= args.days <= 90:
        parser.error("--days must be between 1 and 90")
    if not math.isfinite(args.balance) or args.balance <= 0:
        parser.error("--balance must be a positive number")
    end_ms = int(time.time() * 1000)
    start_ms = int((datetime.now(timezone.utc) - timedelta(days=args.days)).timestamp() * 1000)
    print(f"Downloading public Binance {INTERVAL} candles for {len(SYMBOLS)} symbols, {args.days} days...")
    data = {}
    for i, symbol in enumerate(SYMBOLS, 1):
        try:
            candles = get_candles(symbol, start_ms, end_ms)
            if len(candles) < 100:
                raise RuntimeError(f"only {len(candles)} candles received")
            data[symbol] = build_features(candles)
            print(f"[{i}/{len(SYMBOLS)}] {symbol}: {len(candles)} candles")
        except Exception as exc:
            raise SystemExit(f"Download failed for {symbol}: {exc}. No report written; try again later.")
    report, trades = run_backtest(data, args.balance)
    Path("backtest_report.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with open("backtest_trades.csv", "w", newline="", encoding="utf-8") as f:
        fields = ["symbol", "entry_time", "exit_time", "entry", "exit", "qty", "net_pnl", "reason"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader(); writer.writerows(trades)
    print("\n=== BACKTEST RESULTS ===")
    print(f"Starting balance: ${report['starting_balance']:.4f}")
    print(f"Final equity:     ${report['final_equity']:.4f}")
    print(f"Net P/L:          ${report['net_pnl']:.4f} ({report['return_percent']:.2f}%)")
    print(f"Closed trades:    {report['closed_trades']} | Wins: {report['wins']} | Losses: {report['losses']}")
    print(f"Win rate:         {report['win_rate_percent']:.1f}%")
    print(f"Max drawdown:     {report['max_drawdown_percent']:.2f}%")
    print(f"Open position at end: {report['open_position_at_end']}")
    print("Reports: backtest_report.json, backtest_trades.csv")
    print("NOTE: Historical simulation only; no real orders, no account/history files modified.")

if __name__ == "__main__":
    main()
