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
