import json
import csv
from pathlib import Path
import strategy_upgraded as bt

cache = Path("backtest_cached_20261019_cache")
symbols = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT"]

starting_balance = 100.0
balance = starting_balance
fee_rate = 0.001

all_trades = []
target_hits_count = {"tp1": 0, "tp2": 0, "tp3": 0}
stop_exits = 0

print("=== STARTING UPGRADED STAGED-PROFIT BACKTEST ===")

for symbol in symbols:
    path = cache / f"{symbol}_30d.json"
    if not path.exists():
        continue
        
    candles = json.loads(path.read_text(encoding="utf-8"))
    converted = [
        {"time": int(c[0]), "open": float(c[1]),
         "high": float(c[2]), "low": float(c[3]),
         "close": float(c[4]), "volume": float(c[5])}
        if isinstance(c, list) and len(c) >= 6 else c
        for c in candles
    ]
    
    rows = bt.build_features(converted)
    
    in_position = False
    entry_price = 0.0
    entry_time = 0
    stop_loss = 0.0
    tp1_hit = False
    tp2_hit = False
    tp3_hit = False
    qty = 0.0
    partition_val = 16.66
    
    for i, row in enumerate(rows):
        if not in_position and row.get("signal", 0) == 1:
            in_position = True
            entry_price = row["close"]
            entry_time = row["time"]
            atr = row["atr"]
            stop_loss = entry_price - (2.0 * atr)
            qty = partition_val / entry_price
            tp1_hit = False
            tp2_hit = False
            tp3_hit = False
            continue
            
        if in_position:
            high = row["high"]
            low = row["low"]
            close = row["close"]
            
            if low <= stop_loss:
                exit_price = stop_loss
                net_pnl = (exit_price - entry_price) * qty - (entry_price * qty * fee_rate) - (exit_price * qty * fee_rate)
                balance += net_pnl
                
                all_trades.append({
                    "symbol": symbol,
                    "entry_time": entry_time,
                    "exit_time": row["time"],
                    "entry": entry_price,
                    "exit": exit_price,
                    "qty": qty,
                    "net_pnl": net_pnl,
                    "reason": "ATR_OR_PROFIT_STOP",
                    "tp1": tp1_hit,
                    "tp2": tp2_hit,
                    "tp3": tp3_hit
                })
                stop_exits += 1
                in_position = False
                continue
                
            tp1_target = entry_price * 1.01
            tp2_target = entry_price * 1.02
            tp3_target = entry_price * 1.03
            
            if not tp1_hit and high >= tp1_target:
                tp1_hit = True
                target_hits_count["tp1"] += 1
                stop_loss = entry_price
                
            if tp1_hit and not tp2_hit and high >= tp2_target:
                tp2_hit = True
                target_hits_count["tp2"] += 1
                stop_loss = entry_price * 1.005
                
            if tp2_hit and not tp3_hit and high >= tp3_target:
                tp3_hit = True
                target_hits_count["tp3"] += 1
                exit_price = tp3_target
                net_pnl = (exit_price - entry_price) * qty - (entry_price * qty * fee_rate) - (exit_price * qty * fee_rate)
                balance += net_pnl
                
                all_trades.append({
                    "symbol": symbol,
                    "entry_time": entry_time,
                    "exit_time": row["time"],
                    "entry": entry_price,
                    "exit": exit_price,
                    "qty": qty,
                    "net_pnl": net_pnl,
                    "reason": "TP3_STAGED_TARGETS",
                    "tp1": tp1_hit,
                    "tp2": tp2_hit,
                    "tp3": tp3_hit
                })
                in_position = False

wins = sum(1 for t in all_trades if t["net_pnl"] > 0)
losses = sum(1 for t in all_trades if t["net_pnl"] < 0)
win_rate = (wins / len(all_trades) * 100) if all_trades else 0.0

gross_wins = sum(t["net_pnl"] for t in all_trades if t["net_pnl"] > 0)
gross_losses = abs(sum(t["net_pnl"] for t in all_trades if t["net_pnl"] < 0))
profit_factor = (gross_wins / gross_losses) if gross_losses > 0 else 0.0

report = {
    "experiment": "upgraded adx and ema 200 filtered strategy",
    "starting_balance": starting_balance,
    "final_equity": balance,
    "net_equity_change": balance - starting_balance,
    "completed_trades": len(all_trades),
    "wins": wins,
    "losses": losses,
    "win_rate_percent": win_rate,
    "profit_factor": profit_factor,
    "target_hits": target_hits_count,
    "stop_exits": stop_exits
}

Path("backtest_upgraded_report.json").write_text(json.dumps(report, indent=2))

with open("backtest_upgraded_trades.csv", "w", newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=["symbol", "entry_time", "exit_time", "entry", "exit", "qty", "net_pnl", "reason", "tp1", "tp2", "tp3"])
    writer.writeheader()
    for t in all_trades:
        writer.writerow(t)

print("\n=== UPGRADED SIMULATION COMPLETE ===")
print(json.dumps(report, indent=2))
