"""
Tests for POST /bland-webhook — API-04, VOICE-03.

Tests cover:
- Returning correct voice context from active_episodes cache
- Fallback to __latest__ sentinel key when episode_id is unknown
- Empty cache fallback (returns safe NO-GO dict)
- Malformed/empty body falls back to __latest__
- Response dict always has exactly 5 required keys
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
    gate_rationale: str = "Adversarial content detected in invoice",
    rules_fired: list[str] | None = None,
    generated_rules_fired: list[str] | None = None,
    prediction_report: dict | None = None,
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
        gate_rationale=gate_rationale,
        rules_fired=rules_fired or ["adversarial_content_rule"],
        generated_rules_fired=generated_rules_fired or ["generated_rule_001"],
        prediction_report=prediction_report or {
            "summary_score": 5.85,
            "predicted_z_score": 3.0,
            "step_deviation": False,
            "investigation_outcome_errors": {"forensics": False},
        },
    )


def _get_test_app():
    """Return the FastAPI app with test app_state injected."""
    from sentinel.api.main import app, app_state
    return app, app_state


# ---------------------------------------------------------------------------
# Test: POST /bland-webhook returns context for known episode_id
# ---------------------------------------------------------------------------


def test_webhook_returns_context():
    """POST /bland-webhook with known episode_id returns correct 5-field context."""
    app, app_state = _get_test_app()

    ep = _make_episode("ep-1", gate_decision="NO-GO")
    app_state["active_episodes"] = {"ep-1": ep}

    client = TestClient(app)
    resp = client.post("/bland-webhook", json={"episode_id": "ep-1"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["gate_decision"] == "NO-GO"
    assert "5.85" in data["composite_score"] or data["composite_score"] == "5.85"
    assert "Adversarial content" in data["attribution"]
    assert "adversarial_content_rule" in data["rules_fired"]
    assert data["prediction_errors"] != ""


# ---------------------------------------------------------------------------
# Test: POST /bland-webhook falls back to __latest__ when episode_id unknown
# ---------------------------------------------------------------------------


def test_webhook_fallback_latest():
    """POST /bland-webhook with unknown episode_id falls back to __latest__ key."""
    app, app_state = _get_test_app()

    ep = _make_episode("ep-1", gate_decision="NO-GO")
    app_state["active_episodes"] = {
        "ep-1": ep,
        "__latest__": "ep-1",
    }

    client = TestClient(app)
    resp = client.post("/bland-webhook", json={"episode_id": "unknown-episode"})
    assert resp.status_code == 200
    data = resp.json()

    # Should have resolved to ep-1's data via __latest__
    assert data["gate_decision"] == "NO-GO"
    assert "Adversarial content" in data["attribution"]


# ---------------------------------------------------------------------------
# Test: POST /bland-webhook returns safe fallback when cache is empty
# ---------------------------------------------------------------------------


def test_webhook_empty_cache():
    """POST /bland-webhook with empty active_episodes returns safe NO-GO fallback."""
    app, app_state = _get_test_app()
    app_state["active_episodes"] = {}

    client = TestClient(app)
    resp = client.post("/bland-webhook", json={"episode_id": "ep-1"})
    assert resp.status_code == 200
    data = resp.json()

    assert data["gate_decision"] == "NO-GO"
    assert "not available" in data["attribution"].lower()


# ---------------------------------------------------------------------------
# Test: POST /bland-webhook handles empty/malformed body (falls back to __latest__)
# ---------------------------------------------------------------------------


def test_webhook_no_body():
    """POST /bland-webhook with empty body falls back to __latest__ episode."""
    app, app_state = _get_test_app()

    ep = _make_episode("ep-latest", gate_decision="ESCALATE")
    app_state["active_episodes"] = {
        "ep-latest": ep,
        "__latest__": "ep-latest",
    }

    client = TestClient(app)
    # Send empty body (no JSON)
    resp = client.post(
        "/bland-webhook",
        content=b"",
        headers={"content-type": "application/json"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["gate_decision"] == "ESCALATE"


# ---------------------------------------------------------------------------
# Test: Response dict always has exactly 5 keys
# ---------------------------------------------------------------------------


def test_context_fields_complete():
    """Response dict always contains exactly 5 keys: gate_decision, composite_score, attribution, rules_fired, prediction_errors."""
    app, app_state = _get_test_app()

    ep = _make_episode("ep-check")
    app_state["active_episodes"] = {"ep-check": ep, "__latest__": "ep-check"}

    client = TestClient(app)
    resp = client.post("/bland-webhook", json={"episode_id": "ep-check"})
    assert resp.status_code == 200
    data = resp.json()

    required_keys = {"gate_decision", "composite_score", "attribution", "rules_fired", "prediction_errors"}
    assert set(data.keys()) == required_keys, f"Expected {required_keys}, got {set(data.keys())}"
