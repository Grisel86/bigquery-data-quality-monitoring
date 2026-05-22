"""BigQuery I/O layer.

Kept deliberately thin and separate from `checks.py` so that:
  - Unit tests for check logic never need a BigQuery connection.
  - Integration tests can exercise just the connector against a sandbox.
  - Swapping clients requires no changes to check logic.
"""

from __future__ import annotations

import logging
import re

import pandas as pd
from google.cloud import bigquery

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────
# Identifier validation — first line of defence against SQL injection
# ──────────────────────────────────────────────────────────────────────

_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_identifier(name: str, kind: str = "identifier") -> str:
    """Reject anything that isn't a plain SQL identifier.

    BigQuery identifiers must match [A-Za-z_][A-Za-z0-9_]*.
    This blocks injection attempts before SQL is built.

    Raises:
        ValueError: If `name` is not a valid identifier.
    """
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid {kind} name: {name!r}")
    return name


# ──────────────────────────────────────────────────────────────────────
# Connector
# ──────────────────────────────────────────────────────────────────────


class BigQueryConnector:
    """Thin wrapper around the BigQuery client.

    Responsibilities:
      - Authenticated client construction.
      - Query execution returning DataFrames.
      - Identifier validation before SQL construction.

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

        All identifiers are validated against a strict regex before being
        interpolated into SQL. BigQuery cannot parameterize identifiers,
        so input validation is the safe alternative.
        """
        _validate_identifier(dataset, "dataset")
        _validate_identifier(table, "table")
        if columns:
            for col in columns:
                _validate_identifier(col, "column")
            col_expr = ", ".join(columns)
        else:
            col_expr = "*"

        limit_clause = f"LIMIT {int(limit)}" if limit else ""

        # B608: identifiers are validated above; LIMIT is int-coerced.
        # BigQuery cannot parameterize identifiers, so f-string SQL is
        # unavoidable here.
        sql = (
            f"SELECT {col_expr} "  # nosec B608
            f"FROM `{self.project_id}.{dataset}.{table}` "
            f"{limit_clause}"
        )
        return self.query_to_dataframe(sql)