"""
WebSocket event taxonomy — SCHEMA-04.

Defines all named events emitted over the /ws WebSocket connection to dashboard clients.
EventType has 12 literal values covering 14 named events (agent_completed is sent 3x,
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
    "supervisor_token",         # Streaming text delta from Supervisor reasoning (D-03)
    "narrative_template",       # Immediate template-filled narrative after gate evaluation (D-09)
    "narrative_ready",          # LLM-polished narrative arrives 3-5s later (D-09)
    "report_delivered",         # Airbyte+Slack report delivery status (DEMO-POLISH-04)
]


class WSEvent(BaseModel):
    """WebSocket event emitted to connected dashboard clients."""

    event: EventType
    timestamp: datetime
    episode_id: str
    data: dict[str, Any] = {}
