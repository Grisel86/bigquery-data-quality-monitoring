"""Data quality check primitives.

Each check is a pure function that takes a pandas DataFrame and returns
a CheckResult. This makes them trivial to unit-test without touching BigQuery.

Design principle: BigQuery I/O lives in `connector.py`; pure logic lives here.
This separation is what makes the test pyramid work.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class CheckResult:
    """Outcome of a single data quality check."""

    check_name: str
    passed: bool
    severity: str  # "info" | "warning" | "critical"
    message: str
    metrics: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_dict(self) -> dict[str, Any]:
        """Serialize for logging or alerting."""
        return {
            "check_name": self.check_name,
            "passed": self.passed,
            "severity": self.severity,
            "message": self.message,
            "metrics": self.metrics,
            "timestamp": self.timestamp.isoformat(),
        }


def check_null_rate(
    df: pd.DataFrame,
    column: str,
    max_null_rate: float = 0.0,
    severity: str = "critical",
) -> CheckResult:
    """Verify that a column's null rate stays below a threshold.

    Args:
        df: Data to inspect.
        column: Column name to check.
        max_null_rate: Allowed proportion of nulls in [0.0, 1.0].
        severity: Severity label if the check fails.

    Returns:
        CheckResult with the observed null rate in `metrics`.

    Raises:
        KeyError: If `column` is not in the DataFrame.
        ValueError: If `max_null_rate` is outside [0, 1].
    """
    if not 0.0 <= max_null_rate <= 1.0:
        raise ValueError(
            f"max_null_rate must be between 0 and 1, got {max_null_rate}"
        )
    if column not in df.columns:
        raise KeyError(f"Column '{column}' not found in DataFrame")

    total = len(df)
    if total == 0:
        return CheckResult(
            check_name=f"null_rate[{column}]",
            passed=True,
            severity="info",
            message="Empty DataFrame — null check vacuously passes",
            metrics={"total_rows": 0, "null_count": 0, "null_rate": 0.0},
        )

    null_count = int(df[column].isna().sum())
    null_rate = null_count / total
    passed = null_rate <= max_null_rate

    return CheckResult(
        check_name=f"null_rate[{column}]",
        passed=passed,
        severity="info" if passed else severity,
        message=(
            f"{null_count}/{total} nulls ({null_rate:.2%}); "
            f"threshold {max_null_rate:.2%}"
        ),
        metrics={
            "total_rows": total,
            "null_count": null_count,
            "null_rate": null_rate,
            "threshold": max_null_rate,
        },
    )


def check_uniqueness(
    df: pd.DataFrame,
    columns: list[str],
    severity: str = "critical",
) -> CheckResult:
    """Verify the combination of `columns` is unique across all rows.

    Useful for primary keys and natural keys.
    """
    missing = [c for c in columns if c not in df.columns]
    if missing:
        raise KeyError(f"Columns not found: {missing}")

    total = len(df)
    duplicates = int(df.duplicated(subset=columns).sum())
    passed = duplicates == 0

    return CheckResult(
        check_name=f"uniqueness[{','.join(columns)}]",
        passed=passed,
        severity="info" if passed else severity,
        message=(
            "No duplicates"
            if passed
            else f"{duplicates} duplicate rows on {columns}"
        ),
        metrics={
            "total_rows": total,
            "duplicate_count": duplicates,
            "unique_count": total - duplicates,
        },
    )


def check_value_range(
    df: pd.DataFrame,
    column: str,
    min_value: float | None = None,
    max_value: float | None = None,
    severity: str = "warning",
) -> CheckResult:
    """Verify numeric values fall within [min_value, max_value]."""
    if column not in df.columns:
        raise KeyError(f"Column '{column}' not found in DataFrame")
    if min_value is None and max_value is None:
        raise ValueError("At least one of min_value or max_value is required")

    series = df[column].dropna()
    if series.empty:
        return CheckResult(
            check_name=f"value_range[{column}]",
            passed=True,
            severity="info",
            message="No non-null values to validate",
            metrics={"checked_rows": 0},
        )

    below = int((series < min_value).sum()) if min_value is not None else 0
    above = int((series > max_value).sum()) if max_value is not None else 0
    out_of_range = below + above
    passed = out_of_range == 0

    return CheckResult(
        check_name=f"value_range[{column}]",
        passed=passed,
        severity="info" if passed else severity,
        message=(
            "All values in range"
            if passed
            else f"{out_of_range} out-of-range ({below} below, {above} above)"
        ),
        metrics={
            "checked_rows": len(series),
            "below_min": below,
            "above_max": above,
            "min_value": min_value,
            "max_value": max_value,
            "observed_min": float(series.min()),
            "observed_max": float(series.max()),
        },
    )
