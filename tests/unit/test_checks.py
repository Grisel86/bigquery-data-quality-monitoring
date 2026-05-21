"""Unit tests for src/checks.py.

Notice the patterns used here:
  - Each test exercises ONE behavior — no compound assertions.
  - We test happy path, failure path, edge cases, and invalid input separately.
  - Parametrization is used to cover variants without copy-paste.
  - We assert on metrics, not just `passed`, because metrics are part of the contract.
"""

from __future__ import annotations

import pandas as pd
import pytest

from src.checks import (
    CheckResult,
    check_null_rate,
    check_uniqueness,
    check_value_range,
)


class TestCheckResultSerialization:
    """The CheckResult.to_dict() contract — used by alerting and logging."""

    def test_to_dict_includes_all_fields(self):
        result = CheckResult(
            check_name="x",
            passed=True,
            severity="info",
            message="ok",
            metrics={"k": 1},
        )
        d = result.to_dict()
        assert set(d.keys()) == {
            "check_name",
            "passed",
            "severity",
            "message",
            "metrics",
            "timestamp",
        }

    def test_timestamp_is_iso_format(self):
        result = CheckResult(
            check_name="x", passed=True, severity="info", message="ok"
        )
        # Just verify it parses — exact value is fixture-dependent.
        from datetime import datetime

        datetime.fromisoformat(result.to_dict()["timestamp"])


class TestCheckNullRate:
    """check_null_rate covers null-tolerance validation."""

    def test_passes_when_no_nulls_present(self, clean_customers_df):
        result = check_null_rate(clean_customers_df, "email", max_null_rate=0.0)
        assert result.passed is True
        assert result.metrics["null_count"] == 0
        assert result.metrics["null_rate"] == 0.0

    def test_fails_when_nulls_exceed_threshold(self, df_with_nulls):
        result = check_null_rate(df_with_nulls, "email", max_null_rate=0.0)
        assert result.passed is False
        assert result.metrics["null_count"] == 2
        assert result.metrics["null_rate"] == 0.5

    def test_passes_when_nulls_within_threshold(self, df_with_nulls):
        # 50% nulls, threshold 50% — should pass
        result = check_null_rate(df_with_nulls, "email", max_null_rate=0.5)
        assert result.passed is True

    def test_severity_is_info_when_passing(self, clean_customers_df):
        result = check_null_rate(
            clean_customers_df, "email", severity="critical"
        )
        assert result.severity == "info"

    def test_severity_propagates_when_failing(self, df_with_nulls):
        result = check_null_rate(df_with_nulls, "email", severity="warning")
        assert result.severity == "warning"

    def test_empty_dataframe_passes_vacuously(self, empty_df):
        result = check_null_rate(empty_df, "email", max_null_rate=0.0)
        assert result.passed is True
        assert result.metrics["total_rows"] == 0

    def test_raises_on_missing_column(self, clean_customers_df):
        with pytest.raises(KeyError, match="not found"):
            check_null_rate(clean_customers_df, "nonexistent_column")

    @pytest.mark.parametrize("invalid_rate", [-0.1, 1.1, 2.0, -1.0])
    def test_raises_on_invalid_threshold(self, clean_customers_df, invalid_rate):
        with pytest.raises(ValueError, match="between 0 and 1"):
            check_null_rate(
                clean_customers_df, "email", max_null_rate=invalid_rate
            )


class TestCheckUniqueness:
    """check_uniqueness enforces single-column or composite key uniqueness."""

    def test_passes_when_all_unique(self, clean_customers_df):
        result = check_uniqueness(clean_customers_df, ["customer_id"])
        assert result.passed is True
        assert result.metrics["duplicate_count"] == 0

    def test_fails_when_duplicates_present(self, df_with_duplicates):
        result = check_uniqueness(df_with_duplicates, ["customer_id"])
        assert result.passed is False
        assert result.metrics["duplicate_count"] == 3

    def test_composite_key_uniqueness(self, df_with_duplicates):
        # customer_id AND email together — still has duplicates
        result = check_uniqueness(df_with_duplicates, ["customer_id", "email"])
        assert result.passed is False

    def test_raises_on_missing_column(self, clean_customers_df):
        with pytest.raises(KeyError, match="not found"):
            check_uniqueness(clean_customers_df, ["nonexistent"])


class TestCheckValueRange:
    """check_value_range enforces numeric bounds."""

    def test_passes_when_all_in_range(self, clean_customers_df):
        result = check_value_range(
            clean_customers_df, "age", min_value=0, max_value=120
        )
        assert result.passed is True

    def test_fails_with_values_below_minimum(self, df_with_out_of_range):
        result = check_value_range(df_with_out_of_range, "age", min_value=0)
        assert result.passed is False
        assert result.metrics["below_min"] == 1

    def test_fails_with_values_above_maximum(self, df_with_out_of_range):
        result = check_value_range(df_with_out_of_range, "age", max_value=120)
        assert result.passed is False
        assert result.metrics["above_max"] == 2

    def test_min_only_allows_unbounded_max(self):
        df = pd.DataFrame({"x": [1, 2, 999]})
        result = check_value_range(df, "x", min_value=0)
        assert result.passed is True

    def test_requires_at_least_one_bound(self, clean_customers_df):
        with pytest.raises(ValueError, match="At least one"):
            check_value_range(clean_customers_df, "age")

    def test_handles_all_null_column(self):
        df = pd.DataFrame({"x": [None, None, None]})
        result = check_value_range(df, "x", min_value=0, max_value=100)
        assert result.passed is True
        assert result.metrics["checked_rows"] == 0
