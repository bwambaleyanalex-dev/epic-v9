import json, glob, csv
from pathlib import Path
import strategy_v3 as bt

# CONFIG
starting_balance = 100.0
fee_rate = 0.001
partition_val = 16.66
symbol = "BTCUSDT"

# load candles - find file
files = glob.glob("*candles*.json") + glob.glob("*.json")
candle_file = None
for f in files:
    if "candle" in f.lower() or "btc" in f.lower() or "data" in f.lower():
        candle_file = f
        break
if not candle_file:
    # try the file used in original script
    candle_file = "btc_15m_candles.json"
    if not Path(candle_file).exists():
        # fallback: search in parent
        parent_files = glob.glob("../*.json") + glob.glob("../../*.json")
        if parent_files:
            candle_file = parent_files[0]

print(f"Using candle file: {candle_file}")
with open(candle_file) as f:
    raw = json.load(f)
# convert format if needed
converted=[]
if isinstance(raw, list) and len(raw)>0:
    if isinstance(raw[0], dict) and "close" in raw[0]:
        converted=raw
    else:
        # assume [time,open,high,low,close,volume] format
        for c in raw:
            if isinstance(c, list) and len(c)>=5:
                converted.append({"time":c[0],"open":float(c[1]),"high":float(c[2]),"low":float(c[3]),"close":float(c[4]),"volume":float(c[5]) if len(c)>5 else 0})
            elif isinstance(c, dict):
                converted.append(c)

rows = bt.build_features(converted)
print(f"Rows with features: {len(rows)}")

balance=starting_balance
all_trades=[]; stop_exits=0
target_hits_count={"tp1":0,"tp2":0,"tp3":0}
in_position=False; entry_price=0; entry_time=0; stop_loss=0; tp1_hit=False; tp2_hit=False; tp3_hit=False; qty=0

for i,row in enumerate(rows):
    if not in_position and row.get("signal",0)==1:
        in_position=True
        entry_price=row["close"]; entry_time=row["time"]
        atr=row["atr"]
        # V4: tighter stop 1.5 ATR, not 2.0
        stop_loss=entry_price - (1.5*atr)
        qty=partition_val/entry_price
        tp1_hit=False; tp2_hit=False; tp3_hit=False
        continue
    if in_position:
        high=row["high"]; low=row["low"]; close=row["close"]
        if low <= stop_loss:
            exit_price=stop_loss
            net_pnl=(exit_price-entry_price)*qty - (entry_price*qty*fee_rate) - (exit_price*qty*fee_rate)
            balance+=net_pnl
            all_trades.append({"symbol":symbol,"entry_time":entry_time,"exit_time":row["time"],"entry":entry_price,"exit":exit_price,"qty":qty,"net_pnl":net_pnl,"reason":"STOP","tp1":tp1_hit,"tp2":tp2_hit,"tp3":tp3_hit})
            stop_exits+=1; in_position=False; continue

        # V4: BIGGER TARGETS - 2%, 4%, 6% (was 1,2,3)
        tp1_target=entry_price*1.02
        tp2_target=entry_price*1.04
        tp3_target=entry_price*1.06

        if not tp1_hit and high>=tp1_target:
            tp1_hit=True; target_hits_count["tp1"]+=1
            # V4: lock +0.5% profit, not breakeven
            stop_loss=entry_price*1.005

        if tp1_hit and not tp2_hit and high>=tp2_target:
            tp2_hit=True; target_hits_count["tp2"]+=1
            # V4: lock 2.5% profit
            stop_loss=entry_price*1.025

        if tp2_hit and not tp3_hit and high>=tp3_target:
            tp3_hit=True; target_hits_count["tp3"]+=1
            exit_price=tp3_target
            net_pnl=(exit_price-entry_price)*qty - (entry_price*qty*fee_rate) - (exit_price*qty*fee_rate)
            balance+=net_pnl
            all_trades.append({"symbol":symbol,"entry_time":entry_time,"exit_time":row["time"],"entry":entry_price,"exit":exit_price,"qty":qty,"net_pnl":net_pnl,"reason":"TP3_6PCT","tp1":tp1_hit,"tp2":tp2_hit,"tp3":tp3_hit})
            in_position=False

        # V4: trailing stop after TP1 using EMA9
        if tp1_hit and in_position:
            ema9_trail=row.get("ema_9",0)
            if ema9_trail>stop_loss:
                stop_loss=ema9_trail

wins=sum(1 for t in all_trades if t["net_pnl"]>0)
losses=sum(1 for t in all_trades if t["net_pnl"]<0)
win_rate=(wins/len(all_trades)*100) if all_trades else 0
gross_wins=sum(t["net_pnl"] for t in all_trades if t["net_pnl"]>0)
gross_losses=abs(sum(t["net_pnl"] for t in all_trades if t["net_pnl"]<0))
profit_factor=(gross_wins/gross_losses) if gross_losses>0 else 0

report={"experiment":"v4 2-4-6% targets + 1.5ATR stop + profit lock","starting_balance":starting_balance,"final_equity":balance,"net_equity_change":balance-starting_balance,"completed_trades":len(all_trades),"wins":wins,"losses":losses,"win_rate_percent":win_rate,"profit_factor":profit_factor,"target_hits":target_hits_count,"stop_exits":stop_exits}
Path("backtest_v4_report.json").write_text(json.dumps(report,indent=2))
with open("backtest_v4_trades.csv","w",newline="") as csvfile:
    writer=csv.DictWriter(csvfile,fieldnames=["symbol","entry_time","exit_time","entry","exit","qty","net_pnl","reason","tp1","tp2","tp3"])
    writer.writeheader()
    for t in all_trades: writer.writerow(t)

print("\n=== V4 SIMULATION COMPLETE ===")
print(json.dumps(report,indent=2))
