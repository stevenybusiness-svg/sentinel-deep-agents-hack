"""
PredictionEngine and PredictionReport — D-08, D-09, D-10, D-11.

Computes behavioral expectations from baselines BEFORE investigation dispatch.
The gap between prediction and reality (prediction error) is the primary
learning signal for the self-improvement loop.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from sentinel.schemas.payment import PaymentDecision


class PredictionReport(BaseModel):
    """Behavioral prediction formed before investigation dispatch (D-08)."""

    predicted_z_score: float  # (agent_confidence - mean) / std
    step_sequence_deviation: bool  # True if steps differ from expected order
    deviation_details: list[str] = []  # Top deviations for dashboard display (D-11)
    summary_score: float = Field(ge=0.0)  # Compact score: abs(z) * 0.3 + 0.5 if deviation
    expected_investigation_outcomes: dict[str, bool] = {}  # D-09: e.g. {"kyc_should_verify": True, ...}


class PredictionEngine:
    """Computes behavioral expectations from baselines BEFORE investigation (D-08, D-09, D-10)."""

    def predict(
        self,
        payment_decision: PaymentDecision,
        baselines: dict,
        expected_step_sequence: list[str] | None = None,
    ) -> PredictionReport:
        """Form behavioral predictions before dispatching investigators.

        Args:
            payment_decision: The Payment Agent's structured decision.
            baselines: Behavioral baseline stats dict (from fixtures).
            expected_step_sequence: Optional ordered list of expected tool calls.

        Returns:
            PredictionReport with z-score, step deviation, summary score,
            and expected investigation outcomes per D-09.
        """
        # 1. Confidence z-score from behavioral baselines
        agent_stats = baselines.get("payment_agent", {"mean": 0.52, "std": 0.11})
        mean = agent_stats["mean"]
        std = agent_stats["std"]
        z_score = (payment_decision.confidence - mean) / std if std > 0 else 0.0

        # 2. Step sequence deviation (D-07)
        deviation = False
        deviation_details: list[str] = []
        if expected_step_sequence:
            actual = payment_decision.steps_taken
            deviation, deviation_details = self._compute_step_deviation(
                actual, expected_step_sequence
            )

        # 3. Summary score (D-11: compact, dashboard-displayable)
        summary_score = abs(z_score) * 0.3 + (0.5 if deviation else 0.0)

        # 4. Expected investigation outcomes (D-09)
        expected_outcomes = self._compute_expected_outcomes(payment_decision)

        return PredictionReport(
            predicted_z_score=round(z_score, 4),
            step_sequence_deviation=deviation,
            deviation_details=deviation_details,
            summary_score=round(summary_score, 4),
            expected_investigation_outcomes=expected_outcomes,
        )

    def compare_outcomes(
        self,
        prediction: PredictionReport,
        actual_findings: dict[str, bool],
    ) -> dict:
        """Compare expected investigation outcomes with actual findings (D-09).

        Returns investigation-level prediction errors for Phase 3 rule generation.
        actual_findings keys should match expected_investigation_outcomes keys.
        e.g. {"kyc_should_verify": False} means KYC actually failed verification.
        """
        errors: dict[str, dict] = {}
        for key, expected in prediction.expected_investigation_outcomes.items():
            actual = actual_findings.get(key)
            if actual is not None and actual != expected:
                errors[key] = {
                    "expected": expected,
                    "actual": actual,
                    "error": True,
                }
            elif actual is not None:
                errors[key] = {
                    "expected": expected,
                    "actual": actual,
                    "error": False,
                }
        return {
            "outcome_errors": errors,
            "error_count": sum(1 for v in errors.values() if v["error"]),
            "total_predictions": len(prediction.expected_investigation_outcomes),
        }

    def _compute_expected_outcomes(self, payment_decision: PaymentDecision) -> dict[str, bool]:
        """Derive expected investigation outcomes from agent's claims (D-09).

        If the agent claims kyc_verified=true, we expect investigators to confirm KYC.
        If the agent claims counterparty_authorized=true, we expect it in the DB.
        If the agent read an invoice, we expect the document to be clean.
        """
        outcomes: dict[str, bool] = {}
        claims = payment_decision.claims

        # KYC verification expectation
        if claims.get("kyc_verified", "").lower() in ("true", "verified", "passed"):
            outcomes["kyc_should_verify"] = True
        elif "kyc_verified" in claims:
            outcomes["kyc_should_verify"] = False

        # Counterparty authorization expectation
        if claims.get("counterparty_authorized", "").lower() in ("true", "authorized", "found"):
            outcomes["beneficiary_in_counterparty_db"] = True
        elif "counterparty_authorized" in claims:
            outcomes["beneficiary_in_counterparty_db"] = False

        # Document cleanliness expectation (if invoice was read)
        if "read_invoice" in payment_decision.steps_taken:
            outcomes["document_should_be_clean"] = True

        # We always expect no critical field mismatches — a legitimate agent should
        # produce claims that investigators can independently confirm (Bug 3 fix)
        outcomes["no_critical_field_mismatches"] = True

        return outcomes

    def _compute_step_deviation(
        self, actual: list[str], expected: list[str]
    ) -> tuple[bool, list[str]]:
        """Check if actual steps deviate from expected sequence.

        Detects: missing steps, extra steps, and reordered steps.
        Returns (has_deviation, detail_list).
        """
        details: list[str] = []
        missing = [s for s in expected if s not in actual]
        extra = [s for s in actual if s not in expected]
        if missing:
            details.append(f"Missing steps: {', '.join(missing)}")
        if extra:
            details.append(f"Unexpected steps: {', '.join(extra)}")
        # Check order of common steps
        common_actual = [s for s in actual if s in expected]
        common_expected = [s for s in expected if s in actual]
        if common_actual != common_expected:
            details.append("Step order differs from expected sequence")
        has_deviation = len(details) > 0
        return has_deviation, details
