def score(verdict_board: dict) -> float:
    """Multiple behavioral flags compound anomaly signal.
    High flag count indicates a broadly compromised reasoning process."""
    flags = verdict_board.get("behavioral_flags", [])
    count = len(flags)
    if count > 5:
        return 0.5
    if count > 3:
        return 0.3
    return 0.0
