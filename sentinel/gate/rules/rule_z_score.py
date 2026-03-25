def score(verdict_board: dict) -> float:
    """Confidence z-score anomaly detection.
    Agent confidence far from behavioral baseline is a manipulation signal."""
    z = verdict_board.get("confidence_z_score")
    if z is None:
        return 0.0
    abs_z = abs(z)
    if abs_z > 3.0:
        return 0.6
    if abs_z > 2.0:
        return 0.3
    return 0.0
