# BigQuery Data Quality Monitoring

[![CI](https://github.com/Grisel86/bigquery-data-quality-monitoring/actions/workflows/ci.yml/badge.svg)](https://github.com/Grisel86/bigquery-data-quality-monitoring/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade data quality monitoring framework for Google BigQuery, built with the rigor of a QA engineer and the practicality of a data engineer.

## Why this project

Bad data is silent. By the time a stakeholder notices, a dashboard has already lied, a model has already trained on garbage, or a customer has already received a wrong invoice. This framework catches it at the source — at the warehouse layer — before it propagates downstream.

Built by a Senior QA Automation Engineer transitioning to Data Engineering, this project deliberately treats data pipelines the way a senior QE treats production software: with a test pyramid, regression catalogs, CI gates, contract tests, and coverage thresholds. **Data quality isn't an afterthought — it's a test suite that runs against your warehouse.**

## Features

- ✅ **Composable check primitives** — null rate, uniqueness, value range, with more to come (referential integrity, schema drift, freshness, volume anomalies)
- ✅ **Pure-function design** — checks are pandas-only and trivially unit-testable; BigQuery I/O is isolated
- ✅ **Regression catalog** — every known-bad data scenario becomes a permanent contract test
- ✅ **Multi-layer CI** — lint, type-check, security scan, unit tests, contract tests, integration tests, nightly E2E
- ✅ **Severity-aware** — checks return structured results with severity levels for alerting integration
- ✅ **Production-ready scaffolding** — pre-commit hooks, conventional commits, branch protection, PR templates

## Architecture

```
src/
├── checks.py      # Pure validation logic — no I/O
├── connector.py   # BigQuery I/O — thin and isolated
└── alerting.py    # (planned) — Slack/email notifications

tests/
├── unit/          # Fast, isolated — mocks BigQuery
├── integration/   # Sandbox-only — real BigQuery
├── contract/      # Regression catalog of known-bad data
└── fixtures/      # Versioned bad-data samples
```

## Quick start

```bash
# 1. Clone & set up env
git clone https://github.com/Grisel86/bigquery-data-quality-monitoring.git
cd bigquery-data-quality-monitoring
python -m venv venv
source venv/Scripts/activate  # Windows Git Bash
# or: source venv/bin/activate  # macOS/Linux

# 2. Install dev dependencies
pip install -r requirements-dev.txt

# 3. Install pre-commit hooks
pre-commit install
pre-commit install --hook-type commit-msg

# 4. Run the test suite
pytest tests/unit               # fast unit tests
pytest tests/contract           # regression catalog
pytest tests/ -m "not integration"  # everything except real BigQuery

# 5. Use the framework
python -c "
import pandas as pd
from src.checks import check_null_rate

df = pd.DataFrame({'email': ['a@x.com', None, 'c@x.com']})
result = check_null_rate(df, 'email', max_null_rate=0.0)
print(result.to_dict())
"
```

## Example usage

```python
from src.connector import BigQueryConnector
from src.checks import check_null_rate, check_uniqueness, check_value_range

connector = BigQueryConnector(project_id="my-gcp-project")
df = connector.fetch_table(
    dataset="analytics",
    table="customers",
    columns=["customer_id", "email", "age"],
)

results = [
    check_uniqueness(df, ["customer_id"]),
    check_null_rate(df, "email", max_null_rate=0.0),
    check_value_range(df, "age", min_value=0, max_value=120),
]

for r in results:
    icon = "✅" if r.passed else "❌"
    print(f"{icon} [{r.severity}] {r.check_name}: {r.message}")
```

## Development workflow

This repo uses a GitFlow-inspired branching model:

| Branch              | Purpose                                          |
| ------------------- | ------------------------------------------------ |
| `main`              | Production-ready; protected; tagged releases     |
| `develop`           | Integration branch; protected; CI must pass      |
| `feature/<desc>`    | New features (branched from `develop`)           |
| `bugfix/<desc>`     | Non-urgent bug fixes                             |
| `hotfix/<desc>`     | Urgent production fixes (branched from `main`)   |
| `refactor/<desc>`   | Internal restructuring, no behavior change       |
| `test/<desc>`       | Test infrastructure changes only                 |
| `qa/<scenario>`     | Exploratory chaos/scenario testing               |

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `test:`, `refactor:`, `docs:`, `chore:`, `ci:`, `perf:`.

## Testing strategy

This project applies the test pyramid to data tooling:

| Layer             | Speed       | What it verifies                                          |
| ----------------- | ----------- | --------------------------------------------------------- |
| **Unit**          | ms          | Check logic with hand-crafted DataFrames; no I/O          |
| **Contract**      | ms          | Regression catalog — every known-bad scenario stays caught|
| **Integration**   | seconds     | Real BigQuery sandbox; one check per fixture table        |
| **E2E**           | minutes     | Full flow: config → connect → check → alert → report      |

**Coverage gate:** 60% minimum, ratcheted upward, never downward.

## Project status

This is an active portfolio project. Roadmap:

- [x] Core check primitives (null, unique, range)
- [x] Test pyramid + CI/CD
- [ ] Schema drift detection
- [ ] Freshness checks (max(updated_at) thresholds)
- [ ] Volume anomaly detection (week-over-week ratios)
- [ ] Slack alerting
- [ ] Streamlit dashboard for check results history
- [ ] dbt integration

## About

Built by **[Fabiana Grisel González](https://www.linkedin.com/in/fabiana-grisel-gonzalez)** — Senior QA Automation Engineer transitioning to Data Engineering. The combination matters: data pipelines that aren't tested are pipelines waiting to fail silently. This project is a working demonstration that QA engineering principles are exactly what modern data platforms need.

## License

MIT
