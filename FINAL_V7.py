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
bal=100.0; wins=0; losses=0; last_trade=-100
dips=[]

for i in range(200, len(closes)-50):
    if i - last_trade < 10: continue
    # check dip size
    diff = (closes[i]-ema200[i])/ema200[i]*100
    if i%1000==0: dips.append(diff)
    # BUY if price is below EMA200 (mean reversion)
    if closes[i] >= ema200[i]: continue
    
    entry=closes[i]
    stop=entry*0.93  # 7% stop
    tp=entry*1.035  # 3.5% TP
    
    for j in range(1,50):
        if highs[i+j] >= tp:
            bal*=1.035; wins+=1; last_trade=i+j; break
        if lows[i+j] <= stop:
            bal*=0.985; losses+=1; last_trade=i+j; break

print(f"Candles: {len(candles)}")
print(f"Sample dip % (close vs EMA200): {dips[:5]}")
print(f"Min close: {min(closes)} Max: {max(closes)}")
print(f"\n=== FINAL V7 BELOW EMA ===")
print(f"Start 100 -> End {bal:.2f}")
print(f"Net: {bal-100:.2f}%")
print(f"Wins: {wins} Losses: {losses} Total: {wins+losses}")
if wins+losses>0:
    print(f"WinRate: {wins/(wins+losses)*100:.1f}%")
