"""
Unit tests for POST /confirm route — API-03.

Tests cover:
1. 202 Accepted with valid episode_id
2. 404 for unknown episode_id
3. 422 validation error without attack_type
4. Background task (asyncio.create_task) is called
5. Response schema contains episode_id and status="accepted"
6. ConfirmRequest model validates required fields
7. ConfirmResponse model validates required fields

No external dependencies required — mocks all app_state components.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from sentinel.api.main import app, app_state
from sentinel.api.routes.confirm import ConfirmRequest, ConfirmResponse
from sentinel.schemas.episode import Episode
from sentinel.schemas.verdict_board import VerdictBoard

EPISODE_ID = "test-episode-abc123"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mock_episode() -> Episode:
    """Create a minimal mock Episode with required fields populated."""
    vb = VerdictBoard(
        mismatches=[],
        behavioral_flags=[],
        agent_confidence=0.85,
        confidence_z_score=2.5,
        step_sequence_deviation=False,
        hardcoded_rule_fired=True,
        unable_to_verify=[],
    )
    return Episode(
        action_request={"amount": 50000, "beneficiary": "Evil Corp"},
        agent_verdicts=[],
        verdict_board=vb,
        gate_decision="NO-GO",
        gate_rationale="Attack confirmed",
        prediction_report={"summary_score": 0.9, "top_deviations": []},
        generated_rules_fired=[],
    )


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Return a TestClient with mock episode pre-loaded in app_state.

    The episode must be injected INSIDE the TestClient context (after lifespan
    startup) — the lifespan initializes active_episodes = {} on startup.
    """
    with TestClient(app) as c:
        # Inject mock episode after startup initializes active_episodes
        app_state["active_episodes"][EPISODE_ID] = _make_mock_episode()
        yield c
        # Cleanup
        app_state["active_episodes"].pop(EPISODE_ID, None)


# ---------------------------------------------------------------------------
# Test 1: POST /confirm returns 202 for valid episode
# ---------------------------------------------------------------------------


def test_confirm_returns_202(client):
    """POST /confirm with a valid episode_id returns 202 Accepted immediately."""
    with patch("asyncio.create_task"):
        response = client.post(
            "/confirm",
            json={"episode_id": EPISODE_ID, "attack_type": "prompt_injection_hidden_text"},
        )
    assert response.status_code == 202


# ---------------------------------------------------------------------------
# Test 2: POST /confirm returns 404 for unknown episode
# ---------------------------------------------------------------------------


def test_confirm_returns_404_for_unknown_episode(client):
    """POST /confirm with nonexistent episode_id returns 404 Not Found."""
    response = client.post(
        "/confirm",
        json={"episode_id": "nonexistent-episode-xyz", "attack_type": "test"},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


# ---------------------------------------------------------------------------
# Test 3: POST /confirm returns 422 without attack_type
# ---------------------------------------------------------------------------


def test_confirm_request_validation(client):
    """POST /confirm without attack_type returns 422 Unprocessable Entity."""
    response = client.post(
        "/confirm",
        json={"episode_id": EPISODE_ID},  # Missing attack_type
    )
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# Test 4: POST /confirm spawns background task
# ---------------------------------------------------------------------------


def test_confirm_spawns_background_task(client):
    """After POST /confirm, asyncio.create_task is called once."""
    with patch("asyncio.create_task") as mock_create_task:
        response = client.post(
            "/confirm",
            json={"episode_id": EPISODE_ID, "attack_type": "prompt_injection_hidden_text"},
        )
    assert response.status_code == 202
    mock_create_task.assert_called_once()


# ---------------------------------------------------------------------------
# Test 5: Response schema contains episode_id and status="accepted"
# ---------------------------------------------------------------------------


def test_confirm_response_schema(client):
    """Response body contains episode_id matching the request and status='accepted'."""
    with patch("asyncio.create_task"):
        response = client.post(
            "/confirm",
            json={"episode_id": EPISODE_ID, "attack_type": "identity_spoofing"},
        )
    assert response.status_code == 202
    body = response.json()
    assert body["episode_id"] == EPISODE_ID
    assert body["status"] == "accepted"


# ---------------------------------------------------------------------------
# Test 6: ConfirmRequest model validates required fields
# ---------------------------------------------------------------------------


def test_confirm_request_model():
    """ConfirmRequest Pydantic model validates required fields."""
    req = ConfirmRequest(episode_id="ep-001", attack_type="prompt_injection")
    assert req.episode_id == "ep-001"
    assert req.attack_type == "prompt_injection"


# ---------------------------------------------------------------------------
# Test 7: ConfirmResponse model validates fields
# ---------------------------------------------------------------------------


def test_confirm_response_model():
    """ConfirmResponse Pydantic model validates required fields."""
    resp = ConfirmResponse(episode_id="ep-001", status="accepted")
    assert resp.episode_id == "ep-001"
    assert resp.status == "accepted"
