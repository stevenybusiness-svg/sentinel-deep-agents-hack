"""
POST /bland-call — Bland AI voice call initiation route.

VOICE-01, VOICE-02.

Initiates a Bland AI voice call grounded in the investigation context from
app_state["active_episodes"]. The call uses dynamic_data with cache: false
to inject pre-computed investigation context before each AI utterance.

Barge-in is enabled via interruption_threshold=150 and block_interruptions=False (VOICE-02).
Uses model="base" (not "turbo") for full dynamic_data support (VOICE-01).
"""
from __future__ import annotations

import os

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

BLAND_API_URL = "https://api.bland.ai/v1/calls"


class StartCallRequest(BaseModel):
    """Request payload to initiate a Bland AI voice call."""

    episode_id: str
    public_host: str   # e.g. "https://abc.ngrok.io" or production URL
    phone_number: str | None = None  # E.164 format; falls back to DEMO_PHONE_NUMBER env var


class StartCallResponse(BaseModel):
    """Response from POST /bland-call."""

    call_id: str
    status: str


@router.post("/bland-call", response_model=StartCallResponse)
async def start_bland_call(req: StartCallRequest) -> StartCallResponse:
    """Initiate a Bland AI voice call grounded in the investigation context (VOICE-01).

    Checks that the episode_id exists in the active_episodes cache, then
    calls the Bland AI API with a fully-constructed payload including
    dynamic_data that points to /bland-webhook for real-time context injection.

    Barge-in is enabled per VOICE-02.
    """
    from sentinel.api.main import app_state  # Local import to avoid circular dependency

    # Verify episode exists in cache
    episode = app_state.get("active_episodes", {}).get(req.episode_id)
    if episode is None:
        raise HTTPException(
            status_code=404,
            detail=f"Episode {req.episode_id!r} not found in active cache",
        )

    # Resolve Bland API key
    api_key = app_state.get("bland_api_key") or os.getenv("BLAND_API_KEY", "")
    if not api_key or api_key == "test-bland-placeholder":
        raise HTTPException(
            status_code=503,
            detail="BLAND_API_KEY not configured — set env var BLAND_API_KEY to a valid key",
        )

    # Resolve phone number: request body overrides env var
    phone_number = req.phone_number or os.getenv("DEMO_PHONE_NUMBER", "")
    if not phone_number:
        raise HTTPException(
            status_code=422,
            detail="Phone number required — set DEMO_PHONE_NUMBER env var or pass phone_number in request",
        )

    payload = _build_call_payload(req, phone_number)

    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.post(
            BLAND_API_URL,
            headers={
                "authorization": api_key,
                "Content-Type": "application/json",
            },
            json=payload,
        )
        resp.raise_for_status()
        data = resp.json()

    return StartCallResponse(
        call_id=data.get("call_id", ""),
        status="initiated",
    )


def _build_call_payload(req: StartCallRequest, phone_number: str) -> dict:
    """Construct the full Bland AI call payload.

    Parameters follow Bland AI v1/calls spec:
    - model: "base" (not "turbo" — turbo breaks dynamic_data)
    - interruption_threshold: 150ms for barge-in (VOICE-02)
    - block_interruptions: False for barge-in (VOICE-02)
    - dynamic_data: POST to /bland-webhook before each AI utterance with timeout=3000ms
    - request_data: episode_id threaded through for webhook fallback
    """
    task = (
        "You are the Sentinel Supervisor — an AI security system that just completed "
        "a payment investigation. Answer questions from the operator about why the "
        "payment was blocked or escalated.\n\n"
        "You have these investigation details:\n"
        "Decision: {{gate_decision}}\n"
        "Anomaly score: {{composite_score}}\n"
        "Attribution: {{attribution}}\n"
        "Rules fired: {{rules_fired}}\n"
        "Prediction errors: {{prediction_errors}}\n\n"
        "Speak in plain language. Use exact numbers and rule names. "
        "Be specific about what triggered the block. "
        "Do not make up information — use only the details provided."
    )

    return {
        "phone_number": phone_number,
        "task": task,
        "voice": "maya",
        "model": "base",  # base supports dynamic_data; turbo has limited capabilities
        "interruption_threshold": 150,   # ms — enables barge-in (VOICE-02)
        "block_interruptions": False,    # false = barge-in enabled (VOICE-02)
        "max_duration": 5,               # minutes
        "first_sentence": (
            "I'm the Sentinel Supervisor. I just completed an investigation. "
            "Ask me anything about why I made my decision."
        ),
        "dynamic_data": [
            {
                "url": f"{req.public_host}/bland-webhook",
                "method": "POST",
                "headers": {"Content-Type": "application/json"},
                "body": {"episode_id": "{{episode_id}}"},
                "timeout": 3000,   # ms — 3s, well within 8s CLAUDE.md budget
                "cache": False,    # refresh before each AI utterance
                "response_data": [
                    {
                        "name": "gate_decision",
                        "data": "$.gate_decision",
                        "context": "Gate decision: {{gate_decision}}",
                    },
                    {
                        "name": "composite_score",
                        "data": "$.composite_score",
                        "context": "Composite anomaly score: {{composite_score}}",
                    },
                    {
                        "name": "attribution",
                        "data": "$.attribution",
                        "context": "Attribution: {{attribution}}",
                    },
                    {
                        "name": "rules_fired",
                        "data": "$.rules_fired",
                        "context": "Rules fired: {{rules_fired}}",
                    },
                    {
                        "name": "prediction_errors",
                        "data": "$.prediction_errors",
                        "context": "Prediction errors: {{prediction_errors}}",
                    },
                ],
            }
        ],
        "request_data": {"episode_id": req.episode_id},
        "metadata": {"episode_id": req.episode_id},
    }
