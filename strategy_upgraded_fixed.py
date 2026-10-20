import math

def ema(values, span):
    alpha = 2/(span+1)
    out = []
    ema_val = None
    for v in values:
        if ema_val is None:
            ema_val = v
        else:
            ema_val = alpha * v + (1-alpha) * ema_val
        out.append(ema_val)
    return out

def rsi(closes, period=14):
    gains = []
    losses = []
    for i in range(1, len(closes)):
        d = closes[i] - closes[i-1]
        gains.append(d if d>0 else 0)
        losses.append(-d if d<0 else 0)
    rsi_vals = [None]*len(closes)
    for i in range(period, len(closes)):
        g = sum(gains[i-period:i]) / period
        l = sum(losses[i-period:i]) / period
        if l == 0:
            rsi_vals[i] = 100
        else:
            rs = g / l
            rsi_vals[i] = 100 - (100/(1+rs))
    return rsi_vals

def atr(highs, lows, closes, period=14):
    trs = []
    for i in range(len(closes)):
        if i==0:
            trs.append(highs[i]-lows[i])
        else:
            tr1 = highs[i]-lows[i]
            tr2 = abs(highs[i]-closes[i-1])
            tr3 = abs(lows[i]-closes[i-1])
            trs.append(max(tr1,tr2,tr3))
    atr_vals = [None]*len(closes)
    for i in range(period-1, len(closes)):
        atr_vals[i] = sum(trs[i-period+1:i+1])/period
    return atr_vals

def calculate_adx(candles, period=14):
    highs = [x['high'] for x in candles]
    lows = [x['low'] for x in candles]
    closes = [x['close'] for x in candles]
    tr_vals = atr(highs, lows, closes, period)
    plus_dm = [0]*len(closes)
    minus_dm = [0]*len(closes)
    for i in range(1, len(closes)):
        up = highs[i]-highs[i-1]
        down = lows[i-1]-lows[i]
        if up>down and up>0:
            plus_dm[i]=up
        if down>up and down>0:
            minus_dm[i]=down
    adx_vals=[None]*len(closes)
    dx=[None]*len(closes)
    for i in range(period-1, len(closes)):
        if tr_vals[i] and tr_vals[i]!=0:
            pdm_avg = sum(plus_dm[max(0,i-period+1):i+1])/period
            mdm_avg = sum(minus_dm[max(0,i-period+1):i+1])/period
            plus_di=100*pdm_avg/tr_vals[i]
            minus_di=100*mdm_avg/tr_vals[i]
            di_sum=plus_di+minus_di
            if di_sum!=0:
                dx[i]=100*abs(plus_di-minus_di)/di_sum
    for i in range(2*period-1, len(closes)):
        vals=[v for v in dx[i-period+1:i+1] if v is not None]
        if len(vals)==period:
            adx_vals[i]=sum(vals)/period
    return adx_vals

def build_features(candles):
    closes = [c['close'] for c in candles]
    highs = [c['high'] for c in candles]
    lows = [c['low'] for c in candles]
    ema9 = ema(closes, 9)
    ema21 = ema(closes, 21)
    ema200 = ema(closes, 200)
    rsi14 = rsi(closes, 14)
    atr_vals = atr(highs, lows, closes, 14)
    adx_vals = calculate_adx(candles, 14)
    signals=[]
    for i in range(len(candles)):
        if i<200:
            signals.append(0)
            continue
        crossover = (ema9[i-1] <= ema21[i-1]) and (ema9[i] > ema21[i])
        macro_trend = closes[i] > ema200[i]
        strong_trend = (adx_vals[i] is not None and adx_vals[i] > 22.0)
        rsi_v = rsi14[i]
        rsi_valid = (rsi_v is not None and 45 <= rsi_v <= 68)
        sig = 1 if (crossover and macro_trend and strong_trend and rsi_valid) else 0
        signals.append(sig)
    result=[]
    for i in range(len(candles)):
        if ema9[i] is None or rsi14[i] is None or atr_vals[i] is None or adx_vals[i] is None:
            continue
        rec = dict(candles[i])
        rec['ema_9']=ema9[i]
        rec['ema_21']=ema21[i]
        rec['ema_200']=ema200[i]
        rec['rsi']=rsi14[i]
        rec['atr']=atr_vals[i]
        rec['adx']=adx_vals[i]
        rec['signal']=signals[i]
        result.append(rec)
    return result
