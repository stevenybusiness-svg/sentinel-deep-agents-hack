"""
Risk Agent — PIPE-03, D-14.

Analyzes payment agent behavior against statistical baselines.
Computes confidence z-score and detects step-sequence deviations.
Returns structured Verdict with behavioral_flags.
"""
from __future__ import annotations

from sentinel.schemas.payment import PaymentDecision
from sentinel.schemas.verdict import ClaimCheck, Verdict


async def analyze(
    payment_decision: PaymentDecision,
    baselines: dict,
    expected_step_sequence: list[str] | None = None,
) -> Verdict:
    """Analyze a payment decision against behavioral baselines.

    Args:
        payment_decision: The payment agent's structured decision.
        baselines: Behavioral baseline dict with keys like "payment_agent"
                   containing {"mean": float, "std": float}.
        expected_step_sequence: Optional ordered list of expected tool call names.
                                 If provided, deviations are flagged.

    Returns:
        Verdict with agent_id="risk", z-score, and behavioral flags.
    """
    agent_baseline = baselines.get("payment_agent", {})
    mean = agent_baseline.get("mean", 0.52)
    std = agent_baseline.get("std", 0.11)

    # Compute confidence z-score — PIPE-03
    z = (payment_decision.confidence - mean) / std

    # Determine ClaimCheck match and severity for confidence
    abs_z = abs(z)
    if abs_z > 3.0:
        severity = "critical"
    elif abs_z > 2.0:
        severity = "warning"
    else:
        severity = "info"

    confidence_match = abs_z < 2.0

    claims_checked: list[ClaimCheck] = [
        ClaimCheck(
            field="agent_confidence",
            agent_claimed=str(payment_decision.confidence),
            independently_found=f"z-score: {z:.2f} (baseline mean={mean}, std={std})",
            match=confidence_match,
            severity=severity,
        )
    ]

    # Build behavioral flags
    behavioral_flags: list[str] = []

    if abs_z > 2.0:
        behavioral_flags.append("confidence_anomaly")

    if z > 3.0:
        behavioral_flags.append("high_confidence_deviation")

    # Step-sequence deviation detection — PIPE-03
    if expected_step_sequence is not None:
        steps_match = payment_decision.steps_taken == expected_step_sequence
        if not steps_match:
            behavioral_flags.append("step_sequence_deviation")

        claims_checked.append(
            ClaimCheck(
                field="steps_taken",
                agent_claimed=str(payment_decision.steps_taken),
                independently_found=str(expected_step_sequence),
                match=steps_match,
                severity="warning" if not steps_match else "info",
            )
        )

    return Verdict(
        agent_id="risk",
        claims_checked=claims_checked,
        behavioral_flags=behavioral_flags,
        agent_confidence=0.85,
        confidence_z_score=z,
    )
