import json
import hmac
import hmac
import os
import subprocess
import sys
from pathlib import Path
from flask import Flask, jsonify, request, Response, request, Response

BASE = Path(__file__).resolve().parent
STATE = Path(os.environ.get("STATE_FILE", str(BASE / "epic_v9_paper_state.json")))
TRADES = Path(os.environ.get("TRADES_FILE", str(BASE / "epic_v9_paper_trades.jsonl")))
LOG = STATE.parent / "epic_v9_bot.log"
app = Flask(__name__)
worker = None

def prepare_existing_state():
    STATE.parent.mkdir(parents=True, exist_ok=True)
    if not STATE.exists():
        initial = os.environ.get("INITIAL_STATE_JSON", "")
        if not initial:
            return False
        parsed = json.loads(initial)
        if not isinstance(parsed, dict) or "position" not in parsed:
            raise ValueError("Initial state is invalid; refusing to start.")
        tmp = STATE.with_suffix(".tmp")
        tmp.write_text(json.dumps(parsed, indent=2))
        os.replace(tmp, STATE)

    if not TRADES.exists():
        initial_trades = os.environ.get("INITIAL_TRADES_JSONL", "")
        if initial_trades:
            TRADES.write_text(initial_trades.rstrip() + "\n")
        else:
            TRADES.touch()
    return True

def start_worker():
    global worker
    if not prepare_existing_state():
        return
    if worker is None or worker.poll() is not None:
        log_file = open(LOG, "a", buffering=1)
        worker = subprocess.Popen(
            [sys.executable, str(BASE / "epic_v9_paper.py")],
            cwd=str(BASE),
            env=os.environ.copy(),
            stdin=subprocess.DEVNULL,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )

start_worker()

def dashboard_auth_response():
    password = os.environ.get("DASHBOARD_PASSWORD", "")
    if not password:
        return Response("Dashboard password is not configured.", 503)
    auth = request.authorization
    if not auth or not hmac.compare_digest(auth.password or "", password):
        return Response(
            "Authentication required.", 401,
            {"WWW-Authenticate": 'Basic realm="EPIC V9 Paper Dashboard"'}
        )
    return None


def dashboard_auth_response():
    password = os.environ.get("DASHBOARD_PASSWORD", "")
    if not password:
        return Response("Dashboard password is not configured.", 503)
    auth = request.authorization
    if not auth or not hmac.compare_digest(auth.password or "", password):
        return Response(
            "Authentication required.", 401,
            {"WWW-Authenticate": 'Basic realm="EPIC V9 Paper Dashboard"'}
        )
    return None


@app.get("/")
def dashboard():
    denied = dashboard_auth_response()
    if denied is not None:
        return denied
    denied = dashboard_auth_response()
    if denied is not None:
        return denied
    if not STATE.exists():
        return (
            "<h2>EPIC V9 Paper Dashboard</h2>"
            "<p>Setup required: saved paper state has not been installed. "
            "The bot has not been started.</p>", 503
        )
    state = json.loads(STATE.read_text())
    pos = state.get("position")
    try:
        trades = [
            json.loads(line) for line in TRADES.read_text().splitlines()
            if line.strip()
        ]
    except (OSError, ValueError):
        trades = []
    position_html = (
        f"<p>Entry: ${pos['entry']:.2f}<br>"
        f"Take-profit: ${pos['target']:.2f}<br>"
        f"Stop-loss: ${pos['stop']:.2f}<br>"
        f"Bars held: {pos['bars_held']}</p>"
        if pos else "<p>No open position</p>"
    )
    rows = "".join(
        "<tr>" + "".join(
            f"<td>{t.get(k, '')}</td>"
            for k in ("time", "entry", "exit", "reason", "net_pnl", "balance")
        ) + "</tr>" for t in reversed(trades[-20:])
    )
    return f"""<!doctype html><html><head>
    <meta name="viewport" content="width=device-width,initial-scale=1">
    <meta http-equiv="refresh" content="20">
    <title>EPIC V9 Paper Dashboard</title>
    <style>body{{font:16px Arial;max-width:850px;margin:24px auto;padding:0 14px}}
    table{{border-collapse:collapse;width:100%;font-size:13px}}
    td,th{{border:1px solid #bbb;padding:6px;text-align:left;overflow-wrap:anywhere}}
    .safe{{font-weight:bold}}</style></head><body>
    <h2>EPIC V9 — Paper Dashboard</h2>
    <p class="safe">REAL TRADING DISABLED — PAPER ONLY</p>
    <p>Pair: BTCUSDT | Timeframe: 5m</p>
    <p>Paper cash: ${state.get('balance', 0):.2f}</p>
    {position_html}
    <p>Last processed candle: {state.get('last_candle')}</p>
    <h3>Recent completed trades</h3>
    <table><tr><th>Time</th><th>Entry</th><th>Exit</th>
    <th>Reason</th><th>Net P/L</th><th>Cash</th></tr>{rows}</table>
    <p>Refreshes every 20 seconds. No real-money orders are enabled.</p>
    </body></html>"""

@app.get("/health")
def health():
    return jsonify(
        status="ok",
        state_exists=STATE.exists(),
        paper_only=True,
        worker_running=worker is not None and worker.poll() is None
    )
