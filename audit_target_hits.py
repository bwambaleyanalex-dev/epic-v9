#!/usr/bin/env python3
import csv,json
from pathlib import Path
from datetime import datetime
root=Path.cwd()
cache=root/"backtest_cached_20261019_cache"
trades_file=root/"backtest_cached_20261019_trades.csv"
fee=0.001
net_target=0.05
def ms(iso):
    return round(datetime.fromisoformat(iso.replace("Z","+00:00")).timestamp()*1000)
def load(symbol):
    p=cache/(symbol+"_30d.json")
    if not p.is_file(): return {}
    out={}
    for c in json.loads(p.read_text(encoding="utf-8")):
        try: out[int(c[0])]={"open":float(c[1]),"high":float(c[2]),"low":float(c[3]),"close":float(c[4])}
        except (IndexError,TypeError,ValueError): pass
    return out
def main():
    if not trades_file.is_file():
        print("ERROR: trade CSV not found:",trades_file); return
    with trades_file.open(newline="",encoding="utf-8") as f: trades=list(csv.DictReader(f))
    maps={}
    keys=["trades","missing_entry_candle","missing_exit_candle","entry_candle_target_hit","target_hit_before_exit_after_entry","exit_candle_target_hit","target_never_hit_from_entry_through_exit","stop_exits_target_hit_before_exit","stop_exits_target_hit_on_exit_candle","target_reason_but_exit_candle_target_not_hit"]
    counts=dict.fromkeys(keys,0); counts["trades"]=len(trades)
    entry_hits=[]; review=[]
    for tr in trades:
        s=tr["symbol"]
        if s not in maps: maps[s]=load(s)
        candles=maps[s]
        try:
            et=ms(tr["entry_time"]); xt=ms(tr["exit_time"]); entry=float(tr["entry"])
            target=entry*(1+fee+net_target)/(1-fee)
        except (KeyError,TypeError,ValueError) as e:
            print("SKIP malformed row:",e); continue
        ec=candles.get(et); xc=candles.get(xt)
        if ec is None: counts["missing_entry_candle"]+=1
        if xc is None: counts["missing_exit_candle"]+=1
        eh=bool(ec and ec["high"]>=target); xh=bool(xc and xc["high"]>=target)
        if eh:
            counts["entry_candle_target_hit"]+=1
            entry_hits.append((s,tr["entry_time"],tr["exit_time"],tr.get("reason","")))
        if xh: counts["exit_candle_target_hit"]+=1
        bh=any(t>et and t<xt and c["high"]>=target for t,c in candles.items())
        if bh: counts["target_hit_before_exit_after_entry"]+=1
        if not (eh or bh or xh): counts["target_never_hit_from_entry_through_exit"]+=1
        reason=tr.get("reason","")
        if "STOP" in reason.upper():
            if bh:
                counts["stop_exits_target_hit_before_exit"]+=1
                review.append((s,tr["entry_time"],tr["exit_time"],reason,"target hit on an earlier post-entry candle"))
            if xh:
                counts["stop_exits_target_hit_on_exit_candle"]+=1
                review.append((s,tr["entry_time"],tr["exit_time"],reason,"target also touched on exit candle; intrabar order unknown"))
        if "TARGET" in reason.upper() and not xh:
            counts["target_reason_but_exit_candle_target_not_hit"]+=1
            review.append((s,tr["entry_time"],tr["exit_time"],reason,"exit candle high below target"))
    print("READ-ONLY TARGET AUDIT")
    print("Trade CSV:",trades_file.name,"| cache:",cache.name)
    print("Target price includes modeled 0.1% entry and exit fees for 5% net target.")
    print("---- COUNTS ----")
    for k,v in counts.items(): print(f"{k}: {v}")
    print("---- ENTRY-CANDLE TARGET TOUCHES (strategy skips entry-candle exits) ----")
    for x in entry_hits[:30]: print(" | ".join(x))
    if len(entry_hits)>30: print("... plus",len(entry_hits)-30,"more")
    if not entry_hits: print("None")
    print("---- STOP/TARGET REVIEW ITEMS ----")
    for x in review[:60]: print(" | ".join(x))
    if len(review)>60: print("... plus",len(review)-60,"more")
    if not review: print("None")
    print("Audit did not change any files.")
if __name__=="__main__": main()
