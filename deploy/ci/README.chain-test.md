# Requirement Chain CI

- GitHub Actions: `.github/workflows/requirement-chain-test.yml`
- GitLab CI: `deploy/ci/gitlab.requirement-chain-test.yml`
- Docker: `deploy/ci/Dockerfile.chain-test`

These templates run `lee ssot chain-test` and publish `report.json` plus `scorecard.md`.
