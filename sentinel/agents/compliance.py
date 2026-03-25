"""
Compliance Agent — PIPE-04, D-16.

Independently validates payment agent claims against authoritative fixtures:
- KYC ledger (identity verification records)
- Counterparty DB (authorization records)

Returns structured Verdict with KYC and authorization claim checks.
"""
from __future__ import annotations

from sentinel.fixtures import FixtureData
from sentinel.schemas.payment import PaymentDecision
from sentinel.schemas.verdict import ClaimCheck, Verdict


def _find_counterparty_by_name(counterparty_db: dict, name: str) -> dict | None:
    """Search counterparty_db (keyed by CP-NNN) for a counterparty by name."""
    for entry in counterparty_db.values():
        if entry.get("name", "").lower() == name.lower():
            return entry
    return None


async def validate(
    payment_decision: PaymentDecision,
    fixtures: FixtureData,
) -> Verdict:
    """Validate payment agent claims against KYC and counterparty fixtures.

    Args:
        payment_decision: The payment agent's structured decision.
        fixtures: Loaded fixture data with kyc_ledger and counterparty_db.

    Returns:
        Verdict with agent_id="compliance", KYC and authorization claim checks,
        and behavioral flags for gaps found.
    """
    kyc_ledger: dict = fixtures["kyc_ledger"]
    counterparty_db: dict = fixtures["counterparty_db"]
    beneficiary = payment_decision.beneficiary

    claims_checked: list[ClaimCheck] = []
    behavioral_flags: list[str] = []

    # --- KYC ledger check ---
    kyc_record = kyc_ledger.get(beneficiary)
    agent_kyc_claim = payment_decision.claims.get("kyc_verified", "not_checked")

    if kyc_record is None:
        kyc_found = "NOT FOUND in KYC ledger"
        kyc_match = False
        behavioral_flags.append("kyc_gap")
    else:
        status = kyc_record.get("status", "unknown")
        kyc_found = f"status={status}"
        # Agent claimed kyc_verified="true" — check if it's actually verified
        kyc_match = (agent_kyc_claim.lower() == "true") and (status == "verified")
        if not kyc_match and agent_kyc_claim.lower() == "true":
            kyc_match = False

    claims_checked.append(
        ClaimCheck(
            field="kyc_status",
            agent_claimed=agent_kyc_claim,
            independently_found=kyc_found,
            match=kyc_match,
            severity="critical" if not kyc_match else "info",
        )
    )

    # --- Counterparty DB check ---
    cp_record = _find_counterparty_by_name(counterparty_db, beneficiary)
    agent_cp_claim = payment_decision.claims.get("counterparty_authorized", "not_checked")

    if cp_record is None:
        cp_found = "NOT FOUND in counterparty DB"
        cp_match = False
        behavioral_flags.append("counterparty_not_authorized")
    else:
        authorized = cp_record.get("authorized", False)
        cp_found = f"authorized={authorized}"
        cp_match = (agent_cp_claim.lower() == "true") and authorized

    claims_checked.append(
        ClaimCheck(
            field="counterparty_authorized",
            agent_claimed=agent_cp_claim,
            independently_found=cp_found,
            match=cp_match,
            severity="critical" if not cp_match else "info",
        )
    )

    # Identity unverifiable if missing from both
    if kyc_record is None and cp_record is None:
        behavioral_flags.append("identity_unverifiable")

    return Verdict(
        agent_id="compliance",
        claims_checked=claims_checked,
        behavioral_flags=behavioral_flags,
        agent_confidence=0.90,
    )
