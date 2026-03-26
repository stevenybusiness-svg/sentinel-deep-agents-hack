"""
POST /bland-webhook — dynamic_data webhook handler for Bland AI voice calls.

API-04, VOICE-03.

Bland AI calls this endpoint before each AI utterance (when dynamic_data cache: false).
Must respond in under 3s. Reads from in-memory app_state["active_episodes"] only.
Zero I/O: no Aerospike, no LLM calls, no file reads — pure dict lookups.

Falls back to __latest__ sentinel key when episode_id is missing or unrecognized.
Returns a safe NO-GO context dict when no episode is found at all.
"""
from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()

# Required keys that must always be present in the response
_REQUIRED_KEYS = frozenset(
    {"gate_decision", "composite_score", "attribution", "rules_fired", "prediction_errors"}
)


@router.post("/bland-webhook")
async def bland_webhook(request: Request) -> dict:
    """Serve investigation context to Bland AI dynamic_data requests (VOICE-03, API-04).

    Bland AI calls this before each AI utterance with cache: false.
    Zero I/O — reads from in-memory active_episodes dict only.
    Response time target: < 100ms (budget: 3000ms timeout configured at call-time).
    """
    from sentinel.api.main import app_state  # Local import to avoid circular dependency

    # Parse body — tolerate malformed/empty bodies
    try:
        body = await request.json()
    except Exception:
        body = {}

    episode_id = body.get("episode_id", "")

    # Resolve episode: specific ID → __latest__ sentinel key → empty fallback
    active = app_state.get("active_episodes", {})
    episode = active.get(episode_id) if episode_id else None

    if episode is None:
        # Fall back to __latest__ sentinel key
        latest_id = active.get("__latest__")
        episode = active.get(latest_id) if latest_id else None

    if episode is None:
        return _empty_context()

    return _build_voice_context(episode)


def _build_voice_context(episode) -> dict:
    """Build 5-field voice context dict from Episode model — zero I/O, pure in-memory."""
    if hasattr(episode, "gate_decision"):
        # Pydantic Episode model
        gate_decision = episode.gate_decision
        gate_rationale = episode.gate_rationale or ""
        rules_fired = ", ".join(episode.rules_fired or [])
        generated_fired = ", ".join(episode.generated_rules_fired or [])
        prediction_report = episode.prediction_report or {}
    else:
        # Raw dict fallback
        gate_decision = episode.get("gate_decision", "UNKNOWN")
        gate_rationale = episode.get("gate_rationale", "")
        rules_fired = ", ".join(episode.get("rules_fired", []))
        generated_fired = ", ".join(episode.get("generated_rules_fired", []))
        prediction_report = episode.get("prediction_report") or {}

    # Extract composite score from prediction report
    composite_score = prediction_report.get("summary_score", "computed at gate")

    # Build rules summary
    rules_parts = []
    if rules_fired:
        rules_parts.append(f"hardcoded: {rules_fired}")
    if generated_fired:
        rules_parts.append(f"generated: {generated_fired}")
    rules_summary = "; ".join(rules_parts) or "none"

    return {
        "gate_decision": gate_decision,
        "composite_score": str(composite_score),
        "attribution": gate_rationale,
        "rules_fired": rules_summary,
        "prediction_errors": _summarize_prediction_errors(prediction_report),
    }


def _summarize_prediction_errors(prediction_report: dict) -> str:
    """Summarize prediction errors from prediction_report into a human-readable string.

    Extracts z-score deviation, step sequence deviation, and investigation outcome
    mismatches. Returns 'none recorded' if prediction_report is empty.
    """
    if not prediction_report:
        return "none recorded"

    parts = []

    z = prediction_report.get("predicted_z_score")
    if z is not None:
        parts.append(f"z-score={z:.2f}")

    deviation = prediction_report.get("step_deviation")
    if deviation:
        parts.append("step deviation detected")

    errors = prediction_report.get("investigation_outcome_errors", {})
    if errors:
        mismatches = [k for k, v in errors.items() if not v]
        if mismatches:
            parts.append(f"outcome mismatches: {', '.join(mismatches)}")

    return "; ".join(parts) if parts else "within normal range"


def _empty_context() -> dict:
    """Return a safe fallback context dict when no episode is found in the cache."""
    return {
        "gate_decision": "NO-GO",
        "composite_score": "unavailable",
        "attribution": "Investigation context not available",
        "rules_fired": "unknown",
        "prediction_errors": "unavailable",
    }
