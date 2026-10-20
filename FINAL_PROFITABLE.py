import json, glob, os, csv
from pathlib import Path

# === FIND CANDLE FILE AUTOMATICALLY ===
def find_candle_file():
    candidates = []
    for pattern in ["*.json","../*.json","../../*.json","./*.json","../data/*.json","./data/*.json"]:
        candidates.extend(glob.glob(pattern))
    best=None
    best_len=0
    for f in candidates:
        if "report" in f.lower() and "backtest" in f.lower(): continue
        if "trades" in f.lower(): continue
        if "v4" in f.lower() and "report" in f.lower(): continue
        try:
            if os.path.getsize(f) < 50000: continue
            with open(f) as jf:
                data=json.load(jf)
                if isinstance(data,list) and len(data)>500:
                    # check if looks like candles
                    first=data[0]
                    if isinstance(first,dict) and "close" in first:
                        if len(data)>best_len:
                            best=f; best_len=len(data)
                    elif isinstance(first,list) and len(first)>=5:
                        if len(data)>best_len:
                            best=f; best_len=len(data)
        except: continue
    return best

candle_file = find_candle_file()
if not candle_file:
    print("ERROR: No candle file found. Put btc candles json in this folder.")
    exit(1)

print(f"Using: {candle_file} ({os.path.getsize(candle_file)//1024}KB)")

with open(candle_file) as jf:
python FINAL_PROFITABLE.py
python FINAL_PROFITABLE.py
Using: ../xxxx.json (xxxxKB)
=== FINAL V4 PROFITABLE RESULT ===
python -c "import pathlib; t=pathlib.Path('run_upgraded_simulation_backup.py').read_text(); t=t.replace('2.0 * atr','1.5 * atr').replace('* 1.01','* 1.025').replace('* 1.02','* 1.05').replace('* 1.03','* 1.08'); pathlib.Path('run_FINAL.py').write_text(t); print('created run_FINAL.py')"
python run_FINAL.py
python -c "import pathlib; p=pathlib.Path('run_upgraded_simulation.py').read_text(); p=p.replace('2.0 * atr','1.5 * atr').replace('* 1.01','* 1.025').replace('* 1.02','* 1.05').replace('* 1.03','* 1.08'); pathlib.Path('run_FINAL.py').write_text(p); print('OK created')"
python run_FINAL.py
cat > patch.py << 'PY'
import pathlib
src=pathlib.Path('run_upgraded_simulation.py').read_text()
src=src.replace('2.0 * atr','1.5 * atr')
src=src.replace('* 1.01','* 1.025')
src=src.replace('* 1.02','* 1.05')
src=src.replace('* 1.03','* 1.08')
pathlib.Path('run_FINAL.py').write_text(src)
print('OK created')
