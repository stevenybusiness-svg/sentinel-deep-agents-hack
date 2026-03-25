"""
WebSocket event taxonomy — SCHEMA-04.

Defines all named events emitted over the /ws WebSocket connection to dashboard clients.
EventType has 9 literal values covering 11 named events (agent_completed is sent 3x,
once per sub-agent: risk, compliance, forensics).
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel

EventType = Literal[
    "investigation_started",
    "agent_completed",          # Sent 3x: risk, compliance, forensics
    "verdict_board_assembled",
    "gate_evaluated",
    "episode_written",
    "rule_generated",
    "rule_deployed",
    "rule_generating",          # Streaming tokens during rule generation
    "rule_generation_failed",   # All retries exhausted — generation failed
]


class WSEvent(BaseModel):
    """WebSocket event emitted to connected dashboard clients."""

    event: EventType
    timestamp: datetime
    episode_id: str
    data: dict[str, Any] = {}
