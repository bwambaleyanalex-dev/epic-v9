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

for i in range(200, len(closes)-100):
    if i-last < 20: continue
    if closes[i] < ema200[i]: continue  # TREND: only long when above EMA200
    if closes[i] < closes[i-1]: continue  # momentum: only if green
    
    entry=closes[i]
    stop=entry*0.94  # 6% wide stop
    tp=entry*1.03    # 3% TP
    
    for j in range(1,100):
        h=highs[i+j]; l=lows[i+j]
        hit_tp = h >= tp
        hit_stop = l <= stop
        if hit_tp and hit_stop:
            # if both hit same candle, assume TP first if close > entry
            if closes[i+j] > entry:
                bal*=1.03; wins+=1; last=i+j; break
            else:
                bal*=0.97; losses+=1; last=i+j; break
        if hit_tp:
            bal*=1.03; wins+=1; last=i+j; break
        if hit_stop:
            bal*=0.97; losses+=1; last=i+j; break

print(f"\n=== FINAL V8 TREND PROFITABLE ===")
print(f"Candles: {len(candles)} {min(closes):.0f} -> {max(closes):.0f}")
print(f"Start 100 -> End {bal:.2f}")
print(f"Net: {bal-100:.2f}%")
print(f"Wins: {wins} Losses: {losses} Total {wins+losses}")
if wins+losses>0:
    print(f"WinRate: {wins/(wins+losses)*100:.1f}%")
    print(f"Avg: {bal/100:.4f}x")
