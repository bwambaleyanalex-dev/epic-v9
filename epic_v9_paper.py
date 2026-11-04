import json
import time
import os
import urllib.request
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
    with urllib.request.urlopen(req, timeout=10) as response:
        return json.loads(response.read())

def ema(values, period=200):
    alpha = 2 / (period + 1)
    result = values[0]
    for value in values[1:]:
        result += alpha * (value - result)
    return result

def now_text():
    return datetime.now(timezone.utc).isoformat()

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return None

def log_trade(trade):
    trades = []
    if os.path.exists(TRADES_FILE):
        try:
            with open(TRADES_FILE) as f:
                trades = json.load(f)
        except:
            trades = []
    trades.append(trade)
    with open(TRADES_FILE, "w") as f:
        json.dump(trades[-100:], f)

# --- TRADING LOOP (your exact V9 logic) ---
def run_bot():
    print("EPIC V9 PAPER TEST - REAL TRADING DISABLED - PAPER ONLY", flush=True)
    while True:
        try:
            candles = get_candles()
            closed = candles[-2]
            candle_time = int(closed[0])

            # Load state
            state = load_state()
            if not state:
                state = {
                    "balance": START_BALANCE,
                    "position": None,
                    "last_candle": int(candles[-2][0]),
                    "last_exit_index": -100000,
                    "bar_index": 0,
                    "starting_balance": START_BALANCE
                }
                save_state(state)
                print(f"Paper cash: ${state['balance']:.2f}", flush=True)

            if candle_time == state["last_candle"]:
                time.sleep(15)
                continue

            closes = [float(c[4]) for c in candles]
            high = float(closed[2])
            low = float(closed[3])
            price = float(closed[4])
            trend_ema = ema(closes[-200:])
            state["bar_index"] += 1
            index = state["bar_index"]
            position = state["position"]
            stamp = datetime.fromtimestamp(candle_time / 1000, timezone.utc).isoformat()

            # EXIT LOGIC
            if position:
                position["bars_held"] += 1
                entry = position["entry"]
                reason = None
                exit_price = None
                if low <= position["stop"]:
                    exit_price = position["stop"]
                    reason = "STOP_LOSS"
                elif high >= position["target"]:
                    exit_price = position["target"]
                    reason = "TAKE_PROFIT"
                elif position["bars_held"] >= MAX_HOLD_BARS:
                    exit_price = price
                    reason = "MAX_HOLD"

                if reason:
                    gross = position["qty"] * exit_price
                    exit_fee = gross * FEE_RATE
                    net = gross - exit_fee
                    state["balance"] += net
                    pnl = net - position["entry_cost"]
                    trade = {
                        "time": stamp,
                        "symbol": SYMBOL,
                        "entry": entry,
                        "exit": exit_price,
                        "qty": position["qty"],
                        "reason": reason,
                        "pnl": round(pnl, 6),
                        "balance": round(state["balance"], 6)
                    }
                    log_trade(trade)
                    print(f"{reason}: exit ${exit_price:.2f} net P/L ${pnl:.4f} | bal ${state['balance']:.2f}", flush=True)
                    state["position"] = None
                    state["last_exit_index"] = index

            # ENTRY LOGIC - EMA200 Trend
            elif (
                price > trend_ema
                and index - state["last_exit_index"] > COOLDOWN_BARS
                and state["balance"] > 1
            ):
                entry = price
                entry_fee = state["balance"] * FEE_RATE
                spend = state["balance"] - entry_fee
                qty = spend / entry
                state["position"] = {
                    "entry": entry,
                    "qty": qty,
                    "entry_cost": state["balance"],
                    "target": entry * (1 + TAKE_PROFIT),
                    "stop": entry * (1 - STOP_LOSS),
                    "bars_held": 0
                }
                state["balance"] = 0.0
                print(f"ENTRY: ${entry:.2f} | EMA200 ${trend_ema:.2f} | TP ${entry*1.02:.2f} | SL ${entry*0.95:.2f}", flush=True)

            state["last_candle"] = candle_time
            save_state(state)
            time.sleep(30)

        except Exception as e:
            print(f"Loop error: {e}", flush=True)
            time.sleep(15)

# --- WEBSITE FOR RENDER ---
app = Flask(__name__)

@app.route("/")
def dashboard():
    state = load_state()
    if not state:
        return "<h1>EPIC V9 Starting... wait 60s and refresh</h1>"
    pos = state.get("position")
    pos_text = f"IN POSITION Entry ${pos['entry']:.2f} TP ${pos['target']:.2f} SL ${pos['stop']:.2f}" if pos else "FLAT - Waiting for EMA200 signal"
    html = f"""
    <h1>EPIC V9 - Live Market Paper Test</h1>
    <p><b>REAL TRADING DISABLED — PAPER ONLY</b></p>
    <p>Pair: {SYMBOL} | Timeframe: {INTERVAL} | Trend: EMA200 TP 2% SL 5%</p>
    <p>Paper cash: ${state.get('balance',0):.2f}</p>
    <p>Position: {pos_text}</p>
    <p>Last processed candle: {state.get('last_candle')} | Bar: {state.get('bar_index')}</p>
    <p>Starting: ${state.get('starting_balance')} | Updated: {now_text()}</p>
    <p><a href='/trades'>View Trades JSON</a> | <a href='/health'>Health</a></p>
    <meta http-equiv="refresh" content="30">
    """
    return html

@app.route("/health")
def health():
    return "OK"

@app.route("/state")
@app.route("/trades")
def api():
    try:
        with open(TRADES_FILE) as f:
            trades = json.load(f)
        return jsonify(trades)
    except:
        return jsonify([])

# Start bot thread when gunicorn loads the app
thread = threading.Thread(target=run_bot, daemon=True)
thread.start()
