"""Integration tests — hit a real BigQuery sandbox.

These tests are SKIPPED unless GCP_PROJECT_ID and BIGQUERY_DATASET are set.
Locally: export GCP_PROJECT_ID=... BIGQUERY_DATASET=... and run:
    pytest tests/integration -m integration

CI: secrets are injected via the `integration` GitHub Environment.
"""

from __future__ import annotations

import os

import pytest

from src.checks import check_null_rate
from src.connector import BigQueryConnector

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def bq_config():
    project = os.getenv("GCP_PROJECT_ID")
    dataset = os.getenv("BIGQUERY_DATASET")
    if not project or not dataset:
        pytest.skip("BigQuery sandbox credentials not configured")
    return {"project": project, "dataset": dataset}


@pytest.fixture(scope="module")
def connector(bq_config):
    return BigQueryConnector(project_id=bq_config["project"])


def test_can_query_public_dataset(connector):
    """Smoke test: verify we can run any query at all."""
    df = connector.query_to_dataframe(
        "SELECT 1 AS one, 'hello' AS greeting"
    )
    assert len(df) == 1
    assert df["one"].iloc[0] == 1
    assert df["greeting"].iloc[0] == "hello"


def test_null_check_against_seeded_table(connector, bq_config):
    """Pull a seeded table and run a real check against it.

    The test dataset must contain a `customers_clean` table seeded by
    `tests/integration/cleanup.py` or a fixture loader.
    """
    df = connector.fetch_table(
        dataset=bq_config["dataset"],
        table="customers_clean",
        columns=["customer_id", "email"],
        limit=1000,
    )
    if df.empty:
        pytest.skip("Seed table is empty — run the fixture loader first")
    result = check_null_rate(df, "customer_id", max_null_rate=0.0)
    assert result.passed, f"Seed table has nulls in customer_id: {result.message}"
