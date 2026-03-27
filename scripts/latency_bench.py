"""
End-to-end latency benchmark for Attack 1 and Attack 2.
Connects via WebSocket to capture per-phase timing, then fires POST /investigate.
"""
import asyncio
import json
import time
import websockets

API = "http://localhost:8000"
WS  = "ws://localhost:8000/ws"

SCENARIOS = [
    {"name": "Attack 1: Invoice Hidden Text Injection", "key": "phase1"},
    {"name": "Attack 2: Identity Spoofing",             "key": "phase2"},
]

async def run_attack(scenario_key: str, scenario_name: str):
    import aiohttp

    events = []
    t0 = time.perf_counter()

    # Connect WebSocket to capture event timestamps
    ws = await websockets.connect(WS)
    ws_task = asyncio.create_task(collect_events(ws, events, t0))

    # Fire the investigation
    async with aiohttp.ClientSession() as session:
        payload = {"scenario": scenario_key}
        req_start = time.perf_counter()
        async with session.post(f"{API}/api/investigate", json=payload) as resp:
            req_end = time.perf_counter()
            result = await resp.json()

    # Wait for remaining WS events (rule generation etc.)
    await asyncio.sleep(25)
    ws_task.cancel()
    try:
        await ws_task
    except asyncio.CancelledError:
        pass
    await ws.close()

    total = time.perf_counter() - t0

    # Print results
    print(f"\n{'='*70}")
    print(f"  {scenario_name}")
    print(f"{'='*70}")
    print(f"\n  HTTP Response time: {(req_end - req_start)*1000:.0f}ms")
    print(f"  HTTP Result: decision={result.get('decision')}, score={result.get('composite_score')}")
    print(f"\n  WebSocket Event Timeline:")
    print(f"  {'Event':<35} {'Time (ms)':>10}  {'Delta (ms)':>10}")
    print(f"  {'-'*35} {'-'*10}  {'-'*10}")

    prev = 0.0
    for evt in events:
        delta = evt['ms'] - prev
        print(f"  {evt['type']:<35} {evt['ms']:>10.0f}  {'+' + str(int(delta)):>10}")
        prev = evt['ms']

    print(f"\n  Total wall time (incl rule gen): {total*1000:.0f}ms")
    print(f"{'='*70}\n")

    return events, result


async def collect_events(ws, events, t0):
    try:
        async for msg in ws:
            data = json.loads(msg)
            evt_type = data.get("type", "unknown")
            elapsed = (time.perf_counter() - t0) * 1000
            events.append({"type": evt_type, "ms": elapsed, "data": data})
    except asyncio.CancelledError:
        pass


async def main():
    print("\nSentinel Latency Benchmark")
    print("=" * 70)

    all_results = []
    for scenario in SCENARIOS:
        events, result = await run_attack(scenario["key"], scenario["name"])
        all_results.append((scenario["name"], events, result))
        # Brief pause between attacks
        await asyncio.sleep(2)

    # Summary
    print("\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)
    for name, events, result in all_results:
        gate_evt = next((e for e in events if e["type"] == "gate_evaluated"), None)
        ep_evt = next((e for e in events if e["type"] == "episode_written"), None)
        rule_evt = next((e for e in events if e["type"] == "rule_deployed"), None)
        agent_evts = [e for e in events if e["type"] == "agent_completed"]
        first_agent = min((e["ms"] for e in agent_evts), default=0)
        last_agent = max((e["ms"] for e in agent_evts), default=0)

        print(f"\n  {name}")
        print(f"    Decision: {result.get('decision')} (score: {result.get('composite_score')})")
        if gate_evt:
            print(f"    Time to gate decision:    {gate_evt['ms']:.0f}ms")
        if ep_evt:
            print(f"    Time to episode written:  {ep_evt['ms']:.0f}ms")
            ae_latency = ep_evt['data'].get('data', {}).get('write_latency_ms')
            if ae_latency:
                print(f"    Aerospike write latency:  {ae_latency}ms")
        if agent_evts:
            print(f"    Sub-agent window:         {first_agent:.0f}ms -> {last_agent:.0f}ms ({last_agent - first_agent:.0f}ms spread)")
        if rule_evt:
            print(f"    Time to rule deployed:    {rule_evt['ms']:.0f}ms")


if __name__ == "__main__":
    asyncio.run(main())
