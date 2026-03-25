def score(verdict_board: dict) -> float:
    """Field-level mismatch severity scoring.
    Each critical mismatch strongly indicates manipulated agent output."""
    mismatches = verdict_board.get("mismatches", [])
    total = 0.0
    for m in mismatches:
        severity = m.get("severity", "info")
        if severity == "critical":
            total += 0.4
        elif severity == "warning":
            total += 0.15
    return total
