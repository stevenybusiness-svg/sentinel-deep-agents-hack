"""
PaymentDecision Pydantic model — SCHEMA-05 (D-05).

Output from the Payment Agent — the structured verdict that gets intercepted
and investigated by Sentinel before any action is taken.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class PaymentDecision(BaseModel):
    """Output from the Payment Agent -- what gets investigated."""

    episode_id: str
    decision: Literal["approve", "deny"]
    amount: float
    beneficiary: str
    account: str
    rationale: str  # Agent's explanation (may be corrupted by prompt injection)
    steps_taken: list[str]  # Ordered tool calls the agent made
    confidence: float = Field(ge=0.0, le=1.0)
    claims: dict[str, str]  # e.g. {"kyc_verified": "true", "counterparty_authorized": "true"}
    document_urls: list[str] = []
