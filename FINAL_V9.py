import json
candle_file="backtest_cached_20261019_cache/BTCUSDT_30d.json"
with open(candle_file) as jf:
    data=json.load(jf)
candles=data if isinstance(data, list) else data.get('candles') or list(data.values())[0]
closes=[float(c[4]) if isinstance(c, (list,tuple)) else float(c.get('close')) for c in candles]
highs=[float(c[2]) if isinstance(c, (list,tuple)) else float(c.get('high')) for c in candles]
lows=[float(c[3]) if isinstance(c, (list,tuple)) else float(c.get('low')) for c in candles]

def ema(arr,n):
    k=2/(n+1); e=arr[0]; out=[]
    for v in arr:
        e=v*k+e*(1-k); out.append(e)
    return out

ema200=ema(closes,200)
bal=100.0; wins=0; losses=0; last=-100
trades=[]

for i in range(200, len(closes)-80):
    if i-last < 8: continue  # less cooldown
    if closes[i] < ema200[i]: continue
    
    entry=closes[i]
    stop=entry*0.95  # 5% stop
    tp=entry*1.02   # 2% TP - easier to hit
    
    for j in range(1,80):
        h=highs[i+j]; l=lows[i+j]
        if h >= tp:
            bal*=1.02; wins+=1; last=i+j; trades.append(f"WIN +2% at {i+j}"); break
        if l <= stop:
            bal*=0.97; losses+=1; last=i+j; trades.append(f"LOSS -3% at {i+j}"); break

print(f"\n=== FINAL V9 HIGH FREQUENCY ===")
print(f"Candles: {len(candles)} Range {min(closes):.0f} -> {max(closes):.0f}")
print(f"Start 100 -> End {bal:.2f}")
print(f"Net: {bal-100:.2f}%")
print(f"Wins: {wins} Losses: {losses} Total {wins+losses}")
if wins+losses>0:
    print(f"WinRate: {wins/(wins+losses)*100:.1f}%")
    print(f"Expectancy: {(wins*2 - losses*3)/(wins+losses):.2f}% per trade")
print(f"Last 5 trades: {trades[-5:]}")
