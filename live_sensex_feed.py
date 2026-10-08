"""Live SENSEX feed for the Neo API v2 used by this repository.

Reads BSE SENSEX index ticks and writes the latest tick to data/sensex_live.json.
Credentials are supplied only through environment variables / GitHub Actions secrets.
No orders are placed by this process.
"""
import json
import os
from datetime import datetime, timezone
from neo_api_client import NeoAPI

def req(name):
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value

OUT = "data/sensex_live.json"

def save_tick(message):
    if not isinstance(message, dict):
        return
    if "iv" not in message:
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
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(tick, f, ensure_ascii=False, indent=2)
    print(json.dumps(tick, ensure_ascii=False))

client = NeoAPI(
    environment="prod",
    access_token=None,
    neo_fin_key=None,
    consumer_key=req("KOTAK_CONSUMER_KEY"),
)
client.totp_login(
    mobilenumber=req("KOTAK_MOBILE"),
    ucc=req("KOTAK_UCC"),
    totp=req("KOTAK_TOTP"),
)
client.totp_validate(mpin=req("KOTAK_MPIN"))

def on_message(message):
    try:
        if isinstance(message, str):
            message = json.loads(message)
        save_tick(message)
    except Exception as exc:
        print(f"message_error: {exc}")

def on_error(message):
    print(f"websocket_error: {message}")

def on_open(message):
    print(f"websocket_open: {message}")

def on_close(message):
    print(f"websocket_close: {message}")

client.on_message = on_message
client.on_error = on_error
client.on_open = on_open
client.on_close = on_close

client.subscribe(
    instrument_tokens=[{"instrument_token": "SENSEX", "exchange_segment": "bse_cm"}],
    isIndex=True,
    isDepth=False,
)

print("BALA SENSEX live feed started.")
input("Press Enter to stop...")
