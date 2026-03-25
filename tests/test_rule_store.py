"""Tests for rule_store.py — MEM-02, MEM-05.

Uses AsyncMock for AerospikeClient so tests run without a real Aerospike instance.
"""
import json
from unittest.mock import AsyncMock, call

import pytest

from sentinel.memory.rule_store import (
    RULES_SET,
    _update_rules_index,
    increment_fire_count,
    load_all_rules,
    next_rule_id,
    write_rule,
)


# ---------------------------------------------------------------------------
# Helpers / Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_client() -> AsyncMock:
    """Return an AsyncMock simulating AerospikeClient interface."""
    client = AsyncMock()
    return client


_SAMPLE_SOURCE = "def score(verdict_board):\n    return 0.5"
_SAMPLE_EPISODE_IDS = ["ep-001", "ep-002"]
_SAMPLE_PRED_ERRORS = {"confidence_delta": 0.30, "step_deviation": True}


# ---------------------------------------------------------------------------
# write_rule tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_write_rule_stores_all_bins(mock_client: AsyncMock) -> None:
    """write_rule() calls client.put with RULES_SET, rule_id, and all required bins."""
    mock_client.get.side_effect = Exception("no index yet")

    await write_rule(
        "rule_001",
        _SAMPLE_SOURCE,
        _SAMPLE_EPISODE_IDS,
        _SAMPLE_PRED_ERRORS,
        1,
        mock_client,
    )

    # First call is the rule record write
    first_call = mock_client.put.call_args_list[0]
    set_name, pk, bins = first_call.args

    assert set_name == RULES_SET, f"Expected RULES_SET={RULES_SET!r}, got {set_name!r}"
    assert pk == "rule_001"
    assert bins["rule_id"] == "rule_001"
    assert bins["source"] == _SAMPLE_SOURCE
    assert json.loads(bins["episode_ids"]) == _SAMPLE_EPISODE_IDS
    assert json.loads(bins["prediction_errors"]) == _SAMPLE_PRED_ERRORS
    assert isinstance(bins["timestamp"], int)
    assert bins["version"] == 1
    assert bins["fire_count"] == 0


@pytest.mark.asyncio
async def test_write_rule_returns_latency(mock_client: AsyncMock) -> None:
    """write_rule() returns a float > 0 representing write latency in ms."""
    mock_client.get.side_effect = Exception("no index yet")

    latency = await write_rule(
        "rule_001",
        _SAMPLE_SOURCE,
        _SAMPLE_EPISODE_IDS,
        _SAMPLE_PRED_ERRORS,
        1,
        mock_client,
    )

    assert isinstance(latency, float), "Expected float latency"
    assert latency >= 0, "Expected non-negative latency"


@pytest.mark.asyncio
async def test_write_rule_updates_index(mock_client: AsyncMock) -> None:
    """write_rule() calls client.put twice — rule write + index update."""
    mock_client.get.return_value = {"rule_ids": json.dumps([])}

    await write_rule(
        "rule_001",
        _SAMPLE_SOURCE,
        _SAMPLE_EPISODE_IDS,
        _SAMPLE_PRED_ERRORS,
        1,
        mock_client,
    )

    assert mock_client.put.call_count == 2, "Expected two puts: rule + index"


# ---------------------------------------------------------------------------
# load_all_rules tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_load_all_rules_returns_stored(mock_client: AsyncMock) -> None:
    """load_all_rules() returns list of 2 rule dicts when 2 rules stored."""
    rule_ids = ["rule_001", "rule_002"]
    index_bins = {"rule_ids": json.dumps(rule_ids)}

    def _make_rule_bins(rid: str) -> dict:
        return {
            "rule_id": rid,
            "source": _SAMPLE_SOURCE,
            "episode_ids": json.dumps(_SAMPLE_EPISODE_IDS),
            "prediction_errors": json.dumps(_SAMPLE_PRED_ERRORS),
            "timestamp": 1000000,
            "version": 1,
            "fire_count": 0,
        }

    mock_client.get.side_effect = [
        index_bins,
        _make_rule_bins("rule_001"),
        _make_rule_bins("rule_002"),
    ]

    result = await load_all_rules(mock_client)

    assert len(result) == 2, f"Expected 2 rules, got {len(result)}"
    # Verify JSON fields are deserialized
    assert isinstance(result[0]["episode_ids"], list)
    assert isinstance(result[0]["prediction_errors"], dict)
    assert result[0]["episode_ids"] == _SAMPLE_EPISODE_IDS
    assert result[1]["rule_id"] == "rule_002"


@pytest.mark.asyncio
async def test_load_all_rules_empty_on_no_index(mock_client: AsyncMock) -> None:
    """load_all_rules() returns empty list when __rules_index__ is missing."""
    mock_client.get.side_effect = Exception("Record not found")

    result = await load_all_rules(mock_client)

    assert result == [], "Expected empty list when index missing"


# ---------------------------------------------------------------------------
# increment_fire_count tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_increment_fire_count_adds_one(mock_client: AsyncMock) -> None:
    """increment_fire_count() increments fire_count bin by 1."""
    existing_bins = {
        "rule_id": "rule_001",
        "source": _SAMPLE_SOURCE,
        "episode_ids": json.dumps([]),
        "prediction_errors": json.dumps({}),
        "timestamp": 1000000,
        "version": 1,
        "fire_count": 3,
    }
    mock_client.get.return_value = existing_bins.copy()

    await increment_fire_count("rule_001", mock_client)

    assert mock_client.put.called
    put_call = mock_client.put.call_args
    bins = put_call.args[2]
    assert bins["fire_count"] == 4, f"Expected fire_count=4, got {bins['fire_count']}"


@pytest.mark.asyncio
async def test_increment_fire_count_silent_on_error(mock_client: AsyncMock) -> None:
    """increment_fire_count() swallows exceptions — telemetry must never block."""
    mock_client.get.side_effect = Exception("Aerospike unavailable")

    # Should not raise
    await increment_fire_count("rule_001", mock_client)


# ---------------------------------------------------------------------------
# next_rule_id tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_next_rule_id_sequential(mock_client: AsyncMock) -> None:
    """next_rule_id() returns sequential IDs on successive calls."""
    # First call: counter is at 5
    mock_client.get.side_effect = [{"count": 5}, {"count": 6}]

    first = await next_rule_id(mock_client)
    second = await next_rule_id(mock_client)

    assert first == "rule_006", f"Expected 'rule_006', got {first!r}"
    assert second == "rule_007", f"Expected 'rule_007', got {second!r}"


@pytest.mark.asyncio
async def test_next_rule_id_on_fresh_db(mock_client: AsyncMock) -> None:
    """next_rule_id() returns 'rule_001' when __rule_counter__ is missing."""
    mock_client.get.side_effect = Exception("Record not found")

    result = await next_rule_id(mock_client)

    assert result == "rule_001", f"Expected 'rule_001', got {result!r}"
    # Verify counter was written as count=1
    assert mock_client.put.called
    put_call = mock_client.put.call_args
    set_name, pk, bins = put_call.args
    assert set_name == RULES_SET
    assert pk == "__rule_counter__"
    assert bins == {"count": 1}
