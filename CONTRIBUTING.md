# Contributing

Thank you for considering a contribution! This document covers how to set up the project, our development standards, and how to submit changes.

## Local setup

```bash
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
pip install -r requirements-dev.txt
pre-commit install
pre-commit install --hook-type commit-msg
```

Verify everything works:

```bash
pre-commit run --all-files
pytest tests/unit
```

## Branching

1. Create your branch from `develop`, not `main`.
2. Use a descriptive prefix:
   - `feature/` — new functionality
   - `bugfix/` — non-urgent fix
   - `hotfix/` — urgent production fix (branched from `main`)
   - `refactor/` — internal cleanup
   - `test/` — test infrastructure
   - `docs/` — documentation only
3. Keep branches short-lived. Rebase or merge from `develop` frequently.

## Commits

We use [Conventional Commits](https://www.conventionalcommits.org/). Format:

```
<type>(<optional scope>): <short description>

<optional body>

<optional footer>
```

Valid types: `feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `ci`, `perf`, `build`, `revert`.

Examples:
- `feat(checks): add referential integrity check`
- `fix(connector): handle empty result sets`
- `test: add fixture for null-heavy customer data`

## Pull requests

1. Open the PR against `develop` (or `main` for hotfixes only).
2. Fill out the PR template completely. The "How was this tested?" section is non-negotiable.
3. All CI jobs must pass.
4. At least one review approval is required.
5. Squash-merge by default; preserve commits only when history is meaningful.

## Adding a new data quality check

1. Add the pure-function implementation in `src/checks.py`.
2. Add unit tests in `tests/unit/test_checks.py` covering:
   - Happy path
   - Each failure mode
   - Edge cases (empty input, all nulls)
   - Invalid input (wrong type, out-of-range params)
3. If the check addresses a real bug, add a row to `tests/fixtures/bad_data_catalog.csv` and a parametrized entry to `EXPECTED_FAILURES` in `tests/contract/test_bad_data_regression.py`.
4. Update `README.md` examples if user-facing.

## Reporting bugs

Use the bug report issue template. Critical: if you can include a minimal reproducing dataset, paste it into the issue — we'll add it to the regression catalog.
