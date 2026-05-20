"""
src/runner.py
─────────────
Main entrypoint for the BigQuery data quality monitoring pipeline.

Usage:
    python src/runner.py --project YOUR_PROJECT --log-dataset YOUR_DATASET

    # Dry run (no writes to audit log):
    python src/runner.py --project YOUR_PROJECT --dry-run

    # Fail fast on first critical check failure:
    python src/runner.py --project YOUR_PROJECT --fail-fast
"""

import argparse
import sys
from datetime import datetime, timezone

from google.cloud import bigquery

from quality.checks import (
    CompletenessChecker,
    UniquenessChecker,
    ValidityChecker,
    ConsistencyChecker,
)
from quality.reporter import QualityReporter


# ── Source table ──────────────────────────────────────────────────────────────
SOURCE_TABLE = "bigquery-public-data.chicago_crime.crime"

# ── Default audit log ─────────────────────────────────────────────────────────
DEFAULT_LOG_TABLE_TEMPLATE = "{project}.{dataset}.dq_check_log"


def build_checks(client: bigquery.Client, run_id: str) -> list:
    """Define all quality checks for the Chicago Crime dataset."""

    completeness = CompletenessChecker(client, SOURCE_TABLE)
    uniqueness   = UniquenessChecker(client, SOURCE_TABLE)
    validity     = ValidityChecker(client, SOURCE_TABLE)
    consistency  = ConsistencyChecker(client, SOURCE_TABLE)

    return [
        # ── Completeness ───────────────────────────────────────────────────
        completeness.check_not_null("unique_key",    critical=True,  run_id=run_id),
        completeness.check_not_null("date",          critical=True,  run_id=run_id),
        completeness.check_not_empty("primary_type", critical=True,  run_id=run_id),
        completeness.check_not_null("arrest",        critical=False, run_id=run_id),
        completeness.check_not_null("domestic",      critical=False, run_id=run_id),
        completeness.check_completeness_threshold(
            "latitude",  threshold_pct=80.0, critical=False, run_id=run_id
        ),
        completeness.check_completeness_threshold(
            "district",  threshold_pct=90.0, critical=False, run_id=run_id
        ),

        # ── Uniqueness ─────────────────────────────────────────────────────
        uniqueness.check_unique("unique_key",   critical=True,  run_id=run_id),
        uniqueness.check_unique("case_number",  critical=False, run_id=run_id),

        # ── Validity ───────────────────────────────────────────────────────
        validity.check_range(
            "year",
            min_val=2001,
            max_val=datetime.now(timezone.utc).year,
            critical=True,
            run_id=run_id,
        ),
        validity.check_range(
            "district", min_val=1, max_val=31, critical=False, run_id=run_id
        ),
        validity.check_not_future("date", critical=True, run_id=run_id),

        # ── Consistency ────────────────────────────────────────────────────
        consistency.check_year_matches_date(critical=True, run_id=run_id),
        consistency.check_coordinates_in_bbox(critical=False, run_id=run_id),
    ]


def main(args: argparse.Namespace) -> int:
    run_id    = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    client    = bigquery.Client(project=args.project)
    log_table = DEFAULT_LOG_TABLE_TEMPLATE.format(
        project=args.project, dataset=args.log_dataset
    )

    print(f"\n[Runner] Starting quality checks — run {run_id}")
    print(f"[Runner] Source:    {SOURCE_TABLE}")
    print(f"[Runner] Log table: {log_table}\n")

    reporter = QualityReporter(client=client, log_table=log_table, run_id=run_id)
    checks   = build_checks(client, run_id)

    for check in checks:
        status = "✓" if check.passed else "✗"
        print(f"  {status}  {check.check_name}")

        if args.fail_fast and not check.passed and check.critical:
            print(f"\n[Runner] FAIL FAST — critical check failed: {check.check_name}")
            reporter.add(check).print_summary()
            if not args.dry_run:
                reporter.save()
            return 1

        reporter.add(check)

    reporter.print_summary()

    if args.dry_run:
        print("[Runner] Dry run — results NOT written to BigQuery.")
    else:
        reporter.save()

    # Exit code 1 if any critical failures
    return 1 if reporter.critical_failures else 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="BigQuery data quality monitoring — Chicago Crime dataset"
    )
    parser.add_argument(
        "--project",
        required=True,
        help="GCP project ID where the audit log lives",
    )
    parser.add_argument(
        "--log-dataset",
        default="chicago_crime_dq",
        help="BigQuery dataset for the dq_check_log table (default: chicago_crime_dq)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run checks but do not write results to BigQuery",
    )
    parser.add_argument(
        "--fail-fast",
        action="store_true",
        help="Stop on the first critical check failure",
    )

    args = parser.parse_args()
    sys.exit(main(args))
