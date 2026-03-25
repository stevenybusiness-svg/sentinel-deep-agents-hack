"""
VerdictBoardEngine — ENGN-01.

Assembles a VerdictBoard from a PaymentDecision and a list of investigator
Verdicts by performing deterministic field-level comparison. No LLM in this path.
"""
from __future__ import annotations

from sentinel.schemas.payment import PaymentDecision
from sentinel.schemas.verdict import Verdict
from sentinel.schemas.verdict_board import VerdictBoard


class VerdictBoardEngine:
    """Assembles VerdictBoard from Payment Agent decision and investigator verdicts.

    All logic is deterministic — no inference, no model weights. The board is
    the structured input to the Safety Gate.
    """

    def assemble(
        self,
        payment_decision: PaymentDecision,
        verdicts: list[Verdict],
    ) -> VerdictBoard:
        """Produce a VerdictBoard from the payment agent's decision and sub-agent findings.

        Args:
            payment_decision: Structured output from the Payment Agent.
            verdicts: List of Verdict objects from Risk, Compliance, and Forensics agents.

        Returns:
            VerdictBoard with mismatches, behavioral_flags, z-score, and deviation flags.
        """
        # 1. Collect all mismatches from each verdict's claims_checked
        mismatches: list[dict] = []
        for v in verdicts:
            for cc in v.claims_checked:
                if not cc.match:
                    mismatches.append({
                        "field": cc.field,
                        "agent_claimed": cc.agent_claimed,
                        "found": cc.independently_found,
                        "severity": cc.severity,
                        "agent_id": v.agent_id,
                    })

        # 2. Union all behavioral_flags from all verdicts (deduplicated, order preserved)
        seen_flags: set[str] = set()
        behavioral_flags: list[str] = []
        for v in verdicts:
            for flag in v.behavioral_flags:
                if flag not in seen_flags:
                    seen_flags.add(flag)
                    behavioral_flags.append(flag)

        # 3. Use payment_decision.confidence as agent_confidence
        agent_confidence = payment_decision.confidence

        # 4. Extract confidence_z_score from Risk agent verdict (agent_id="risk")
        confidence_z_score: float | None = None
        for v in verdicts:
            if v.agent_id == "risk" and v.confidence_z_score is not None:
                confidence_z_score = v.confidence_z_score
                break

        # 5. Detect step_sequence_deviation
        step_sequence_deviation = any(
            "step_sequence_deviation" in v.behavioral_flags
            for v in verdicts
        )

        # 6. hardcoded_rule_fired starts False — SafetyGate will set this after evaluation
        hardcoded_rule_fired = False

        # 7. Collect unable_to_verify: list of agent_ids where verdict.unable_to_verify=True
        unable_to_verify = [v.agent_id for v in verdicts if v.unable_to_verify]

        return VerdictBoard(
            mismatches=mismatches,
            behavioral_flags=behavioral_flags,
            agent_confidence=agent_confidence,
            confidence_z_score=confidence_z_score,
            step_sequence_deviation=step_sequence_deviation,
            hardcoded_rule_fired=hardcoded_rule_fired,
            unable_to_verify=unable_to_verify,
        )
