"""
src/quality/reporter.py
────────────────────────
Collects QualityCheckResult objects and writes them to the BigQuery
dq_check_log audit table for historical tracking.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional

from google.cloud import bigquery

from .checks import QualityCheckResult


class QualityReporter:

    def __init__(
        self,
        client:     bigquery.Client,
        log_table:  str,            # e.g. "my-project.my_dataset.dq_check_log"
        run_id:     Optional[str] = None,
    ):
        self.client    = client
        self.log_table = log_table
        self.run_id    = run_id or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        self._results: list[QualityCheckResult] = []

    def add(self, result: QualityCheckResult) -> "QualityReporter":
        result.run_id = self.run_id
        self._results.append(result)
        return self

    def add_all(self, results: list[QualityCheckResult]) -> "QualityReporter":
        for r in results:
            self.add(r)
        return self

    @property
    def passed(self) -> int:
        return sum(1 for r in self._results if r.passed)

    @property
    def failed(self) -> int:
        return len(self._results) - self.passed

    @property
    def critical_failures(self) -> list[QualityCheckResult]:
        return [r for r in self._results if not r.passed and r.critical]

    def print_summary(self) -> None:
        print(f"\n{'='*65}")
        print(f" Quality Report — Run {self.run_id}")
        print(f"{'='*65}")
        print(f" {'CHECK':<50} {'STATUS'}")
        print(f" {'-'*50} {'------'}")
        for r in self._results:
            status  = "✓ PASS" if r.passed else ("✗ FAIL [CRITICAL]" if r.critical else "⚠ FAIL")
            pct_str = f"  ({r.pct_valid:.1f}% valid)" if r.pct_valid is not None else ""
            print(f" {r.check_name:<50} {status}{pct_str}")
        print(f"{'='*65}")
        print(f" Total: {len(self._results)} | Passed: {self.passed} | Failed: {self.failed}")
        if self.critical_failures:
            print(f" ⚠  Critical failures: {len(self.critical_failures)}")
        print(f"{'='*65}\n")

    def save(self) -> dict:
        """Insert all results into the BigQuery audit log table."""
        rows = [r.to_bq_row() for r in self._results]
        errors = self.client.insert_rows_json(self.log_table, rows)
        if errors:
            print(f"[QualityReporter] WARNING: {len(errors)} row(s) failed to insert: {errors}")
        else:
            print(f"[QualityReporter] {len(rows)} results written to {self.log_table}")

        return {
            "run_id":             self.run_id,
            "total_checks":       len(self._results),
            "passed":             self.passed,
            "failed":             self.failed,
            "critical_failures":  len(self.critical_failures),
            "log_table":          self.log_table,
        }
