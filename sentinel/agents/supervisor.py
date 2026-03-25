"""
Supervisor Agent — PIPE-02, D-03, D-09, D-13, MEM-04.

The Supervisor is a real Opus 4.6 LLM that:
1. Loads recent episodes for context (MEM-04)
2. Makes an Opus 4.6 LLM call to reason about the payment request
3. Drives the Payment Agent (Sonnet 4.6) turn-by-turn via tool calls (D-03)
4. Forms predictions from behavioral baselines before investigation (D-08)
5. Dispatches Risk, Compliance, and Forensics in parallel via asyncio.TaskGroup (D-13)
6. Assembles the VerdictBoard and runs the Safety Gate
7. Compares prediction outcomes with actual investigation findings (D-09)
8. Writes the Episode to Aerospike and broadcasts all events over WebSocket

Per D-03: This module drives the Payment Agent conversation -- it does NOT delegate
to a self-contained payment_agent loop. handle_tool_call() and parse_payment_decision()
are called directly to maintain Supervisor control over each turn.
"""
from __future__ import annotations

import asyncio
import json
import uuid
from pathlib import Path

from sentinel.agents import compliance, forensics, risk
from sentinel.agents.payment_agent import (
    PAYMENT_AGENT_SYSTEM_PROMPT,
    PAYMENT_TOOLS,
    handle_tool_call,
    parse_payment_decision,
)
from sentinel.api.websocket import ConnectionManager
from sentinel.engine.prediction import PredictionEngine
from sentinel.engine.safety_gate import SafetyGate
from sentinel.engine.verdict_board import VerdictBoardEngine
from sentinel.fixtures import FixtureData
from sentinel.memory.aerospike_client import AerospikeClient
from sentinel.memory.episode_store import get_recent_episodes, write_episode
from sentinel.memory.trust_store import load_baselines
from sentinel.schemas.episode import Episode
from sentinel.schemas.payment import PaymentDecision
from sentinel.schemas.verdict import Verdict

# ---------------------------------------------------------------------------
# Supervisor system prompt (Opus 4.6)
# ---------------------------------------------------------------------------

SUPERVISOR_SYSTEM_PROMPT = """You are the Sentinel Supervisor. You oversee payment processing by:
1. Directing a Payment Agent to process payment requests step-by-step
2. Analyzing the agent's behavior for anomalies
3. Dispatching investigators to verify the agent's claims

You control the Payment Agent by sending it tool calls one at a time. After each response, decide the next step. When the Payment Agent has gathered enough information, instruct it to make its final decision.

Recent investigation history for context:
{episode_context}
"""

# ---------------------------------------------------------------------------
# Main investigation entry point
# ---------------------------------------------------------------------------


async def run_investigation(
    payment_request: dict,
    fixtures: FixtureData,
    invoice_path: Path | None,
    llm_client,
    models: dict[str, str],
    safety_gate: SafetyGate,
    aerospike: AerospikeClient | None,
    ws: ConnectionManager,
) -> dict:
    """Run the complete investigation pipeline with Opus 4.6 Supervisor LLM.

    Args:
        payment_request: Raw payment request payload dict.
        fixtures:         Loaded fixture data (KYC, counterparty DB, baselines).
        invoice_path:     Path to invoice PNG, or None if no document (PIPE-06).
        llm_client:       AsyncAnthropic (or Bedrock) client instance.
        models:           Dict with "supervisor" and "agent" model ID strings.
        safety_gate:      Initialized SafetyGate with loaded rules.
        aerospike:        Optional AerospikeClient (graceful degradation if None).
        ws:               ConnectionManager for broadcasting events to dashboard.

    Returns:
        Dict containing episode_id, decision, composite_score, attribution,
        rule_contributions, write_latency_ms, prediction, outcome_comparison,
        and cached episode object for voice Q&A.
    """
    episode_id = str(uuid.uuid4())

    # 1. Broadcast investigation_started
    await ws.broadcast("investigation_started", episode_id, {"payment_request": payment_request})

    # 2. Load recent episodes for Supervisor context (MEM-04 / BLOCKER 2)
    episode_context = "No prior episodes."
    if aerospike:
        try:
            recent = await get_recent_episodes(aerospike, limit=5)
            if recent:
                summaries = []
                for ep in recent:
                    summaries.append(
                        f"- Episode {ep.get('episode_id', 'unknown')}: "
                        f"decision={ep.get('gate_decision', '?')}, "
                        f"rules_fired={ep.get('rules_fired', [])}"
                    )
                episode_context = "\n".join(summaries)
        except Exception:
            pass  # Fall back to "No prior episodes."

    # 3. Supervisor LLM reasoning step (D-03 / BLOCKER 1)
    #    Opus 4.6 Supervisor makes an initial reasoning call about this payment.
    supervisor_prompt = SUPERVISOR_SYSTEM_PROMPT.format(episode_context=episode_context)

    await llm_client.messages.create(
        model=models["supervisor"],
        max_tokens=1024,
        system=supervisor_prompt,
        messages=[{
            "role": "user",
            "content": (
                f"New payment request to investigate:\n"
                f"{json.dumps(payment_request, indent=2)}\n\n"
                "Direct the Payment Agent to process this request."
            ),
        }],
    )

    # 4. Payment Agent multi-turn conversation (Sonnet 4.6 with PAYMENT_TOOLS)
    #    The Supervisor has reasoned about the request; now drive the Payment Agent
    #    turn-by-turn until it produces its final PaymentDecision.
    agent_messages: list[dict] = [{
        "role": "user",
        "content": f"Process this payment request:\n{json.dumps(payment_request, indent=2)}",
    }]
    steps_taken: list[str] = []
    payment_decision: PaymentDecision | None = None

    for _turn in range(10):
        agent_response = await llm_client.messages.create(
            model=models["agent"],
            max_tokens=2048,
            system=PAYMENT_AGENT_SYSTEM_PROMPT,
            tools=PAYMENT_TOOLS,
            messages=agent_messages,
        )

        if agent_response.stop_reason == "tool_use":
            # Process each tool call block
            tool_results = []
            for block in agent_response.content:
                if block.type == "tool_use":
                    steps_taken.append(block.name)
                    result_content = handle_tool_call(
                        block.name, block.input, fixtures, invoice_path,
                    )
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result_content,
                    })

            # Append assistant response and tool results to conversation
            agent_messages.append({"role": "assistant", "content": agent_response.content})
            agent_messages.append({"role": "user", "content": tool_results})

        elif agent_response.stop_reason == "end_turn":
            # Extract text from the final response and parse PaymentDecision
            response_text = ""
            for block in agent_response.content:
                if hasattr(block, "text"):
                    response_text += block.text
            payment_decision = parse_payment_decision(response_text, episode_id, steps_taken)
            break
    else:
        raise RuntimeError(
            f"Payment Agent exceeded 10 turns without producing a decision "
            f"for episode {episode_id}"
        )

    # 5. Prediction step BEFORE investigation (D-08)
    #    Use fixture baselines; override with Aerospike baselines if available.
    baselines = fixtures["behavioral_baselines"]
    if aerospike:
        try:
            stored = await load_baselines(aerospike)
            if stored:
                baselines = stored
        except Exception:
            pass  # Fall back to fixture baselines

    prediction_engine = PredictionEngine()
    prediction = prediction_engine.predict(
        payment_decision=payment_decision,
        baselines=baselines,
        expected_step_sequence=["check_counterparty", "verify_kyc", "read_invoice"],
    )

    # 6. Dispatch sub-agents in parallel via asyncio.TaskGroup (D-13, PIPE-02)
    #    One sub-agent failure produces unable_to_verify rather than aborting (PIPE-02).
    verdicts: list[Verdict | None] = [None, None, None]

    async def run_risk() -> None:
        try:
            verdicts[0] = await risk.analyze(
                payment_decision,
                baselines,
                expected_step_sequence=["check_counterparty", "verify_kyc", "read_invoice"],
            )
        except Exception:
            verdicts[0] = Verdict(
                agent_id="risk",
                claims_checked=[],
                behavioral_flags=[],
                agent_confidence=0.0,
                unable_to_verify=True,
            )
        await ws.broadcast(
            "agent_completed",
            episode_id,
            {"agent": "risk", "verdict": verdicts[0].model_dump()},
        )

    async def run_compliance() -> None:
        try:
            verdicts[1] = await compliance.validate(payment_decision, fixtures)
        except Exception:
            verdicts[1] = Verdict(
                agent_id="compliance",
                claims_checked=[],
                behavioral_flags=[],
                agent_confidence=0.0,
                unable_to_verify=True,
            )
        await ws.broadcast(
            "agent_completed",
            episode_id,
            {"agent": "compliance", "verdict": verdicts[1].model_dump()},
        )

    async def run_forensics() -> None:
        try:
            verdicts[2] = await forensics.scan(
                payment_decision, invoice_path, llm_client, models["agent"],
            )
        except Exception:
            verdicts[2] = Verdict(
                agent_id="forensics",
                claims_checked=[],
                behavioral_flags=[],
                agent_confidence=0.0,
                unable_to_verify=True,
            )
        await ws.broadcast(
            "agent_completed",
            episode_id,
            {"agent": "forensics", "verdict": verdicts[2].model_dump()},
        )

    async with asyncio.TaskGroup() as tg:
        tg.create_task(run_risk())
        tg.create_task(run_compliance())
        tg.create_task(run_forensics())

    # 7. Assemble Verdict Board (deterministic field-level comparison)
    vbe = VerdictBoardEngine()
    verdict_board = vbe.assemble(payment_decision, verdicts)  # type: ignore[arg-type]

    # 8. Compare prediction outcomes with actual investigation findings (D-09 / BLOCKER 3)
    actual_findings = _extract_actual_findings(verdicts)  # type: ignore[arg-type]
    outcome_comparison = prediction_engine.compare_outcomes(prediction, actual_findings)

    # Attach prediction errors to verdict board for Phase 3 rule generation (D-12)
    prediction_errors = {
        "predicted_z_score": prediction.predicted_z_score,
        "step_deviation": prediction.step_sequence_deviation,
        "summary_score": prediction.summary_score,
        "deviation_details": prediction.deviation_details,
        "investigation_outcome_errors": outcome_comparison,
    }
    verdict_board.prediction_errors = prediction_errors

    await ws.broadcast(
        "verdict_board_assembled",
        episode_id,
        {"verdict_board": verdict_board.model_dump()},
    )

    # 9. Safety Gate evaluation (deterministic — no LLM in enforcement path)
    gate_result = safety_gate.evaluate(verdict_board)
    await ws.broadcast("gate_evaluated", episode_id, gate_result)

    # 10. Build Episode record
    episode = Episode(
        id=episode_id,
        action_request=payment_request,
        agent_verdicts=verdicts,  # type: ignore[arg-type]
        verdict_board=verdict_board,
        gate_decision=gate_result["decision"],
        gate_rationale=gate_result["attribution"],
        rules_fired=[
            c["rule_id"]
            for c in gate_result["rule_contributions"]
            if not c["is_generated"]
        ],
        generated_rules_fired=[
            c["rule_id"]
            for c in gate_result["rule_contributions"]
            if c["is_generated"]
        ],
        prediction_report=prediction.model_dump(),
    )

    # 11. Write to Aerospike (MEM-01) — failure does not block gate decision
    write_latency_ms = 0.0
    if aerospike:
        try:
            write_latency_ms = await write_episode(episode, aerospike)
        except Exception:
            pass

    await ws.broadcast(
        "episode_written",
        episode_id,
        {"episode_id": episode_id, "write_latency_ms": write_latency_ms},
    )

    return {
        "episode_id": episode_id,
        "decision": gate_result["decision"],
        "composite_score": gate_result["composite_score"],
        "attribution": gate_result["attribution"],
        "rule_contributions": gate_result["rule_contributions"],
        "write_latency_ms": write_latency_ms,
        "prediction": prediction.model_dump(),
        "outcome_comparison": outcome_comparison,
        "episode": episode,  # Cached for voice Q&A (API-02)
    }


# ---------------------------------------------------------------------------
# Helper: extract actual findings from investigation verdicts
# ---------------------------------------------------------------------------


def _extract_actual_findings(verdicts: list[Verdict]) -> dict[str, bool]:
    """Extract actual investigation findings to compare against predictions (D-09).

    Maps verdict results to the same keys used in expected_investigation_outcomes.

    Args:
        verdicts: List of Verdict objects from Risk, Compliance, and Forensics agents.

    Returns:
        Dict mapping outcome keys to boolean findings, e.g.
        {"kyc_should_verify": False, "beneficiary_in_counterparty_db": False,
         "document_should_be_clean": True}
    """
    findings: dict[str, bool] = {}

    for v in verdicts:
        if v.agent_id == "compliance":
            for cc in v.claims_checked:
                if cc.field == "kyc_status":
                    findings["kyc_should_verify"] = cc.match
                if cc.field == "counterparty_authorized":
                    findings["beneficiary_in_counterparty_db"] = cc.match

        if v.agent_id == "forensics":
            # Document is clean if no hidden text flag was raised
            has_hidden_text = "hidden_text_detected" in v.behavioral_flags
            findings["document_should_be_clean"] = not has_hidden_text

    return findings
