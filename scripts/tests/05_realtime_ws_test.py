#!/usr/bin/env python3
"""Simple realtime websocket test using websockets library.

This script connects to the realtime websocket endpoint (wss://realtime.${BASE_DOMAIN}/socket)
and attempts to perform a minimal subscribe/receive. It's intentionally lightweight and prints
what it receives. It requires `websockets` (pip install websockets) and a running stack.

Usage:
  python3 scripts/tests/05_realtime_ws_test.py
"""
import asyncio
import os
import json

import websockets

BASE = os.environ.get("BASE_DOMAIN") or "localhost"
REALTIME_HOST = os.environ.get("REALTIME_HOSTNAME") or f"realtime.{BASE}"

URI = f"wss://{REALTIME_HOST}/socket"

async def main():
    print(f"Connecting to {URI}")
    try:
        async with websockets.connect(URI, ping_interval=20) as ws:
            print("Connected — sending a basic ping message")
            # Raw protocol depends on Supabase Realtime; for a basic smoke test do handshake
            await ws.send(json.dumps({"type": "ping"}))
            msg = await asyncio.wait_for(ws.recv(), timeout=10)
            print("Received:", msg)
    except Exception as e:
        print("Realtime WS test failed:", e)
        raise

if __name__ == '__main__':
    asyncio.run(main())
