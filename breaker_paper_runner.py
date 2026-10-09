"""Manual/scheduled paper-only 15M Breaker monitor for SENSEX/NIFTY.

Uses Yahoo Finance index candles for signal development. Paper P&L is in index points,
NOT option-premium rupees. No Kotak login and no order placement are used.
"""
import json, os, time, urllib.parse, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from breaker_strategy import evaluate, paper_step

ROOT = Path(__file__).resolve().parent
STATE_PATH = ROOT / "data" / "breaker_paper_state.json"
SYMBOLS = {"SENSEX": "^BSESN", "NIFTY": "^NSEI"}
IST = timezone(timedelta(hours=5, minutes=30))


def candles(symbol, interval, range_="5d"):
    query = urllib.parse.urlencode({"range": range_, "interval": interval})
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(symbol, safe='')}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.loads(response.read().decode("utf-8"))
    result = payload["chart"]["result"][0]
    ts = result["timestamp"]
    q = result["indicators"]["quote"][0]
    rows = []
    for i, stamp in enumerate(ts):
        if any(q[k][i] is None for k in ("open", "high", "low", "close")):
            continue
        rows.append({"time": stamp, "open": float(q["open"][i]), "high": float(q["high"][i]),
                     "low": float(q["low"][i]), "close": float(q["close"][i]),
                     "volume": float((q.get("volume") or [0] * len(ts))[i] or 0)})
    # Drop the latest bar because it may still be forming.
    return rows[:-1]


def main():
    now = datetime.now(IST)
    report = {"timestamp": int(time.time()), "mode": "PAPER_ONLY", "live_orders": False,
              "data_source": "Yahoo Finance chart API", "pnl_unit": "index points",
              "note": "This is not option-premium P&L.", "symbols": {}}
    if now.weekday() >= 5 or not (now.replace(hour=9, minute=15, second=0, microsecond=0)
                                  <= now <= now.replace(hour=15, minute=30, second=0, microsecond=0)):
        report["status"] = "OUTSIDE_MARKET_HOURS"
        print(json.dumps(report, indent=2))
        return
    state = json.loads(STATE_PATH.read_text()) if STATE_PATH.exists() else {
        "mode": "PAPER_ONLY", "symbols": {}}
    for name, ticker in SYMBOLS.items():
        try:
            c1, c5, c15 = candles(ticker, "1m"), candles(ticker, "5m"), candles(ticker, "15m")
            signal = evaluate(c15, c5, c1)
            signal["timestamp"] = int(time.time())
            symbol_state = state.setdefault("symbols", {}).setdefault(
                name, {"mode": "PAPER_ONLY", "open_trade": None, "trades": []})
            paper_step(symbol_state, signal, c1[-1]["close"])
            report["symbols"][name] = {"price": c1[-1]["close"], "signal": signal,
                                       "open_trade": symbol_state.get("open_trade"),
                                       "closed_trades": len(symbol_state.get("trades", [])),
                                       "realized_pnl_points": sum(t.get("pnl_points", 0)
                                                                   for t in symbol_state.get("trades", []))}
        except Exception as exc:
            report["symbols"][name] = {"state": "DATA WAIT",
                                       "error": f"{type(exc).__name__}: {exc}"}
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2))
    report["state_file"] = str(STATE_PATH)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
