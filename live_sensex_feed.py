"""Live SENSEX feed for Kotak Neo API v2.

Reads BSE SENSEX index ticks and writes the latest tick to
data/sensex_live.json. Credentials must be supplied via environment variables.
This script is a data feed only; it does not place orders.
"""
import json
import os
import threading
from datetime import datetime, timezone

from neo_api_client import NeoAPI

OUT = "data/sensex_live.json"


def req(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def save_tick(message):
    if isinstance(message, str):
        try:
            message = json.loads(message)
        except json.JSONDecodeError:
            print("message_error: received non-JSON websocket message", flush=True)
            return
    if not isinstance(message, dict):
        return

    # Neo websocket payloads may wrap tick data in a list or nested object.
    if "iv" not in message:
        print("message_info: websocket message did not contain an 'iv' last-price field", flush=True)
        return

    tick = {
        "symbol": "SENSEX",
        "exchange": "bse_cm",
        "ltp": message.get("iv"),
        "previous_close": message.get("ic"),
        "exchange_time": message.get("tvalue"),
        "change": message.get("cng"),
        "change_pct": message.get("nc"),
        "received_at": datetime.now(timezone.utc).isoformat(),
        "raw": message,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    temp_path = OUT + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(tick, f, ensure_ascii=False, indent=2)
    os.replace(temp_path, OUT)
    print(json.dumps({k: tick[k] for k in ("symbol", "ltp", "received_at")}), flush=True)


def main():
    client = NeoAPI(
        environment="prod",
        access_token=None,
        neo_fin_key=None,
        consumer_key=req("KOTAK_CONSUMER_KEY"),
    )

    print("BALA: starting Kotak Neo TOTP login...", flush=True)
    client.totp_login(
        mobilenumber=req("KOTAK_MOBILE"),
        ucc=req("KOTAK_UCC"),
        totp=req("KOTAK_TOTP"),
    )
    client.totp_validate(mpin=req("KOTAK_MPIN"))
    print("BALA: login validation completed; registering websocket callbacks.", flush=True)

    def on_message(message):
        try:
            save_tick(message)
        except Exception as exc:
            print(f"message_error: {type(exc).__name__}: {exc}", flush=True)

    def on_error(message):
        print(f"websocket_error: {message}", flush=True)

    def on_open(message):
        print(f"websocket_open: {message}", flush=True)

    def on_close(message):
        print(f"websocket_close: {message}", flush=True)

    client.on_message = on_message
    client.on_error = on_error
    client.on_open = on_open
    client.on_close = on_close

    client.subscribe(
        instrument_tokens=[{"instrument_token": "SENSEX", "exchange_segment": "bse_cm"}],
        isIndex=True,
        isDepth=False,
    )
    print("BALA: subscribe request sent for SENSEX. Waiting for websocket ticks...", flush=True)

    # GitHub Actions has no interactive stdin. input() raises EOFError there and
    # terminates the process immediately; block here until the runner stops the job.
    try:
        threading.Event().wait()
    except KeyboardInterrupt:
        print("BALA: stopped by user.", flush=True)


if __name__ == "__main__":
    main()
