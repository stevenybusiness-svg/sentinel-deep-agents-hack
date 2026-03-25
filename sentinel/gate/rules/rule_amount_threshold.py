def score(verdict_board: dict) -> float:
    """High-value transaction anomaly scoring.
    Large amounts warrant higher scrutiny; elevated flag on mismatches."""
    mismatches = verdict_board.get("mismatches", [])
    # Extract amount from mismatch fields if present, or from a top-level field
    # The verdict board may carry amount via mismatches tagged 'amount' field
    amount = verdict_board.get("amount", 0)
    if not amount:
        # Scan mismatches for amount-related fields
        for m in mismatches:
            if "amount" in m.get("field", "").lower():
                try:
                    amount = float(str(m.get("agent_claimed", "0")).replace(",", ""))
                except (ValueError, TypeError):
                    pass
    if amount > 100000:
        return 0.35
    if amount > 50000:
        return 0.2
    return 0.0
