"""
API unit tests — API-01, API-02.

Tests that verify schema validation and WebSocket manager behavior.
No external dependencies required (no ANTHROPIC_API_KEY, no Aerospike).
"""
from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest

from sentinel.api.routes.investigate import InvestigateRequest, InvestigateResponse
from sentinel.api.websocket import ConnectionManager


# ---------------------------------------------------------------------------
# Test 1: App imports successfully
# ---------------------------------------------------------------------------


def test_app_imports():
    """Assert that FastAPI app can be imported without error."""
    from sentinel.api.main import app  # noqa: F401

    assert app is not None


# ---------------------------------------------------------------------------
# Test 2: ConnectionManager.broadcast sends to all connected clients
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_websocket_manager_broadcast():
    """Broadcast sends a typed WSEvent JSON to all connected clients."""
    manager = ConnectionManager()

    # Create a mock WebSocket with an async send_text method
    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()
    mock_ws.send_text = AsyncMock()

    await manager.connect(mock_ws)
    assert mock_ws in manager.connections

    await manager.broadcast(
        event="investigation_started",
        episode_id="test-episode-001",
        data={"payment_request": {"amount": 100}},
    )

    mock_ws.send_text.assert_called_once()
    call_args = mock_ws.send_text.call_args[0][0]
    parsed = json.loads(call_args)
    assert "event" in parsed
    assert parsed["event"] == "investigation_started"
    assert parsed["episode_id"] == "test-episode-001"


# ---------------------------------------------------------------------------
# Test 3: InvestigateRequest schema validates
# ---------------------------------------------------------------------------


def test_investigate_request_schema():
    """InvestigateRequest model validates required and optional fields."""
    req = InvestigateRequest(
        payment_request={"amount": 100, "beneficiary": "ACME Corp"},
        scenario="phase1",
    )
    assert req.payment_request["amount"] == 100
    assert req.scenario == "phase1"

    # Default scenario value
    req_default = InvestigateRequest(payment_request={"amount": 50})
    assert req_default.scenario == "phase1"


# ---------------------------------------------------------------------------
# Test 4: InvestigateResponse schema validates
# ---------------------------------------------------------------------------


def test_investigate_response_schema():
    """InvestigateResponse model validates all required fields."""
    resp = InvestigateResponse(
        episode_id="abc-123",
        decision="NO-GO",
        composite_score=1.2,
        attribution="NO-GO (composite: 1.20) | Rule rule_hidden_text: 1.00",
        write_latency_ms=3.14,
    )
    assert resp.episode_id == "abc-123"
    assert resp.decision == "NO-GO"
    assert resp.composite_score == 1.2
    assert resp.write_latency_ms == 3.14


# ---------------------------------------------------------------------------
# Test 5: ConnectionManager.disconnect removes client
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_connection_manager_disconnect():
    """Disconnect removes the WebSocket from active connections list."""
    manager = ConnectionManager()

    mock_ws = AsyncMock()
    mock_ws.accept = AsyncMock()

    await manager.connect(mock_ws)
    assert mock_ws in manager.connections

    manager.disconnect(mock_ws)
    assert mock_ws not in manager.connections
    assert len(manager.connections) == 0


# ---------------------------------------------------------------------------
# Test 6: Broadcast prunes dead connections
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_broadcast_prunes_dead_connections():
    """Dead connections (send failure) are silently pruned during broadcast."""
    manager = ConnectionManager()

    # Healthy connection
    live_ws = AsyncMock()
    live_ws.accept = AsyncMock()
    live_ws.send_text = AsyncMock()

    # Dead connection that raises on send
    dead_ws = AsyncMock()
    dead_ws.accept = AsyncMock()
    dead_ws.send_text = AsyncMock(side_effect=Exception("connection closed"))

    await manager.connect(live_ws)
    await manager.connect(dead_ws)
    assert len(manager.connections) == 2

    await manager.broadcast("gate_evaluated", "ep-001")

    # Dead connection should be pruned
    assert dead_ws not in manager.connections
    assert live_ws in manager.connections
    assert len(manager.connections) == 1
