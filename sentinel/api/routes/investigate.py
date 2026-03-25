"""
POST /investigate route — API-02.

Accepts a payment request, triggers the full investigation pipeline via the
Supervisor, caches the resulting episode for voice Q&A, and returns the
gate decision with composite score and attribution.

Per WARNING 3: invoice_path is None when no invoice (not Path('/dev/null')).
The Forensics Agent handles None correctly per PIPE-06.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from sentinel.agents.supervisor import run_investigation
from sentinel.api.websocket import ws_manager

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
    write_latency_ms: float


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

    result = await run_investigation(
        payment_request=req.payment_request,
        fixtures=app_state["fixtures"],
        invoice_path=invoice_path,
        llm_client=app_state["llm_client"],
        models=app_state["models"],
        safety_gate=app_state["safety_gate"],
        aerospike=app_state.get("aerospike"),
        ws=ws_manager,
    )

    # Cache active episode for voice Q&A (API-02)
    app_state["active_episodes"][result["episode_id"]] = result["episode"]

    return InvestigateResponse(
        episode_id=result["episode_id"],
        decision=result["decision"],
        composite_score=result["composite_score"],
        attribution=result["attribution"],
        write_latency_ms=result["write_latency_ms"],
    )
