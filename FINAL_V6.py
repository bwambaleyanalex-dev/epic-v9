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

for i in range(200, len(closes)-50):
    if i - last_trade < 15: continue
    # MEAN REVERSION: buy dip 2% below EMA200
    if closes[i] > ema200[i] * 0.98: continue
    
    entry=closes[i]
    stop=entry*0.92  # 8% stop wide
    tp=entry*1.04    # 4% TP
    
    for j in range(1,50):
        # check TP first
        if highs[i+j] >= tp:
            bal*=1.04; wins+=1; last_trade=i+j; break
        if lows[i+j] <= stop:
            bal*=0.99; losses+=1; last_trade=i+j; break

print("\n=== FINAL V6 MEAN REVERSION ===")
print(f"Candles: {len(candles)}")
print(f"Start 100 -> End {bal:.2f}")
print(f"Net: {bal-100:.2f}%")
print(f"Wins: {wins} Losses: {losses} WinRate: {wins/(wins+losses)*100 if wins+losses>0 else 0:.2f}%")
print(f"Profit factor est: {(wins*4)/(losses*1) if losses>0 else 0:.2f}")
