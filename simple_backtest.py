import json, os, glob
# simple backtest without pandas
files = glob.glob("*cache*.json") + glob.glob("*.json")
print("Files found:", files[:5])
# try to load backtest_staged report if exists
if os.path.exists("backtest_staged_20261019_report.json"):
    with open("backtest_staged_20261019_report.json") as f:
        data=json.load(f)
    print("\n--- ORIGINAL STRATEGY ---")
    print(f"Return: {data.get('total_return_percent', 'N/A')}%")
    print(f"Win rate: {data.get('win_rate_percent', 0):.1f}%")
    print(f"Trades: {data.get('total_trades', 0)}")
    print("\nOriginal loses -17%. Upgraded file needs pandas which fails on phone.")
    print("\nSOLUTION: Edit strategy_upgraded.py to remove pandas line.")
else:
    print("no report found")
