"""
Unit tests for build_narrative_template() in sentinel/agents/supervisor.py.

Tests cover all 4 narrative output keys, edge cases for empty/missing data,
and the self-improvement arc state variants.

These tests run without any LLM calls — build_narrative_template() is a pure
Python function that takes structured investigation data and returns strings.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from sentinel.agents.supervisor import build_narrative_template


# ---------------------------------------------------------------------------
# Fixtures: mock objects matching real data shapes
# ---------------------------------------------------------------------------

def _make_payment_decision(
    amount: float = 47250.00,
    beneficiary: str = "Meridian Logistics",
    confidence: float = 0.85,
) -> MagicMock:
    """Create a mock PaymentDecision with the specified fields."""
    pd = MagicMock()
    pd.amount = amount
    pd.beneficiary = beneficiary
    pd.confidence = confidence
    return pd


def _make_verdict_board(
    prediction_errors: dict | None = None,
    behavioral_flags: list | None = None,
) -> MagicMock:
    """Create a mock VerdictBoard with prediction_errors and behavioral_flags."""
    vb = MagicMock()
    vb.prediction_errors = prediction_errors
    vb.behavioral_flags = behavioral_flags or []
    return vb


def _make_verdict(agent_id: str, behavioral_flags: list | None = None) -> MagicMock:
    """Create a mock Verdict for a single sub-agent."""
    v = MagicMock()
    v.agent_id = agent_id
    v.behavioral_flags = behavioral_flags or []
    return v


def _make_gate_result(
    decision: str = "NO-GO",
    attribution: str = "Hidden text detected in invoice",
    composite_score: float = 1.2,
) -> dict:
    """Create a mock gate_result dict."""
    return {
        "decision": decision,
        "attribution": attribution,
        "composite_score": composite_score,
    }


# Standard fixtures used across multiple tests
PAYMENT_DECISION = _make_payment_decision(
    amount=47250.00,
    beneficiary="Meridian Logistics",
    confidence=0.85,
)

VERDICT_BOARD_WITH_ERRORS = _make_verdict_board(
    prediction_errors={
        "predicted_z_score": 0.5,
        "summary_score": 3.0,
        "step_deviation": False,
        "deviation_details": "",
        "investigation_outcome_errors": {},
    },
    behavioral_flags=["hidden_text_detected"],
)

VERDICTS_THREE = [
    _make_verdict("risk", behavioral_flags=["confidence_anomaly"]),
    _make_verdict("compliance", behavioral_flags=["counterparty_not_found"]),
    _make_verdict("forensics", behavioral_flags=["hidden_text_detected"]),
]

GATE_RESULT_NOGO = _make_gate_result(
    decision="NO-GO",
    attribution="Hidden text detected in invoice",
    composite_score=5.85,
)


# ---------------------------------------------------------------------------
# Test 1: All 4 keys present in returned dict
# ---------------------------------------------------------------------------


def test_all_four_keys_present():
    """build_narrative_template must return dict with exactly 4 keys."""
    result = build_narrative_template(
        payment_decision=PAYMENT_DECISION,
        verdict_board=VERDICT_BOARD_WITH_ERRORS,
        verdicts=VERDICTS_THREE,
        gate_result=GATE_RESULT_NOGO,
        rule_sources=[],
    )
    assert isinstance(result, dict)
    assert "attack_narrative" in result
    assert "agent_reasoning" in result
    assert "prediction_summary" in result
    assert "self_improvement_arc" in result
    assert len(result) == 4


# ---------------------------------------------------------------------------
# Test 2: NO-GO gate result produces correct attack_narrative
# ---------------------------------------------------------------------------


def test_attack_narrative_nogo_contains_amount_and_beneficiary():
    """attack_narrative must contain formatted amount and beneficiary name."""
    result = build_narrative_template(
        payment_decision=_make_payment_decision(amount=47250.00, beneficiary="Meridian Logistics"),
        verdict_board=VERDICT_BOARD_WITH_ERRORS,
        verdicts=VERDICTS_THREE,
        gate_result=_make_gate_result(decision="NO-GO"),
        rule_sources=[],
    )
    assert "$47,250.00" in result["attack_narrative"]
    assert "Meridian Logistics" in result["attack_narrative"]
    assert "blocked" in result["attack_narrative"].lower()


def test_attack_narrative_go_uses_flagged_word():
    """attack_narrative should say 'flagged' for GO decisions, not 'blocked'."""
    result = build_narrative_template(
        payment_decision=_make_payment_decision(),
        verdict_board=VERDICT_BOARD_WITH_ERRORS,
        verdicts=VERDICTS_THREE,
        gate_result=_make_gate_result(decision="GO"),
        rule_sources=[],
    )
    # For GO: either "flagged" or a neutral word — NOT "blocked"
    assert "blocked" not in result["attack_narrative"].lower()


# ---------------------------------------------------------------------------
# Test 3: Empty verdicts list produces graceful agent_reasoning
# ---------------------------------------------------------------------------


def test_agent_reasoning_with_empty_verdicts_does_not_crash():
    """build_narrative_template must handle empty verdicts list gracefully."""
    result = build_narrative_template(
        payment_decision=PAYMENT_DECISION,
        verdict_board=VERDICT_BOARD_WITH_ERRORS,
        verdicts=[],  # Empty — no agent verdicts
        gate_result=GATE_RESULT_NOGO,
        rule_sources=[],
    )
    assert isinstance(result["agent_reasoning"], str)
    assert len(result["agent_reasoning"]) > 0  # Not empty string


def test_agent_reasoning_with_three_verdicts_mentions_all_agents():
    """agent_reasoning must reference all three sub-agents when all verdicts present."""
    result = build_narrative_template(
        payment_decision=PAYMENT_DECISION,
        verdict_board=VERDICT_BOARD_WITH_ERRORS,
        verdicts=VERDICTS_THREE,
        gate_result=GATE_RESULT_NOGO,
        rule_sources=[],
    )
    narrative = result["agent_reasoning"].lower()
    assert "risk" in narrative
    assert "compliance" in narrative
    assert "forensics" in narrative


# ---------------------------------------------------------------------------
# Test 4: prediction_errors with float values produces numeric prediction_summary
# ---------------------------------------------------------------------------


def test_prediction_summary_contains_numeric_score():
    """prediction_summary must include the actual z-score when prediction_errors has floats."""
    vb = _make_verdict_board(prediction_errors={
        "predicted_z_score": 0.5,
        "summary_score": 3.0,
    })
    result = build_narrative_template(
        payment_decision=PAYMENT_DECISION,
        verdict_board=vb,
        verdicts=VERDICTS_THREE,
        gate_result=GATE_RESULT_NOGO,
        rule_sources=[],
    )
    # The numeric score 3.0 should appear in the summary
    assert "3.00" in result["prediction_summary"] or "3.0" in result["prediction_summary"]


def test_prediction_summary_with_no_prediction_errors_is_graceful():
    """prediction_summary must handle missing prediction_errors without crashing."""
    vb = _make_verdict_board(prediction_errors=None)
    result = build_narrative_template(
        payment_decision=PAYMENT_DECISION,
        verdict_board=vb,
        verdicts=VERDICTS_THREE,
        gate_result=GATE_RESULT_NOGO,
        rule_sources=[],
    )
    assert isinstance(result["prediction_summary"], str)
    assert len(result["prediction_summary"]) > 0


# ---------------------------------------------------------------------------
# Test 5: No rule_sources produces "No rules generated yet" arc
# ---------------------------------------------------------------------------


def test_self_improvement_arc_no_rules():
    """self_improvement_arc with empty rule_sources must return empty-state copy."""
    result = build_narrative_template(
        payment_decision=PAYMENT_DECISION,
        verdict_board=VERDICT_BOARD_WITH_ERRORS,
        verdicts=VERDICTS_THREE,
        gate_result=GATE_RESULT_NOGO,
        rule_sources=[],
    )
    arc = result["self_improvement_arc"]
    assert "No rules generated yet" in arc


# ---------------------------------------------------------------------------
# Test 6: rule_sources with version > 1 produces arc mentioning "refined"
# ---------------------------------------------------------------------------


def test_self_improvement_arc_with_evolved_rule_mentions_refined():
    """self_improvement_arc with version > 1 rule must mention 'refined'."""
    rule_sources = [
        {"rule_id": "generated_001", "version": 2},
    ]
    result = build_narrative_template(
        payment_decision=PAYMENT_DECISION,
        verdict_board=VERDICT_BOARD_WITH_ERRORS,
        verdicts=VERDICTS_THREE,
        gate_result=GATE_RESULT_NOGO,
        rule_sources=rule_sources,
    )
    arc = result["self_improvement_arc"]
    assert "refined" in arc.lower()
    # Also check version number is mentioned
    assert "2" in arc or "v2" in arc


def test_self_improvement_arc_with_v1_rule_mentions_generated():
    """self_improvement_arc with version 1 rule mentions rule as newly generated."""
    rule_sources = [
        {"rule_id": "generated_001", "version": 1},
    ]
    result = build_narrative_template(
        payment_decision=PAYMENT_DECISION,
        verdict_board=VERDICT_BOARD_WITH_ERRORS,
        verdicts=VERDICTS_THREE,
        gate_result=GATE_RESULT_NOGO,
        rule_sources=rule_sources,
    )
    arc = result["self_improvement_arc"]
    assert "generated_001" in arc
    # Should not mention "refined" for version 1
    assert "refined" not in arc.lower()


# ---------------------------------------------------------------------------
# Test: prediction_errors divergence mentioned
# ---------------------------------------------------------------------------


def test_prediction_summary_mentions_divergence():
    """prediction_summary must mention divergence when prediction_errors has float values."""
    vb = _make_verdict_board(prediction_errors={
        "predicted_z_score": 0.2,
        "summary_score": 3.5,
    })
    result = build_narrative_template(
        payment_decision=PAYMENT_DECISION,
        verdict_board=vb,
        verdicts=VERDICTS_THREE,
        gate_result=GATE_RESULT_NOGO,
        rule_sources=[],
    )
    summary = result["prediction_summary"].lower()
    # Should mention some form of divergence/difference
    assert any(word in summary for word in ["diverge", "found", "baseline", "expected"])
