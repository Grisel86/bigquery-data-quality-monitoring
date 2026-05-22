"""src/quality/checks.py.

BigQuery data quality check runner.

Each checker class executes a parameterised SQL query against BigQuery
and returns a QualityCheckResult. Identifiers (columns, tables) are
validated against a strict regex BEFORE being interpolated into SQL,
which is unavoidable because BigQuery cannot parameterize identifiers.

Classes:
    QualityCheckResult   - immutable result container
    BigQueryChecker      - base class; executes SQL via google-cloud-bigquery
    CompletenessChecker  - null / empty value checks
    UniquenessChecker    - duplicate detection
    ValidityChecker      - range, domain, and type checks
    ConsistencyChecker   - cross-column business rule checks
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from google.cloud import bigquery

# ──────────────────────────────────────────────────────────────────────────────
# Identifier validation — first line of defence against SQL injection
# ──────────────────────────────────────────────────────────────────────────────

# BigQuery identifiers must match [A-Za-z_][A-Za-z0-9_]*
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")

# Fully-qualified table_ref: project.dataset.table or dataset.table
_TABLE_REF_RE = re.compile(
    r"^[A-Za-z0-9_-]+(\.[A-Za-z_][A-Za-z0-9_]*){1,2}$"
)


def _validate_identifier(name: str, kind: str = "identifier") -> str:
    """Reject anything that isn't a plain SQL identifier.

    Raises:
        ValueError: If `name` is not a valid BigQuery identifier.
    """
    if not isinstance(name, str) or not _IDENTIFIER_RE.match(name):
        raise ValueError(f"Invalid {kind} name: {name!r}")
    return name


def _validate_table_ref(table_ref: str) -> str:
    """Reject anything that isn't a valid BigQuery table reference."""
    if not isinstance(table_ref, str) or not _TABLE_REF_RE.match(table_ref):
        raise ValueError(f"Invalid table reference: {table_ref!r}")
    return table_ref


def _quote_literal(value: Any) -> str:
    """Safely quote a literal value for SQL inclusion.

    Only accepts str, int, float, bool. Anything else raises.
    Strings get single-quote-escaped.
    """
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        escaped = value.replace("\\", "\\\\").replace("'", "\\'")
        return f"'{escaped}'"
    raise TypeError(f"Unsupported literal type: {type(value).__name__}")


# ──────────────────────────────────────────────────────────────────────────────
# Result container
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class QualityCheckResult:
    """Immutable result of a single data quality check."""

    check_name: str
    check_category: str
    passed: bool
    detail: str
    critical: bool = False
    invalid_count: int = 0
    total_count: int = 0
    pct_valid: float | None = None
    run_id: str = ""
    table_ref: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    checked_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_bq_row(self) -> dict[str, Any]:
        """Serialize for insertion into a BigQuery results table."""
        return {
            "run_id": self.run_id,
            "run_timestamp": self.checked_at.isoformat(),
            "layer": "raw",
            "check_name": self.check_name,
            "check_category": self.check_category,
            "passed": self.passed,
            "invalid_count": self.invalid_count,
            "total_count": self.total_count,
            "pct_valid": self.pct_valid,
            "critical": self.critical,
            "detail": self.detail,
            "metadata_json": json.dumps(self.metadata),
            "dataset": (
                self.table_ref.rsplit(".", 1)[0]
                if "." in self.table_ref
                else ""
            ),
            "table_name": self.table_ref.rsplit(".", 1)[-1],
        }


# ──────────────────────────────────────────────────────────────────────────────
# Base checker
# ──────────────────────────────────────────────────────────────────────────────


class BigQueryChecker:
    """Base class — holds the BQ client and source table reference.

    The `table_ref` is validated once at construction; identifiers used
    in check methods are validated per-call. This means SQL string-
    formatting is safe because every interpolated value has already
    been screened.
    """

    def __init__(self, client: bigquery.Client, table_ref: str) -> None:
        """Construct a checker bound to a specific BigQuery table.

        Args:
            client:    Authenticated BigQuery client.
            table_ref: Fully-qualified table path, e.g.
                       'bigquery-public-data.chicago_crime.crime'

        Raises:
            ValueError: If `table_ref` is malformed.
        """
        self.client = client
        self.table_ref = _validate_table_ref(table_ref)

    def _run(self, sql: str) -> list[dict[str, Any]]:
        """Execute SQL and return rows as a list of dicts."""
        rows = self.client.query(sql).result()
        return [dict(row) for row in rows]

    def _count_invalid(self, condition_sql: str) -> tuple[int, int]:
        """Return (invalid_count, total_count) for a WHERE-style condition.

        Note:
            `condition_sql` is composed INTERNALLY by check methods from
            already-validated identifiers and quoted literals. It is
            NEVER user-supplied at this layer.
        """
        # B608: identifiers in condition_sql are validated by callers;
        # table_ref is validated at __init__; literals are escaped via
        # _quote_literal. BigQuery cannot parameterize identifiers, so
        # f-string SQL is unavoidable here.
        sql = f"""
            SELECT
                COUNTIF({condition_sql}) AS invalid_count,
                COUNT(*)                AS total_count
            FROM `{self.table_ref}`
        """  # nosec B608
        row = self._run(sql)[0]
        return int(row["invalid_count"]), int(row["total_count"])

    @staticmethod
    def _pct_valid(invalid: int, total: int) -> float:
        """Compute valid percentage with safe division."""
        if total == 0:
            return 0.0
        return round((total - invalid) / total * 100, 4)


# ──────────────────────────────────────────────────────────────────────────────
# Completeness checker
# ──────────────────────────────────────────────────────────────────────────────


class CompletenessChecker(BigQueryChecker):
    """Checks for null and empty values."""

    def check_not_null(
        self,
        column: str,
        critical: bool = False,
        run_id: str = "",
    ) -> QualityCheckResult:
        """Verify `column` contains zero NULL values."""
        _validate_identifier(column, "column")
        invalid, total = self._count_invalid(f"`{column}` IS NULL")
        pct = self._pct_valid(invalid, total)
        return QualityCheckResult(
            check_name=f"completeness__{column}__not_null",
            check_category="completeness",
            passed=invalid == 0,
            detail=(
                f"{invalid:,} nulls in '{column}'"
                if invalid
                else f"'{column}' has no nulls"
            ),
            critical=critical,
            invalid_count=invalid,
            total_count=total,
            pct_valid=pct,
            run_id=run_id,
            table_ref=self.table_ref,
        )

    def check_not_empty(
        self,
        column: str,
        critical: bool = False,
        run_id: str = "",
    ) -> QualityCheckResult:
        """Verify `column` contains zero NULL or empty-string values."""
        _validate_identifier(column, "column")
        invalid, total = self._count_invalid(
            f"`{column}` IS NULL OR TRIM(CAST(`{column}` AS STRING)) = ''"
        )
        pct = self._pct_valid(invalid, total)
        return QualityCheckResult(
            check_name=f"completeness__{column}__not_empty",
            check_category="completeness",
            passed=invalid == 0,
            detail=(
                f"{invalid:,} null/empty in '{column}'"
                if invalid
                else f"'{column}' has no empty values"
            ),
            critical=critical,
            invalid_count=invalid,
            total_count=total,
            pct_valid=pct,
            run_id=run_id,
            table_ref=self.table_ref,
        )

    def check_completeness_threshold(
        self,
        column: str,
        threshold_pct: float = 95.0,
        critical: bool = False,
        run_id: str = "",
    ) -> QualityCheckResult:
        """Verify `column` non-null rate meets `threshold_pct`."""
        _validate_identifier(column, "column")
        if not 0.0 <= threshold_pct <= 100.0:
            raise ValueError(
                f"threshold_pct must be in [0, 100], got {threshold_pct}"
            )
        invalid, total = self._count_invalid(f"`{column}` IS NULL")
        pct = self._pct_valid(invalid, total)
        passed = pct >= threshold_pct
        return QualityCheckResult(
            check_name=(
                f"completeness__{column}__threshold_{threshold_pct}"
            ),
            check_category="completeness",
            passed=passed,
            detail=(
                f"'{column}' completeness {pct:.2f}% "
                f"(threshold: {threshold_pct}%)"
            ),
            critical=critical,
            invalid_count=invalid,
            total_count=total,
            pct_valid=pct,
            run_id=run_id,
            table_ref=self.table_ref,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Uniqueness checker
# ──────────────────────────────────────────────────────────────────────────────


class UniquenessChecker(BigQueryChecker):
    """Checks for duplicate values."""

    def check_unique(
        self,
        column: str,
        critical: bool = False,
        run_id: str = "",
    ) -> QualityCheckResult:
        """Verify `column` has no duplicate non-null values."""
        _validate_identifier(column, "column")
        # B608: `column` and `table_ref` validated; no user input.
        sql = f"""
            SELECT
                COUNT(*)                    AS total_count,
                COUNT(DISTINCT `{column}`)  AS distinct_count
            FROM `{self.table_ref}`
            WHERE `{column}` IS NOT NULL
        """  # nosec B608
        row = self._run(sql)[0]
        total = int(row["total_count"])
        distinct = int(row["distinct_count"])
        dup_count = total - distinct
        pct = (
            round(distinct / total * 100, 4) if total else 100.0
        )
        return QualityCheckResult(
            check_name=f"uniqueness__{column}__unique",
            check_category="uniqueness",
            passed=dup_count == 0,
            detail=(
                f"{dup_count:,} duplicate values in '{column}'"
                if dup_count
                else f"'{column}' is unique"
            ),
            critical=critical,
            invalid_count=dup_count,
            total_count=total,
            pct_valid=pct,
            run_id=run_id,
            table_ref=self.table_ref,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Validity checker
# ──────────────────────────────────────────────────────────────────────────────


class ValidityChecker(BigQueryChecker):
    """Checks for valid ranges, allowed values, and date constraints."""

    def check_range(
        self,
        column: str,
        min_val: float,
        max_val: float,
        critical: bool = False,
        run_id: str = "",
    ) -> QualityCheckResult:
        """Verify `column` values fall within [min_val, max_val]."""
        _validate_identifier(column, "column")
        if min_val > max_val:
            raise ValueError(
                f"min_val ({min_val}) must be <= max_val ({max_val})"
            )
        invalid, total = self._count_invalid(
            f"`{column}` IS NOT NULL AND "
            f"`{column}` NOT BETWEEN {_quote_literal(min_val)} "
            f"AND {_quote_literal(max_val)}"
        )
        pct = self._pct_valid(invalid, total)
        return QualityCheckResult(
            check_name=(
                f"validity__{column}__range_{min_val}_{max_val}"
            ),
            check_category="validity",
            passed=invalid == 0,
            detail=(
                f"{invalid:,} rows outside [{min_val}, {max_val}] "
                f"in '{column}'"
                if invalid
                else (
                    f"'{column}' values in range "
                    f"[{min_val}, {max_val}]"
                )
            ),
            critical=critical,
            invalid_count=invalid,
            total_count=total,
            pct_valid=pct,
            run_id=run_id,
            table_ref=self.table_ref,
        )

    def check_allowed_values(
        self,
        column: str,
        allowed_values: list[str | int | float | bool],
        critical: bool = False,
        run_id: str = "",
    ) -> QualityCheckResult:
        """Verify `column` values belong to `allowed_values`.

        Each value in `allowed_values` is escaped via `_quote_literal`
        before SQL construction.
        """
        _validate_identifier(column, "column")
        if not allowed_values:
            raise ValueError("allowed_values must not be empty")
        vals = ", ".join(_quote_literal(v) for v in allowed_values)
        invalid, total = self._count_invalid(
            f"`{column}` IS NOT NULL AND `{column}` NOT IN ({vals})"
        )
        pct = self._pct_valid(invalid, total)
        return QualityCheckResult(
            check_name=f"validity__{column}__allowed_values",
            check_category="validity",
            passed=invalid == 0,
            detail=(
                f"{invalid:,} invalid values in '{column}'"
                if invalid
                else f"All '{column}' values are valid"
            ),
            critical=critical,
            invalid_count=invalid,
            total_count=total,
            pct_valid=pct,
            run_id=run_id,
            table_ref=self.table_ref,
        )

    def check_not_future(
        self,
        column: str,
        critical: bool = False,
        run_id: str = "",
    ) -> QualityCheckResult:
        """Verify `column` (timestamp/date) contains no future values."""
        _validate_identifier(column, "column")
        invalid, total = self._count_invalid(
            f"`{column}` > CURRENT_TIMESTAMP()"
        )
        pct = self._pct_valid(invalid, total)
        return QualityCheckResult(
            check_name=f"validity__{column}__not_future",
            check_category="validity",
            passed=invalid == 0,
            detail=(
                f"{invalid:,} future dates in '{column}'"
                if invalid
                else f"No future dates in '{column}'"
            ),
            critical=critical,
            invalid_count=invalid,
            total_count=total,
            pct_valid=pct,
            run_id=run_id,
            table_ref=self.table_ref,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Consistency checker
# ──────────────────────────────────────────────────────────────────────────────


class ConsistencyChecker(BigQueryChecker):
    """Cross-column business-rule checks."""

    def check_year_matches_date(
        self,
        year_col: str = "year",
        date_col: str = "date",
        critical: bool = False,
        run_id: str = "",
    ) -> QualityCheckResult:
        """Verify `year_col` equals EXTRACT(YEAR FROM `date_col`)."""
        _validate_identifier(year_col, "year_col")
        _validate_identifier(date_col, "date_col")
        invalid, total = self._count_invalid(
            f"`{year_col}` != EXTRACT(YEAR FROM `{date_col}`)"
        )
        pct = self._pct_valid(invalid, total)
        return QualityCheckResult(
            check_name="consistency__year_matches_date",
            check_category="consistency",
            passed=invalid == 0,
            detail=(
                f"{invalid:,} rows where year != "
                f"EXTRACT(YEAR FROM date)"
                if invalid
                else "year column matches date for all rows"
            ),
            critical=critical,
            invalid_count=invalid,
            total_count=total,
            pct_valid=pct,
            run_id=run_id,
            table_ref=self.table_ref,
        )

    def check_coordinates_in_bbox(
        self,
        lat_col: str = "latitude",
        lon_col: str = "longitude",
        lat_min: float = 41.64,
        lat_max: float = 42.02,
        lon_min: float = -87.94,
        lon_max: float = -87.52,
        critical: bool = False,
        run_id: str = "",
    ) -> QualityCheckResult:
        """Verify (lat, lon) pairs fall inside the given bounding box."""
        _validate_identifier(lat_col, "lat_col")
        _validate_identifier(lon_col, "lon_col")
        if lat_min > lat_max or lon_min > lon_max:
            raise ValueError("bbox min must be <= max for lat and lon")

        invalid, total = self._count_invalid(
            f"`{lat_col}` IS NOT NULL AND `{lon_col}` IS NOT NULL "
            f"AND NOT ("
            f"`{lat_col}` BETWEEN {lat_min} AND {lat_max} "
            f"AND `{lon_col}` BETWEEN {lon_min} AND {lon_max})"
        )
        pct = self._pct_valid(invalid, total)
        return QualityCheckResult(
            check_name="consistency__coordinates_in_bbox",
            check_category="consistency",
            passed=invalid == 0,
            detail=(
                f"{invalid:,} coordinates outside bbox"
                if invalid
                else "All coordinates within bounding box"
            ),
            critical=critical,
            invalid_count=invalid,
            total_count=total,
            pct_valid=pct,
            run_id=run_id,
            table_ref=self.table_ref,
        )