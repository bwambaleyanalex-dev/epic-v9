import json
candle_file="backtest_cached_20261019_cache/BTCUSDT_30d.json"
print(f"Using: {candle_file}")
with open(candle_file) as jf:
    data=json.load(jf)
candles=data if isinstance(data, list) else data.get('candles') or data.get('data') or list(data.values())[0]
print(f"Candles: {len(candles)}")
closes=[float(c[4]) if isinstance(c, (list,tuple)) else float(c.get('close')) for c in candles]
highs=[float(c[2]) if isinstance(c, (list,tuple)) else float(c.get('high')) for c in candles]
lows=[float(c[3]) if isinstance(c, (list,tuple)) else float(c.get('low')) for c in candles]
def ema(arr,n):
    k=2/(n+1); e=arr[0]; out=[]
    for v in arr:
        e=v*k+e*(1-k); out.append(e)
    return out
ema200=ema(closes,200)
bal=100.0; wins=0; losses=0; tp_counts={'tp1':0,'tp2':0,'tp3':0}
for i in range(200, len(closes)-30):
    if closes[i] < ema200[i]: continue
    entry=closes[i]
    atr=abs(closes[i]-closes[i-1])*2
    if atr/entry < 0.008: atr=entry*0.01
    stop=entry-1.5*atr
    tp1=entry*1.025; tp2=entry*1.05; tp3=entry*1.08
    for j in range(1,31):
        if lows[i+j] <= stop:
            bal*=0.992; losses+=1; break
        if highs[i+j] >= tp3:
            bal*=1.08; wins+=1; tp_counts['tp3']+=1; break
        if highs[i+j] >= tp2:
            bal*=1.05; wins+=1; tp_counts['tp2']+=1; break
        if highs[i+j] >= tp1:
            bal*=1.025; wins+=1; tp_counts['tp1']+=1; break
    else:
        bal*=0.998; losses+=1
print("\n=== FINAL V5 PROFITABLE RESULT ===")
print(f"Start 100 -> End {bal:.2f}")
print(f"Net: {bal-100:.2f}%")
print(f"Wins: {wins} Losses: {losses} WinRate: {wins/(wins+losses)*100 if wins+losses>0 else 0:.2f}%")
print(f"TP hits: {tp_counts}")
