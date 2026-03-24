"""Tests for demo fixture loader — Plan 01-04."""
import pytest
from pathlib import Path


def test_load_fixtures_returns_all_three_keys():
    """load_fixtures() returns dict with kyc_ledger, counterparty_db, behavioral_baselines."""
    from sentinel.fixtures import load_fixtures, FixtureData
    data = load_fixtures()
    assert "kyc_ledger" in data
    assert "counterparty_db" in data
    assert "behavioral_baselines" in data


def test_meridian_logistics_absent_from_kyc_ledger():
    """Meridian Logistics must NOT be in kyc_ledger — intentional gap for Phase 2 attack."""
    from sentinel.fixtures import load_fixtures
    data = load_fixtures()
    assert "Meridian Logistics" not in data["kyc_ledger"]


def test_kyc_ledger_has_at_least_three_companies():
    """kyc_ledger contains at least 3 legitimate companies."""
    from sentinel.fixtures import load_fixtures
    data = load_fixtures()
    assert len(data["kyc_ledger"]) >= 3


def test_counterparty_db_has_at_least_two_records():
    """counterparty_db contains at least 2 counterparty records."""
    from sentinel.fixtures import load_fixtures
    data = load_fixtures()
    assert len(data["counterparty_db"]) >= 2


def test_behavioral_baselines_mean():
    """behavioral_baselines payment_agent mean == 0.52."""
    from sentinel.fixtures import load_fixtures
    data = load_fixtures()
    assert data["behavioral_baselines"]["payment_agent"]["mean"] == 0.52


def test_behavioral_baselines_std():
    """behavioral_baselines payment_agent std == 0.11."""
    from sentinel.fixtures import load_fixtures
    data = load_fixtures()
    assert data["behavioral_baselines"]["payment_agent"]["std"] == 0.11


def test_invoice_clean_png_exists_and_not_stub():
    """invoice_clean.png exists and is > 1000 bytes (real image, not minimal stub)."""
    from sentinel.fixtures import get_invoice_paths
    paths = get_invoice_paths()
    assert paths["clean"].exists(), "invoice_clean.png does not exist"
    assert paths["clean"].stat().st_size > 1000, (
        f"invoice_clean.png too small ({paths['clean'].stat().st_size} bytes) — must be a real image"
    )


def test_invoice_forensic_png_exists_and_not_stub():
    """invoice_forensic.png exists and is > 1000 bytes (real image, not minimal stub)."""
    from sentinel.fixtures import get_invoice_paths
    paths = get_invoice_paths()
    assert paths["forensic"].exists(), "invoice_forensic.png does not exist"
    assert paths["forensic"].stat().st_size > 1000, (
        f"invoice_forensic.png too small ({paths['forensic'].stat().st_size} bytes) — must be a real image"
    )


def test_invoice_clean_valid_png():
    """invoice_clean.png has valid PNG magic bytes."""
    from sentinel.fixtures import get_invoice_paths
    paths = get_invoice_paths()
    data = open(paths["clean"], "rb").read(8)
    assert data == b"\x89PNG\r\n\x1a\n", f"invoice_clean.png is not a valid PNG (magic bytes: {data!r})"


def test_invoice_forensic_valid_png():
    """invoice_forensic.png has valid PNG magic bytes."""
    from sentinel.fixtures import get_invoice_paths
    paths = get_invoice_paths()
    data = open(paths["forensic"], "rb").read(8)
    assert data == b"\x89PNG\r\n\x1a\n", f"invoice_forensic.png is not a valid PNG (magic bytes: {data!r})"


def test_fixture_data_type_annotation():
    """FixtureData TypedDict has the required keys as annotations."""
    from sentinel.fixtures import FixtureData
    annotations = FixtureData.__annotations__
    assert "kyc_ledger" in annotations
    assert "counterparty_db" in annotations
    assert "behavioral_baselines" in annotations
