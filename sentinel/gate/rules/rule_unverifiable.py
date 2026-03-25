def score(verdict_board: dict) -> float:
    """Unverifiable claims penalty.
    Each agent that couldn't independently verify adds anomaly signal."""
    unable_to_verify = verdict_board.get("unable_to_verify", [])
    return len(unable_to_verify) * 0.3
