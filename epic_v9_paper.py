import json, time, os, urllib.request
from datetime import datetime, timezone
import threading
from flask import Flask, jsonify

SYMBOL = "BTCUSDT"
INTERVAL = "5m"
START_BALANCE = 100.0
FEE_RATE = 0.001
TAKE_PROFIT = 0.02
STOP_LOSS = 0.05
COOLDOWN_BARS = 8
MAX_HOLD_BARS = 80
STATE_FILE = os.environ.get("STATE_FILE", "state.json")
TRADES_FILE = os.environ.get("TRADES_FILE", "trades.json")

def get_candles():
    url = f"https://api.binance.com/api/v3/klines?symbol={SYMBOL}&interval={INTERVAL}&limit=250"
    req = urllib.request.Request(url, headers={"User-Agent": "EPIC-V9"})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read())

def ema(values, period=200):
    alpha = 2/(period+1)
    res = values[0]
    for v in values[1:]:
        res += alpha*(v-res)
    return res

def now_text():
    return datetime.now(timezone.utc).isoformat()

def save_state(s):
    with open(STATE_FILE,"w") as f:
        json.dump(s,f)

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except:
            pass
    return None

def log_trade(t):
    trades=[]
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE) as f:
                trades=json.load(f)
        except:
            trades=[]
    trades.append(t)
    with open(TRADES_FILE,"w") as f:
        json.dump(trades[-100:],f)

def run_bot():
    print("EPIC V9 PAPER TEST - REAL TRADING DISABLED", flush=True)
    while True:
        try:
            candles=get_candles()
            ct=int(candles[-2][0])
            state=load_state()
            if not state:
                state={"balance":START_BALANCE,"position":None,"last_candle":ct-1,"last_exit_index":-100000,"bar_index":0,"starting_balance":START_BALANCE}
                save_state(state)
            if ct==state["last_candle"]:
                time.sleep(15)
                continue
            closes=[float(c[4]) for c in candles]
            price=float(candles[-2][4])
            high=float(candles[-2][2])
            low=float(candles[-2][3])
            trend_ema=ema(closes[-200:])
            state["bar_index"]+=1
            idx=state["bar_index"]
            pos=state["position"]
            stamp=datetime.fromtimestamp(ct/1000, timezone.utc).isoformat()
            if pos:
                pos["bars_held"]+=1
                entry=pos["entry"]
                reason=None
                exit_p=None
                if low<=pos["stop"]:
                    exit_p=pos["stop"]
                    reason="STOP_LOSS"
                elif high>=pos["target"]:
                    exit_p=pos["target"]
                    reason="TAKE_PROFIT"
                elif pos["bars_held"]>=MAX_HOLD_BARS:
                    exit_p=price
                    reason="MAX_HOLD"
                if reason:
                    gross=pos["qty"]*exit_p
                    net=gross-gross*FEE_RATE
                    state["balance"]+=net
                    pnl=net-pos["entry_cost"]
                    log_trade({"time":stamp,"symbol":SYMBOL,"entry":entry,"exit":exit_p,"reason":reason,"pnl":round(pnl,6),"balance":round(state["balance"],6)})
                    print(f"{reason} exit ${exit_p:.2f} P/L ${pnl:.4f} bal ${state['balance']:.2f}", flush=True)
                    state["position"]=None
                    state["last_exit_index"]=idx
            elif price>trend_ema and idx-state["last_exit_index"]>COOLDOWN_BARS and state["balance"]>1:
                entry=price
                fee=state["balance"]*FEE_RATE
                spend=state["balance"]-fee
                qty=spend/entry
                state["position"]={"entry":entry,"qty":qty,"entry_cost":state["balance"],"target":entry*(1+TAKE_PROFIT),"stop":entry*(1-STOP_LOSS),"bars_held":0}
                state["balance"]=0.0
                print(f"ENTRY ${entry:.2f} EMA ${trend_ema:.2f}", flush=True)
            state["last_candle"]=ct
            save_state(state)
            time.sleep(30)
        except Exception as e:
            print(f"error {e}", flush=True)
            time.sleep(15)

app=Flask(__name__)
@app.route("/")
def dash():
    s=load_state()
    if not s:
        return "EPIC V9 Starting... refresh in 60s"
    p=s.get("position")
    pt=f"IN POS Entry ${p['entry']:.2f} TP ${p['target']:.2f} SL ${p['stop']:.2f}" if p else "FLAT - Waiting EMA200"
    return f"<h1>EPIC V9 - Live Paper Test</h1><p>REAL TRADING DISABLED - PAPER ONLY</p><p>Paper cash: ${s.get('balance',0):.2f}</p><p>Pos: {pt}</p><p>Last candle: {s.get('last_candle')} Bar:{s.get('bar_index')}</p><p>{now_text()}</p><meta http-equiv='refresh' content='30'>"
@app.route("/health")
def health():
    return "OK"
@app.route("/trades")
def trades():
    try:
        with open(TRADES_FILE) as f:
            return jsonify(json.load(f))
    except:
        return jsonify([])

threading.Thread(target=run_bot, daemon=True).start()
