# GitHub CI/CD for LEE

## Overview

This repository uses `main` as the only release trunk.

- Feature work happens on `feature/*`, `fix/*`, `hotfix/*`, or `refactor/*`.
- Pull requests into `main` run validation and test gates.
- Every push to `main` publishes a candidate package and notifies Marathon staging.
- Every tag matching `v*` publishes a release package and notifies Marathon production.

## Workflows

- `.github/workflows/pr-check.yml`
  Validates pull requests targeting `main`.
- `.github/workflows/main-release.yml`
  Builds and publishes candidate packages from `main`.
- `.github/workflows/tag-release.yml`
  Builds and publishes release packages from version tags.

## Required Secrets

- `PACKAGE_REPOSITORY_URL`
- `PACKAGE_REPOSITORY_USERNAME`
- `PACKAGE_REPOSITORY_TOKEN`
- `MARATHON_REPO`
- `MARATHON_DISPATCH_TOKEN`

`MARATHON_REPO` must be set to `owner/repo`.

## Branch Protection

Protect `main` with these settings:

- Require a pull request before merging.
- Require at least one approval.
- Require status checks to pass before merging.
- Require branches to be up to date before merging.
- Restrict direct pushes to `main`.
- Prefer squash merge.

## Marathon Dispatch Contract

The release workflows send a `repository_dispatch` event with `event_type=lee_release_ready`.

Payload:

```json
{
  "event_type": "lee_release_ready",
  "client_payload": {
    "lee_version": "0.2.1",
    "environment": "prod",
    "release_kind": "release",
    "source_sha": "abc1234def5678",
    "source_repo": "your-org/LEE",
    "triggered_by": "github-actions"
  }
}
```

## Versioning

- Candidate builds: `<base>.devYYYYMMDD+<short_sha>`
- Release builds: Git tag version, for example `v0.2.1` -> `0.2.1`

The workflows temporarily rewrite `pyproject.toml` in the CI workspace before building. This changes the packaged version without requiring a commit back to the repository.
