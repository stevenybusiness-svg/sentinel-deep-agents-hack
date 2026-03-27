"""Rule store — MEM-02, MEM-05.

Reads and writes generated scoring rules to the Aerospike sentinel.rules set.
write_rule() measures and returns write latency in ms for dashboard display.
Rules carry full provenance (episode_ids, prediction_errors, version, fire_count).
"""
import json
import time

from sentinel.memory.aerospike_client import AerospikeClient

RULES_SET = "rules"


async def write_rule(
    rule_id: str,
    source: str,
    episode_ids: list[str],
    prediction_errors: dict,
    version: int,
    client: AerospikeClient,
) -> float:
    """Write a generated scoring rule to Aerospike sentinel.rules set. Returns write latency in ms (MEM-05).

    Args:
        rule_id: Unique identifier for this rule (e.g. "rule_001").
        source: Python source code for the scoring function.
        episode_ids: List of episode IDs that produced this rule.
        prediction_errors: Dict of prediction errors from the source incidents.
        version: Rule version number (incremented on each evolution).
        client: AerospikeClient instance.

    Returns:
        Write latency in milliseconds, rounded to 2 decimal places.
    """
    start = time.perf_counter()
    # Aerospike bin names MUST be <= 15 characters (BinNameError otherwise)
    bins = {
        "rule_id": rule_id,
        "source": source,
        "episode_ids": json.dumps(episode_ids),
        "pred_errors": json.dumps(prediction_errors),
        "timestamp": int(time.time() * 1000),
        "version": version,
        "fire_count": 0,
    }
    await client.put(RULES_SET, rule_id, bins)
    latency_ms = (time.perf_counter() - start) * 1000
    await _update_rules_index(rule_id, client)
    return round(latency_ms, 2)


async def _update_rules_index(rule_id: str, client: AerospikeClient) -> None:
    """Maintain an index of rule IDs for load_all_rules.

    Reads __rules_index__ key from RULES_SET, appends rule_id if not present,
    and writes back. Consistent with __episode_index__ pattern.
    """
    try:
        index_bins = await client.get(RULES_SET, "__rules_index__")
        rule_ids = json.loads(index_bins.get("rule_ids", "[]"))
    except Exception:
        rule_ids = []
    if rule_id not in rule_ids:
        rule_ids.append(rule_id)
    await client.put(RULES_SET, "__rules_index__", {"rule_ids": json.dumps(rule_ids)})


async def load_all_rules(client: AerospikeClient) -> list[dict]:
    """Load all generated rules from Aerospike at startup (MEM-02).

    Reads __rules_index__ to discover all stored rule IDs, then fetches
    each rule record and deserializes JSON bins.

    Returns:
        List of rule dicts with keys: rule_id, source, episode_ids (list),
        prediction_errors (dict), version, fire_count, timestamp.
        Returns empty list on any error (graceful degradation for startup).
    """
    try:
        index_bins = await client.get(RULES_SET, "__rules_index__")
        rule_ids = json.loads(index_bins.get("rule_ids", "[]"))
    except Exception:
        return []

    rules = []
    for rid in rule_ids:
        try:
            bins = await client.get(RULES_SET, rid)
            # Deserialize JSON-encoded bins
            bins["episode_ids"] = json.loads(bins.get("episode_ids", "[]"))
            bins["prediction_errors"] = json.loads(bins.get("pred_errors", "{}"))
            rules.append(bins)
        except Exception:
            continue
    return rules


async def increment_fire_count(rule_id: str, client: AerospikeClient) -> None:
    """Atomically increment fire_count for a rule (telemetry).

    Read-modify-write pattern. Errors are silently swallowed — fire_count
    is telemetry only and must never block the enforcement path.

    Args:
        rule_id: Rule to increment.
        client: AerospikeClient instance.
    """
    try:
        bins = await client.get(RULES_SET, rule_id)
        bins["fire_count"] = bins.get("fire_count", 0) + 1
        await client.put(RULES_SET, rule_id, bins)
    except Exception:
        pass  # fire_count is telemetry — never block on failure


async def next_rule_id(client: AerospikeClient) -> str:
    """Return the next sequential rule ID (e.g. "rule_001", "rule_002").

    Uses a counter record at __rule_counter__ key in RULES_SET.
    Thread-safe at the Aerospike level; adequate for single-node demo scale.

    Args:
        client: AerospikeClient instance.

    Returns:
        Rule ID string in format "rule_NNN" (zero-padded to 3 digits).
    """
    try:
        counter_bins = await client.get(RULES_SET, "__rule_counter__")
        n = counter_bins.get("count", 0) + 1
    except Exception:
        n = 1
    await client.put(RULES_SET, "__rule_counter__", {"count": n})
    return f"rule_{n:03d}"
