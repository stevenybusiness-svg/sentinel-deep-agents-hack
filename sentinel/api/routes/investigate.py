"""
POST /investigate route — API-02.

Accepts a payment request, triggers the full investigation pipeline via the
Supervisor, caches the resulting episode for voice Q&A, and returns the
gate decision with composite score and attribution.

Auto-triggers the rule generation pipeline as a background task when the gate
decision is NO-GO or ESCALATE (LEARN-04 auto-trigger). The "Confirm Attack"
button in the frontend still works but is no longer required to trigger learning.

Per WARNING 3: invoice_path is None when no invoice (not Path('/dev/null')).
The Forensics Agent handles None correctly per PIPE-06.
"""
from __future__ import annotations

import asyncio
import logging

from fastapi import APIRouter
from pydantic import BaseModel

from sentinel.agents.supervisor import run_investigation
from sentinel.api.websocket import ws_manager

logger = logging.getLogger(__name__)

# Scenario -> attack_type mapping for auto-trigger rule generation
_SCENARIO_ATTACK_TYPE: dict[str, str] = {
    "phase1": "prompt_injection_hidden_text",
    "phase2": "identity_spoofing",
}

router = APIRouter()


class InvestigateRequest(BaseModel):
    """Payload for POST /investigate."""

    payment_request: dict  # Raw payment request payload
    scenario: str = "phase1"  # "phase1" (invoice attack) | "phase2" (identity spoofing)


class InvestigateResponse(BaseModel):
    """Response from POST /investigate."""

    episode_id: str
    decision: str
    composite_score: float
    attribution: str
    write_latency_ms: float | None  # None when Aerospike is disabled or write failed


@router.post("/investigate", response_model=InvestigateResponse)
async def investigate(req: InvestigateRequest) -> InvestigateResponse:
    """Trigger the full Sentinel investigation pipeline for a payment request.

    Runs Payment Agent via Supervisor (Opus 4.6), dispatches parallel sub-agents,
    assembles VerdictBoard, evaluates Safety Gate, writes Episode to Aerospike,
    and broadcasts all events over WebSocket.

    Returns the gate decision with attribution for the caller. Active episode is
    cached in app_state["active_episodes"] for voice Q&A (API-02).
    """
    from sentinel.api.main import app_state  # Local import to avoid circular dependency

    # Determine invoice path based on scenario.
    # Per WARNING 3: use None when no invoice — do NOT use Path('/dev/null').
    # The Forensics Agent handles None correctly per PIPE-06.
    invoice_path = None
    if req.scenario == "phase1":
        invoice_path = app_state["invoice_paths"].get("forensic")

    attack_type = _SCENARIO_ATTACK_TYPE.get(req.scenario, "prompt_injection_hidden_text")

    result = await run_investigation(
        payment_request=req.payment_request,
        fixtures=app_state["fixtures"],
        invoice_path=invoice_path,
        llm_client=app_state["llm_client"],
        models=app_state["models"],
        safety_gate=app_state["safety_gate"],
        aerospike=app_state.get("aerospike"),
        ws=ws_manager,
        attack_type=attack_type,
    )

    # Cache active episode for voice Q&A (API-02)
    # Cap at 100 entries to prevent unbounded memory growth (Bug 6 fix)
    episodes = app_state["active_episodes"]
    if len(episodes) >= 100:
        # Evict the oldest non-sentinel key
        oldest = next((k for k in episodes if k != "__latest__"), None)
        if oldest:
            del episodes[oldest]
    episodes[result["episode_id"]] = result["episode"]
    # Update __latest__ sentinel key so webhook fallback always resolves (VOICE-03)
    episodes["__latest__"] = result["episode_id"]

    # Auto-trigger rule generation for blocked/escalated transactions (LEARN-04)
    # Runs as a background task so the API response is not delayed.
    # Wait 1.5s before starting so the frontend has time to render the gate decision.
    if result["decision"] in ("NO-GO", "ESCALATE"):
        asyncio.create_task(
            _auto_trigger_rule_generation(
                episode_id=result["episode_id"],
                attack_type=attack_type,
                episode=result["episode"],
                app_state=app_state,
            )
        )

    return InvestigateResponse(
        episode_id=result["episode_id"],
        decision=result["decision"],
        composite_score=result["composite_score"],
        attribution=result["attribution"],
        write_latency_ms=result["write_latency_ms"],
    )


# ---------------------------------------------------------------------------
# Auto-trigger rule generation (LEARN-04)
# ---------------------------------------------------------------------------


async def _auto_trigger_rule_generation(
    episode_id: str,
    attack_type: str,
    episode,
    app_state: dict,
) -> None:
    """Auto-trigger the rule generation pipeline after a NO-GO/ESCALATE gate decision.

    Waits 1.5 seconds for the frontend to render the gate decision, then runs the
    same pipeline as POST /confirm but without requiring operator confirmation.

    Args:
        episode_id:  Episode UUID from the investigation.
        attack_type: Inferred attack type (e.g. "prompt_injection_hidden_text").
        episode:     Episode object from the investigation result.
        app_state:   Shared application state dict.
    """
    try:
        # Brief delay so frontend renders gate_decision before rule_generating events arrive
        await asyncio.sleep(0.3)

        from sentinel.api.routes.confirm import ConfirmRequest, _run_rule_pipeline

        req = ConfirmRequest(episode_id=episode_id, attack_type=attack_type)
        await _run_rule_pipeline(req, episode, app_state)

        logger.info(
            "Auto-triggered rule generation completed for episode %s (attack_type=%s)",
            episode_id,
            attack_type,
        )
    except Exception:
        logger.exception(
            "Auto-triggered rule generation failed for episode %s", episode_id
        )
