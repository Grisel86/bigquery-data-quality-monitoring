"""
tests/test_reporter.py
───────────────────────
Unit tests for QualityReporter — mocks BigQuery insert calls.
"""

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from quality.checks import QualityCheckResult
from quality.reporter import QualityReporter


def make_result(name: str, passed: bool, critical: bool = False) -> QualityCheckResult:
    return QualityCheckResult(
        check_name     = name,
        check_category = "completeness",
        passed         = passed,
        detail         = "test detail",
        critical       = critical,
        invalid_count  = 0 if passed else 10,
        total_count    = 1000,
        pct_valid      = 100.0 if passed else 99.0,
    )


class TestQualityReporter:

    def test_passed_count(self):
        client   = MagicMock()
        reporter = QualityReporter(client, "p.d.t", run_id="TEST001")
        reporter.add_all([
            make_result("check_a", passed=True),
            make_result("check_b", passed=True),
            make_result("check_c", passed=False),
        ])
        assert reporter.passed == 2
        assert reporter.failed == 1

    def test_critical_failures_filter(self):
        client   = MagicMock()
        reporter = QualityReporter(client, "p.d.t", run_id="TEST001")
        reporter.add_all([
            make_result("critical_fail", passed=False, critical=True),
            make_result("non_critical_fail", passed=False, critical=False),
            make_result("passing_check", passed=True),
        ])
        assert len(reporter.critical_failures) == 1
        assert reporter.critical_failures[0].check_name == "critical_fail"

    def test_save_calls_insert(self):
        client = MagicMock()
        client.insert_rows_json.return_value = []   # no errors

        reporter = QualityReporter(client, "p.d.log_table", run_id="TEST001")
        reporter.add(make_result("check_x", passed=True))
        summary = reporter.save()

        client.insert_rows_json.assert_called_once()
        assert summary["total_checks"] == 1
        assert summary["passed"]       == 1

    def test_save_returns_correct_summary(self):
        client = MagicMock()
        client.insert_rows_json.return_value = []

        reporter = QualityReporter(client, "p.d.log_table", run_id="TEST_SUMMARY")
        reporter.add_all([
            make_result("a", passed=True),
            make_result("b", passed=False, critical=True),
        ])
        summary = reporter.save()

        assert summary["total_checks"]      == 2
        assert summary["passed"]            == 1
        assert summary["failed"]            == 1
        assert summary["critical_failures"] == 1
        assert summary["run_id"]            == "TEST_SUMMARY"

    def test_run_id_injected_into_results(self):
        client   = MagicMock()
        client.insert_rows_json.return_value = []
        reporter = QualityReporter(client, "p.d.t", run_id="INJECTED_ID")
        result   = make_result("my_check", passed=True)
        reporter.add(result)

        assert result.run_id == "INJECTED_ID"

    def test_all_passed_no_critical_failures(self):
        client   = MagicMock()
        reporter = QualityReporter(client, "p.d.t")
        reporter.add_all([
            make_result("check_1", passed=True),
            make_result("check_2", passed=True),
        ])
        assert len(reporter.critical_failures) == 0
