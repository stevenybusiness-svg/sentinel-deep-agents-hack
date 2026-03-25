"""
Tests for PredictionEngine and PredictionReport (D-08, D-09, D-10, D-11).

TDD: Tests written before implementation.
"""
import pytest

from sentinel.schemas.payment import PaymentDecision
from sentinel.engine.prediction import PredictionEngine, PredictionReport


BASELINES = {
    "payment_agent": {
        "mean": 0.52,
        "std": 0.11,
        "sample_size": 847,
    }
}

EXPECTED_STEP_SEQUENCE = [
    "check_kyc",
    "check_counterparty",
    "read_invoice",
    "compute_risk",
]


def make_payment(
    confidence: float = 0.52,
    steps_taken: list[str] | None = None,
    claims: dict[str, str] | None = None,
) -> PaymentDecision:
    return PaymentDecision(
        episode_id="ep-test-001",
        decision="approve",
        amount=5000.0,
        beneficiary="Acme Corp",
        account="ACC-12345",
        rationale="All checks passed",
        steps_taken=steps_taken or ["check_kyc", "check_counterparty"],
        confidence=confidence,
        claims=claims or {},
    )


class TestZScoreComputation:
    """Test 1: z-score computation."""

    def test_mean_confidence_yields_zero_zscore(self):
        engine = PredictionEngine()
        payment = make_payment(confidence=0.52)
        report = engine.predict(payment, BASELINES)
        assert report.predicted_z_score == pytest.approx(0.0, abs=1e-4)

    def test_high_confidence_yields_positive_zscore(self):
        engine = PredictionEngine()
        payment = make_payment(confidence=0.85)
        report = engine.predict(payment, BASELINES)
        # z = (0.85 - 0.52) / 0.11 = 3.0
        assert report.predicted_z_score == pytest.approx(3.0, abs=1e-3)

    def test_low_confidence_yields_negative_zscore(self):
        engine = PredictionEngine()
        payment = make_payment(confidence=0.30)
        report = engine.predict(payment, BASELINES)
        # z = (0.30 - 0.52) / 0.11 ≈ -2.0
        assert report.predicted_z_score == pytest.approx(-2.0, abs=0.01)


class TestStepSequenceDeviation:
    """Test 2: step sequence deviation."""

    def test_matching_sequence_yields_no_deviation(self):
        engine = PredictionEngine()
        payment = make_payment(steps_taken=EXPECTED_STEP_SEQUENCE)
        report = engine.predict(payment, BASELINES, expected_step_sequence=EXPECTED_STEP_SEQUENCE)
        assert report.step_sequence_deviation is False
        assert report.deviation_details == []

    def test_missing_step_yields_deviation(self):
        engine = PredictionEngine()
        # Skip "check_counterparty" step
        steps = ["check_kyc", "read_invoice", "compute_risk"]
        payment = make_payment(steps_taken=steps)
        report = engine.predict(payment, BASELINES, expected_step_sequence=EXPECTED_STEP_SEQUENCE)
        assert report.step_sequence_deviation is True
        assert any("Missing" in d for d in report.deviation_details)

    def test_extra_step_yields_deviation(self):
        engine = PredictionEngine()
        steps = EXPECTED_STEP_SEQUENCE + ["unexpected_step"]
        payment = make_payment(steps_taken=steps)
        report = engine.predict(payment, BASELINES, expected_step_sequence=EXPECTED_STEP_SEQUENCE)
        assert report.step_sequence_deviation is True
        assert any("Unexpected" in d for d in report.deviation_details)

    def test_reordered_steps_yields_deviation(self):
        engine = PredictionEngine()
        # Reorder: put compute_risk before read_invoice
        steps = ["check_kyc", "check_counterparty", "compute_risk", "read_invoice"]
        payment = make_payment(steps_taken=steps)
        report = engine.predict(payment, BASELINES, expected_step_sequence=EXPECTED_STEP_SEQUENCE)
        assert report.step_sequence_deviation is True


class TestSummaryScore:
    """Test 3: summary_score computation."""

    def test_no_deviation_and_zero_zscore_yields_low_score(self):
        engine = PredictionEngine()
        payment = make_payment(confidence=0.52, steps_taken=EXPECTED_STEP_SEQUENCE)
        report = engine.predict(payment, BASELINES, expected_step_sequence=EXPECTED_STEP_SEQUENCE)
        # abs(0.0) * 0.3 + 0 = 0.0
        assert report.summary_score == pytest.approx(0.0, abs=1e-4)

    def test_high_zscore_and_deviation_yields_high_score(self):
        engine = PredictionEngine()
        payment = make_payment(confidence=0.95, steps_taken=["only_one_step"])
        report = engine.predict(payment, BASELINES, expected_step_sequence=EXPECTED_STEP_SEQUENCE)
        # High z-score + deviation → score > 0.5
        assert report.summary_score > 0.5


class TestPredictionReportStructure:
    """Test 4: prediction returns PredictionReport with all fields populated."""

    def test_prediction_report_has_all_fields(self):
        engine = PredictionEngine()
        payment = make_payment(confidence=0.75, steps_taken=EXPECTED_STEP_SEQUENCE)
        report = engine.predict(payment, BASELINES, expected_step_sequence=EXPECTED_STEP_SEQUENCE)

        assert isinstance(report, PredictionReport)
        assert isinstance(report.predicted_z_score, float)
        assert isinstance(report.step_sequence_deviation, bool)
        assert isinstance(report.deviation_details, list)
        assert isinstance(report.summary_score, float)
        assert isinstance(report.expected_investigation_outcomes, dict)
        assert report.summary_score >= 0.0


class TestExpectedInvestigationOutcomes:
    """Test 5: expected_investigation_outcomes computed from claims (D-09)."""

    def test_kyc_claim_true_sets_kyc_should_verify(self):
        engine = PredictionEngine()
        payment = make_payment(
            claims={"kyc_verified": "true", "counterparty_authorized": "true"},
            steps_taken=["check_kyc", "check_counterparty", "read_invoice"],
        )
        report = engine.predict(payment, BASELINES)

        assert report.expected_investigation_outcomes.get("kyc_should_verify") is True
        assert report.expected_investigation_outcomes.get("beneficiary_in_counterparty_db") is True
        assert report.expected_investigation_outcomes.get("document_should_be_clean") is True

    def test_kyc_claim_false_sets_kyc_should_not_verify(self):
        engine = PredictionEngine()
        payment = make_payment(claims={"kyc_verified": "false"})
        report = engine.predict(payment, BASELINES)
        assert report.expected_investigation_outcomes.get("kyc_should_verify") is False

    def test_no_invoice_step_does_not_set_document_clean(self):
        engine = PredictionEngine()
        payment = make_payment(claims={}, steps_taken=["check_kyc"])
        report = engine.predict(payment, BASELINES)
        assert "document_should_be_clean" not in report.expected_investigation_outcomes


class TestCompareOutcomes:
    """Test 6: compare_outcomes produces investigation-level prediction errors (D-09)."""

    def test_matching_actual_yields_no_errors(self):
        engine = PredictionEngine()
        payment = make_payment(
            claims={"kyc_verified": "true"},
            steps_taken=["check_kyc"],
        )
        report = engine.predict(payment, BASELINES)

        # Actual confirms what was expected
        actual_findings = {"kyc_should_verify": True}
        result = engine.compare_outcomes(report, actual_findings)
        assert result["error_count"] == 0

    def test_differing_actual_yields_prediction_errors(self):
        engine = PredictionEngine()
        payment = make_payment(
            claims={"kyc_verified": "true", "counterparty_authorized": "true"},
            steps_taken=["check_kyc", "check_counterparty"],
        )
        report = engine.predict(payment, BASELINES)

        # Actual contradicts expected outcomes
        actual_findings = {
            "kyc_should_verify": False,  # Agent claimed verified; investigation found NOT
            "beneficiary_in_counterparty_db": False,  # Agent claimed authorized; NOT found
        }
        result = engine.compare_outcomes(report, actual_findings)
        assert result["error_count"] > 0
        assert result["outcome_errors"]["kyc_should_verify"]["error"] is True
        assert result["outcome_errors"]["beneficiary_in_counterparty_db"]["error"] is True

    def test_compare_outcomes_returns_required_structure(self):
        engine = PredictionEngine()
        payment = make_payment(claims={"kyc_verified": "true"})
        report = engine.predict(payment, BASELINES)

        result = engine.compare_outcomes(report, {"kyc_should_verify": True})
        assert "outcome_errors" in result
        assert "error_count" in result
        assert "total_predictions" in result
        assert isinstance(result["error_count"], int)
