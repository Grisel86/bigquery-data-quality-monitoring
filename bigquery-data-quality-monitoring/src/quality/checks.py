"""
src/quality/checks.py
─────────────────────
BigQuery data quality check runner.

Each check class executes a parameterised SQL query against BigQuery
and returns a QualityCheckResult. No hardcoded project/dataset references
— everything is injected via config.

Classes:
    QualityCheckResult   — immutable result container
    BigQueryChecker      — base class, executes SQL via google-cloud-bigquery
    CompletenessChecker  — null / empty value checks
    UniquenessChecker    — duplicate detection
    ValidityChecker      — range, domain, and type checks
    ConsistencyChecker   — cross-column business rule checks
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from google.cloud import bigquery


# ──────────────────────────────────────────────────────────────────────────────
# Result container
# ──────────────────────────────────────────────────────────────────────────────

@dataclass
class QualityCheckResult:
    check_name:     str
    check_category: str
    passed:         bool
    detail:         str
    critical:       bool      = False
    invalid_count:  int       = 0
    total_count:    int       = 0
    pct_valid:      Optional[float] = None
    run_id:         str       = ""
    table_ref:      str       = ""
    metadata:       dict      = field(default_factory=dict)
    checked_at:     datetime  = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_bq_row(self) -> dict:
        return {
            "run_id":          self.run_id,
            "run_timestamp":   self.checked_at.isoformat(),
            "layer":           "raw",
            "check_name":      self.check_name,
            "check_category":  self.check_category,
            "passed":          self.passed,
            "invalid_count":   self.invalid_count,
            "total_count":     self.total_count,
            "pct_valid":       self.pct_valid,
            "critical":        self.critical,
            "detail":          self.detail,
            "metadata_json":   json.dumps(self.metadata),
            "dataset":         self.table_ref.rsplit(".", 1)[0] if "." in self.table_ref else "",
            "table_name":      self.table_ref.rsplit(".", 1)[-1],
        }


# ──────────────────────────────────────────────────────────────────────────────
# Base checker
# ──────────────────────────────────────────────────────────────────────────────

class BigQueryChecker:
    """Base class — holds the BQ client and source table reference."""

    def __init__(self, client: bigquery.Client, table_ref: str):
        """
        Args:
            client:    Authenticated BigQuery client.
            table_ref: Fully-qualified table path, e.g.
                       'bigquery-public-data.chicago_crime.crime'
        """
        self.client    = client
        self.table_ref = table_ref

    def _run(self, sql: str) -> list[dict]:
        """Execute SQL and return rows as a list of dicts."""
        rows = self.client.query(sql).result()
        return [dict(row) for row in rows]

    def _count_invalid(self, condition_sql: str) -> tuple[int, int]:
        """Returns (invalid_count, total_count) for a WHERE condition."""
        sql = f"""
            SELECT
                COUNTIF({condition_sql}) AS invalid_count,
                COUNT(*)                AS total_count
            FROM `{self.table_ref}`
        """
        row = self._run(sql)[0]
        return row["invalid_count"], row["total_count"]


# ──────────────────────────────────────────────────────────────────────────────
# Completeness checker
# ──────────────────────────────────────────────────────────────────────────────

class CompletenessChecker(BigQueryChecker):

    def check_not_null(
        self,
        column:   str,
        critical: bool = False,
        run_id:   str  = "",
    ) -> QualityCheckResult:
        invalid, total = self._count_invalid(f"`{column}` IS NULL")
        pct = round((total - invalid) / total * 100, 4) if total else 0.0
        return QualityCheckResult(
            check_name     = f"completeness__{column}__not_null",
            check_category = "completeness",
            passed         = invalid == 0,
            detail         = (f"{invalid:,} nulls in '{column}'" if invalid
                              else f"'{column}' has no nulls"),
            critical       = critical,
            invalid_count  = invalid,
            total_count    = total,
            pct_valid      = pct,
            run_id         = run_id,
            table_ref      = self.table_ref,
        )

    def check_not_empty(
        self,
        column:   str,
        critical: bool = False,
        run_id:   str  = "",
    ) -> QualityCheckResult:
        invalid, total = self._count_invalid(
            f"`{column}` IS NULL OR TRIM(CAST(`{column}` AS STRING)) = ''"
        )
        pct = round((total - invalid) / total * 100, 4) if total else 0.0
        return QualityCheckResult(
            check_name     = f"completeness__{column}__not_empty",
            check_category = "completeness",
            passed         = invalid == 0,
            detail         = (f"{invalid:,} null/empty in '{column}'" if invalid
                              else f"'{column}' has no empty values"),
            critical       = critical,
            invalid_count  = invalid,
            total_count    = total,
            pct_valid      = pct,
            run_id         = run_id,
            table_ref      = self.table_ref,
        )

    def check_completeness_threshold(
        self,
        column:        str,
        threshold_pct: float = 95.0,
        critical:      bool  = False,
        run_id:        str   = "",
    ) -> QualityCheckResult:
        invalid, total = self._count_invalid(f"`{column}` IS NULL")
        pct = round((total - invalid) / total * 100, 4) if total else 0.0
        passed = pct >= threshold_pct
        return QualityCheckResult(
            check_name     = f"completeness__{column}__threshold_{threshold_pct}",
            check_category = "completeness",
            passed         = passed,
            detail         = (f"'{column}' completeness {pct:.2f}% "
                              f"(threshold: {threshold_pct}%)"),
            critical       = critical,
            invalid_count  = invalid,
            total_count    = total,
            pct_valid      = pct,
            run_id         = run_id,
            table_ref      = self.table_ref,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Uniqueness checker
# ──────────────────────────────────────────────────────────────────────────────

class UniquenessChecker(BigQueryChecker):

    def check_unique(
        self,
        column:   str,
        critical: bool = False,
        run_id:   str  = "",
    ) -> QualityCheckResult:
        sql = f"""
            SELECT
                COUNT(*)                    AS total_count,
                COUNT(DISTINCT `{column}`)  AS distinct_count
            FROM `{self.table_ref}`
            WHERE `{column}` IS NOT NULL
        """
        row          = self._run(sql)[0]
        total        = row["total_count"]
        distinct     = row["distinct_count"]
        dup_count    = total - distinct
        pct          = round(distinct / total * 100, 4) if total else 100.0
        return QualityCheckResult(
            check_name     = f"uniqueness__{column}__unique",
            check_category = "uniqueness",
            passed         = dup_count == 0,
            detail         = (f"{dup_count:,} duplicate values in '{column}'" if dup_count
                              else f"'{column}' is unique"),
            critical       = critical,
            invalid_count  = dup_count,
            total_count    = total,
            pct_valid      = pct,
            run_id         = run_id,
            table_ref      = self.table_ref,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Validity checker
# ──────────────────────────────────────────────────────────────────────────────

class ValidityChecker(BigQueryChecker):

    def check_range(
        self,
        column:   str,
        min_val:  float,
        max_val:  float,
        critical: bool  = False,
        run_id:   str   = "",
    ) -> QualityCheckResult:
        invalid, total = self._count_invalid(
            f"`{column}` IS NOT NULL AND `{column}` NOT BETWEEN {min_val} AND {max_val}"
        )
        pct = round((total - invalid) / total * 100, 4) if total else 0.0
        return QualityCheckResult(
            check_name     = f"validity__{column}__range_{min_val}_{max_val}",
            check_category = "validity",
            passed         = invalid == 0,
            detail         = (f"{invalid:,} rows outside [{min_val}, {max_val}] in '{column}'"
                              if invalid else f"'{column}' values in range [{min_val}, {max_val}]"),
            critical       = critical,
            invalid_count  = invalid,
            total_count    = total,
            pct_valid      = pct,
            run_id         = run_id,
            table_ref      = self.table_ref,
        )

    def check_allowed_values(
        self,
        column:         str,
        allowed_values: list,
        critical:       bool = False,
        run_id:         str  = "",
    ) -> QualityCheckResult:
        vals = ", ".join(f"'{v}'" if isinstance(v, str) else str(v) for v in allowed_values)
        invalid, total = self._count_invalid(
            f"`{column}` IS NOT NULL AND `{column}` NOT IN ({vals})"
        )
        pct = round((total - invalid) / total * 100, 4) if total else 0.0
        return QualityCheckResult(
            check_name     = f"validity__{column}__allowed_values",
            check_category = "validity",
            passed         = invalid == 0,
            detail         = (f"{invalid:,} invalid values in '{column}'" if invalid
                              else f"All '{column}' values are valid"),
            critical       = critical,
            invalid_count  = invalid,
            total_count    = total,
            pct_valid      = pct,
            run_id         = run_id,
            table_ref      = self.table_ref,
        )

    def check_not_future(
        self,
        column:   str,
        critical: bool = False,
        run_id:   str  = "",
    ) -> QualityCheckResult:
        invalid, total = self._count_invalid(
            f"`{column}` > CURRENT_TIMESTAMP()"
        )
        pct = round((total - invalid) / total * 100, 4) if total else 0.0
        return QualityCheckResult(
            check_name     = f"validity__{column}__not_future",
            check_category = "validity",
            passed         = invalid == 0,
            detail         = (f"{invalid:,} future dates in '{column}'" if invalid
                              else f"No future dates in '{column}'"),
            critical       = critical,
            invalid_count  = invalid,
            total_count    = total,
            pct_valid      = pct,
            run_id         = run_id,
            table_ref      = self.table_ref,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Consistency checker
# ──────────────────────────────────────────────────────────────────────────────

class ConsistencyChecker(BigQueryChecker):

    def check_year_matches_date(
        self,
        year_col: str = "year",
        date_col: str = "date",
        critical: bool = False,
        run_id:   str  = "",
    ) -> QualityCheckResult:
        invalid, total = self._count_invalid(
            f"`{year_col}` != EXTRACT(YEAR FROM `{date_col}`)"
        )
        pct = round((total - invalid) / total * 100, 4) if total else 0.0
        return QualityCheckResult(
            check_name     = "consistency__year_matches_date",
            check_category = "consistency",
            passed         = invalid == 0,
            detail         = (f"{invalid:,} rows where year ≠ EXTRACT(YEAR FROM date)"
                              if invalid else "year column matches date for all rows"),
            critical       = critical,
            invalid_count  = invalid,
            total_count    = total,
            pct_valid      = pct,
            run_id         = run_id,
            table_ref      = self.table_ref,
        )

    def check_coordinates_in_bbox(
        self,
        lat_col:  str   = "latitude",
        lon_col:  str   = "longitude",
        lat_min:  float = 41.64,
        lat_max:  float = 42.02,
        lon_min:  float = -87.94,
        lon_max:  float = -87.52,
        critical: bool  = False,
        run_id:   str   = "",
    ) -> QualityCheckResult:
        invalid, total = self._count_invalid(
            f"""`{lat_col}` IS NOT NULL AND `{lon_col}` IS NOT NULL
            AND NOT (`{lat_col}` BETWEEN {lat_min} AND {lat_max}
                     AND `{lon_col}` BETWEEN {lon_min} AND {lon_max})"""
        )
        pct = round((total - invalid) / total * 100, 4) if total else 0.0
        return QualityCheckResult(
            check_name     = "consistency__coordinates_in_chicago_bbox",
            check_category = "consistency",
            passed         = invalid == 0,
            detail         = (f"{invalid:,} coordinates outside Chicago bbox" if invalid
                              else "All coordinates within Chicago bounding box"),
            critical       = critical,
            invalid_count  = invalid,
            total_count    = total,
            pct_valid      = pct,
            run_id         = run_id,
            table_ref      = self.table_ref,
        )
