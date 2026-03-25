"""Trust store — MEM-03.

Reads and writes behavioral baselines to the Aerospike sentinel.trust set.
Baselines are loaded at investigation start for the prediction step.
Falls back to empty dict if not yet stored (first-run safety).
"""
import json
import time

from sentinel.memory.aerospike_client import AerospikeClient

TRUST_SET = "trust"


async def store_baselines(baselines: dict, client: AerospikeClient) -> float:
    """Store behavioral baselines to Aerospike sentinel.trust set. Returns write latency ms (MEM-03)."""
    start = time.perf_counter()
    bins = {
        "baselines": json.dumps(baselines),
        "updated_at": int(time.time() * 1000),
    }
    await client.put(TRUST_SET, "behavioral_baselines", bins)
    return round((time.perf_counter() - start) * 1000, 2)


async def load_baselines(client: AerospikeClient) -> dict:
    """Load behavioral baselines from Aerospike sentinel.trust set (MEM-03).

    Falls back to empty dict if not yet stored (first-run or connection error).
    """
    try:
        bins = await client.get(TRUST_SET, "behavioral_baselines")
        return json.loads(bins.get("baselines", "{}"))
    except Exception:
        return {}


async def store_prediction_history(
    episode_id: str,
    prediction_errors: dict,
    client: AerospikeClient,
) -> None:
    """Store prediction history entry for a specific episode.

    Persists the prediction errors for this episode so Phase 3 rule generation
    can reference prior prediction failures when generating composite scoring functions.
    """
    bins = {
        "episode_id": episode_id,
        "prediction_errors": json.dumps(prediction_errors),
        "timestamp": int(time.time() * 1000),
    }
    await client.put(TRUST_SET, f"prediction_{episode_id}", bins)
