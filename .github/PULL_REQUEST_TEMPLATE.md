# Pull Request

## Summary
<!-- One-paragraph description of what this PR changes and why. -->

## Type of change
<!-- Check all that apply -->
- [ ] 🚀 `feat`: New feature
- [ ] 🐛 `fix`: Bug fix
- [ ] ♻️ `refactor`: Code refactor (no behavior change)
- [ ] ✅ `test`: Test addition or update
- [ ] 📝 `docs`: Documentation only
- [ ] 🔧 `chore`: Tooling, CI, dependencies
- [ ] ⚠️ Breaking change

## Linked issues
<!-- e.g. Closes #42, Relates to #17 -->

## How was this tested?
<!-- Be specific. "Added tests" alone is not enough. -->
- [ ] Unit tests added/updated
- [ ] Integration tests added/updated
- [ ] Contract tests / fixtures added for the bug scenario
- [ ] Tested locally against BigQuery sandbox
- [ ] Manual verification steps:
  1.
  2.

## Test results
<!-- Paste relevant test output, coverage delta, or screenshots. -->
```
$ pytest tests/unit
```

## Rollback plan
<!-- How do we revert if this breaks production? Is the change additive, or does it require a migration? -->

## Risk assessment
- **Blast radius**: <!-- Which datasets, tables, or downstream systems are affected? -->
- **Reversibility**: <!-- Easy revert / requires data backfill / irreversible -->
- **Monitoring**: <!-- What metric/alert tells us this is working in production? -->

## Checklist
- [ ] I have run `pre-commit run --all-files` locally
- [ ] My code follows the project style (Black, Ruff)
- [ ] I have added type hints to new functions
- [ ] I have updated documentation where needed
- [ ] I have updated the CHANGELOG (if applicable)
- [ ] No secrets, credentials, or production data are included in this PR
- [ ] CI passes
