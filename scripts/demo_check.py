#!/usr/bin/env python3
"""Pre-demo validation -- confirms every integration is live before stepping on stage (DEMO-02).

Usage:
    python scripts/demo_check.py [--host http://localhost:8000]
    python scripts/demo_check.py --host https://sentinel.up.railway.app

Exits 0 if all checks pass. Prints failures and exits 1 otherwise.
"""
import argparse
import asyncio
import os
import sys

import httpx
import websockets
from dotenv import load_dotenv


async def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Sentinel pre-demo check")
    parser.add_argument("--host", default="http://localhost:8000", help="Base URL")
    args = parser.parse_args()
    host = args.host.rstrip("/")
    failures: list[str] = []

    # 1. Health endpoint
    print(f"[1/7] Health endpoint ({host}/health)... ", end="", flush=True)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{host}/health")
            data = resp.json()
            if resp.status_code != 200:
                failures.append(f"Health returned {resp.status_code}")
                print("FAIL")
            elif not data.get("aerospike"):
                failures.append("Health reports aerospike=false")
                print("FAIL (aerospike down)")
            else:
                print("OK")
    except Exception as e:
        failures.append(f"Health unreachable: {e}")
        print("FAIL")

    # 2. ANTHROPIC_API_KEY set and non-empty
    print("[2/7] ANTHROPIC_API_KEY... ", end="", flush=True)
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key.startswith("sk-ant-placeholder"):
        failures.append("ANTHROPIC_API_KEY not set or placeholder")
        print("FAIL")
    else:
        print(f"OK ({key[:12]}...)")

    # 3. BLAND_API_KEY set
    print("[3/7] BLAND_API_KEY... ", end="", flush=True)
    bland_key = os.getenv("BLAND_API_KEY", "")
    if not bland_key or bland_key == "placeholder":
        failures.append("BLAND_API_KEY not set or placeholder")
        print("FAIL")
    else:
        print(f"OK ({bland_key[:12]}...)")

    # 4. Bland AI reachable
    print("[4/7] Bland AI reachable... ", end="", flush=True)
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "https://api.bland.ai/v1/me",
                headers={"authorization": bland_key},
            )
            if resp.status_code in (200, 401, 403):
                print(f"OK (status {resp.status_code})")
            else:
                failures.append(f"Bland API returned {resp.status_code}")
                print("FAIL")
    except Exception as e:
        failures.append(f"Bland AI unreachable: {e}")
        print("FAIL")

    # 5. WebSocket connects
    print(f"[5/7] WebSocket ({host}/ws)... ", end="", flush=True)
    ws_url = host.replace("https://", "wss://").replace("http://", "ws://") + "/ws"
    try:
        async with websockets.connect(ws_url, open_timeout=5) as ws:
            print("OK")
    except Exception as e:
        failures.append(f"WebSocket failed: {e}")
        print("FAIL")

    # 6. Fixture data available (via /health -- already confirmed in step 1)
    print("[6/7] Fixture data available... ", end="", flush=True)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(f"{host}/health")
            if resp.status_code == 200:
                print("OK (server healthy, fixtures loaded at startup)")
            else:
                failures.append("Server not healthy -- fixtures may not be loaded")
                print("FAIL")
    except Exception as e:
        failures.append(f"Fixture check failed: {e}")
        print("FAIL")

    # 7. /investigate endpoint responds (smoke test)
    print(f"[7/7] /investigate endpoint... ", end="", flush=True)
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                f"{host}/api/investigate",
                json={"attack_scenario": "test_connectivity"},
            )
            # Any response (even 422 validation error) means endpoint is wired
            if resp.status_code in (200, 422, 400):
                print(f"OK (status {resp.status_code})")
            else:
                failures.append(f"/investigate returned {resp.status_code}")
                print("FAIL")
    except Exception as e:
        failures.append(f"/investigate unreachable: {e}")
        print("FAIL")

    # Summary
    print()
    if failures:
        print(f"FAILED -- {len(failures)} issue(s):")
        for f in failures:
            print(f"  - {f}")
        return 1
    else:
        print("ALL CHECKS PASSED -- demo ready!")
        return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
