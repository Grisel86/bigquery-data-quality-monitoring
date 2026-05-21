"""Shared pytest fixtures.

Anything reused by 2+ tests goes here. Test-local fixtures stay in the test file.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"


# ============================================================
# DataFrame fixtures — known-good and known-bad shapes
# ============================================================
@pytest.fixture
def clean_customers_df() -> pd.DataFrame:
    """Reference 'good' dataset — no nulls, no duplicates, valid ranges."""
    return pd.DataFrame(
        {
            "customer_id": [1, 2, 3, 4, 5],
            "email": [
                "ana@example.com",
                "bea@example.com",
                "carla@example.com",
                "diana@example.com",
                "elena@example.com",
            ],
            "age": [25, 34, 41, 29, 52],
            "country": ["AR", "AR", "BR", "CL", "AR"],
        }
    )


@pytest.fixture
def df_with_nulls() -> pd.DataFrame:
    """Dataset with nulls in email and age columns."""
    return pd.DataFrame(
        {
            "customer_id": [1, 2, 3, 4],
            "email": ["a@x.com", None, "c@x.com", None],
            "age": [25, 34, None, 29],
        }
    )


@pytest.fixture
def df_with_duplicates() -> pd.DataFrame:
    """Dataset with duplicate customer_id values."""
    return pd.DataFrame(
        {
            "customer_id": [1, 2, 2, 3, 3, 3],
            "email": ["a", "b", "b", "c", "c", "c"],
        }
    )


@pytest.fixture
def df_with_out_of_range() -> pd.DataFrame:
    """Dataset with age values outside [0, 120]."""
    return pd.DataFrame(
        {
            "customer_id": [1, 2, 3, 4, 5],
            "age": [25, -5, 200, 34, 999],
        }
    )


@pytest.fixture
def empty_df() -> pd.DataFrame:
    """Edge case: empty DataFrame with the expected schema."""
    return pd.DataFrame({"customer_id": [], "email": [], "age": []})


# ============================================================
# Mock BigQuery client — for testing the connector
# ============================================================
@pytest.fixture
def mock_bq_client(mocker):
    """A mocked bigquery.Client that returns a controllable DataFrame."""
    mock_client = mocker.MagicMock()
    mock_job = mocker.MagicMock()
    mock_job.to_dataframe.return_value = pd.DataFrame(
        {"customer_id": [1, 2], "email": ["a@x.com", "b@x.com"]}
    )
    mock_client.query.return_value = mock_job
    return mock_client


# ============================================================
# Markers — runtime guards
# ============================================================
def pytest_collection_modifyitems(config, items):
    """Mark integration/e2e tests so they're easy to filter."""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "contract" in str(item.fspath):
            item.add_marker(pytest.mark.contract)
        elif "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        elif "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
