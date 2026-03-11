# GitHub CI/CD for LEE

## Overview

This repository uses `main` as the only release trunk.

- Feature work happens on `feature/*`, `fix/*`, `hotfix/*`, or `refactor/*`.
- Pull requests into `main` run validation and test gates.
- Every push to `main` builds a release package and uploads it as a workflow artifact.
- Tag-based release is no longer automatic.
- Marathon consumes packages produced from `main`.

## Workflows

- `.github/workflows/pr-check.yml`
  Validates pull requests targeting `main`.
- `.github/workflows/main-release.yml`
  Builds release packages from `main` and uploads them as workflow artifacts.
- `.github/workflows/tag-release.yml`
  Manual-only workflow for exceptional tag-based packaging.

## Branch Protection

Protect `main` with these settings:

- Require a pull request before merging.
- Require at least one approval.
- Require status checks to pass before merging.
- Require branches to be up to date before merging.
- Restrict direct pushes to `main`.
- Prefer squash merge.

## Release Artifacts

`main-release.yml` uploads the package to the workflow run as an artifact named:

```text
lee-dist-<version>
```

Use that artifact, or the local publish script, as the source for Marathon installs.

Expected wheel asset naming:

```text
lee_framework-<version>-py3-none-any.whl
```

## Versioning

- Candidate builds: `<base>.devYYYYMMDD+<short_sha>`
- `main` release packages: `<base>.devYYYYMMDD+<short_sha>`
- Manual tag builds: Git tag version, for example `v0.2.1` -> `0.2.1`

The workflows temporarily rewrite `pyproject.toml` in the CI workspace before building. This changes the packaged version without requiring a commit back to the repository.
