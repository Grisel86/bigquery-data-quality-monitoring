"""
tests/test_checks.py
─────────────────────
Unit tests for the quality check classes.

All BigQuery calls are mocked — no GCP credentials required.
Tests validate the check logic (pass/fail conditions, pct calculation)
without making real API calls.
"""

import os
import sys
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from quality.checks import (
    QualityCheckResult,
    CompletenessChecker,
    UniquenessChecker,
    ValidityChecker,
    ConsistencyChecker,
)


TABLE_REF = "bigquery-public-data.chicago_crime.crime"


def make_client(query_rows: list[dict]) -> MagicMock:
    """Build a mock BigQuery client that returns `query_rows` on .query().result()."""
    mock_row_iter = MagicMock()
    mock_row_iter.__iter__ = MagicMock(return_value=iter(query_rows))

    mock_query_job = MagicMock()
    mock_query_job.result.return_value = mock_row_iter

    mock_client = MagicMock()
    mock_client.query.return_value = mock_query_job
    return mock_client


# ──────────────────────────────────────────────────────────────────────────────
# QualityCheckResult
# ──────────────────────────────────────────────────────────────────────────────

class TestQualityCheckResult:

    def test_to_bq_row_has_required_keys(self):
        result = QualityCheckResult(
            check_name     = "test_check",
            check_category = "completeness",
            passed         = True,
            detail         = "All good",
            run_id         = "20240101_120000",
            table_ref      = "project.dataset.table",
        )
        row = result.to_bq_row()
        required = ["run_id", "run_timestamp", "check_name", "passed",
                    "check_category", "invalid_count", "total_count", "pct_valid"]
        for key in required:
            assert key in row, f"Missing key in bq_row: {key}"

    def test_to_bq_row_splits_table_ref(self):
        result = QualityCheckResult(
            check_name="x", check_category="c", passed=True, detail="d",
            table_ref="my-project.my_dataset.my_table"
        )
        row = result.to_bq_row()
        assert row["table_name"] == "my_table"
        assert row["dataset"]    == "my-project.my_dataset"


# ──────────────────────────────────────────────────────────────────────────────
# CompletenessChecker
# ──────────────────────────────────────────────────────────────────────────────

class TestCompletenessChecker:

    def test_not_null_passes_when_no_nulls(self):
        client  = make_client([{"invalid_count": 0, "total_count": 1000}])
        checker = CompletenessChecker(client, TABLE_REF)
        result  = checker.check_not_null("date", critical=True)

        assert result.passed
        assert result.invalid_count == 0
        assert result.pct_valid     == 100.0
        assert result.critical      is True

    def test_not_null_fails_when_nulls_exist(self):
        client  = make_client([{"invalid_count": 50, "total_count": 1000}])
        checker = CompletenessChecker(client, TABLE_REF)
        result  = checker.check_not_null("date")

        assert not result.passed
        assert result.invalid_count == 50
        assert result.pct_valid     == pytest.approx(95.0, abs=0.01)

    def test_completeness_threshold_passes_above(self):
        client  = make_client([{"invalid_count": 100, "total_count": 1000}])
        checker = CompletenessChecker(client, TABLE_REF)
        result  = checker.check_completeness_threshold("latitude", threshold_pct=85.0)

        assert result.passed          # 90% > 85%
        assert result.pct_valid == pytest.approx(90.0, abs=0.01)

    def test_completeness_threshold_fails_below(self):
        client  = make_client([{"invalid_count": 300, "total_count": 1000}])
        checker = CompletenessChecker(client, TABLE_REF)
        result  = checker.check_completeness_threshold("latitude", threshold_pct=95.0)

        assert not result.passed      # 70% < 95%
        assert result.pct_valid == pytest.approx(70.0, abs=0.01)

    def test_check_name_format(self):
        client  = make_client([{"invalid_count": 0, "total_count": 500}])
        checker = CompletenessChecker(client, TABLE_REF)
        result  = checker.check_not_null("primary_type")
        assert result.check_name == "completeness__primary_type__not_null"

    def test_run_id_propagated(self):
        client  = make_client([{"invalid_count": 0, "total_count": 500}])
        checker = CompletenessChecker(client, TABLE_REF)
        result  = checker.check_not_null("date", run_id="TEST_RUN_001")
        assert result.run_id == "TEST_RUN_001"

    def test_zero_total_count_handled(self):
        client  = make_client([{"invalid_count": 0, "total_count": 0}])
        checker = CompletenessChecker(client, TABLE_REF)
        result  = checker.check_not_null("date")
        assert result.pct_valid == 0.0  # no division by zero


# ──────────────────────────────────────────────────────────────────────────────
# UniquenessChecker
# ──────────────────────────────────────────────────────────────────────────────

class TestUniquenessChecker:

    def test_unique_passes_no_duplicates(self):
        client  = make_client([{"total_count": 1000, "distinct_count": 1000}])
        checker = UniquenessChecker(client, TABLE_REF)
        result  = checker.check_unique("unique_key", critical=True)

        assert result.passed
        assert result.invalid_count == 0
        assert result.pct_valid     == 100.0

    def test_unique_fails_with_duplicates(self):
        client  = make_client([{"total_count": 1000, "distinct_count": 950}])
        checker = UniquenessChecker(client, TABLE_REF)
        result  = checker.check_unique("unique_key")

        assert not result.passed
        assert result.invalid_count == 50
        assert result.pct_valid     == pytest.approx(95.0, abs=0.01)

    def test_check_name_format(self):
        client  = make_client([{"total_count": 500, "distinct_count": 500}])
        checker = UniquenessChecker(client, TABLE_REF)
        result  = checker.check_unique("case_number")
        assert result.check_name == "uniqueness__case_number__unique"


# ──────────────────────────────────────────────────────────────────────────────
# ValidityChecker
# ──────────────────────────────────────────────────────────────────────────────

class TestValidityChecker:

    def test_range_passes_all_in_range(self):
        client  = make_client([{"invalid_count": 0, "total_count": 2000}])
        checker = ValidityChecker(client, TABLE_REF)
        result  = checker.check_range("year", min_val=2001, max_val=2024)
        assert result.passed

    def test_range_fails_out_of_range(self):
        client  = make_client([{"invalid_count": 15, "total_count": 2000}])
        checker = ValidityChecker(client, TABLE_REF)
        result  = checker.check_range("year", min_val=2001, max_val=2024)
        assert not result.passed
        assert result.invalid_count == 15

    def test_not_future_passes(self):
        client  = make_client([{"invalid_count": 0, "total_count": 5000}])
        checker = ValidityChecker(client, TABLE_REF)
        result  = checker.check_not_future("date", critical=True)
        assert result.passed

    def test_allowed_values_passes(self):
        client  = make_client([{"invalid_count": 0, "total_count": 3000}])
        checker = ValidityChecker(client, TABLE_REF)
        result  = checker.check_allowed_values("district", allowed_values=list(range(1, 32)))
        assert result.passed

    def test_allowed_values_fails(self):
        client  = make_client([{"invalid_count": 8, "total_count": 3000}])
        checker = ValidityChecker(client, TABLE_REF)
        result  = checker.check_allowed_values("district", allowed_values=[1, 2, 3])
        assert not result.passed
        assert result.invalid_count == 8


# ──────────────────────────────────────────────────────────────────────────────
# ConsistencyChecker
# ──────────────────────────────────────────────────────────────────────────────

class TestConsistencyChecker:

    def test_year_matches_date_passes(self):
        client  = make_client([{"invalid_count": 0, "total_count": 5000}])
        checker = ConsistencyChecker(client, TABLE_REF)
        result  = checker.check_year_matches_date(critical=True)
        assert result.passed
        assert result.check_name == "consistency__year_matches_date"

    def test_year_matches_date_fails(self):
        client  = make_client([{"invalid_count": 120, "total_count": 5000}])
        checker = ConsistencyChecker(client, TABLE_REF)
        result  = checker.check_year_matches_date()
        assert not result.passed
        assert result.invalid_count == 120

    def test_bbox_passes(self):
        client  = make_client([{"invalid_count": 0, "total_count": 4000}])
        checker = ConsistencyChecker(client, TABLE_REF)
        result  = checker.check_coordinates_in_bbox()
        assert result.passed

    def test_bbox_fails(self):
        client  = make_client([{"invalid_count": 25, "total_count": 4000}])
        checker = ConsistencyChecker(client, TABLE_REF)
        result  = checker.check_coordinates_in_bbox()
        assert not result.passed
        assert "25" in result.detail
