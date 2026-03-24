"""Fixture loader for Sentinel demo data."""
import json
from pathlib import Path
from typing import TypedDict

FIXTURES_DIR = Path(__file__).parent


class FixtureData(TypedDict):
    kyc_ledger: dict
    counterparty_db: dict
    behavioral_baselines: dict


def load_fixtures() -> FixtureData:
    """Load all demo fixtures from JSON files. Called once at startup."""
    def _load(name: str) -> dict:
        with open(FIXTURES_DIR / name) as f:
            return json.load(f)

    return FixtureData(
        kyc_ledger=_load("kyc_ledger.json"),
        counterparty_db=_load("counterparty_db.json"),
        behavioral_baselines=_load("behavioral_baselines.json"),
    )


def get_invoice_paths() -> dict[str, Path]:
    """Return paths to invoice image fixtures."""
    return {
        "clean": FIXTURES_DIR / "invoice_clean.png",
        "forensic": FIXTURES_DIR / "invoice_forensic.png",
    }
