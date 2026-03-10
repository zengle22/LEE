# GitHub CI/CD for LEE

## Overview

This repository uses `main` as the only release trunk.

- Feature work happens on `feature/*`, `fix/*`, `hotfix/*`, or `refactor/*`.
- Pull requests into `main` run validation and test gates.
- Every push to `main` builds a candidate package and uploads it as a workflow artifact.
- Every tag matching `v*` publishes release assets to a GitHub Release.
- Marathon consumes published LEE versions by downloading the wheel from a GitHub Release URL.

## Workflows

- `.github/workflows/pr-check.yml`
  Validates pull requests targeting `main`.
- `.github/workflows/main-release.yml`
  Builds candidate packages from `main` and uploads them as workflow artifacts.
- `.github/workflows/tag-release.yml`
  Builds release packages from version tags and uploads them to GitHub Releases.

## Branch Protection

Protect `main` with these settings:

- Require a pull request before merging.
- Require at least one approval.
- Require status checks to pass before merging.
- Require branches to be up to date before merging.
- Restrict direct pushes to `main`.
- Prefer squash merge.

## Release Assets

- Public repository:
  Marathon can install directly from the release URL.
- Private repository:
  Marathon should download the wheel with a GitHub token and then install the local file.

Expected wheel asset naming:

```text
lee_framework-<version>-py3-none-any.whl
```

Example public install:

```bash
pip install "https://github.com/shadowyang-42/LEE-ff82194b/releases/download/v0.2.1/lee_framework-0.2.1-py3-none-any.whl"
```

Example download then install:

```bash
python scripts/ci/install_from_github_release.py --repo shadowyang-42/LEE-ff82194b --version 0.2.1
```

For private repositories, use a GitHub token with `curl` or the GitHub CLI to download the asset before calling `pip install`.

## Versioning

- Candidate builds: `<base>.devYYYYMMDD+<short_sha>`
- Release builds: Git tag version, for example `v0.2.1` -> `0.2.1`

The workflows temporarily rewrite `pyproject.toml` in the CI workspace before building. This changes the packaged version without requiring a commit back to the repository.
