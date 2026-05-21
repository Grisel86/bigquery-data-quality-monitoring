"""Sandbox cleanup utilities.

Called after integration tests to purge any test data they left behind.
Keep this idempotent — it must succeed even if no test data exists.
"""

from __future__ import annotations

import logging
import os

from google.cloud import bigquery

logger = logging.getLogger(__name__)


def purge_test_data() -> None:
    """Delete tables prefixed with 'test_' in the configured test dataset."""
    project = os.getenv("GCP_PROJECT_ID")
    dataset = os.getenv("BIGQUERY_DATASET")
    if not project or not dataset:
        logger.info("No sandbox configured — skipping cleanup")
        return

    client = bigquery.Client(project=project)
    dataset_ref = f"{project}.{dataset}"
    for table in client.list_tables(dataset_ref):
        if table.table_id.startswith("test_"):
            client.delete_table(
                f"{dataset_ref}.{table.table_id}", not_found_ok=True
            )
            logger.info("Deleted test table: %s", table.table_id)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    purge_test_data()
