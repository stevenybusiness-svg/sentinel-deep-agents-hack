def score(verdict_board: dict) -> float:
    """Unknown or unauthorized beneficiary detection.
    Counterparty not in ledger or KYC gap are strong anomaly signals."""
    flags = verdict_board.get("behavioral_flags", [])
    total = 0.0
    if "counterparty_not_authorized" in flags:
        total += 0.4
    if "kyc_gap" in flags:
        total += 0.3
    return total
