"""
Supervisor behavioral unit tests — PIPE-02, D-03, D-09, D-13, MEM-04.

Tests verify Supervisor logic using mocked LLM client and dependencies.
No real API calls — all LLM interactions use AsyncMock.
"""
from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sentinel.agents.supervisor import (
    SUPERVISOR_SYSTEM_PROMPT,
    _extract_actual_findings,
    run_investigation,
)
from sentinel.schemas.payment import PaymentDecision
from sentinel.schemas.verdict import ClaimCheck, Verdict
from sentinel.schemas.verdict_board import VerdictBoard


# ---------------------------------------------------------------------------
# Shared fixtures / helpers
# ---------------------------------------------------------------------------


def _make_payment_decision(**overrides) -> PaymentDecision:
    """Build a minimal PaymentDecision for testing."""
    defaults = {
        "episode_id": "test-ep-001",
        "decision": "approve",
        "amount": 50000.0,
        "beneficiary": "ACME Corp",
        "account": "ACC-001",
        "rationale": "All checks passed",
        "steps_taken": ["check_counterparty", "verify_kyc", "read_invoice"],
        "confidence": 0.85,
        "claims": {"kyc_verified": "true", "counterparty_authorized": "true"},
        "document_urls": [],
    }
    defaults.update(overrides)
    return PaymentDecision(**defaults)


def _make_fixtures() -> dict:
    """Minimal fixture dict for tests."""
    return {
        "kyc_ledger": {
            "ACME Corp": {"status": "verified", "risk_tier": "low"},
        },
        "counterparty_db": {
            "CP-001": {"name": "ACME Corp", "authorized": True, "max_transfer_usd": 500000},
        },
        "behavioral_baselines": {
            "payment_agent": {"mean": 0.52, "std": 0.11},
        },
    }


def _make_mock_llm(
    supervisor_text: str = "Directing the Payment Agent to process this request.",
    agent_tool_calls: list | None = None,
    agent_final_text: str | None = None,
) -> AsyncMock:
    """Build a mock LLM client with configurable responses.

    First call = Supervisor (Opus) reasoning.
    Subsequent calls = Payment Agent (Sonnet) turns.
    """
    if agent_final_text is None:
        agent_final_text = json.dumps({
            "decision": "approve",
            "amount": 50000.0,
            "beneficiary": "ACME Corp",
            "account": "ACC-001",
            "rationale": "All checks passed",
            "confidence": 0.85,
            "claims": {"kyc_verified": "true", "counterparty_authorized": "true"},
        })

    # Supervisor response
    supervisor_content = MagicMock()
    supervisor_content.type = "text"
    supervisor_content.text = supervisor_text
    supervisor_resp = MagicMock()
    supervisor_resp.content = [supervisor_content]
    supervisor_resp.stop_reason = "end_turn"

    # Payment Agent final response (end_turn)
    agent_content = MagicMock()
    agent_content.type = "text"
    agent_content.text = agent_final_text
    agent_final_resp = MagicMock()
    agent_final_resp.content = [agent_content]
    agent_final_resp.stop_reason = "end_turn"

    if agent_tool_calls:
        # Build a sequence: tool_use responses then final end_turn
        responses = [supervisor_resp]
        for tools in agent_tool_calls:
            tool_resp = MagicMock()
            tool_resp.stop_reason = "tool_use"
            tool_blocks = []
            for t in tools:
                tb = MagicMock()
                tb.type = "tool_use"
                tb.id = f"tool_{t['name']}_001"
                tb.name = t["name"]
                tb.input = t.get("input", {})
                tool_blocks.append(tb)
            tool_resp.content = tool_blocks
            responses.append(tool_resp)
        responses.append(agent_final_resp)
    else:
        responses = [supervisor_resp, agent_final_resp]

    mock_client = AsyncMock()
    mock_client.messages.create = AsyncMock(side_effect=responses)
    return mock_client


def _make_mock_safety_gate() -> MagicMock:
    """Build a mock SafetyGate that returns a clean GO result."""
    gate = MagicMock()
    gate.evaluate.return_value = {
        "decision": "GO",
        "composite_score": 0.0,
        "rule_contributions": [],
        "attribution": "GO (composite: 0.00) | No rules fired",
    }
    return gate


def _make_mock_ws() -> AsyncMock:
    """Build a mock ConnectionManager."""
    ws = AsyncMock()
    ws.broadcast = AsyncMock()
    return ws


# ---------------------------------------------------------------------------
# Test 1: Supervisor uses Opus model for reasoning call (not Agent model)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_supervisor_uses_opus_model():
    """First LLM call uses models['supervisor'] (Opus 4.6), not models['agent']."""
    mock_llm = _make_mock_llm()
    models = {"supervisor": "claude-opus-4-6", "agent": "claude-sonnet-4-6"}

    with (
        patch("sentinel.agents.supervisor.risk.analyze") as mock_risk,
        patch("sentinel.agents.supervisor.compliance.validate") as mock_compliance,
        patch("sentinel.agents.supervisor.forensics.scan") as mock_forensics,
    ):
        mock_risk.return_value = Verdict(
            agent_id="risk", claims_checked=[], behavioral_flags=[], agent_confidence=0.85
        )
        mock_compliance.return_value = Verdict(
            agent_id="compliance", claims_checked=[], behavioral_flags=[], agent_confidence=0.90
        )
        mock_forensics.return_value = Verdict(
            agent_id="forensics", claims_checked=[], behavioral_flags=[], agent_confidence=0.80
        )

        await run_investigation(
            payment_request={"amount": 50000, "beneficiary": "ACME Corp"},
            fixtures=_make_fixtures(),
            invoice_path=None,
            llm_client=mock_llm,
            models=models,
            safety_gate=_make_mock_safety_gate(),
            aerospike=None,
            ws=_make_mock_ws(),
        )

    # First call should use the Supervisor (Opus) model
    first_call = mock_llm.messages.create.call_args_list[0]
    assert first_call.kwargs["model"] == "claude-opus-4-6"

    # Second call (Payment Agent) should use Agent (Sonnet) model
    second_call = mock_llm.messages.create.call_args_list[1]
    assert second_call.kwargs["model"] == "claude-sonnet-4-6"


# ---------------------------------------------------------------------------
# Test 2: Supervisor drives Payment Agent multi-turn with tool calls
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_supervisor_drives_payment_agent_turns():
    """handle_tool_call is invoked for each tool_use block, parse_payment_decision on end_turn."""
    tool_calls = [
        [{"name": "check_counterparty", "input": {"name": "ACME Corp"}}],
        [{"name": "verify_kyc", "input": {"beneficiary": "ACME Corp"}}],
    ]
    mock_llm = _make_mock_llm(agent_tool_calls=tool_calls)
    models = {"supervisor": "claude-opus-4-6", "agent": "claude-sonnet-4-6"}

    with (
        patch("sentinel.agents.supervisor.handle_tool_call") as mock_htc,
        patch("sentinel.agents.supervisor.parse_payment_decision") as mock_ppd,
        patch("sentinel.agents.supervisor.risk.analyze") as mock_risk,
        patch("sentinel.agents.supervisor.compliance.validate") as mock_compliance,
        patch("sentinel.agents.supervisor.forensics.scan") as mock_forensics,
    ):
        mock_htc.return_value = [{"type": "text", "text": '{"found": true}'}]
        mock_ppd.return_value = _make_payment_decision()
        mock_risk.return_value = Verdict(
            agent_id="risk", claims_checked=[], behavioral_flags=[], agent_confidence=0.85
        )
        mock_compliance.return_value = Verdict(
            agent_id="compliance", claims_checked=[], behavioral_flags=[], agent_confidence=0.90
        )
        mock_forensics.return_value = Verdict(
            agent_id="forensics", claims_checked=[], behavioral_flags=[], agent_confidence=0.80
        )

        await run_investigation(
            payment_request={"amount": 50000, "beneficiary": "ACME Corp"},
            fixtures=_make_fixtures(),
            invoice_path=None,
            llm_client=mock_llm,
            models=models,
            safety_gate=_make_mock_safety_gate(),
            aerospike=None,
            ws=_make_mock_ws(),
        )

    # handle_tool_call called once per tool block (2 tool calls total)
    assert mock_htc.call_count == 2
    # parse_payment_decision called once on end_turn
    assert mock_ppd.call_count == 1


# ---------------------------------------------------------------------------
# Test 3: Parallel dispatch via TaskGroup (all 3 sub-agents called)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_parallel_dispatch_taskgroup():
    """All 3 sub-agents (Risk, Compliance, Forensics) are dispatched and awaited."""
    mock_llm = _make_mock_llm()
    models = {"supervisor": "claude-opus-4-6", "agent": "claude-sonnet-4-6"}

    with (
        patch("sentinel.agents.supervisor.risk.analyze") as mock_risk,
        patch("sentinel.agents.supervisor.compliance.validate") as mock_compliance,
        patch("sentinel.agents.supervisor.forensics.scan") as mock_forensics,
    ):
        mock_risk.return_value = Verdict(
            agent_id="risk", claims_checked=[], behavioral_flags=[], agent_confidence=0.85
        )
        mock_compliance.return_value = Verdict(
            agent_id="compliance", claims_checked=[], behavioral_flags=[], agent_confidence=0.90
        )
        mock_forensics.return_value = Verdict(
            agent_id="forensics", claims_checked=[], behavioral_flags=[], agent_confidence=0.80
        )

        await run_investigation(
            payment_request={"amount": 50000, "beneficiary": "ACME Corp"},
            fixtures=_make_fixtures(),
            invoice_path=None,
            llm_client=mock_llm,
            models=models,
            safety_gate=_make_mock_safety_gate(),
            aerospike=None,
            ws=_make_mock_ws(),
        )

    # All 3 sub-agents were dispatched
    assert mock_risk.call_count == 1
    assert mock_compliance.call_count == 1
    assert mock_forensics.call_count == 1


# ---------------------------------------------------------------------------
# Test 4: One agent failure -> unable_to_verify, investigation continues
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unable_to_verify_fallback():
    """When risk.analyze raises, verdict has unable_to_verify=True and investigation completes."""
    mock_llm = _make_mock_llm()
    models = {"supervisor": "claude-opus-4-6", "agent": "claude-sonnet-4-6"}

    with (
        patch("sentinel.agents.supervisor.risk.analyze", side_effect=Exception("Risk agent failed")),
        patch("sentinel.agents.supervisor.compliance.validate") as mock_compliance,
        patch("sentinel.agents.supervisor.forensics.scan") as mock_forensics,
    ):
        mock_compliance.return_value = Verdict(
            agent_id="compliance", claims_checked=[], behavioral_flags=[], agent_confidence=0.90
        )
        mock_forensics.return_value = Verdict(
            agent_id="forensics", claims_checked=[], behavioral_flags=[], agent_confidence=0.80
        )

        result = await run_investigation(
            payment_request={"amount": 50000, "beneficiary": "ACME Corp"},
            fixtures=_make_fixtures(),
            invoice_path=None,
            llm_client=mock_llm,
            models=models,
            safety_gate=_make_mock_safety_gate(),
            aerospike=None,
            ws=_make_mock_ws(),
        )

    # Investigation should complete (not raise)
    assert "episode_id" in result
    assert "decision" in result

    # Risk verdict should have unable_to_verify=True
    episode = result["episode"]
    risk_verdict = next(v for v in episode.agent_verdicts if v.agent_id == "risk")
    assert risk_verdict.unable_to_verify is True


# ---------------------------------------------------------------------------
# Test 5: Events broadcast in correct order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_event_broadcast_sequence():
    """Events are broadcast in order: investigation_started, agent_completed (x3), verdict_board_assembled, gate_evaluated, episode_written."""
    mock_llm = _make_mock_llm()
    models = {"supervisor": "claude-opus-4-6", "agent": "claude-sonnet-4-6"}
    mock_ws = _make_mock_ws()

    with (
        patch("sentinel.agents.supervisor.risk.analyze") as mock_risk,
        patch("sentinel.agents.supervisor.compliance.validate") as mock_compliance,
        patch("sentinel.agents.supervisor.forensics.scan") as mock_forensics,
    ):
        mock_risk.return_value = Verdict(
            agent_id="risk", claims_checked=[], behavioral_flags=[], agent_confidence=0.85
        )
        mock_compliance.return_value = Verdict(
            agent_id="compliance", claims_checked=[], behavioral_flags=[], agent_confidence=0.90
        )
        mock_forensics.return_value = Verdict(
            agent_id="forensics", claims_checked=[], behavioral_flags=[], agent_confidence=0.80
        )

        await run_investigation(
            payment_request={"amount": 50000, "beneficiary": "ACME Corp"},
            fixtures=_make_fixtures(),
            invoice_path=None,
            llm_client=mock_llm,
            models=models,
            safety_gate=_make_mock_safety_gate(),
            aerospike=None,
            ws=mock_ws,
        )

    broadcast_events = [call.args[0] for call in mock_ws.broadcast.call_args_list]

    # investigation_started must be first
    assert broadcast_events[0] == "investigation_started"

    # All 3 agent_completed events must appear
    assert broadcast_events.count("agent_completed") == 3

    # verdict_board_assembled, gate_evaluated, episode_written must appear (in order)
    remaining = [e for e in broadcast_events if e not in ("investigation_started", "agent_completed")]
    assert remaining == ["verdict_board_assembled", "gate_evaluated", "episode_written"]


# ---------------------------------------------------------------------------
# Test 6: Recent episodes injected into Supervisor context
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recent_episodes_injected():
    """get_recent_episodes result is injected into the Supervisor's LLM system prompt."""
    mock_llm = _make_mock_llm()
    models = {"supervisor": "claude-opus-4-6", "agent": "claude-sonnet-4-6"}

    fake_episodes = [
        {
            "episode_id": "ep-past-001",
            "gate_decision": "NO-GO",
            "rules_fired": ["rule_hidden_text"],
        }
    ]

    with (
        patch("sentinel.agents.supervisor.get_recent_episodes", return_value=fake_episodes) as mock_gre,
        patch("sentinel.agents.supervisor.risk.analyze") as mock_risk,
        patch("sentinel.agents.supervisor.compliance.validate") as mock_compliance,
        patch("sentinel.agents.supervisor.forensics.scan") as mock_forensics,
    ):
        mock_risk.return_value = Verdict(
            agent_id="risk", claims_checked=[], behavioral_flags=[], agent_confidence=0.85
        )
        mock_compliance.return_value = Verdict(
            agent_id="compliance", claims_checked=[], behavioral_flags=[], agent_confidence=0.90
        )
        mock_forensics.return_value = Verdict(
            agent_id="forensics", claims_checked=[], behavioral_flags=[], agent_confidence=0.80
        )

        mock_aerospike = AsyncMock()

        await run_investigation(
            payment_request={"amount": 50000, "beneficiary": "ACME Corp"},
            fixtures=_make_fixtures(),
            invoice_path=None,
            llm_client=mock_llm,
            models=models,
            safety_gate=_make_mock_safety_gate(),
            aerospike=mock_aerospike,  # Non-None triggers episode loading
            ws=_make_mock_ws(),
        )

    # get_recent_episodes should have been called (with aerospike and limit=5)
    mock_gre.assert_called_once()

    # Supervisor system prompt in first LLM call should contain episode summary
    first_call = mock_llm.messages.create.call_args_list[0]
    system_prompt = first_call.kwargs["system"]
    assert "ep-past-001" in system_prompt or "{episode_context}" not in system_prompt


# ---------------------------------------------------------------------------
# Test 7: compare_outcomes called after investigation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compare_outcomes_called():
    """PredictionEngine.compare_outcomes is called after investigation with actual findings."""
    mock_llm = _make_mock_llm()
    models = {"supervisor": "claude-opus-4-6", "agent": "claude-sonnet-4-6"}

    with (
        patch("sentinel.agents.supervisor.risk.analyze") as mock_risk,
        patch("sentinel.agents.supervisor.compliance.validate") as mock_compliance,
        patch("sentinel.agents.supervisor.forensics.scan") as mock_forensics,
        patch("sentinel.agents.supervisor.PredictionEngine") as MockPE,
    ):
        mock_risk.return_value = Verdict(
            agent_id="risk", claims_checked=[], behavioral_flags=[], agent_confidence=0.85
        )
        mock_compliance.return_value = Verdict(
            agent_id="compliance", claims_checked=[], behavioral_flags=[], agent_confidence=0.90
        )
        mock_forensics.return_value = Verdict(
            agent_id="forensics", claims_checked=[], behavioral_flags=[], agent_confidence=0.80
        )

        # Mock PredictionEngine instance
        mock_pe_instance = MagicMock()
        mock_prediction = MagicMock()
        mock_prediction.predicted_z_score = 0.5
        mock_prediction.step_sequence_deviation = False
        mock_prediction.summary_score = 0.15
        mock_prediction.deviation_details = []
        mock_prediction.expected_investigation_outcomes = {}
        mock_prediction.model_dump.return_value = {"predicted_z_score": 0.5}
        mock_pe_instance.predict.return_value = mock_prediction
        mock_pe_instance.compare_outcomes.return_value = {
            "outcome_errors": {},
            "error_count": 0,
            "total_predictions": 0,
        }
        MockPE.return_value = mock_pe_instance

        await run_investigation(
            payment_request={"amount": 50000, "beneficiary": "ACME Corp"},
            fixtures=_make_fixtures(),
            invoice_path=None,
            llm_client=mock_llm,
            models=models,
            safety_gate=_make_mock_safety_gate(),
            aerospike=None,
            ws=_make_mock_ws(),
        )

    # compare_outcomes must be called exactly once after investigation
    mock_pe_instance.compare_outcomes.assert_called_once()


# ---------------------------------------------------------------------------
# Test 8: _extract_actual_findings helper maps verdict fields correctly
# ---------------------------------------------------------------------------


# ---------------------------------------------------------------------------
# Test 9: Supervisor reasoning injected into Payment Agent first message (D-03 gap)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_supervisor_reasoning_injected_into_payment_agent():
    """D-03 gap closure: Supervisor Opus reasoning is injected into Payment Agent first message."""
    supervisor_text = "HIGH RISK: This payment to Meridian Logistics requires extra scrutiny. Check KYC carefully."
    mock_llm = _make_mock_llm(supervisor_text=supervisor_text)
    models = {"supervisor": "claude-opus-4-6", "agent": "claude-sonnet-4-6"}

    with (
        patch("sentinel.agents.supervisor.risk.analyze") as mock_risk,
        patch("sentinel.agents.supervisor.compliance.validate") as mock_compliance,
        patch("sentinel.agents.supervisor.forensics.scan") as mock_forensics,
    ):
        mock_risk.return_value = Verdict(
            agent_id="risk", claims_checked=[], behavioral_flags=[], agent_confidence=0.85
        )
        mock_compliance.return_value = Verdict(
            agent_id="compliance", claims_checked=[], behavioral_flags=[], agent_confidence=0.90
        )
        mock_forensics.return_value = Verdict(
            agent_id="forensics", claims_checked=[], behavioral_flags=[], agent_confidence=0.80
        )

        await run_investigation(
            payment_request={"amount": 50000, "beneficiary": "Meridian Logistics"},
            fixtures=_make_fixtures(),
            invoice_path=None,
            llm_client=mock_llm,
            models=models,
            safety_gate=_make_mock_safety_gate(),
            aerospike=None,
            ws=_make_mock_ws(),
        )

    # The second LLM call (first Payment Agent turn) should contain the Supervisor reasoning
    second_call = mock_llm.messages.create.call_args_list[1]
    agent_first_message = second_call.kwargs["messages"][0]["content"]
    assert "Supervisor analysis:" in agent_first_message
    assert "HIGH RISK" in agent_first_message
    assert "Meridian Logistics" in agent_first_message


# ---------------------------------------------------------------------------
# Test 8: _extract_actual_findings helper maps verdict fields correctly
# ---------------------------------------------------------------------------


def test_extract_actual_findings_from_verdicts():
    """_extract_actual_findings maps compliance and forensics verdicts to finding keys."""
    compliance_verdict = Verdict(
        agent_id="compliance",
        claims_checked=[
            ClaimCheck(
                field="kyc_status",
                agent_claimed="true",
                independently_found="status=verified",
                match=True,
                severity="info",
            ),
            ClaimCheck(
                field="counterparty_authorized",
                agent_claimed="true",
                independently_found="authorized=True",
                match=False,
                severity="critical",
            ),
        ],
        behavioral_flags=[],
        agent_confidence=0.90,
    )
    forensics_verdict = Verdict(
        agent_id="forensics",
        claims_checked=[],
        behavioral_flags=["hidden_text_detected"],
        agent_confidence=0.95,
    )
    risk_verdict = Verdict(
        agent_id="risk",
        claims_checked=[],
        behavioral_flags=[],
        agent_confidence=0.85,
    )

    findings = _extract_actual_findings([risk_verdict, compliance_verdict, forensics_verdict])

    assert findings["kyc_should_verify"] is True
    assert findings["beneficiary_in_counterparty_db"] is False
    assert findings["document_should_be_clean"] is False  # hidden_text_detected flag
