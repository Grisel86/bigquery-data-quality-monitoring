"""BigQuery I/O layer.

Kept deliberately thin and separate from `checks.py` so that:
  - Unit tests for check logic never need a BigQuery connection.
  - Integration tests can exercise just the connector against a sandbox.
  - Swapping clients (e.g. for a SQLAlchemy backend) requires no changes
    to check logic.
"""

from __future__ import annotations

import logging

import pandas as pd
from google.cloud import bigquery

logger = logging.getLogger(__name__)


class BigQueryConnector:
    """Thin wrapper around the BigQuery client.

    Responsibilities:
      - Authenticated client construction.
      - Query execution returning DataFrames.
      - Connection-level error handling and logging.

    Non-responsibilities:
      - Quality checks themselves (see `checks.py`).
      - Alerting (see `alerting.py` when implemented).
    """

    def __init__(
        self,
        project_id: str,
        location: str = "US",
        client: bigquery.Client | None = None,
    ) -> None:
        self.project_id = project_id
        self.location = location
        self._client = client or bigquery.Client(
            project=project_id, location=location
        )

    def query_to_dataframe(self, sql: str) -> pd.DataFrame:
        """Run a SQL query and return a pandas DataFrame.

        Args:
            sql: BigQuery Standard SQL. Avoid SELECT * in production checks —
                 prefer explicit columns to control cost.
        """
        logger.info("Executing BigQuery query")
        logger.debug("SQL: %s", sql)
        job = self._client.query(sql)
        return job.to_dataframe()

    def fetch_table(
        self,
        dataset: str,
        table: str,
        columns: list[str] | None = None,
        limit: int | None = None,
    ) -> pd.DataFrame:
        """Pull a table (or column subset) into a DataFrame.

        Always prefer this over raw SQL when you just need the data —
        it generates a safer, cheaper query.
        """
        col_expr = ", ".join(columns) if columns else "*"
        limit_clause = f"LIMIT {int(limit)}" if limit else ""
        sql = (
            f"SELECT {col_expr} "
            f"FROM `{self.project_id}.{dataset}.{table}` "
            f"{limit_clause}"
        )
        return self.query_to_dataframe(sql)
