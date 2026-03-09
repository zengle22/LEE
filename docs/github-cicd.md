# GitHub CI/CD for LEE

## Overview

This repository uses `main` as the only release trunk.

- Feature work happens on `feature/*`, `fix/*`, `hotfix/*`, or `refactor/*`.
- Pull requests into `main` run validation and test gates.
- Every push to `main` builds a candidate package and uploads it as a workflow artifact.
- Every tag matching `v*` publishes a release package to a Python package registry and creates a GitHub Release.
- Marathon consumes published LEE versions separately by updating its dependency version.

## Workflows

- `.github/workflows/pr-check.yml`
  Validates pull requests targeting `main`.
- `.github/workflows/main-release.yml`
  Builds candidate packages from `main` and uploads them as workflow artifacts.
- `.github/workflows/tag-release.yml`
  Builds and publishes release packages from version tags.

## Required Secrets

- `PYPI_API_TOKEN`
- `PACKAGE_REPOSITORY_URL` (optional; omit for PyPI, set to `https://test.pypi.org/legacy/` for TestPyPI, or point to your private Python index)

If you publish to PyPI, you can leave `PACKAGE_REPOSITORY_URL` unset and the publish action will use PyPI defaults.

## Branch Protection

Protect `main` with these settings:

- Require a pull request before merging.
- Require at least one approval.
- Require status checks to pass before merging.
- Require branches to be up to date before merging.
- Restrict direct pushes to `main`.
- Prefer squash merge.

## Registry Choice

Use a standard Python package registry.

- PyPI for public releases
- TestPyPI for dry runs
- A private Python index such as Artifactory, Nexus, Cloudsmith, Azure Artifacts, or a self-hosted devpi server for internal use

GitHub Packages does not provide a Python package registry. This workflow is therefore designed around standard Python indexes instead.

Marathon should update `lee-framework==<version>` in its own repository and then run its own test and deployment flow.

## Versioning

- Candidate builds: `<base>.devYYYYMMDD+<short_sha>`
- Release builds: Git tag version, for example `v0.2.1` -> `0.2.1`

The workflows temporarily rewrite `pyproject.toml` in the CI workspace before building. This changes the packaged version without requiring a commit back to the repository.
