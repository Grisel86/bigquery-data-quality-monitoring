"""Contract tests — regression catalog of known-bad data scenarios.

This is a senior QE pattern adapted for data quality tooling:
  Every bug we fix adds a scenario row to `bad_data_catalog.csv` along with the
  check that should now catch it. If the check ever stops catching it, this test
  fails and prevents the regression from shipping silently.

Add new scenarios to the catalog AND register them in EXPECTED_FAILURES below.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

from src.checks import check_null_rate, check_uniqueness, check_value_range

CATALOG = Path(__file__).parent.parent / "fixtures" / "bad_data_catalog.csv"


@pytest.fixture(scope="module")
def catalog_df() -> pd.DataFrame:
    """Load the bad-data catalog once per test module."""
    return pd.read_csv(CATALOG)


# Each entry: (scenario_id, check function name, expected to fail?)
EXPECTED_FAILURES = [
    ("NULL_EMAIL_001", "null_email", True),
    ("NULL_EMAIL_002", "null_email", True),
    ("DUP_ID_001", "duplicate_id", True),
    ("NEG_AGE_001", "invalid_age", True),
    ("HIGH_AGE_001", "invalid_age", True),
]


@pytest.mark.contract
@pytest.mark.parametrize(
    "scenario_id,check_kind,should_fail", EXPECTED_FAILURES
)
def test_known_bad_data_is_caught(
    catalog_df, scenario_id, check_kind, should_fail
):
    """Every known-bad scenario must still be detected by the right check."""
    subset = catalog_df[catalog_df["scenario_id"] == scenario_id]
    assert not subset.empty, f"Scenario {scenario_id} missing from catalog"

    if check_kind == "null_email":
        result = check_null_rate(subset, "email", max_null_rate=0.0)
    elif check_kind == "duplicate_id":
        result = check_uniqueness(subset, ["customer_id"])
    elif check_kind == "invalid_age":
        result = check_value_range(subset, "age", min_value=0, max_value=120)
    else:
        pytest.fail(f"Unknown check kind: {check_kind}")

    assert result.passed != should_fail, (
        f"Scenario {scenario_id}: expected check to "
        f"{'fail' if should_fail else 'pass'}, got passed={result.passed}"
    )
