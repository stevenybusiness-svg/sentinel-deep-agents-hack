"""Episode store — MEM-01 and MEM-04.

Reads and writes Episode records to the Aerospike sentinel.episodes set.
write_episode() measures and returns write latency in ms for dashboard display.
get_recent_episodes() provides supervisor context injection at investigation start.
"""
import json
import time

from sentinel.memory.aerospike_client import AerospikeClient
from sentinel.schemas.episode import Episode

EPISODES_SET = "episodes"


async def write_episode(episode: Episode, client: AerospikeClient) -> float:
    """Write episode to Aerospike sentinel.episodes set. Returns write latency in ms (MEM-01)."""
    start = time.perf_counter()
    bins = {
        "episode_id": episode.id,
        "timestamp": int(episode.timestamp.timestamp() * 1000),
        "action_request": json.dumps(episode.action_request),
        "gate_decision": episode.gate_decision,
        "gate_rationale": episode.gate_rationale,
        "rules_fired": json.dumps(episode.rules_fired),
        "generated_rules_fired": json.dumps(episode.generated_rules_fired),
        "verdict_board": json.dumps(episode.verdict_board.model_dump()),
        "agent_verdicts": json.dumps([v.model_dump() for v in episode.agent_verdicts]),
        "prediction_report": json.dumps(episode.prediction_report) if episode.prediction_report else "null",
        "operator_confirmation": episode.operator_confirmation or "",
        "attack_type": episode.attack_type or "",
    }
    await client.put(EPISODES_SET, episode.id, bins)
    latency_ms = (time.perf_counter() - start) * 1000
    await _update_episode_index(episode.id, client)
    return round(latency_ms, 2)


async def get_episode(episode_id: str, client: AerospikeClient) -> dict:
    """Read a single episode from Aerospike by ID."""
    bins = await client.get(EPISODES_SET, episode_id)
    # Deserialize JSON fields
    bins["action_request"] = json.loads(bins.get("action_request", "{}"))
    bins["rules_fired"] = json.loads(bins.get("rules_fired", "[]"))
    bins["generated_rules_fired"] = json.loads(bins.get("generated_rules_fired", "[]"))
    bins["verdict_board"] = json.loads(bins.get("verdict_board", "{}"))
    bins["agent_verdicts"] = json.loads(bins.get("agent_verdicts", "[]"))
    bins["prediction_report"] = json.loads(bins.get("prediction_report", "null"))
    return bins


async def get_recent_episodes(client: AerospikeClient, limit: int = 5) -> list[dict]:
    """Query recent episodes from Aerospike for supervisor context injection (MEM-04).

    Uses an index record to track episode IDs. Returns list of episode dicts
    sorted by timestamp descending.
    Note: For demo scale, this approach is acceptable. Production would use a
    secondary index on the timestamp bin.
    """
    try:
        index_bins = await client.get(EPISODES_SET, "__episode_index__")
        episode_ids = json.loads(index_bins.get("ids", "[]"))
    except Exception:
        return []

    episodes = []
    for eid in episode_ids[-limit:]:
        try:
            ep = await get_episode(eid, client)
            episodes.append(ep)
        except Exception:
            continue
    return sorted(episodes, key=lambda e: e.get("timestamp", 0), reverse=True)


async def _update_episode_index(episode_id: str, client: AerospikeClient) -> None:
    """Maintain an index of episode IDs for get_recent_episodes."""
    try:
        index_bins = await client.get(EPISODES_SET, "__episode_index__")
        ids = json.loads(index_bins.get("ids", "[]"))
    except Exception:
        ids = []
    ids.append(episode_id)
    await client.put(EPISODES_SET, "__episode_index__", {"ids": json.dumps(ids)})
