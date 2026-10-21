import json
import time
import os
import urllib.request
from datetime import datetime, timezone

SYMBOL = "BTCUSDT"
INTERVAL = "5m"
START_BALANCE = 100.0
FEE_RATE = 0.001
TAKE_PROFIT = 0.02
STOP_LOSS = 0.05
COOLDOWN_BARS = 8
MAX_HOLD_BARS = 80
STATE_FILE = os.environ.get("STATE_FILE", "epic_v9_paper_state.json")
TRADES_FILE = os.environ.get("TRADES_FILE", "epic_v9_paper_trades.jsonl")

def get_candles():
    url = (
        "https://api.binance.com/api/v3/klines"
        f"?symbol={SYMBOL}&interval={INTERVAL}&limit=250"
    )
    req = urllib.request.Request(
        url, headers={"User-Agent": "EPIC-V9-Paper-Test"}
    )
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.loads(response.read().decode())

def ema(values, period=200):
    alpha = 2 / (period + 1)
    result = values[0]
    for value in values[1:]:
        result += alpha * (value - result)
    return result

def now_text():
    return datetime.now(timezone.utc).isoformat()

def save_state(state):
    temp = STATE_FILE + ".tmp"
    with open(temp, "w") as f:
        json.dump(state, f, indent=2)
    os.replace(temp, STATE_FILE)

def log_trade(trade):
    with open(TRADES_FILE, "a") as f:
        f.write(json.dumps(trade) + "\n")

if os.path.exists(STATE_FILE):
    with open(STATE_FILE) as f:
        state = json.load(f)
else:
    candles = get_candles()
    state = {
        "balance": START_BALANCE,
        "position": None,
        "last_candle": int(candles[-2][0]),
        "last_exit_index": -100000,
        "bar_index": 0,
        "starting_balance": START_BALANCE
    }
    save_state(state)

print("EPIC V9 PAPER TEST — REAL TRADING DISABLED")
print(f"Pair: {SYMBOL} | Timeframe: {INTERVAL}")
print(f"Paper cash: ${state['balance']:.2f}")
print("Waiting for new closed candles. Press Ctrl+C to stop.")

while True:
    try:
        candles = get_candles()
        closed = candles[-2]
        candle_time = int(closed[0])

        if candle_time == state["last_candle"]:
            time.sleep(15)
            continue

        closes = [float(c[4]) for c in candles[:-1]]
        high = float(closed[2])
        low = float(closed[3])
        price = float(closed[4])
        trend_ema = ema(closes[-200:])
        state["bar_index"] += 1
        index = state["bar_index"]
        position = state["position"]

        stamp = datetime.fromtimestamp(
            candle_time / 1000, timezone.utc
        ).isoformat()

        if position:
            position["bars_held"] += 1
            entry = position["entry"]
            reason = None
            exit_price = None

            # Conservative assumption if TP and stop both hit
            # within the same candle: stop is hit first.
            if low <= position["stop"]:
                exit_price = position["stop"]
                reason = "STOP_LOSS"
            elif high >= position["target"]:
                exit_price = position["target"]
                reason = "TAKE_PROFIT"
            elif position["bars_held"] >= MAX_HOLD_BARS:
                exit_price = price
                reason = "MAX_HOLD"

            if reason:
                gross = position["qty"] * exit_price
                exit_fee = gross * FEE_RATE
                net = gross - exit_fee
                state["balance"] += net
                pnl = net - position["entry_cost"]
                trade = {
                    "time": stamp,
                    "symbol": SYMBOL,
                    "entry": entry,
                    "exit": exit_price,
                    "reason": reason,
                    "bars_held": position["bars_held"],
                    "net_pnl": round(pnl, 6),
                    "balance": round(state["balance"], 6)
                }
                log_trade(trade)
                print(
                    f"{reason}: exit ${exit_price:.2f} | "
                    f"net P/L ${pnl:.4f} | cash ${state['balance']:.2f}"
                )
                state["position"] = None
                state["last_exit_index"] = index

        elif (
            price > trend_ema
            and index - state["last_exit_index"] >= COOLDOWN_BARS
            and state["balance"] > 1
        ):
            entry = price
            entry_fee = state["balance"] * FEE_RATE
            spend = state["balance"] - entry_fee
            qty = spend / entry
            state["position"] = {
                "entry": entry,
                "qty": qty,
                "entry_cost": state["balance"],
                "target": entry * (1 + TAKE_PROFIT),
                "stop": entry * (1 - STOP_LOSS),
                "bars_held": 0
            }
            state["balance"] = 0.0
            print(
                f"ENTRY: ${entry:.2f} | EMA200 ${trend_ema:.2f} | "
                f"TP ${entry * 1.02:.2f} | SL ${entry * 0.95:.2f}"
            )

        state["last_candle"] = candle_time
        save_state(state)

        position = state["position"]
        if position:
            mark_value = position["qty"] * price * (1 - FEE_RATE)
            equity = state["balance"] + mark_value
        else:
            equity = state["balance"]

        print(
            f"{stamp} | close ${price:.2f} | EMA200 ${trend_ema:.2f} | "
            f"equity ${equity:.2f}"
        )
        time.sleep(15)

    except KeyboardInterrupt:
        print("\nStopped safely. Paper state and trade log are saved.")
        break
    except Exception as e:
        print(f"Temporary error: {e}")
        time.sleep(30)
