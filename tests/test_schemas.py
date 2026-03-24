"""
Comprehensive schema tests for Sentinel Pydantic models.
Wave 0 — tests created before implementation (TDD RED phase).
Covers SCHEMA-01 through SCHEMA-04.
"""
import json
import pytest
from datetime import datetime
from pydantic import ValidationError

from sentinel.schemas import Verdict, ClaimCheck, VerdictBoard, Episode, WSEvent, EventType


class TestClaimCheck:
    """Tests for ClaimCheck model (SCHEMA-01)."""

    def test_valid_construction(self):
        """ClaimCheck constructs with all valid fields."""
        cc = ClaimCheck(
            field="amount",
            agent_claimed="$50000",
            independently_found="$50000",
            match=True,
            severity="info",
        )
        assert cc.field == "amount"
        assert cc.agent_claimed == "$50000"
        assert cc.independently_found == "$50000"
        assert cc.match is True
        assert cc.severity == "info"

    def test_invalid_severity_rejected(self):
        """ClaimCheck rejects invalid severity values."""
        with pytest.raises(ValidationError):
            ClaimCheck(
                field="amount",
                agent_claimed="$50000",
                independently_found="$60000",
                match=False,
                severity="bad",
            )

    def test_all_valid_severities(self):
        """ClaimCheck accepts all valid severity levels."""
        for severity in ["critical", "warning", "info"]:
            cc = ClaimCheck(
                field="amount",
                agent_claimed="$50000",
                independently_found="$50000",
                match=True,
                severity=severity,
            )
            assert cc.severity == severity

    def test_match_is_bool(self):
        """ClaimCheck match field is strict bool."""
        cc = ClaimCheck(
            field="beneficiary",
            agent_claimed="Acme Corp",
            independently_found="Acme Corp",
            match=True,
            severity="info",
        )
        assert isinstance(cc.match, bool)

    def test_mismatch_with_critical_severity(self):
        """ClaimCheck constructs with mismatch and critical severity."""
        cc = ClaimCheck(
            field="amount",
            agent_claimed="$50000",
            independently_found="$500000",
            match=False,
            severity="critical",
        )
        assert cc.match is False
        assert cc.severity == "critical"


class TestVerdict:
    """Tests for Verdict model (SCHEMA-01)."""

    def test_valid_construction(self):
        """Verdict constructs with all required fields."""
        v = Verdict(
            agent_id="risk",
            claims_checked=[],
            behavioral_flags=["high_confidence"],
            agent_confidence=0.52,
        )
        assert v.agent_id == "risk"
        assert v.claims_checked == []
        assert v.behavioral_flags == ["high_confidence"]
        assert v.agent_confidence == 0.52

    def test_confidence_lower_boundary(self):
        """Verdict accepts confidence of 0.0."""
        v = Verdict(
            agent_id="risk",
            claims_checked=[],
            behavioral_flags=[],
            agent_confidence=0.0,
        )
        assert v.agent_confidence == 0.0

    def test_confidence_upper_boundary(self):
        """Verdict accepts confidence of 1.0."""
        v = Verdict(
            agent_id="compliance",
            claims_checked=[],
            behavioral_flags=[],
            agent_confidence=1.0,
        )
        assert v.agent_confidence == 1.0

    def test_confidence_above_max_rejected(self):
        """Verdict rejects confidence > 1.0."""
        with pytest.raises(ValidationError):
            Verdict(
                agent_id="risk",
                claims_checked=[],
                behavioral_flags=[],
                agent_confidence=1.01,
            )

    def test_confidence_below_min_rejected(self):
        """Verdict rejects confidence < 0.0."""
        with pytest.raises(ValidationError):
            Verdict(
                agent_id="risk",
                claims_checked=[],
                behavioral_flags=[],
                agent_confidence=-0.01,
            )

    def test_unable_to_verify_default(self):
        """Verdict unable_to_verify defaults to False."""
        v = Verdict(
            agent_id="forensics",
            claims_checked=[],
            behavioral_flags=[],
            agent_confidence=0.75,
        )
        assert v.unable_to_verify is False

    def test_confidence_z_score_optional(self):
        """Verdict confidence_z_score is optional (defaults to None)."""
        v = Verdict(
            agent_id="risk",
            claims_checked=[],
            behavioral_flags=[],
            agent_confidence=0.52,
        )
        assert v.confidence_z_score is None

    def test_verdict_with_claims_checked(self):
        """Verdict accepts a list of ClaimCheck objects."""
        cc = ClaimCheck(
            field="amount",
            agent_claimed="$50000",
            independently_found="$50000",
            match=True,
            severity="info",
        )
        v = Verdict(
            agent_id="compliance",
            claims_checked=[cc],
            behavioral_flags=[],
            agent_confidence=0.85,
        )
        assert len(v.claims_checked) == 1
        assert v.claims_checked[0].field == "amount"


class TestVerdictBoard:
    """Tests for VerdictBoard model (SCHEMA-02)."""

    def test_valid_construction(self):
        """VerdictBoard constructs with all required fields."""
        vb = VerdictBoard(
            mismatches=[],
            behavioral_flags=[],
            agent_confidence=0.52,
            step_sequence_deviation=False,
            hardcoded_rule_fired=False,
        )
        assert vb.mismatches == []
        assert vb.behavioral_flags == []
        assert vb.agent_confidence == 0.52
        assert vb.step_sequence_deviation is False
        assert vb.hardcoded_rule_fired is False

    def test_confidence_bounds(self):
        """VerdictBoard confidence respects 0.0-1.0 bounds."""
        with pytest.raises(ValidationError):
            VerdictBoard(
                mismatches=[],
                behavioral_flags=[],
                agent_confidence=1.5,
                step_sequence_deviation=False,
                hardcoded_rule_fired=False,
            )

    def test_unable_to_verify_default(self):
        """VerdictBoard unable_to_verify defaults to empty list."""
        vb = VerdictBoard(
            mismatches=[],
            behavioral_flags=[],
            agent_confidence=0.52,
            step_sequence_deviation=False,
            hardcoded_rule_fired=False,
        )
        assert vb.unable_to_verify == []

    def test_mismatches_accept_dicts(self):
        """VerdictBoard mismatches accepts list of dicts."""
        vb = VerdictBoard(
            mismatches=[{"field": "amount", "severity": "critical"}],
            behavioral_flags=["step_deviation"],
            agent_confidence=0.25,
            step_sequence_deviation=True,
            hardcoded_rule_fired=False,
        )
        assert len(vb.mismatches) == 1


class TestEpisode:
    """Tests for Episode model (SCHEMA-03)."""

    def _make_verdict_board(self):
        return VerdictBoard(
            mismatches=[],
            behavioral_flags=[],
            agent_confidence=0.52,
            step_sequence_deviation=False,
            hardcoded_rule_fired=False,
        )

    def test_valid_construction(self):
        """Episode constructs with all required fields."""
        ep = Episode(
            gate_decision="NO-GO",
            action_request={"amount": 50000},
            agent_verdicts=[],
            verdict_board=self._make_verdict_board(),
            gate_rationale="blocked due to critical mismatch",
        )
        assert ep.gate_decision == "NO-GO"
        assert ep.action_request == {"amount": 50000}

    def test_invalid_gate_decision_rejected(self):
        """Episode rejects invalid gate_decision values."""
        with pytest.raises(ValidationError):
            Episode(
                gate_decision="BLOCK",
                action_request={"amount": 50000},
                agent_verdicts=[],
                verdict_board=self._make_verdict_board(),
                gate_rationale="test",
            )

    def test_all_valid_gate_decisions(self):
        """Episode accepts GO, NO-GO, and ESCALATE."""
        for decision in ["GO", "NO-GO", "ESCALATE"]:
            ep = Episode(
                gate_decision=decision,
                action_request={"amount": 50000},
                agent_verdicts=[],
                verdict_board=self._make_verdict_board(),
                gate_rationale="test",
            )
            assert ep.gate_decision == decision

    def test_id_auto_generated(self):
        """Episode auto-generates UUID id."""
        ep = Episode(
            gate_decision="GO",
            action_request={},
            agent_verdicts=[],
            verdict_board=self._make_verdict_board(),
            gate_rationale="ok",
        )
        assert ep.id is not None
        assert len(ep.id) > 0

    def test_timestamp_auto_set(self):
        """Episode auto-sets timestamp."""
        ep = Episode(
            gate_decision="GO",
            action_request={},
            agent_verdicts=[],
            verdict_board=self._make_verdict_board(),
            gate_rationale="ok",
        )
        assert isinstance(ep.timestamp, datetime)

    def test_contains_nested_verdicts(self):
        """Episode accepts list of Verdict objects."""
        v = Verdict(
            agent_id="risk",
            claims_checked=[],
            behavioral_flags=[],
            agent_confidence=0.52,
        )
        ep = Episode(
            gate_decision="NO-GO",
            action_request={"amount": 50000},
            agent_verdicts=[v],
            verdict_board=self._make_verdict_board(),
            gate_rationale="blocked",
        )
        assert len(ep.agent_verdicts) == 1
        assert ep.agent_verdicts[0].agent_id == "risk"

    def test_contains_nested_verdict_board(self):
        """Episode accepts and stores VerdictBoard."""
        vb = self._make_verdict_board()
        ep = Episode(
            gate_decision="GO",
            action_request={},
            agent_verdicts=[],
            verdict_board=vb,
            gate_rationale="ok",
        )
        assert ep.verdict_board.agent_confidence == 0.52

    def test_serialization_round_trip(self):
        """Episode.model_dump() produces JSON-serializable dict."""
        v = Verdict(
            agent_id="compliance",
            claims_checked=[
                ClaimCheck(
                    field="amount",
                    agent_claimed="$50000",
                    independently_found="$50000",
                    match=True,
                    severity="info",
                )
            ],
            behavioral_flags=["normal"],
            agent_confidence=0.85,
        )
        ep = Episode(
            gate_decision="GO",
            action_request={"amount": 50000, "beneficiary": "Acme Corp"},
            agent_verdicts=[v],
            verdict_board=self._make_verdict_board(),
            gate_rationale="all checks passed",
        )
        dumped = ep.model_dump()
        assert isinstance(dumped, dict)
        assert "gate_decision" in dumped
        assert "agent_verdicts" in dumped
        assert "verdict_board" in dumped
        # Must be JSON serializable
        serialized = json.dumps(dumped, default=str)
        assert isinstance(serialized, str)

    def test_optional_fields_default(self):
        """Episode optional fields default correctly."""
        ep = Episode(
            gate_decision="GO",
            action_request={},
            agent_verdicts=[],
            verdict_board=self._make_verdict_board(),
            gate_rationale="ok",
        )
        assert ep.rules_fired == []
        assert ep.generated_rules_fired == []
        assert ep.operator_confirmation is None
        assert ep.attack_type is None
        assert ep.generated_rule_source is None
        assert ep.new_rules_deployed == []


class TestWSEvent:
    """Tests for WSEvent model and EventType (SCHEMA-04)."""

    def test_valid_construction(self):
        """WSEvent constructs with a valid event type."""
        ev = WSEvent(
            event="investigation_started",
            timestamp=datetime.utcnow(),
            episode_id="ep-001",
            data={},
        )
        assert ev.event == "investigation_started"
        assert ev.episode_id == "ep-001"

    def test_invalid_event_type_rejected(self):
        """WSEvent rejects invalid event type strings."""
        with pytest.raises(ValidationError):
            WSEvent(
                event="bad_event",
                timestamp=datetime.utcnow(),
                episode_id="ep-001",
                data={},
            )

    def test_all_seven_event_types(self):
        """WSEvent accepts all 7 EventType values."""
        event_types = [
            "investigation_started",
            "agent_completed",
            "verdict_board_assembled",
            "gate_evaluated",
            "episode_written",
            "rule_generated",
            "rule_deployed",
        ]
        assert len(event_types) == 7
        for event_type in event_types:
            ev = WSEvent(
                event=event_type,
                timestamp=datetime.utcnow(),
                episode_id="ep-001",
                data={},
            )
            assert ev.event == event_type

    def test_data_defaults_to_empty_dict(self):
        """WSEvent data field defaults to empty dict."""
        ev = WSEvent(
            event="gate_evaluated",
            timestamp=datetime.utcnow(),
            episode_id="ep-002",
        )
        assert ev.data == {}

    def test_event_type_is_literal(self):
        """EventType is a Literal type alias covering 7 values."""
        # Verify the EventType can be imported and used
        # (type annotation check — just ensure it's accessible)
        assert EventType is not None

    def test_data_accepts_arbitrary_payload(self):
        """WSEvent data accepts arbitrary dict payload."""
        payload = {
            "agent_id": "risk",
            "confidence": 0.52,
            "flags": ["high_z_score"],
        }
        ev = WSEvent(
            event="agent_completed",
            timestamp=datetime.utcnow(),
            episode_id="ep-003",
            data=payload,
        )
        assert ev.data["agent_id"] == "risk"
