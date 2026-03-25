"""Tests for episode_store.py and trust_store.py.

Uses AsyncMock for AerospikeClient so tests run without a real Aerospike instance.
"""
import json
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from sentinel.memory.episode_store import (
    EPISODES_SET,
    get_episode,
    get_recent_episodes,
    write_episode,
)
from sentinel.memory.trust_store import (
    TRUST_SET,
    load_baselines,
    store_baselines,
    store_prediction_history,
)
from sentinel.schemas.episode import Episode
from sentinel.schemas.verdict import Verdict
from sentinel.schemas.verdict_board import VerdictBoard


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_test_episode() -> Episode:
    """Build a minimal Episode with required fields for testing."""
    verdict = Verdict(
        agent_id="risk",
        claims_checked=[],
        behavioral_flags=[],
        agent_confidence=0.72,
    )
    board = VerdictBoard(
        mismatches=[],
        behavioral_flags=[],
        agent_confidence=0.72,
    )
    return Episode(
        action_request={"amount": 10000, "beneficiary": "ACME Corp"},
        agent_verdicts=[verdict],
        verdict_board=board,
        gate_decision="GO",
        gate_rationale="No anomalies detected.",
    )


def _mock_aerospike_client() -> AsyncMock:
    """Return an AsyncMock simulating AerospikeClient interface."""
    client = AsyncMock()
    return client


# ---------------------------------------------------------------------------
# Episode Store Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_write_episode_returns_latency():
    """write_episode() returns a float > 0 representing write latency in ms."""
    client = _mock_aerospike_client()
    episode = _make_test_episode()

    latency_ms = await write_episode(episode, client)

    assert isinstance(latency_ms, float), "Expected float latency"
    assert latency_ms > 0, "Expected latency > 0 ms"


@pytest.mark.asyncio
async def test_write_episode_serializes_verdict_board():
    """write_episode() calls client.put with verdict_board as a JSON string."""
    client = _mock_aerospike_client()
    episode = _make_test_episode()

    await write_episode(episode, client)

    # client.put is called twice: once for the episode, once for the index
    # First call is the episode write
    assert client.put.called, "client.put should have been called"

    episode_call = client.put.call_args_list[0]
    args, kwargs = episode_call
    set_name, pk, bins = args[0], args[1], args[2]

    assert set_name == EPISODES_SET, f"Expected set_name={EPISODES_SET!r}, got {set_name!r}"
    assert pk == episode.id, f"Expected pk={episode.id!r}, got {pk!r}"
    assert "verdict_board" in bins, "bins must contain 'verdict_board'"
    # Verify it's valid JSON
    parsed = json.loads(bins["verdict_board"])
    assert isinstance(parsed, dict), "verdict_board bin must be a JSON object"


@pytest.mark.asyncio
async def test_write_episode_updates_index():
    """write_episode() makes two put calls — episode write + index update."""
    client = _mock_aerospike_client()
    # Simulate existing index returning an empty list
    client.get.return_value = {"ids": json.dumps([])}
    episode = _make_test_episode()

    await write_episode(episode, client)

    assert client.put.call_count == 2, "Expected two put calls: episode + index"


@pytest.mark.asyncio
async def test_get_recent_episodes_empty_when_no_index():
    """get_recent_episodes() returns [] when there is no index record."""
    client = _mock_aerospike_client()
    client.get.side_effect = Exception("Record not found")

    result = await get_recent_episodes(client, limit=5)

    assert result == [], "Expected empty list when index record missing"


@pytest.mark.asyncio
async def test_get_recent_episodes_returns_sorted():
    """get_recent_episodes() returns episodes sorted by timestamp descending."""
    client = _mock_aerospike_client()

    ep1_id = "ep-1"
    ep2_id = "ep-2"
    index_bins = {"ids": json.dumps([ep1_id, ep2_id])}

    ep1_bins = {
        "episode_id": ep1_id,
        "timestamp": 1000,
        "action_request": "{}",
        "gate_decision": "GO",
        "gate_rationale": "ok",
        "rules_fired": "[]",
        "generated_rules_fired": "[]",
        "verdict_board": "{}",
        "agent_verdicts": "[]",
        "prediction_report": "null",
    }
    ep2_bins = {
        "episode_id": ep2_id,
        "timestamp": 2000,
        "action_request": "{}",
        "gate_decision": "GO",
        "gate_rationale": "ok",
        "rules_fired": "[]",
        "generated_rules_fired": "[]",
        "verdict_board": "{}",
        "agent_verdicts": "[]",
        "prediction_report": "null",
    }

    # client.get is called: first for the index, then for each episode
    client.get.side_effect = [index_bins, ep1_bins, ep2_bins]

    result = await get_recent_episodes(client, limit=5)

    assert len(result) == 2
    # Sorted descending by timestamp: ep2 (2000) before ep1 (1000)
    assert result[0]["episode_id"] == ep2_id
    assert result[1]["episode_id"] == ep1_id


# ---------------------------------------------------------------------------
# Trust Store Tests
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_store_baselines_returns_latency():
    """store_baselines() returns a float > 0 representing write latency in ms."""
    client = _mock_aerospike_client()
    baselines = {"payment_agent": {"mean": 0.52, "std": 0.11}}

    latency_ms = await store_baselines(baselines, client)

    assert isinstance(latency_ms, float), "Expected float latency"
    assert latency_ms > 0, "Expected latency > 0 ms"


@pytest.mark.asyncio
async def test_store_baselines_writes_to_trust_set():
    """store_baselines() calls client.put with set_name=TRUST_SET."""
    client = _mock_aerospike_client()
    baselines = {"payment_agent": {"mean": 0.52}}

    await store_baselines(baselines, client)

    assert client.put.called
    args, _ = client.put.call_args
    assert args[0] == TRUST_SET, f"Expected TRUST_SET={TRUST_SET!r}, got {args[0]!r}"
    assert args[1] == "behavioral_baselines"


@pytest.mark.asyncio
async def test_load_baselines_fallback():
    """load_baselines() returns empty dict when Aerospike raises an exception."""
    client = _mock_aerospike_client()
    client.get.side_effect = Exception("Record not found")

    result = await load_baselines(client)

    assert result == {}, "Expected empty dict fallback"


@pytest.mark.asyncio
async def test_load_baselines_success():
    """load_baselines() correctly deserializes stored baselines."""
    client = _mock_aerospike_client()
    stored = {"payment_agent": {"mean": 0.52, "std": 0.11}}
    client.get.return_value = {"baselines": json.dumps(stored)}

    result = await load_baselines(client)

    assert "payment_agent" in result, "Expected payment_agent key in baselines"
    assert result["payment_agent"]["mean"] == 0.52


@pytest.mark.asyncio
async def test_store_prediction_history_persists_episode_id():
    """store_prediction_history() writes to TRUST_SET with episode-scoped key."""
    client = _mock_aerospike_client()
    episode_id = "ep-abc123"
    errors = {"confidence_delta": 0.30, "expected": 0.72, "actual": 0.42}

    await store_prediction_history(episode_id, errors, client)

    assert client.put.called
    args, _ = client.put.call_args
    assert args[0] == TRUST_SET
    assert args[1] == f"prediction_{episode_id}"
    bins = args[2]
    parsed_errors = json.loads(bins["prediction_errors"])
    assert parsed_errors["confidence_delta"] == 0.30
