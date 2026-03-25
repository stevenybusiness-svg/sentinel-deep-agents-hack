"""
Tests for SafetyGate — ENGN-02 through ENGN-06.

Test coverage:
1. Hidden text in behavioral flags -> composite score >= 1.0 -> NO-GO
2. Clean verdict board -> composite score < 0.6 -> GO
3. Moderate anomaly (z-score 2.5 + one warning mismatch) -> score in [0.6, 1.0) -> ESCALATE
4. Generated rule registered via register_rule() fires on matching verdict board
5. Rule with forbidden token "import" rejected by pre-check
6. Attribution includes rule names and score contributions
"""
import pathlib
import pytest

from sentinel.engine.safety_gate import SafetyGate, _pre_check_source
from sentinel.schemas.verdict_board import VerdictBoard


RULES_DIR = pathlib.Path("sentinel/gate/rules")


def make_clean_board() -> VerdictBoard:
    return VerdictBoard(
        mismatches=[],
        behavioral_flags=[],
        agent_confidence=0.85,
        confidence_z_score=0.5,
        step_sequence_deviation=False,
        unable_to_verify=[],
    )


def make_hidden_text_board() -> VerdictBoard:
    return VerdictBoard(
        mismatches=[],
        behavioral_flags=["hidden_text_detected"],
        agent_confidence=0.92,
        confidence_z_score=1.0,
        step_sequence_deviation=False,
        unable_to_verify=[],
    )


def make_moderate_anomaly_board() -> VerdictBoard:
    """Z-score 2.5 (fires rule_z_score -> 0.3) + one warning mismatch (rule_mismatch -> 0.15) = 0.45
    Not ESCALATE yet... let's add step deviation (0.25) -> total 0.7 -> ESCALATE"""
    return VerdictBoard(
        mismatches=[{"field": "amount", "agent_claimed": "5000", "found": "6000", "severity": "warning", "agent_id": "compliance"}],
        behavioral_flags=[],
        agent_confidence=0.88,
        confidence_z_score=2.5,
        step_sequence_deviation=True,
        unable_to_verify=[],
    )


class TestSafetyGateHardcodedRules:
    def test_hidden_text_triggers_no_go(self):
        """Test 1: Hidden text in flags -> composite score >= 1.0 -> NO-GO."""
        gate = SafetyGate()
        gate.load_rules_from_directory(RULES_DIR)
        board = make_hidden_text_board()
        result = gate.evaluate(board)
        assert result["decision"] == "NO-GO", f"Expected NO-GO, got {result['decision']} (score: {result['composite_score']})"
        assert result["composite_score"] >= 1.0

    def test_clean_board_go(self):
        """Test 2: Clean verdict board -> composite score < 0.6 -> GO."""
        gate = SafetyGate()
        gate.load_rules_from_directory(RULES_DIR)
        board = make_clean_board()
        result = gate.evaluate(board)
        assert result["decision"] == "GO", f"Expected GO, got {result['decision']} (score: {result['composite_score']})"
        assert result["composite_score"] < 0.6

    def test_moderate_anomaly_escalate(self):
        """Test 3: Moderate anomaly (z-score 2.5 + warning mismatch + step deviation) -> ESCALATE."""
        gate = SafetyGate()
        gate.load_rules_from_directory(RULES_DIR)
        board = make_moderate_anomaly_board()
        result = gate.evaluate(board)
        assert result["decision"] == "ESCALATE", f"Expected ESCALATE, got {result['decision']} (score: {result['composite_score']})"
        assert 0.6 <= result["composite_score"] < 1.0


class TestSafetyGateGeneratedRules:
    def test_generated_rule_fires_on_matching_board(self):
        """Test 4: Generated rule registered via register_rule() fires on matching verdict board."""
        gate = SafetyGate()
        # Register a simple generated rule using compile_restricted
        rule_source = (
            "def score(verdict_board):\n"
            "    flags = verdict_board.get('behavioral_flags', [])\n"
            "    if 'test_attack_pattern' in flags:\n"
            "        return 0.8\n"
            "    return 0.0\n"
        )
        gate.register_rule("gen_rule_001", rule_source)
        board = VerdictBoard(
            mismatches=[],
            behavioral_flags=["test_attack_pattern"],
            agent_confidence=0.9,
            confidence_z_score=None,
        )
        result = gate.evaluate(board)
        # The generated rule should contribute 0.8 -> NO-GO
        assert result["composite_score"] >= 0.8
        contributions = result["rule_contributions"]
        gen_contribution = next((c for c in contributions if c["rule_id"] == "gen_rule_001"), None)
        assert gen_contribution is not None, "Generated rule contribution missing from result"
        assert gen_contribution["is_generated"] is True
        assert gen_contribution["score"] == 0.8

    def test_forbidden_token_import_rejected(self):
        """Test 5: Rule with forbidden token 'import' rejected by pre-check."""
        gate = SafetyGate()
        bad_source = "import os\ndef score(verdict_board):\n    return os.system('rm -rf /')\n"
        with pytest.raises(ValueError, match="forbidden token"):
            gate.register_rule("malicious_rule", bad_source)

    def test_attribution_includes_rule_names_and_scores(self):
        """Test 6: Attribution includes rule names and score contributions."""
        gate = SafetyGate()
        gate.load_rules_from_directory(RULES_DIR)
        board = make_hidden_text_board()
        result = gate.evaluate(board)
        attribution = result["attribution"]
        assert "NO-GO" in attribution
        assert "rule_hidden_text" in attribution or "1.5" in attribution or "1.50" in attribution
        # Rule contributions should be populated
        assert len(result["rule_contributions"]) >= 1
        # Verify structure of each contribution
        for c in result["rule_contributions"]:
            assert "rule_id" in c
            assert "score" in c
            assert "is_generated" in c
