# bigquery-data-quality-monitoring

> Data quality monitoring suite built on **BigQuery** and **GCP Free Tier**, using **dbt Core** and **Python** to validate the Chicago Crime public dataset — with automated checks for completeness, uniqueness, validity, and consistency, persisted to a Delta audit log and tested via GitHub Actions CI/CD.

[![CI](https://github.com/Grisel86/bigquery-data-quality-monitoring/actions/workflows/ci.yml/badge.svg)](https://github.com/Grisel86/bigquery-data-quality-monitoring/actions)
![Python](https://img.shields.io/badge/python-3.11-blue)
![BigQuery](https://img.shields.io/badge/BigQuery-GCP-4285F4?logo=google-cloud)
![dbt](https://img.shields.io/badge/dbt--core-1.7-FF694B)
![Cost](https://img.shields.io/badge/GCP%20cost-free%20tier-brightgreen)

---

## Overview

This project applies a structured data quality engineering approach to the **Chicago Crime public dataset** available natively in BigQuery. It combines:

- **Raw SQL validation scripts** — portable, readable, runnable directly in the BQ console
- **Python quality framework** — reusable checker classes that mock-able and unit-tested
- **dbt Core models** — staging → intermediate → mart transformation pipeline with schema tests
- **BigQuery audit log** — every check result is persisted for trend analysis
- **GitHub Actions CI/CD** — unit tests run on every push; full pipeline runs on main

---

## Architecture

```
bigquery-public-data.chicago_crime.crime  (source — free, no ingestion cost)
        │
        ▼
┌──────────────────────────────────────────────────────────┐
│  SQL Validation Scripts  (sql/validation/)               │
│  01_completeness  02_uniqueness  03_validity  04_consistency │
│  Run directly in BigQuery console or via Python runner   │
└──────────────────────┬───────────────────────────────────┘
                       │
        ┌──────────────▼──────────────┐
        │   Python Quality Runner     │
        │   src/runner.py             │
        │   CompletenessChecker       │
        │   UniquenessChecker         │
        │   ValidityChecker           │
        │   ConsistencyChecker        │
        └──────────────┬──────────────┘
                       │ writes results
                       ▼
        ┌──────────────────────────────┐
        │  BigQuery Audit Log          │
        │  YOUR_PROJECT.dq.dq_check_log│
        │  Partitioned by run_date     │
        └──────────────────────────────┘
                       
        ┌──────────────────────────────┐
        │  dbt Core Pipeline           │
        │  staging/stg_chicago_crime   │
        │  intermediate/int_enriched   │
        │  marts/mart_daily_summary    │
        │        mart_district_analysis│
        │  + 8 dbt tests (generic +    │
        │    3 singular assertions)    │
        └──────────────────────────────┘
```

---

## Quality Checks

### Python Runner (14 checks)

| Category | Check | Critical |
|----------|-------|----------|
| Completeness | `unique_key`, `date`, `primary_type` not null | ✅ |
| Completeness | `arrest`, `domestic` not null | No |
| Completeness | `latitude` ≥ 80% populated | No |
| Completeness | `district` ≥ 90% populated | No |
| Uniqueness | `unique_key` is unique | ✅ |
| Uniqueness | `case_number` is unique | No |
| Validity | `year` in [2001, current year] | ✅ |
| Validity | `district` in [1, 31] | No |
| Validity | `date` not in the future | ✅ |
| Consistency | `year` = EXTRACT(YEAR FROM `date`) | ✅ |
| Consistency | coordinates within Chicago bounding box | No |

### dbt Tests (schema.yml + singular)

| Test | Type |
|------|------|
| `unique_key` — unique + not_null | Generic |
| `case_number` — unique + not_null | Generic |
| `incident_year` in [2001, 2024] | `dbt_utils.accepted_range` |
| `district` in [1, 31] | `dbt_utils.accepted_range` |
| `year_matches_date` = true | `accepted_values` |
| No future incidents | Singular SQL assertion |
| `year` matches `date` | Singular SQL assertion |
| `updated_on` ≥ `incident_datetime` | Singular SQL assertion |

---

## Project Structure

```
bigquery-data-quality-monitoring/
├── sql/
│   ├── validation/
│   │   ├── 01_completeness_checks.sql
│   │   ├── 02_uniqueness_checks.sql
│   │   ├── 03_validity_checks.sql
│   │   └── 04_consistency_checks.sql
│   └── setup/
│       └── create_quality_log_table.sql
├── dbt/
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── models/
│   │   ├── staging/   stg_chicago_crime.sql + schema.yml
│   │   ├── intermediate/  int_crime_enriched.sql
│   │   └── marts/     mart_daily_crime_summary.sql
│   │                  mart_district_analysis.sql
│   ├── tests/singular/   3 SQL assertions
│   └── macros/        quality_macros.sql (2 generic tests)
├── src/
│   ├── quality/
│   │   ├── checks.py   (4 checker classes, 11 check methods)
│   │   └── reporter.py (BigQuery audit log writer)
│   └── runner.py       (CLI entrypoint)
├── tests/
│   ├── test_checks.py    (25 unit tests — all mocked, no GCP needed)
│   └── test_reporter.py  (6 unit tests)
├── config/quality_config.yaml
├── .github/workflows/ci.yml
└── requirements.txt
```

---

## Getting Started

### Prerequisites
- Python 3.11+
- [Google Cloud SDK](https://cloud.google.com/sdk/docs/install) (`gcloud`)
- GCP Free Tier account (free $300 credit, BigQuery 1TB/month permanently free)

### 1. Clone and install

```bash
git clone https://github.com/Grisel86/bigquery-data-quality-monitoring.git
cd bigquery-data-quality-monitoring
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run unit tests locally (no GCP credentials needed)

```bash
pytest tests/ -v
# 31 tests, all pass with mocked BigQuery client
```

### 3. Set up GCP Free Tier

```bash
# Authenticate
gcloud auth application-default login

# Create the audit log table (replace with your project/dataset)
bq query --use_legacy_sql=false < sql/setup/create_quality_log_table.sql
```

### 4. Run SQL checks directly in BigQuery Console

Open any file in `sql/validation/` and run it in the [BigQuery Console](https://console.cloud.google.com/bigquery). The Chicago Crime dataset is already public — no setup needed.

### 5. Run the Python quality pipeline

```bash
python src/runner.py \
    --project YOUR_GCP_PROJECT \
    --log-dataset chicago_crime_dq \
    --dry-run          # omit --dry-run to write results to BigQuery
```

### 6. Run dbt

```bash
cd dbt

# Edit profiles.yml: replace YOUR_GCP_PROJECT
dbt deps
dbt run   # builds staging → intermediate → mart models
dbt test  # runs all schema + singular tests
```

---

## CI/CD

| Job | Trigger | GCP needed? |
|-----|---------|-------------|
| Unit tests (pytest) | Every push / PR | No |
| dbt compile | Every push / PR | No |
| Full quality pipeline | Push to main only | Yes (secrets) |

Add these secrets to your GitHub repo (`Settings → Secrets`):
- `GCP_PROJECT` — your GCP project ID
- `GCP_SERVICE_ACCOUNT_JSON` — service account JSON with BigQuery roles

---

## Dataset

**Chicago Crime Dataset** — `bigquery-public-data.chicago_crime.crime`
- Source: Chicago Police Department CLEAR system
- ~8M rows, 22 columns, updated daily
- Available natively in BigQuery — no ingestion required

---

## Tech Stack

| Tool | Purpose |
|------|---------|
| Google BigQuery | Serverless SQL query engine + data warehouse |
| GCP Free Tier | $300 credit + 1TB/month free BigQuery queries |
| dbt Core (free) | SQL transformations + schema testing |
| Python + google-cloud-bigquery | Programmatic quality checks |
| pytest + unittest.mock | Unit testing without GCP credentials |
| GitHub Actions | CI/CD — tests on every push |

---

## Author

**Fabiana Grisel González**  
QA Automation Engineer → Data Engineering  
[GitHub: @Grisel86](https://github.com/Grisel86) · [LinkedIn](https://www.linkedin.com/in/fabiana-grisel-gonzalez)
