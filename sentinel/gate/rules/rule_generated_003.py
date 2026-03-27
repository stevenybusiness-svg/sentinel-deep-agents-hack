def score(verdict_board: dict) -> float:
    """Scores identity spoofing patterns: extreme confidence with critical mismatches, KYC gaps, and step deviations."""
    total = 0.0

    # Signal 1: Confidence z-score anomaly — extremely high confidence is suspicious
    z = verdict_board.get("confidence_z_score")
    if z is not None:
        abs_z = abs(z)
        if abs_z > 3.5:
            total += 0.5
        elif abs_z > 2.5:
            total += 0.35
        elif abs_z > 2.0:
            total += 0.2

    # Signal 2: Critical and warning mismatches
    mismatches = verdict_board.get("mismatches", [])
    critical_count = 0
    warning_count = 0
    for m in mismatches:
        severity = m.get("severity", "info")
        if severity == "critical":
            critical_count += 1
        elif severity == "warning":
            warning_count += 1
    total += critical_count * 0.25
    total += warning_count * 0.1

    # Signal 3: Behavioral flags — each relevant flag adds signal
    flags = verdict_board.get("behavioral_flags", [])
    kyc_related_flags = 0
    confidence_related_flags = 0
    for flag in flags:
        if "kyc" in flag.lower():
            kyc_related_flags += 1
        if "confidence" in flag.lower():
            confidence_related_flags += 1
    # KYC gaps are strong identity spoofing signals
    total += kyc_related_flags * 0.2
    # Multiple confidence anomaly flags reinforce the signal
    total += min(confidence_related_flags * 0.1, 0.2)

    # Signal 4: Step sequence deviation — skipping verification steps
    if verdict_board.get("step_sequence_deviation", False):
        total += 0.2

    # Signal 5: Prediction errors — system expected normal but found anomalies
    pred = verdict_board.get("prediction_errors")
    if pred is not None:
        summary = pred.get("summary_score", 0.0)
        if summary > 1.5:
            total += 0.3
        elif summary > 1.0:
            total += 0.2
        elif summary > 0.5:
            total += 0.1

        # Investigation outcome errors compound the signal
        outcome_info = pred.get("investigation_outcome_errors", {})
        error_count = outcome_info.get("error_count", 0)
        total_predictions = outcome_info.get("total_predictions", 1)
        if total_predictions > 0 and error_count > 0:
            error_rate = error_count / total_predictions
            total += error_rate * 0.2

        # Missing verification steps
        deviation_details = pred.get("deviation_details", [])
        if len(deviation_details) > 0:
            total += 0.1

    # Signal 6: Compound pattern — high confidence + critical mismatches is especially suspicious
    # (identity spoofing fingerprint: agent claims everything is fine with high confidence
    #  but critical fields don't match)
    agent_conf = verdict_board.get("agent_confidence", 0.5)
    if agent_conf > 0.9 and critical_count >= 2:
        total += 0.2

    return min(total, 2.0)