"""
BALA Live SENSEX Feed
Uses Kotak Neo modern SFeed WebSocket API.
Required environment variables:
KOTAK_CONSUMER_KEY, KOTAK_MOBILE, KOTAK_UCC, KOTAK_TOTP, KOTAK_MPIN
Install: pip install -U "kotakneoapi>=3.0.1"
Run: python live_sensex_feed.py
This module only reads market data; it does not place orders.
"""

import asyncio
import json
import os
from datetime import datetime, timezone

from neo_api_client import NeoAPI
from neo_api_client.websocket.feed import WsToken, SFeedIndex

def required(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Missing environment variable: {name}")
    return value

async def main() -> None:
    client = NeoAPI(consumer_key=required("KOTAK_CONSUMER_KEY"), environment="prod")
    client.totp_login(mobile_number=required("KOTAK_MOBILE"), ucc=required("KOTAK_UCC"), totp=required("KOTAK_TOTP"))
    client.totp_validate(mpin=required("KOTAK_MPIN"))

    async with client.create_websocket() as ws:
        await ws.subscribe_index([WsToken("bse_cm", "SENSEX")])
        print("BALA SENSEX live feed connected.")
        async for message in ws:
            if isinstance(message, SFeedIndex):
                data = message.model_dump()
                ltp = data.get("last_traded_price")
                if ltp is None:
                    ltp = data.get("iv")
                event = {
                    "symbol": "SENSEX",
                    "exchange": "BSE",
                    "ltp": ltp,
                    "previous_close": data.get("close_price", data.get("ic")),
                    "exchange_time": data.get("last_update_time", data.get("tvalue")),
                    "received_at": datetime.now(timezone.utc).isoformat(),
                }
                print(json.dumps(event, default=str))

if __name__ == "__main__":
    asyncio.run(main())
