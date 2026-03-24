"""
Verdict and ClaimCheck Pydantic models — SCHEMA-01.

These schemas represent an individual sub-agent's investigation output.
Strict validators on Safety Gate fields only (D-06); loose typing elsewhere (D-07).
"""
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


class ClaimCheck(BaseModel):
    """Represents one field-level claim verification by an investigator agent."""

    field: str
    agent_claimed: str
    independently_found: str
    match: bool  # Strict per D-06 — bool, not int or truthy value
    severity: Literal["critical", "warning", "info"]  # Strict per D-06


class Verdict(BaseModel):
    """Structured findings returned by a single sub-agent (Risk, Compliance, Forensics)."""

    agent_id: str
    claims_checked: list[ClaimCheck]
    behavioral_flags: list[str]  # Loose per D-07 — free-form flags from agent reasoning
    agent_confidence: float = Field(ge=0.0, le=1.0)  # Strict per D-06
    confidence_z_score: float | None = None  # Risk agent computes this; others leave None
    unable_to_verify: bool = False  # Set True if agent cannot independently verify
