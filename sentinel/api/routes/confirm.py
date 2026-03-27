"""
POST /confirm route — API-03, LEARN-04.

Accepts operator confirmation that an episode was a genuine attack, then spawns
a background task to run the full rule generation/evolution pipeline:

1. Extract VerdictBoard + prediction errors from cached episode
2. Detect generation vs evolution path (generated_rules_fired non-empty = evolve)
3. Stream Opus 4.6 rule generation via WebSocket (rule_generating events)
4. Validate generated rule (AST + forbidden tokens + fire/clean checks)
5. Write .py file to sentinel/gate/rules/ for hot reload
6. Hot-reload SafetyGate from directory
7. Write rule provenance to Aerospike via write_rule()
8. Broadcast rule_deployed on success or rule_generation_failed after 3 failures

Returns 202 Accepted immediately — the pipeline runs asynchronously.
"""
from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from sentinel.api.websocket import ws_manager
from sentinel.engine.rule_generator import RuleGenerator
from sentinel.memory.rule_store import next_rule_id, write_rule

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ConfirmRequest(BaseModel):
    """Payload for POST /confirm."""

    episode_id: str
    attack_type: str  # e.g. "prompt_injection_hidden_text", "identity_spoofing"


class ConfirmResponse(BaseModel):
    """Response from POST /confirm — 202 Accepted immediately."""

    episode_id: str
    status: str  # "accepted"


# ---------------------------------------------------------------------------
# Route handler
# ---------------------------------------------------------------------------


@router.post("/confirm", status_code=202, response_model=ConfirmResponse)
async def confirm(req: ConfirmRequest) -> ConfirmResponse:
    """Accept operator confirmation of an attack and spawn background rule generation.

    Returns 202 immediately. The rule generation pipeline runs in the background
    and streams progress via WebSocket. The episode must be in active_episodes
    cache (populated by POST /investigate).

    Args:
        req: ConfirmRequest with episode_id and attack_type.

    Returns:
        ConfirmResponse with episode_id and status="accepted".

    Raises:
        HTTPException 404: If episode_id not found in active_episodes cache.
    """
    from sentinel.api.main import app_state  # Local import to avoid circular dependency

    episode = app_state["active_episodes"].get(req.episode_id)
    if episode is None:
        raise HTTPException(
            status_code=404,
            detail=f"Episode {req.episode_id} not found in active cache",
        )

    asyncio.create_task(_run_rule_pipeline(req, episode, app_state))
    return ConfirmResponse(episode_id=req.episode_id, status="accepted")


# ---------------------------------------------------------------------------
# Background pipeline
# ---------------------------------------------------------------------------


async def _run_rule_pipeline(
    req: ConfirmRequest,
    episode: Any,
    app_state: dict,
) -> None:
    """Run the complete rule generation/evolution pipeline in the background.

    Handles both the new generation path and the evolution path (when a generated
    rule has already fired for this episode).

    Args:
        req: The original ConfirmRequest (episode_id, attack_type).
        episode: The Episode object from active_episodes cache.
        app_state: Shared application state dict from main.py.
    """
    try:
        await _pipeline(req, episode, app_state)
    except Exception as exc:
        logger.exception("Uncaught exception in rule pipeline for episode %s", req.episode_id)
        try:
            await ws_manager.broadcast(
                "rule_generation_failed",
                req.episode_id,
                {"reason": f"Pipeline error: {exc}", "attempts": 0},
            )
        except Exception:
            pass  # Non-fatal — broadcast is best-effort


async def _pipeline(
    req: ConfirmRequest,
    episode: Any,
    app_state: dict,
) -> None:
    """Inner pipeline — extracted to allow clean try/except in caller.

    Supports both Episode model instances and raw dicts (active_episodes stores
    Episode objects from investigate route, but we handle both defensively).
    """
    # ---- Guard: skip if rule pipeline already ran for this episode ----
    # Prevents double-run when auto-trigger and manual confirm both fire for the
    # same episode (auto-trigger sets new_rules_deployed on completion).
    already_ran = (
        episode.new_rules_deployed if hasattr(episode, "new_rules_deployed")
        else episode.get("new_rules_deployed")
    )
    if already_ran:
        logger.info("Rule pipeline already ran for episode %s, skipping duplicate run", req.episode_id)
        return

    # ---- Step 1: Extract VerdictBoard and prediction errors ----
    if hasattr(episode, "verdict_board"):
        # Episode is a Pydantic model instance
        vb_dict = episode.verdict_board.model_dump()
        prediction_errors = episode.prediction_report or {}
        generated_rules_fired = episode.generated_rules_fired or []
    else:
        # Episode is a raw dict (fallback)
        vb_dict = episode.get("verdict_board", {})
        prediction_errors = episode.get("prediction_report") or {}
        generated_rules_fired = episode.get("generated_rules_fired") or []

    # ---- Step 2: Update episode with autonomous detection confirmation ----
    if hasattr(episode, "operator_confirmation"):
        episode.operator_confirmation = "auto_detected"
        episode.attack_type = req.attack_type
    else:
        episode["operator_confirmation"] = "auto_detected"
        episode["attack_type"] = req.attack_type

    # ---- Step 3: Set up WebSocket broadcast wrapper ----
    async def _broadcast(event: str, data: dict, episode_id: str) -> None:
        """Adapter: RuleGenerator calls broadcast(event, data, episode_id); ws_manager uses (event, episode_id, data)."""
        try:
            await ws_manager.broadcast(event, episode_id, data)  # type: ignore[arg-type]
        except Exception:
            pass  # Non-fatal

    # ---- Step 4: Build RuleGenerator ----
    generator = RuleGenerator(
        llm_client=app_state["llm_client"],
        model=app_state["models"]["agent"],
    )

    # ---- Step 5: Generation vs. evolution path ----
    if not generated_rules_fired:
        # New generation path
        await _generate_new_rule(req, episode, vb_dict, prediction_errors, generator, _broadcast, app_state)
    else:
        # Evolution path — existing rule fired, now refine it
        await _evolve_existing_rule(req, episode, vb_dict, prediction_errors, generated_rules_fired, generator, _broadcast, app_state)


async def _generate_new_rule(
    req: ConfirmRequest,
    episode: Any,
    vb_dict: dict,
    prediction_errors: dict,
    generator: RuleGenerator,
    ws_broadcast: Any,
    app_state: dict,
) -> None:
    """New rule generation path.

    Calls RuleGenerator.generate(), writes .py file, hot-reloads SafetyGate,
    writes provenance to Aerospike, broadcasts rule_deployed.
    """
    source, error = await generator.generate(
        attack_type=req.attack_type,
        verdict_board=vb_dict,
        prediction_errors=prediction_errors,
        ws_broadcast=ws_broadcast,
        episode_id=req.episode_id,
    )

    if source is None:
        # generate() already broadcast rule_generation_failed — nothing more to do
        logger.warning("Rule generation failed for episode %s: %s", req.episode_id, error)
        return

    # Determine rule ID
    aerospike = app_state.get("aerospike")
    if aerospike is not None:
        rule_id = await next_rule_id(aerospike)
    else:
        rule_id = "rule_001"

    rule_num = rule_id.split("_")[-1]  # e.g. "001" from "rule_001"

    # Write .py file to sentinel/gate/rules/
    rules_dir = _get_rules_dir()
    rule_filename = f"rule_generated_{rule_num}.py"
    rule_path = rules_dir / rule_filename
    rule_path.write_text(source, encoding="utf-8")
    logger.info("Wrote generated rule to %s", rule_path)

    # Register generated rule directly (not via load_rules_from_directory, which only
    # loads hardcoded rules — generated rules must go through register_rule so that
    # is_generated=True is set correctly in all future gate evaluations)
    gate = app_state["safety_gate"]
    try:
        gate.register_rule(rule_id, source)
        logger.info("SafetyGate registered generated rule %s", rule_id)
    except Exception as exc:
        logger.warning("SafetyGate register_rule failed for %s: %s", rule_id, exc)

    # Write provenance to Aerospike
    write_latency = 0.0
    if aerospike is not None:
        try:
            write_latency = await write_rule(
                rule_id=rule_id,
                source=source,
                episode_ids=[req.episode_id],
                prediction_errors=prediction_errors,
                version=1,
                client=aerospike,
            )
        except Exception as exc:
            logger.warning("Aerospike write_rule failed for %s: %s", rule_id, exc)

    # Update episode
    if hasattr(episode, "generated_rule_source"):
        episode.generated_rule_source = source
        episode.new_rules_deployed = [rule_id]
    else:
        episode["generated_rule_source"] = source
        episode["new_rules_deployed"] = [rule_id]

    # Broadcast rule_deployed
    await ws_manager.broadcast(
        "rule_deployed",
        req.episode_id,
        {
            "rule_id": rule_id,
            "version": 1,
            "source": source,
            "episode_ids": [req.episode_id],
            "write_latency_ms": write_latency,
            "attribution": (
                f"Generated Rule #{rule_num} "
                f"(learned from Episode #{req.episode_id[:8]}) | Deployed 0s ago"
            ),
        },
    )
    logger.info("rule_deployed broadcast for rule_id=%s episode=%s", rule_id, req.episode_id)


async def _evolve_existing_rule(
    req: ConfirmRequest,
    episode: Any,
    vb2_dict: dict,
    pe2: dict,
    generated_rules_fired: list,
    generator: RuleGenerator,
    ws_broadcast: Any,
    app_state: dict,
) -> None:
    """Rule evolution path.

    Loads the existing rule from Aerospike, retrieves the original episode's
    VerdictBoard + prediction errors, calls RuleGenerator.evolve(), overwrites
    the .py file, hot-reloads SafetyGate, and writes updated provenance.
    """
    aerospike = app_state.get("aerospike")
    existing_rule_id = generated_rules_fired[0]

    # Load existing rule source from Aerospike
    existing_source: str | None = None
    existing_episode_ids: list[str] = []
    existing_version: int = 1
    existing_prediction_errors: dict = {}

    if aerospike is not None:
        try:
            rule_bins = await aerospike.get("rules", existing_rule_id)
            existing_source = rule_bins.get("source", "")
            existing_episode_ids = json.loads(rule_bins.get("episode_ids", "[]"))
            existing_version = rule_bins.get("version", 1)
            existing_prediction_errors = json.loads(rule_bins.get("prediction_errors", "{}"))
        except Exception as exc:
            logger.warning("Could not load rule %s from Aerospike: %s", existing_rule_id, exc)

    if not existing_source:
        # Can't evolve without the original source — fall back to new generation
        logger.warning(
            "Could not load existing rule source for %s, falling back to new generation",
            existing_rule_id,
        )
        await _generate_new_rule(req, episode, vb2_dict, pe2, generator, ws_broadcast, app_state)
        return

    # Get original episode's VerdictBoard and prediction errors
    vb1_dict: dict = {}
    pe1: dict = {}

    original_episode_id = existing_episode_ids[0] if existing_episode_ids else None
    if original_episode_id is not None:
        # Try active cache first
        orig_episode = app_state["active_episodes"].get(original_episode_id)
        if orig_episode is not None:
            if hasattr(orig_episode, "verdict_board"):
                vb1_dict = orig_episode.verdict_board.model_dump()
                pe1 = orig_episode.prediction_report or {}
            else:
                vb1_dict = orig_episode.get("verdict_board", {})
                pe1 = orig_episode.get("prediction_report") or {}
        elif aerospike is not None:
            # Fall back to Aerospike
            try:
                from sentinel.memory.episode_store import get_episode
                orig_ep_bins = await get_episode(original_episode_id, aerospike)
                vb1_dict = orig_ep_bins.get("verdict_board", {})
                pe1 = orig_ep_bins.get("prediction_report") or {}
            except Exception as exc:
                logger.warning("Could not load original episode %s: %s", original_episode_id, exc)

    # If we couldn't get vb1, use existing prediction errors as best-effort fallback
    if not vb1_dict:
        vb1_dict = {}
        pe1 = existing_prediction_errors

    # Call evolve()
    source, error = await generator.evolve(
        v1_source=existing_source,
        attack_type=req.attack_type,
        vb1=vb1_dict,
        vb2=vb2_dict,
        pe1=pe1,
        pe2=pe2,
        ws_broadcast=ws_broadcast,
        episode_id=req.episode_id,
    )

    if source is None:
        # evolve() already broadcast rule_generation_failed
        logger.warning("Rule evolution failed for episode %s: %s", req.episode_id, error)
        return

    # Derive new version and rule number
    new_version = existing_version + 1
    rule_num = existing_rule_id.split("_")[-1]  # e.g. "001"

    # Overwrite .py file on disk (same filename as v1)
    rules_dir = _get_rules_dir()
    rule_filename = f"rule_generated_{rule_num}.py"
    rule_path = rules_dir / rule_filename
    rule_path.write_text(source, encoding="utf-8")
    logger.info("Overwrote evolved rule at %s (v%d)", rule_path, new_version)

    # Register evolved rule directly — same reasoning as new generation path:
    # register_rule() preserves is_generated=True; load_rules_from_directory would not.
    gate = app_state["safety_gate"]
    try:
        gate.register_rule(existing_rule_id, source)
        logger.info("SafetyGate updated evolved rule %s v%d", existing_rule_id, new_version)
    except Exception as exc:
        logger.warning("SafetyGate register_rule failed for evolved %s: %s", existing_rule_id, exc)

    # Combined prediction errors for provenance
    combined_pe = {**existing_prediction_errors, **pe2}
    updated_episode_ids = [*existing_episode_ids, req.episode_id]

    # Write updated provenance to Aerospike
    write_latency = 0.0
    if aerospike is not None:
        try:
            write_latency = await write_rule(
                rule_id=existing_rule_id,
                source=source,
                episode_ids=updated_episode_ids,
                prediction_errors=combined_pe,
                version=new_version,
                client=aerospike,
            )
        except Exception as exc:
            logger.warning("Aerospike write_rule failed for evolved %s: %s", existing_rule_id, exc)

    # Update episode
    if hasattr(episode, "generated_rule_source"):
        episode.generated_rule_source = source
        episode.new_rules_deployed = [existing_rule_id]
    else:
        episode["generated_rule_source"] = source
        episode["new_rules_deployed"] = [existing_rule_id]

    # Broadcast rule_deployed with updated version
    await ws_manager.broadcast(
        "rule_deployed",
        req.episode_id,
        {
            "rule_id": existing_rule_id,
            "version": new_version,
            "source": source,
            "episode_ids": updated_episode_ids,
            "write_latency_ms": write_latency,
            "attribution": (
                f"Generated Rule #{rule_num} v{new_version} "
                f"(evolved from {len(updated_episode_ids)} incident(s)) | Deployed 0s ago"
            ),
        },
    )
    logger.info(
        "rule_deployed (evolved v%d) broadcast for rule_id=%s episode=%s",
        new_version,
        existing_rule_id,
        req.episode_id,
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_rules_dir() -> Path:
    """Return the path to sentinel/gate/rules/ relative to this file."""
    # sentinel/api/routes/confirm.py -> sentinel/gate/rules/
    return Path(__file__).parent.parent.parent / "gate" / "rules"
