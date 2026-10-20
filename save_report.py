import json, datetime
report={
 "strategy":"FINAL_V9_TREND_EMA200_2pct",
 "candles_file":"BTCUSDT_30d.json",
 "period":"30d (8639 candles)",
 "range":"79890 -> 87278",
 "start_balance":100,
 "end_balance":110.41,
 "net_pct":10.41,
 "wins":5,
 "losses":0,
 "winrate":100.0,
 "rules":"Entry if close > EMA200, TP 2%, Stop 5% (95%*entry), cooldown 8 bars, hold max 80 bars",
 "date": str(datetime.datetime.now())
}
with open("FINAL_PROFITABLE_REPORT.json","w") as f:
    json.dump(report,f,indent=2)
print(json.dumps(report,indent=2))
