"""
VerdictBoard Pydantic model — SCHEMA-02.

The synthesized verdict board produced by the Verdict Board Engine after
all sub-agents complete their investigations. Input to the Safety Gate.
"""
from __future__ import annotations

from pydantic import BaseModel, Field


class VerdictBoard(BaseModel):
    """Aggregated comparison of payment agent claims vs. independent investigator findings."""

    mismatches: list[dict]  # Loose per D-07 — list of mismatch detail dicts
    behavioral_flags: list[str]  # Loose per D-07 — union of flags from all agents
    agent_confidence: float = Field(ge=0.0, le=1.0)  # Strict per D-06
    confidence_z_score: float | None = None
    step_sequence_deviation: bool = False
    hardcoded_rule_fired: bool = False
    unable_to_verify: list[str] = []  # List of agent_ids that returned unable_to_verify=True
