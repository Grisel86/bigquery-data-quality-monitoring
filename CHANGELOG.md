# Changelog

All notable changes to this project are documented here.
Format based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).
Versioning follows [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project scaffolding with QE-grade testing infrastructure
- Core check primitives: `check_null_rate`, `check_uniqueness`, `check_value_range`
- BigQuery connector with isolated I/O layer
- Unit test suite with fixtures for clean and bad data
- Contract test suite with versioned bad-data catalog
- Integration test scaffolding for BigQuery sandbox
- CI pipeline: lint, type-check, security scan, unit tests, contract tests
- Nightly E2E workflow
- Pre-commit hooks: Black, Ruff, mypy, Bandit, detect-secrets, conventional-pre-commit
- PR and issue templates
- CODEOWNERS file
- MIT license

## [0.1.0] — TBD

First tagged release coming soon.
