def score(verdict_board: dict) -> float:
    """Scores identity spoofing patterns: extreme confidence anomaly combined with KYC/authorization gaps and critical mismatches."""
    total = 0.0

    # Signal 1: Confidence z-score anomaly — extremely high confidence is a strong spoofing signal
    z = verdict_board.get("confidence_z_score")
    if z is not None:
        abs_z = abs(z)
        if abs_z > 3.5:
            total += 0.6
        elif abs_z > 2.5:
            total += 0.4
        elif abs_z > 2.0:
            total += 0.2

    # Signal 2: Critical mismatches — each one adds significant weight
    mismatches = verdict_board.get("mismatches", [])
    critical_count = 0
    warning_count = 0
    has_identity_related_mismatch = False
    for m in mismatches:
        severity = m.get("severity", "info")
        field = m.get("field", "")
        if severity == "critical":
            critical_count += 1
            # Identity-related fields (KYC, authorization, counterparty) are especially relevant
            if any(keyword in field.lower() for keyword in ["kyc", "authorized", "counterparty", "identity", "beneficiary"]):
                has_identity_related_mismatch = True
        elif severity == "warning":
            warning_count += 1

    total += critical_count * 0.25
    total += warning_count * 0.1
    if has_identity_related_mismatch:
        total += 0.2

    # Signal 3: Behavioral flags — especially identity/KYC/confidence related
    flags = verdict_board.get("behavioral_flags", [])
    identity_flags = 0
    for flag in flags:
        fl = flag.lower()
        if any(kw in fl for kw in ["kyc", "identity", "spoof", "unauthorized", "counterparty"]):
            identity_flags += 1
        if any(kw in fl for kw in ["confidence_anomaly", "high_confidence_deviation"]):
            total += 0.1
    total += identity_flags * 0.15

    # Signal 4: Prediction errors — investigation outcome errors indicate unexpected critical findings
    pred_errors = verdict_board.get("prediction_errors")
    if pred_errors is not None:
        summary_score = pred_errors.get("summary_score", 0.0)
        if summary_score and summary_score > 1.0:
            total += 0.2
        elif summary_score and summary_score > 0.5:
            total += 0.1

        outcome_errors = pred_errors.get("investigation_outcome_errors", {})
        error_count = outcome_errors.get("error_count", 0)
        total_predictions = outcome_errors.get("total_predictions", 1)
        if total_predictions > 0 and error_count > 0:
            total += 0.15 * error_count

    # Signal 5: Compound pattern — high confidence + critical mismatches is especially suspicious
    agent_conf = verdict_board.get("agent_confidence", 0.0)
    if agent_conf and agent_conf > 0.9 and critical_count >= 2:
        total += 0.2

    # Signal 6: Hardcoded rule already fired amplifies score
    if verdict_board.get("hardcoded_rule_fired", False):
        total += 0.15

    return min(total, 2.0)