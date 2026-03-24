"""
Episode Pydantic model — SCHEMA-03.

Represents one complete incident investigation record: the payment action,
all agent verdicts, the synthesized verdict board, and the gate's final decision.
Written to Aerospike after each incident resolution.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from sentinel.schemas.verdict import Verdict
from sentinel.schemas.verdict_board import VerdictBoard


class Episode(BaseModel):
    """Complete incident record for Aerospike episodic memory."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    action_request: dict  # Loose — raw payment request payload
    agent_verdicts: list[Verdict]
    verdict_board: VerdictBoard
    gate_decision: Literal["GO", "NO-GO", "ESCALATE"]  # Strict per D-06
    gate_rationale: str  # Loose — human-readable explanation
    rules_fired: list[str] = []
    generated_rules_fired: list[str] = []
    operator_confirmation: str | None = None
    attack_type: str | None = None
    generated_rule_source: str | None = None
    new_rules_deployed: list[str] = []
