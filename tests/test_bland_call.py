"""
Tests for POST /bland-call — VOICE-01, VOICE-02.

Tests cover:
- _build_call_payload returns correct structure with dynamic_data URL containing /bland-webhook
- Barge-in params: interruption_threshold=150, block_interruptions=False
- POST /bland-call with unknown episode_id returns 404
- dynamic_data[0]["timeout"] == 3000
"""
from __future__ import annotations

import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from sentinel.schemas.episode import Episode
from sentinel.schemas.verdict import Verdict, ClaimCheck
from sentinel.schemas.verdict_board import VerdictBoard


def _make_episode(
    episode_id: str = "ep-test-1",
    gate_decision: str = "NO-GO",
) -> Episode:
    """Build a minimal valid Episode for testing."""
    verdict = Verdict(
        agent_id="risk",
        claims_checked=[
            ClaimCheck(
                field="confidence",
                agent_claimed="0.85",
                independently_found="0.52",
                match=False,
                severity="warning",
            )
        ],
        behavioral_flags=["high_confidence"],
        agent_confidence=0.85,
        confidence_z_score=3.0,
        unable_to_verify=False,
    )
    vb = VerdictBoard(
        mismatches=[{"field": "confidence", "severity": "warning"}],
        behavioral_flags=["high_confidence"],
        agent_confidence=0.85,
        confidence_z_score=3.0,
        step_sequence_deviation=False,
        hardcoded_rule_fired=True,
    )
    return Episode(
        id=episode_id,
        timestamp=datetime.utcnow(),
        action_request={"amount": 50000, "beneficiary": "ACME Corp"},
        agent_verdicts=[verdict],
        verdict_board=vb,
        gate_decision=gate_decision,  # type: ignore[arg-type]
        gate_rationale="Adversarial content detected in invoice",
        rules_fired=["adversarial_content_rule"],
        generated_rules_fired=["generated_rule_001"],
        prediction_report={"summary_score": 5.85},
    )


def _get_test_app():
    """Return the FastAPI app with test app_state injected."""
    from sentinel.api.main import app, app_state
    return app, app_state


# ---------------------------------------------------------------------------
# Test: _build_call_payload returns correct structure
# ---------------------------------------------------------------------------


def test_call_payload_structure():
    """_build_call_payload returns dict with phone_number, task, voice, model='base',
    dynamic_data with /bland-webhook URL, and request_data with episode_id."""
    from sentinel.api.routes.bland_call import _build_call_payload, StartCallRequest

    req = StartCallRequest(
        episode_id="ep-1",
        phone_number="+15551234567",
        public_host="https://abc.ngrok.io",
    )
    payload = _build_call_payload(req)

    assert payload["phone_number"] == "+15551234567"
    assert "task" in payload
    assert payload["voice"] == "maya"
    assert payload["model"] == "base"

    # dynamic_data must be present and contain /bland-webhook URL
    dynamic_data = payload["dynamic_data"]
    assert isinstance(dynamic_data, list) and len(dynamic_data) > 0
    assert "/bland-webhook" in dynamic_data[0]["url"]
    assert "https://abc.ngrok.io" in dynamic_data[0]["url"]

    # request_data must carry episode_id
    assert payload["request_data"]["episode_id"] == "ep-1"


# ---------------------------------------------------------------------------
# Test: Barge-in params
# ---------------------------------------------------------------------------


def test_barge_in_params():
    """Payload has interruption_threshold=150 and block_interruptions=False (VOICE-02)."""
    from sentinel.api.routes.bland_call import _build_call_payload, StartCallRequest

    req = StartCallRequest(
        episode_id="ep-2",
        phone_number="+15559876543",
        public_host="https://demo.example.com",
    )
    payload = _build_call_payload(req)

    assert payload["interruption_threshold"] == 150
    assert payload["block_interruptions"] is False


# ---------------------------------------------------------------------------
# Test: POST /bland-call returns 404 for unknown episode_id
# ---------------------------------------------------------------------------


def test_call_episode_not_found():
    """POST /bland-call with unknown episode_id returns 404."""
    app, app_state = _get_test_app()
    app_state["active_episodes"] = {}  # No episodes cached
    app_state["bland_api_key"] = "test-bland-placeholder"

    client = TestClient(app)
    resp = client.post(
        "/bland-call",
        json={
            "episode_id": "nonexistent-episode",
            "phone_number": "+15551234567",
            "public_host": "https://abc.ngrok.io",
        },
    )
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Test: dynamic_data timeout == 3000
# ---------------------------------------------------------------------------


def test_dynamic_data_timeout():
    """dynamic_data[0]['timeout'] == 3000 (not default 2000)."""
    from sentinel.api.routes.bland_call import _build_call_payload, StartCallRequest

    req = StartCallRequest(
        episode_id="ep-3",
        phone_number="+15550001111",
        public_host="https://test.ngrok.io",
    )
    payload = _build_call_payload(req)

    assert payload["dynamic_data"][0]["timeout"] == 3000
