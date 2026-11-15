import os, json, time, threading, urllib.request
from datetime import datetime, timezone
from flask import Flask, request, jsonify

# EPIC V10: PAPER ONLY. No exchange orders are ever submitted.
PORT = int(os.environ.get("PORT", 5000))
START_BALANCE = 100.0
FEE = 0.001
TP = 0.006
SL = 0.004
RISK = 0.10
MAX_LIMIT = 10
STATE_FILE = "v10_state.json"
TRADES_FILE = "v10_trades.json"
app = Flask(__name__)
lock = threading.RLock()

def fresh():
    return {"cash": START_BALANCE, "symbol": "BTCUSDT", "positions": [],
            "max_positions": 5, "armed": False, "auto": False,
            "last_signal": None, "last_signal_candle": None,
            "realized_today": 0.0, "day": datetime.now(timezone.utc).date().isoformat(),
            "status": "WAITING", "message": "Select a pair and give an initial instruction."}

def read_json(path, default):
    try:
        with open(path) as f: return json.load(f)
    except Exception: return default

state = read_json(STATE_FILE, fresh())
for k, v in fresh().items(): state.setdefault(k, v)

def save():
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f: json.dump(state, f, indent=2)
    os.replace(tmp, STATE_FILE)

def log_trade(t):
    trades = read_json(TRADES_FILE, [])
    trades.append(t)
    with open(TRADES_FILE + ".tmp", "w") as f: json.dump(trades[-1000:], f, indent=2)
    os.replace(TRADES_FILE + ".tmp", TRADES_FILE)

def now(): return datetime.now(timezone.utc).isoformat()

def candles(symbol):
    if not symbol.endswith("USDT") or not symbol[:-4].isalnum():
        raise ValueError("Use a USDT pair such as BTCUSDT.")
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=5m&limit=250"
    req = urllib.request.Request(url, headers={"User-Agent": "EPIC-V10-PAPER"})
    with urllib.request.urlopen(req, timeout=12) as r: return json.loads(r.read())

def ema(xs, n):
    a = 2 / (n + 1); v = xs[0]
    for x in xs[1:]: v += a * (x - v)
    return v

def rsi(xs, n=14):
    changes = [xs[i] - xs[i-1] for i in range(1, len(xs))]
    gains = [max(x, 0) for x in changes[-n:]]
    losses = [max(-x, 0) for x in changes[-n:]]
    ag, al = sum(gains)/n, sum(losses)/n
    if al == 0: return 100 if ag else 50
    return 100 - 100/(1 + ag/al)

def signal_for(data):
    # Ignore the still-forming final candle.
    xs = [float(c[4]) for c in data[:-1]]
    if len(xs) < 205: return None, None, None
    f0, s0 = ema(xs[-30:], 9), ema(xs[-60:], 21)
    f1, s1 = ema(xs[-31:-1], 9), ema(xs[-61:-1], 21)
    trend, mom = ema(xs[-220:], 200), rsi(xs)
    side = None
    if f1 <= s1 and f0 > s0 and xs[-1] > trend and 50 <= mom <= 72: side = "BUY"
    if f1 >= s1 and f0 < s0 and xs[-1] < trend and 28 <= mom <= 50: side = "SELL"
    return side, xs[-1], int(data[-2][0])

def equity():
    value = state["cash"]
    for p in state["positions"]:
        d = 1 if p["side"] == "BUY" else -1
        value += p["margin"] + d * (p["last"] - p["entry"]) * p["qty"]
    return value

def open_pos(side, price, source):
    if len(state["positions"]) >= state["max_positions"]: return False
    margin = min(equity() * RISK, state["cash"])
    fee_in = margin * FEE
    qty = (margin - fee_in) / price
    if margin <= 1 or qty <= 0: return False
    state["cash"] -= margin
    state["positions"].append({
        "id": str(time.time_ns()), "symbol": state["symbol"], "side": side,
        "entry": price, "last": price, "qty": qty, "margin": margin,
        "fee_in": fee_in,
        "tp": price * (1 + TP if side == "BUY" else 1 - TP),
        "sl": price * (1 - SL if side == "BUY" else 1 + SL),
        "opened": now(), "source": source})
    return True

def close_pos(p, price, reason):
    d = 1 if p["side"] == "BUY" else -1
    gross = d * (price - p["entry"]) * p["qty"]
    fee_out = p["qty"] * price * FEE
    pnl = gross - p["fee_in"] - fee_out
    state["cash"] += p["margin"] + gross - fee_out
    state["realized_today"] += pnl
    log_trade({"time": now(), "symbol": p["symbol"], "side": p["side"],
               "entry": p["entry"], "exit": price, "reason": reason,
               "net_pnl": round(pnl, 6), "cash": round(state["cash"], 6)})
    state["positions"].remove(p)
    print(reason, p["side"], p["symbol"], "net P/L", round(pnl, 4), flush=True)

def loop():
    print("EPIC V10 PAPER ONLY - REAL TRADING DISABLED", flush=True)
    while True:
        try:
            with lock: sym = state["symbol"]
            data = candles(sym)
            side, price, candle_id = signal_for(data)
            bar = data[-2]
            high, low, close = float(bar[2]), float(bar[3]), float(bar[4])
            with lock:
                today = datetime.now(timezone.utc).date().isoformat()
                if state["day"] != today:
                    state["day"], state["realized_today"] = today, 0.0
                for p in list(state["positions"]):
                    p["last"] = close
                    if p["side"] == "BUY":
                        if low <= p["sl"]: close_pos(p, p["sl"], "STOP_LOSS")
                        elif high >= p["tp"]: close_pos(p, p["tp"], "TAKE_PROFIT")
                    else:
                        if high >= p["sl"]: close_pos(p, p["sl"], "STOP_LOSS")
                        elif low <= p["tp"]: close_pos(p, p["tp"], "TAKE_PROFIT")
                if state["armed"] and state["auto"] and side and candle_id != state["last_signal_candle"]:
                    # Only act once per completed candle; require a fresh signal direction.
                    if side != state["last_signal"]:
                        if open_pos(side, price, "AUTO"):
                            state["last_signal"] = side
                            state["last_signal_candle"] = candle_id
                            state["message"] = f"Automatic {side} position opened."
                    state["last_signal_candle"] = candle_id
                state["status"] = "ACTIVE" if state["armed"] and state["auto"] else "PAUSED"
                save()
            time.sleep(15)
        except Exception as e:
            with lock:
                state["status"], state["message"] = "DATA ERROR", str(e)
                save()
            print("Scan error:", e, flush=True)
            time.sleep(15)

@app.route("/")
def home():
    return """<!doctype html><meta name=viewport content='width=device-width,initial-scale=1'>
    <title>EPIC V10</title><style>body{font:16px Arial;background:#101820;color:#fff;padding:16px;max-width:650px;margin:auto}
    section{background:#20303c;padding:14px;border-radius:12px;margin:12px 0}input,select,button{width:100%;box-sizing:border-box;padding:12px;margin:5px 0;font-size:16px}
    button{background:#16885e;color:white;border:0;border-radius:8px}.stop{background:#a33}</style>
    <h2>EPIC V10 PAPER BOT</h2><b>REAL TRADING DISABLED</b>
    <section id=status>Loading...</section>
    <section><h3>Choose ONE pair</h3><input id=symbol value=BTCUSDT>
    <select id=limit><option>1</option><option>2</option><option selected>5</option><option>10</option></select>
    <button onclick=configure()>Save pair and position limit</button></section>
    <section><h3>Your initial instruction</h3><select id=side><option>BUY</option><option>SELL</option></select>
    <select id=count><option>1</option><option>2</option><option selected>3</option><option>5</option><option>10</option></select>
    <button onclick=arm()>Open initial positions and enable automatic signals</button>
    <button class=stop onclick=pauseBot()>Pause new entries</button>
    <button class=stop onclick=closeAll()>Close all paper positions</button></section>
    <section><h3>Open positions</h3><div id=positions></div></section><section><h3>Recent closed trades</h3><div id=trades></div></section>
    <script>
    async function post(path,obj){let r=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)});let j=await r.json();alert(j.message||j.error);refresh()}
    function configure(){post('/configure',{symbol:symbol.value.toUpperCase(),max_positions:+limit.value})}
    function arm(){post('/arm',{side:side.value,count:+count.value})}
    function pauseBot(){post('/pause',{})}
    function closeAll(){if(confirm('Close all paper positions?'))post('/close_all',{})}
    async function refresh(){try{let s=await(await fetch('/status')).json();status.innerHTML=s.status+'<br>Pair: '+s.symbol+'<br>Cash: $'+s.cash.toFixed(2)+' | Equity: $'+s.equity.toFixed(2)+'<br>Today realized: $'+s.realized_today.toFixed(2)+'<br>Positions: '+s.positions.length+'/'+s.max_positions+'<br>'+s.message;
    positions.innerHTML=s.positions.map(p=>p.side+' '+p.symbol+' entry '+p.entry.toFixed(5)+' TP '+p.tp.toFixed(5)+' SL '+p.sl.toFixed(5)).join('<br>')||'None';
    let t=await(await fetch('/trades')).json();trades.innerHTML=t.slice(-8).reverse().map(x=>x.side+' '+x.reason+' P/L $'+x.net_pnl).join('<br>')||'None';
    }catch(e){status.innerText=e}}refresh();setInterval(refresh,10000)</script>"""

@app.route("/status")
def status():
    with lock:
        return jsonify({"status": state["status"], "symbol": state["symbol"],
          "cash": state["cash"], "equity": equity(), "realized_today": state["realized_today"],
          "positions": state["positions"], "max_positions": state["max_positions"],
          "message": state["message"]})

@app.route("/configure", methods=["POST"])
def configure():
    d = request.get_json(silent=True) or {}
    sym, maximum = str(d.get("symbol", "")).upper().strip(), int(d.get("max_positions", 5))
    if not sym.endswith("USDT") or not sym[:-4].isalnum():
        return jsonify(error="Enter a valid USDT pair, e.g. BTCUSDT."), 400
    if not 1 <= maximum <= MAX_LIMIT: return jsonify(error="Limit must be 1 to 10."), 400
    with lock:
        if state["positions"]: return jsonify(error="Close positions before changing pair."), 400
        state.update(symbol=sym, max_positions=maximum, last_signal=None, last_signal_candle=None,
                     message=f"Selected {sym}. Ready for your initial instruction.")
        save()
    return jsonify(message=f"Selected {sym}.")

@app.route("/arm", methods=["POST"])
def arm():
    d = request.get_json(silent=True) or {}
    side, count = str(d.get("side", "")).upper(), int(d.get("count", 1))
    if side not in ("BUY", "SELL") or not 1 <= count <= MAX_LIMIT:
        return jsonify(error="Choose BUY or SELL and 1 to 10 positions."), 400
    with lock:
        if state["positions"]: return jsonify(error="Close existing positions first."), 400
        if count > state["max_positions"]: return jsonify(error="Count exceeds position limit."), 400
        try: price = float(candles(state["symbol"])[-2][4])
        except Exception as e: return jsonify(error=f"Market data error: {e}"), 503
        opened = sum(1 for _ in range(count) if open_pos(side, price, "MANUAL"))
        if not opened: return jsonify(error="Insufficient paper balance."), 400
        state.update(armed=True, auto=True, last_signal=side,
                     last_signal_candle=None,
                     message=f"Opened {opened} initial {side} paper positions; auto signals enabled.")
        save()
    return jsonify(message=state["message"])

@app.route("/pause", methods=["POST"])
def pause():
    with lock:
        state.update(armed=False, auto=False, message="New entries paused; open positions remain monitored.")
        save()
    return jsonify(message=state["message"])

@app.route("/close_all", methods=["POST"])
def close_all():
    with lock:
        if not state["positions"]: return jsonify(message="No open positions.")
        try: price = float(candles(state["symbol"])[-2][4])
        except Exception as e: return jsonify(error=f"Market data error: {e}"), 503
        for p in list(state["positions"]): close_pos(p, price, "MANUAL_CLOSE")
        state.update(armed=False, auto=False, message="All paper positions closed; bot paused.")
        save()
    return jsonify(message=state["message"])

@app.route("/trades")
def trades():
    return jsonify(read_json(TRADES_FILE, []))

@app.route("/health")
def health():
    return "OK"

if __name__ == "__main__":
    threading.Thread(target=loop, daemon=True).start()
    app.run(host="0.0.0.0", port=PORT, debug=False, use_reloader=False)
