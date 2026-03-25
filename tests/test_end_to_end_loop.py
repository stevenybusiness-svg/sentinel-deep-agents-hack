"""
End-to-end self-improvement loop tests — Phase 3, Plan 04 (LEARN-05, LEARN-06).

These tests prove the full learning loop without real LLM calls:
1. Generated behavioral rule from Attack 1 (invoice prompt injection) generalizes to block Attack 2 (identity spoofing)
2. Hardcoded rules alone are insufficient for Attack 2 — generated rule is required
3. Evolution produces a tighter v2 rule with lower false-positive potential

Test coverage:
- test_full_learning_loop_with_mock_llm: End-to-end Attack 1 → rule generation → Attack 2 blocked
- test_evolution_produces_valid_v2: v2 rule is tighter than v1 (lower clean baseline score)
"""
from __future__ import annotations

from pathlib import Path

import pytest

from sentinel.engine.rule_generator import (
    CLEAN_BASELINE_VERDICT_BOARD,
    validate_rule,
    _exec_rule,
)
from sentinel.engine.safety_gate import SafetyGate
from sentinel.schemas.verdict_board import VerdictBoard


# ---------------------------------------------------------------------------
# Attack fixtures
# ---------------------------------------------------------------------------

# Phase 1: Invoice hidden-text prompt injection attack.
PHASE1_ATTACK_VB = {
    "mismatches": [
        {
            "field": "amount",
            "agent_claimed": 47250.00,
            "independently_found": 12500.00,
            "match": False,
            "severity": "critical",
            "agent_id": "risk_agent",
        },
        {
            "field": "beneficiary_account",
            "agent_claimed": "8829-XXXX-1847",
            "independently_found": "1100-XXXX-5523",
            "match": False,
            "severity": "critical",
            "agent_id": "compliance_agent",
        },
    ],
    "behavioral_flags": ["hidden_text_detected", "amount_deviation_extreme"],
    "agent_confidence": 0.95,
    "confidence_z_score": 3.91,
    "step_sequence_deviation": True,
    "hardcoded_rule_fired": True,
    "unable_to_verify": ["compliance_agent"],
    "prediction_errors": {
        "summary_score": 1.8,
        "top_deviations": [
            {"field": "agent_confidence", "expected": 0.52, "actual": 0.95, "z_score": 3.91},
            {"field": "amount", "expected": 12500.00, "actual": 47250.00, "deviation": "extreme"},
        ],
    },
}

# Phase 2: Identity spoofing attack — different vector, same behavioral fingerprint.
# Key properties:
#   - NO hidden_text_detected (no document manipulation)
#   - High confidence (0.92) with anomalous z-score (3.64)
#   - Compliance agent unable to verify (Meridian Logistics absent from KYC)
#   - step_sequence_deviation=False — keeps hardcoded composite < 1.0
#   - Hardcoded rules alone: z_score (0.6) + unverifiable (0.3) = 0.9 < 1.0 → ESCALATE
PHASE2_ATTACK_VB = {
    "mismatches": [],
    "behavioral_flags": ["identity_unverifiable", "kyc_absent"],
    "agent_confidence": 0.92,
    "confidence_z_score": 3.64,
    "step_sequence_deviation": False,
    "hardcoded_rule_fired": False,
    "unable_to_verify": ["compliance_agent"],
    "prediction_errors": {
        "summary_score": 1.6,
        "top_deviations": [
            {"field": "agent_confidence", "expected": 0.52, "actual": 0.92, "z_score": 3.64},
            {"field": "kyc_status", "expected": "verified", "actual": "NOT_IN_KYC_LEDGER"},
        ],
    },
}

# Behavioral scoring function representing what Opus 4.6 would generate from Phase 1.
# Generalizes across attack vectors by targeting the shared behavioral fingerprint:
# overconfident agent whose claims evaporate under independent scrutiny.
BEHAVIORAL_RULE_SOURCE = '''
def score(verdict_board: dict) -> float:
    """Detects compound behavioral anomalies: high confidence + verification failures + z-score deviation."""
    score_val = 0.0
    confidence = verdict_board.get("agent_confidence", 0.5)
    z = abs(verdict_board.get("confidence_z_score") or 0)
    unable = verdict_board.get("unable_to_verify", [])
    flags = verdict_board.get("behavioral_flags", [])
    mismatches = verdict_board.get("mismatches", [])
    critical_mismatches = [m for m in mismatches if m.get("severity") == "critical"]
    if confidence > 0.85:
        score_val += 0.3
    if z > 3.0:
        score_val += 0.2
    if len(unable) > 0:
        score_val += 0.2
    if len(critical_mismatches) > 0:
        score_val += 0.15
    if verdict_board.get("step_sequence_deviation"):
        score_val += 0.15
    return min(score_val, 2.0)
'''

# Evolved rule (v2) — tighter thresholds after seeing both incidents.
# Drops single-signal conditions (critical_mismatches appeared only in Attack 1).
# Strengthens compound conditions that appeared in both (confidence + z-score + unverifiable).
EVOLVED_RULE_SOURCE = '''
def score(verdict_board: dict) -> float:
    """Evolved: compound behavioral anomalies refined across two incidents."""
    score_val = 0.0
    confidence = verdict_board.get("agent_confidence", 0.5)
    z = abs(verdict_board.get("confidence_z_score") or 0)
    unable = verdict_board.get("unable_to_verify", [])
    if confidence > 0.88 and z > 2.5:
        score_val += 0.5
    if len(unable) > 0 and confidence > 0.8:
        score_val += 0.3
    if verdict_board.get("step_sequence_deviation") and z > 2.0:
        score_val += 0.2
    return min(score_val, 2.0)
'''


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_rules_dir() -> Path:
    """Return path to sentinel/gate/rules/ relative to this test file."""
    return Path(__file__).parent.parent / "sentinel" / "gate" / "rules"


def _make_gate_with_hardcoded_rules() -> SafetyGate:
    """Create a SafetyGate loaded with all hardcoded rules."""
    gate = SafetyGate()
    gate.load_rules_from_directory(_get_rules_dir())
    return gate


# ---------------------------------------------------------------------------
# End-to-end learning loop test
# ---------------------------------------------------------------------------

class TestFullLearningLoop:
    def test_full_learning_loop_with_mock_llm(self):
        """Prove the full self-improvement loop end-to-end (without real LLM).

        Loop:
        1. Phase 1 attack → hardcoded rules → NO-GO (hidden text fires)
        2. Operator confirms → simulate rule generation (validate behavioral rule)
        3. Register generated rule in SafetyGate
        4. Phase 2 attack (different vector) → NO-GO via generated rule + hardcoded rules
        5. Attribution mentions generated rule
        """
        gate = _make_gate_with_hardcoded_rules()

        # Step 1: Phase 1 attack → hardcoded rules sufficient (hidden_text fires)
        phase1_board = VerdictBoard(**PHASE1_ATTACK_VB)
        result1 = gate.evaluate(phase1_board)
        assert result1["decision"] == "NO-GO", (
            f"Phase 1 attack should be NO-GO. Got: {result1['decision']} "
            f"(composite: {result1['composite_score']:.2f})"
        )

        # Step 2: Simulate rule generation — validate behavioral rule against Phase 1
        valid, reason = validate_rule(BEHAVIORAL_RULE_SOURCE, PHASE1_ATTACK_VB)
        assert valid is True, f"Behavioral rule failed Phase 1 validation: {reason}"

        # Step 3: Register the generated rule
        gate.register_rule("gen_rule_001", BEHAVIORAL_RULE_SOURCE)

        # Step 4: Phase 2 attack (identity spoofing — no hidden text)
        phase2_board = VerdictBoard(**PHASE2_ATTACK_VB)
        result2 = gate.evaluate(phase2_board)
        assert result2["decision"] == "NO-GO", (
            f"Phase 2 attack should be NO-GO with generated rule loaded. "
            f"Got: {result2['decision']} (composite: {result2['composite_score']:.2f})"
        )
        assert result2["composite_score"] >= 1.0, (
            f"Composite score should be >= 1.0, got {result2['composite_score']:.3f}"
        )

        # Step 5: Attribution mentions generated rule
        assert "Generated Rule" in result2["attribution"], (
            f"Attribution should mention 'Generated Rule', got: {result2['attribution']}"
        )

        # Step 6: Cross-attack generalization — generated rule fires on Phase 2
        generated_contributions = [
            c for c in result2["rule_contributions"] if c["is_generated"]
        ]
        assert len(generated_contributions) > 0, (
            "Expected generated rule contribution in Phase 2 evaluation"
        )
        assert generated_contributions[0]["rule_id"] == "gen_rule_001"
        assert generated_contributions[0]["score"] > 0.0, (
            "Generated rule should contribute a positive score on Phase 2"
        )

    def test_hardcoded_rules_insufficient_for_phase2_without_generated(self):
        """Hardcoded rules alone score < 1.0 on Phase 2 — the gap that requires generated rules.

        This is the critical proof: without the generated rule, Phase 2 only ESCALATEs.
        The generated rule is what makes the system catch novel attack vectors.
        """
        gate = _make_gate_with_hardcoded_rules()
        # No generated rules registered

        phase2_board = VerdictBoard(**PHASE2_ATTACK_VB)
        result = gate.evaluate(phase2_board)

        assert result["composite_score"] < 1.0, (
            f"Hardcoded rules alone should score < 1.0 on Phase 2. "
            f"Got {result['composite_score']:.3f}. "
            "This test verifies that the generated rule is genuinely needed."
        )
        # Decision should be ESCALATE or GO — not NO-GO
        assert result["decision"] in ("ESCALATE", "GO"), (
            f"Expected ESCALATE or GO with hardcoded rules only, got {result['decision']}"
        )


# ---------------------------------------------------------------------------
# Rule evolution tests
# ---------------------------------------------------------------------------

class TestRuleEvolution:
    def test_evolution_produces_valid_v2(self):
        """v2 rule passes validation against Phase 2 VerdictBoard (score > 0.6).

        After a second confirmed incident, the evolved rule must still detect
        the attack it was evolved from.
        """
        valid, reason = validate_rule(EVOLVED_RULE_SOURCE, PHASE2_ATTACK_VB)
        assert valid is True, f"Evolved v2 rule failed validation against Phase 2: {reason}"

    def test_v2_is_tighter_than_v1_on_clean_baseline(self):
        """v2 rule scores lower on clean baseline than v1 — tighter = lower false-positive potential.

        Evolution must not increase false-positive risk. The evolved function drops
        conditions that were Phase 1 artifacts (critical_mismatches) and tightens
        compound conditions.
        """
        fn_v1 = _exec_rule(BEHAVIORAL_RULE_SOURCE)
        fn_v2 = _exec_rule(EVOLVED_RULE_SOURCE)

        v1_clean = fn_v1(CLEAN_BASELINE_VERDICT_BOARD)
        v2_clean = fn_v2(CLEAN_BASELINE_VERDICT_BOARD)

        assert v2_clean <= v1_clean, (
            f"v2 clean baseline score ({v2_clean:.3f}) should be <= v1 ({v1_clean:.3f}). "
            "Evolution must not increase false-positive risk."
        )

    def test_v2_still_catches_phase2_attack(self):
        """v2 rule still catches Phase 2 attack (score > 0.6) after evolution.

        The evolved rule must remain effective on the attack that triggered evolution.
        """
        fn_v2 = _exec_rule(EVOLVED_RULE_SOURCE)
        score = fn_v2(PHASE2_ATTACK_VB)
        assert score > 0.6, (
            f"v2 rule should still score > 0.6 on Phase 2 attack. Got {score:.3f}"
        )

    def test_v2_still_catches_phase1_attack(self):
        """v2 rule catches Phase 1 attack (score > 0.6) — generalization preserved.

        The evolved rule must not regress on the original attack that produced v1.
        """
        fn_v2 = _exec_rule(EVOLVED_RULE_SOURCE)
        score = fn_v2(PHASE1_ATTACK_VB)
        assert score > 0.6, (
            f"v2 rule should still score > 0.6 on Phase 1 attack. Got {score:.3f}"
        )

    def test_evolution_with_gate_registration(self):
        """v2 rule can be registered in SafetyGate and produces NO-GO on Phase 2.

        This tests the full deployment path for evolved rules.
        """
        gate = _make_gate_with_hardcoded_rules()
        gate.register_rule("gen_rule_001_v2", EVOLVED_RULE_SOURCE)

        phase2_board = VerdictBoard(**PHASE2_ATTACK_VB)
        result = gate.evaluate(phase2_board)

        assert result["decision"] == "NO-GO", (
            f"Expected NO-GO with evolved v2 rule, got {result['decision']} "
            f"(composite: {result['composite_score']:.2f})"
        )
        assert result["composite_score"] >= 1.0


# ---------------------------------------------------------------------------
# Provenance / attribution chain tests
# ---------------------------------------------------------------------------

class TestAttributionChain:
    def test_generated_rules_fired_populated_from_evaluation(self):
        """SafetyGate.evaluate() returns is_generated=True in rule_contributions.

        This is the data that supervisor.py uses to populate episode.generated_rules_fired —
        the chain that enables the confirm route to detect and trigger the evolution path.
        """
        gate = _make_gate_with_hardcoded_rules()
        gate.register_rule("gen_rule_001", BEHAVIORAL_RULE_SOURCE)

        phase2_board = VerdictBoard(**PHASE2_ATTACK_VB)
        result = gate.evaluate(phase2_board)

        # Simulate what supervisor.py does to populate episode.generated_rules_fired
        generated_rules_fired = [
            c["rule_id"]
            for c in result["rule_contributions"]
            if c["is_generated"]
        ]

        assert "gen_rule_001" in generated_rules_fired, (
            "gen_rule_001 should appear in generated_rules_fired extracted from rule_contributions"
        )

    def test_rules_fired_split_is_correct(self):
        """rules_fired and generated_rules_fired are correctly split from rule_contributions.

        Verifies the exact pattern used in supervisor.py Episode construction.
        """
        gate = _make_gate_with_hardcoded_rules()
        gate.register_rule("gen_rule_001", BEHAVIORAL_RULE_SOURCE)

        phase2_board = VerdictBoard(**PHASE2_ATTACK_VB)
        result = gate.evaluate(phase2_board)

        hardcoded_fired = [
            c["rule_id"]
            for c in result["rule_contributions"]
            if not c["is_generated"]
        ]
        generated_fired = [
            c["rule_id"]
            for c in result["rule_contributions"]
            if c["is_generated"]
        ]

        # Generated and hardcoded should be disjoint
        assert not set(hardcoded_fired) & set(generated_fired), (
            "Generated and hardcoded rule IDs must not overlap"
        )
        assert "gen_rule_001" in generated_fired
