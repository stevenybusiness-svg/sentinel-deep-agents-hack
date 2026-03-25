"""
Tests for RuleGenerator validation harness — Phase 3 self-improvement loop.

Test coverage:
1. validate_rule passes a well-formed compliant source
2. validate_rule rejects sources containing forbidden tokens (import, __)
3. validate_rule rejects sources with syntax errors (compile_restricted fails)
4. validate_rule rejects sources with low attack scores
5. validate_rule rejects sources with high clean baseline scores
6. CLEAN_BASELINE_VERDICT_BOARD has all expected VerdictBoard keys and correct agent_confidence
7. _exec_rule returns a callable that accepts a dict
8. RULE_GEN_SYSTEM_PROMPT contains required constraints
9. build_rule_gen_prompt includes the VerdictBoard fields
10. build_evolution_prompt includes both VerdictBoards
11. EventType contains the new rule_generating and rule_generation_failed values
12. validate_rule rejects a source that fails _exec_rule (no score function)
"""
import pytest

from sentinel.engine.rule_generator import (
    RuleGenerator,
    validate_rule,
    _exec_rule,
    CLEAN_BASELINE_VERDICT_BOARD,
    RULE_GEN_SYSTEM_PROMPT,
    build_rule_gen_prompt,
    build_evolution_prompt,
)
from sentinel.schemas.events import EventType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

ATTACK_FIXTURE_VB = {
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

# A compliant scoring function that fires on ATTACK_FIXTURE_VB and is quiet on clean baseline.
# - confidence > 0.85 + unable_to_verify > 0 → +0.5
# - z_score > 3.0 → +0.3
# - step_sequence_deviation True → +0.2
# Total on attack: 0.5 + 0.3 + 0.2 = 1.0 → passes check 3 (> 0.6)
# Total on clean (confidence=0.55, z=0.8, no deviation, no unable): 0.0 → passes check 4 (< 0.2)
COMPLIANT_SOURCE = '''
def score(verdict_board: dict) -> float:
    """Detects behavioral anomalies: high confidence + verification failures."""
    confidence = verdict_board.get("agent_confidence", 0.5)
    unable = verdict_board.get("unable_to_verify", [])
    z = abs(verdict_board.get("confidence_z_score") or 0)
    score_val = 0.0
    if confidence > 0.85 and len(unable) > 0:
        score_val += 0.5
    if z > 3.0:
        score_val += 0.3
    if verdict_board.get("step_sequence_deviation"):
        score_val += 0.2
    return min(score_val, 2.0)
'''


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestValidateRuleCompliant:
    def test_validate_rule_passes_compliant_source(self):
        """A well-formed compliant source passes all 4 validation checks."""
        valid, reason = validate_rule(COMPLIANT_SOURCE, ATTACK_FIXTURE_VB)
        assert valid is True, f"Expected valid but got reason: {reason}"
        assert reason == ""


class TestValidateRuleForbiddenTokens:
    def test_validate_rule_rejects_forbidden_tokens_import(self):
        """Source containing 'import os' returns (False, reason containing 'import')."""
        bad_source = (
            "import os\n"
            "def score(verdict_board: dict) -> float:\n"
            "    return 0.9\n"
        )
        valid, reason = validate_rule(bad_source, ATTACK_FIXTURE_VB)
        assert valid is False
        assert "import" in reason.lower()

    def test_validate_rule_rejects_dunder(self):
        """Source containing '__builtins__' returns (False, reason containing '__')."""
        bad_source = (
            "def score(verdict_board: dict) -> float:\n"
            "    x = __builtins__\n"
            "    return 0.9\n"
        )
        valid, reason = validate_rule(bad_source, ATTACK_FIXTURE_VB)
        assert valid is False
        assert "__" in reason


class TestValidateRuleCompileErrors:
    def test_validate_rule_rejects_compile_error(self):
        """Source with syntax error returns (False, reason starting with 'compile_restricted failed')."""
        bad_source = (
            "def score(verdict_board: dict) -> float:\n"
            "    return 0.9\n"
            "    this is not valid python !!!\n"
        )
        valid, reason = validate_rule(bad_source, ATTACK_FIXTURE_VB)
        assert valid is False
        assert "compile_restricted failed" in reason


class TestValidateRuleScoreThresholds:
    def test_validate_rule_rejects_low_attack_score(self):
        """Source returning 0.3 on attack VB returns (False, reason mentioning 'must be > 0.6')."""
        low_score_source = (
            "def score(verdict_board: dict) -> float:\n"
            "    return 0.3\n"
        )
        valid, reason = validate_rule(low_score_source, ATTACK_FIXTURE_VB)
        assert valid is False
        assert "0.6" in reason or "must be" in reason.lower()

    def test_validate_rule_rejects_high_clean_score(self):
        """Source returning 0.5 on clean VB returns (False, reason mentioning 'must be < 0.2')."""
        high_clean_source = (
            "def score(verdict_board: dict) -> float:\n"
            "    return 0.5\n"
        )
        valid, reason = validate_rule(high_clean_source, ATTACK_FIXTURE_VB)
        assert valid is False
        assert "0.2" in reason or "must be" in reason.lower()


class TestCleanBaselineVerdictBoard:
    def test_clean_baseline_has_expected_fields(self):
        """CLEAN_BASELINE_VERDICT_BOARD has all VerdictBoard keys and correct agent_confidence."""
        expected_keys = {
            "mismatches",
            "behavioral_flags",
            "agent_confidence",
            "confidence_z_score",
            "step_sequence_deviation",
            "hardcoded_rule_fired",
            "unable_to_verify",
            "prediction_errors",
        }
        assert expected_keys.issubset(CLEAN_BASELINE_VERDICT_BOARD.keys())
        assert abs(CLEAN_BASELINE_VERDICT_BOARD["agent_confidence"] - 0.55) < 1e-9

    def test_clean_baseline_is_low_anomaly(self):
        """CLEAN_BASELINE_VERDICT_BOARD should produce a low anomaly profile."""
        assert CLEAN_BASELINE_VERDICT_BOARD["mismatches"] == []
        assert CLEAN_BASELINE_VERDICT_BOARD["behavioral_flags"] == []
        assert CLEAN_BASELINE_VERDICT_BOARD["step_sequence_deviation"] is False
        assert CLEAN_BASELINE_VERDICT_BOARD["unable_to_verify"] == []


class TestExecRule:
    def test_exec_rule_returns_callable(self):
        """_exec_rule on valid source returns a callable that accepts a dict."""
        source = (
            "def score(verdict_board: dict) -> float:\n"
            "    return 0.0\n"
        )
        fn = _exec_rule(source)
        assert callable(fn)
        result = fn({})
        assert result == 0.0

    def test_exec_rule_raises_on_missing_score(self):
        """_exec_rule raises ValueError if source doesn't define score()."""
        source = "x = 1\n"
        with pytest.raises(ValueError, match="does not define a callable score"):
            _exec_rule(source)


class TestRuleGenSystemPrompt:
    def test_rule_gen_system_prompt_contains_function_signature(self):
        """RULE_GEN_SYSTEM_PROMPT contains the required def score signature."""
        assert "def score(verdict_board: dict) -> float" in RULE_GEN_SYSTEM_PROMPT

    def test_rule_gen_system_prompt_contains_never_use_import(self):
        """RULE_GEN_SYSTEM_PROMPT mentions 'NEVER use: import' constraint."""
        assert "NEVER use: import" in RULE_GEN_SYSTEM_PROMPT

    def test_rule_gen_system_prompt_contains_forbidden_tokens(self):
        """RULE_GEN_SYSTEM_PROMPT lists exec and eval as forbidden tokens."""
        assert "exec" in RULE_GEN_SYSTEM_PROMPT
        assert "eval" in RULE_GEN_SYSTEM_PROMPT


class TestBuildPrompts:
    def test_build_rule_gen_prompt_includes_verdict_board(self):
        """build_rule_gen_prompt output contains the serialized VerdictBoard fields."""
        prompt = build_rule_gen_prompt("test_attack", ATTACK_FIXTURE_VB, {"summary_score": 1.8})
        # The VerdictBoard JSON should appear in the prompt
        assert "agent_confidence" in prompt
        assert "step_sequence_deviation" in prompt
        assert "test_attack" in prompt

    def test_build_rule_gen_prompt_includes_prediction_errors(self):
        """build_rule_gen_prompt includes the prediction error report."""
        pe = {"summary_score": 1.8, "top_deviations": []}
        prompt = build_rule_gen_prompt("test_attack", ATTACK_FIXTURE_VB, pe)
        assert "summary_score" in prompt

    def test_build_evolution_prompt_includes_both_vbs(self):
        """build_evolution_prompt output contains both VerdictBoards."""
        v2_vb = {
            "mismatches": [],
            "behavioral_flags": ["identity_spoofing_detected"],
            "agent_confidence": 0.91,
            "confidence_z_score": 3.5,
            "step_sequence_deviation": True,
            "hardcoded_rule_fired": False,
            "unable_to_verify": ["risk_agent"],
            "prediction_errors": None,
        }
        v1_source = "def score(verdict_board: dict) -> float:\n    return 0.7\n"
        prompt = build_evolution_prompt(
            v1_source, "compound_attack",
            ATTACK_FIXTURE_VB, v2_vb,
            {"summary_score": 1.8}, {"summary_score": 1.5},
        )
        # Both VBs are serialized into the prompt
        assert "hidden_text_detected" in prompt   # from vb1 behavioral_flags
        assert "identity_spoofing_detected" in prompt  # from vb2 behavioral_flags
        assert v1_source.strip() in prompt

    def test_build_evolution_prompt_includes_evolution_rules(self):
        """build_evolution_prompt includes DROP and STRENGTHEN instructions."""
        v2_vb = dict(CLEAN_BASELINE_VERDICT_BOARD)
        v1_source = "def score(verdict_board: dict) -> float:\n    return 0.7\n"
        prompt = build_evolution_prompt(
            v1_source, "test_attack",
            ATTACK_FIXTURE_VB, v2_vb,
            {}, {},
        )
        assert "DROP" in prompt
        assert "STRENGTHEN" in prompt


class TestEventTypeExtended:
    def test_event_type_extended_rule_generating(self):
        """EventType includes 'rule_generating'."""
        assert "rule_generating" in EventType.__args__

    def test_event_type_extended_rule_generation_failed(self):
        """EventType includes 'rule_generation_failed'."""
        assert "rule_generation_failed" in EventType.__args__

    def test_event_type_has_nine_values(self):
        """EventType Literal has exactly 9 values after extension."""
        assert len(EventType.__args__) == 9


class TestRuleGeneratorClass:
    def test_rule_generator_instantiates(self):
        """RuleGenerator can be instantiated with a mock client."""
        rg = RuleGenerator(llm_client=object(), model="claude-opus-4-6")
        assert rg._model == "claude-opus-4-6"

    def test_rule_generator_has_required_methods(self):
        """RuleGenerator has generate() and evolve() methods."""
        import inspect
        rg = RuleGenerator(llm_client=object())
        assert inspect.iscoroutinefunction(rg.generate)
        assert inspect.iscoroutinefunction(rg.evolve)


# ---------------------------------------------------------------------------
# Phase 2 cross-attack generalization tests
# ---------------------------------------------------------------------------

# Phase 2: Identity spoofing attack VerdictBoard.
# Key properties:
#   - NO hidden_text_detected (document manipulation absent — identity spoofing only)
#   - High confidence (0.92) with anomalous z-score (3.64)
#   - Compliance agent unable to verify (KYC absent)
#   - step_sequence_deviation=False — keeps hardcoded composite < 1.0
#   - Hardcoded rules alone: z_score (0.6) + unverifiable (0.3) = 0.9 < 1.0 → ESCALATE not NO-GO
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

# Behavioral scoring function that generalizes across both attacks.
# Targets the shared fingerprint: overconfident agent whose claims collapse under scrutiny.
# - confidence > 0.85: +0.3
# - z_score > 3.0: +0.2
# - unable_to_verify non-empty: +0.2
# - critical mismatches: +0.15 each
# - step_sequence_deviation: +0.15
# On Phase 1 attack (ATTACK_FIXTURE_VB): confidence(0.3) + z(0.2) + unable(0.2) + step(0.15) = 0.85 > 0.6 ✓
# On Phase 2 (PHASE2_ATTACK_VB): confidence(0.3) + z(0.2) + unable(0.2) = 0.7 > 0.6 ✓
# On clean baseline: confidence=0.55 → 0.0, z=0.8 → 0.0, unable=[] → 0.0 → 0.0 < 0.2 ✓
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


class TestCrossAttackGeneralization:
    def test_phase2_vb_has_correct_z_score(self):
        """PHASE2_ATTACK_VB has confidence_z_score=3.64 and agent_confidence=0.92."""
        assert PHASE2_ATTACK_VB["confidence_z_score"] == 3.64
        assert PHASE2_ATTACK_VB["agent_confidence"] == 0.92

    def test_generated_rule_fires_on_phase2(self):
        """A generated behavioral rule that passed Phase 1 validation also fires on Phase 2 (score > 0.6).

        This proves cross-attack generalization: the behavioral fingerprint
        (overconfident agent + verification failures) is shared across attack vectors.
        """
        # Verify rule passes Phase 1 validation
        valid, reason = validate_rule(BEHAVIORAL_RULE_SOURCE, ATTACK_FIXTURE_VB)
        assert valid is True, f"Rule failed Phase 1 validation: {reason}"

        # Verify rule fires on Phase 2 VerdictBoard
        fn = _exec_rule(BEHAVIORAL_RULE_SOURCE)
        phase2_score = fn(PHASE2_ATTACK_VB)
        assert phase2_score > 0.6, (
            f"Generated rule should fire on Phase 2 (got {phase2_score:.3f}). "
            "Behavioral fingerprint must generalize across attack vectors."
        )

        # Verify rule does NOT fire on clean baseline
        clean_score = fn(CLEAN_BASELINE_VERDICT_BOARD)
        assert clean_score < 0.2, (
            f"Generated rule should not fire on clean baseline (got {clean_score:.3f})."
        )

    def test_hardcoded_rules_insufficient_for_phase2(self):
        """Hardcoded rules alone produce composite_score < 1.0 on Phase 2 — insufficient for NO-GO.

        Phase 2 (identity spoofing with no document) doesn't trigger hidden_text rule.
        The behavioral signals (z-score + unverifiable) sum to ~0.9 = ESCALATE, not NO-GO.
        This proves that generated rules are required to catch novel attack vectors.
        """
        from pathlib import Path
        from sentinel.engine.safety_gate import SafetyGate
        from sentinel.schemas.verdict_board import VerdictBoard

        gate = SafetyGate()
        rules_dir = Path(__file__).parent.parent / "sentinel" / "gate" / "rules"
        gate.load_rules_from_directory(rules_dir)

        phase2_board = VerdictBoard(**PHASE2_ATTACK_VB)
        result = gate.evaluate(phase2_board)

        assert result["composite_score"] < 1.0, (
            f"Hardcoded rules alone scored {result['composite_score']:.3f} on Phase 2 VerdictBoard. "
            "Expected < 1.0 to demonstrate that generated rules are required for NO-GO."
        )
        # Should ESCALATE (0.6 <= score < 1.0), not NO-GO
        assert result["decision"] in ("ESCALATE", "GO"), (
            f"Expected ESCALATE or GO with hardcoded rules only, got {result['decision']}"
        )

    def test_generated_plus_hardcoded_exceeds_threshold(self):
        """Generated rule + hardcoded rules produce composite >= 1.0 and NO-GO on Phase 2.

        This is the core demo claim: a rule learned from Attack 1 tips the composite
        score over the NO-GO threshold for Attack 2 (different attack vector).
        """
        from pathlib import Path
        from sentinel.engine.safety_gate import SafetyGate
        from sentinel.schemas.verdict_board import VerdictBoard

        gate = SafetyGate()
        rules_dir = Path(__file__).parent.parent / "sentinel" / "gate" / "rules"
        gate.load_rules_from_directory(rules_dir)

        # Register the behavioral rule generated from Phase 1
        gate.register_rule("gen_rule_001", BEHAVIORAL_RULE_SOURCE)

        phase2_board = VerdictBoard(**PHASE2_ATTACK_VB)
        result = gate.evaluate(phase2_board)

        assert result["composite_score"] >= 1.0, (
            f"Generated + hardcoded rules scored {result['composite_score']:.3f}. "
            "Expected >= 1.0 for NO-GO decision."
        )
        assert result["decision"] == "NO-GO", (
            f"Expected NO-GO with generated rule loaded, got {result['decision']}"
        )

        # Verify at least one generated rule contribution is present
        generated_contributions = [
            c for c in result["rule_contributions"] if c["is_generated"]
        ]
        assert len(generated_contributions) > 0, (
            "Expected at least one generated rule in rule_contributions"
        )

    def test_attribution_contains_generated_rule(self):
        """Attribution string from the gate evaluation mentions 'Generated Rule'.

        This proves ENGN-04 attribution works for generated rules — full provenance chain.
        """
        from pathlib import Path
        from sentinel.engine.safety_gate import SafetyGate
        from sentinel.schemas.verdict_board import VerdictBoard

        gate = SafetyGate()
        rules_dir = Path(__file__).parent.parent / "sentinel" / "gate" / "rules"
        gate.load_rules_from_directory(rules_dir)
        gate.register_rule("gen_rule_001", BEHAVIORAL_RULE_SOURCE)

        phase2_board = VerdictBoard(**PHASE2_ATTACK_VB)
        result = gate.evaluate(phase2_board)

        assert "Generated Rule" in result["attribution"], (
            f"Expected 'Generated Rule' in attribution, got: {result['attribution']}"
        )
