#!/usr/bin/env python3
"""Timed dry-run of the full Sentinel demo arc (DEMO-04).

Usage:
    python scripts/dry_run.py [--host http://localhost:8000]

Runs: Reset -> Attack 1 -> Confirm -> Attack 2 -> Confirm -> Report timing.
Target: full arc < 180 seconds (3 minutes).
"""
import argparse
import asyncio
import sys
import time

import httpx


# ---------------------------------------------------------------------------
# Demo payloads — must match InvestigateRequest and ConfirmRequest schemas
# ---------------------------------------------------------------------------

PHASE1_PAYLOAD = {
    "scenario": "phase1",
    "payment_request": {
        "amount": 75000,
        "beneficiary": "Meridian Logistics",
        "sender": "TechCorp International",
        "reference": "INV-2024-1847",
        "description": "Consulting services Q4 — see attached invoice",
    },
}

PHASE2_PAYLOAD = {
    "scenario": "phase2",
    "payment_request": {
        "amount": 47250,
        "beneficiary": "Meridian Logistics",
        "sender": "TechCorp International",
        "reference": "WIRE-2024-0093",
        "description": "Pre-cleared wire transfer per KYC authorization",
    },
}


async def main() -> int:
    parser = argparse.ArgumentParser(description="Sentinel demo dry run")
    parser.add_argument("--host", default="http://localhost:8000", help="Base URL")
    args = parser.parse_args()
    host = args.host.rstrip("/")

    timeout = httpx.Timeout(120.0, connect=10.0)

    print("=" * 60)
    print("SENTINEL DEMO DRY RUN")
    print(f"Target: {host}")
    print("=" * 60)

    t_start = time.monotonic()

    async with httpx.AsyncClient(timeout=timeout) as client:
        # Step 0: Health check
        print(f"\n[{_elapsed(t_start)}] Checking health...")
        try:
            resp = await client.get(f"{host}/health")
            health = resp.json()
            print(f"  Health: {health}")
            if not health.get("status") == "ok":
                print("  WARN: Server not fully healthy, continuing anyway")
        except Exception as e:
            print(f"  FAIL: Server unreachable -- {e}")
            return 1

        # Step 1: Attack 1 -- Hidden text invoice (phase1)
        print(f"\n[{_elapsed(t_start)}] ATTACK 1: phase1 (hidden text invoice)...")
        try:
            resp = await client.post(
                f"{host}/api/investigate",
                json=PHASE1_PAYLOAD,
            )
            if resp.status_code != 200:
                print(f"  FAIL: /api/investigate returned {resp.status_code}: {resp.text[:200]}")
                return 1
            result1 = resp.json()
            episode_id_1 = result1.get("episode_id")
            decision1 = result1.get("decision")
            score1 = result1.get("composite_score")
            print(f"  Result: decision={decision1}, score={score1}, episode_id={episode_id_1}")
        except Exception as e:
            print(f"  FAIL: Attack 1 failed -- {e}")
            return 1

        # Step 2: Confirm Attack 1 (triggers rule generation)
        print(f"\n[{_elapsed(t_start)}] CONFIRM Attack 1 (episode {episode_id_1})...")
        try:
            resp = await client.post(
                f"{host}/api/confirm",
                json={
                    "episode_id": episode_id_1,
                    "attack_type": "prompt_injection_hidden_text",
                },
            )
            if resp.status_code not in (200, 202):
                print(f"  FAIL: /api/confirm returned {resp.status_code}: {resp.text[:200]}")
                return 1
            confirm1 = resp.json()
            print(f"  Result: {confirm1}")
        except Exception as e:
            print(f"  FAIL: Confirm 1 failed -- {e}")
            return 1

        # Step 2b: Wait for rule generation to complete (background task)
        print(f"\n[{_elapsed(t_start)}] Waiting for rule generation (15s)...")
        await asyncio.sleep(15)

        # Step 3: Attack 2 -- Identity spoofing (phase2)
        print(f"\n[{_elapsed(t_start)}] ATTACK 2: phase2 (identity spoofing)...")
        try:
            resp = await client.post(
                f"{host}/api/investigate",
                json=PHASE2_PAYLOAD,
            )
            if resp.status_code != 200:
                print(f"  FAIL: /api/investigate returned {resp.status_code}: {resp.text[:200]}")
                return 1
            result2 = resp.json()
            episode_id_2 = result2.get("episode_id")
            decision2 = result2.get("decision")
            score2 = result2.get("composite_score")
            print(f"  Result: decision={decision2}, score={score2}, episode_id={episode_id_2}")
        except Exception as e:
            print(f"  FAIL: Attack 2 failed -- {e}")
            return 1

        # Step 4: Confirm Attack 2 (triggers rule evolution)
        print(f"\n[{_elapsed(t_start)}] CONFIRM Attack 2 (episode {episode_id_2})...")
        try:
            resp = await client.post(
                f"{host}/api/confirm",
                json={
                    "episode_id": episode_id_2,
                    "attack_type": "identity_spoofing",
                },
            )
            if resp.status_code not in (200, 202):
                print(f"  FAIL: /api/confirm returned {resp.status_code}: {resp.text[:200]}")
                return 1
            confirm2 = resp.json()
            print(f"  Result: {confirm2}")
        except Exception as e:
            print(f"  FAIL: Confirm 2 failed -- {e}")
            return 1

    # Summary
    elapsed = time.monotonic() - t_start
    print("\n" + "=" * 60)
    print(f"COMPLETED in {elapsed:.1f}s")
    if elapsed < 180:
        print("PASS -- under 3 minute target")
        return 0
    elif elapsed < 240:
        print("WARN -- over 3 minutes but under 4")
        return 0
    else:
        print("FAIL -- over 4 minutes, pipeline too slow for demo")
        return 1


def _elapsed(t_start: float) -> str:
    """Format elapsed time since t_start."""
    s = time.monotonic() - t_start
    return f"{s:6.1f}s"


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
