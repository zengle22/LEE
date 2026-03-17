---
description: Push the current branch, create or reuse a GitHub PR to dev/main, and watch GitHub Actions checks until they finish.
---

# GitHub PR Flow

Push the current branch to GitHub, create or reuse a pull request targeting `dev` or `main` branch, and monitor GitHub Actions checks until completion.

## Prerequisites

- GitHub token must be set in environment: `GH_TOKEN` or `GITHUB_TOKEN`
- Git remote `origin` must be configured and point to a GitHub repository
- Current branch must have unpushed commits or be tracking a remote branch

## Usage

```bash
# The skill will:
# 1. Push current branch to origin
# 2. Create PR if one doesn't exist, or reuse existing PR
# 3. Target dev branch first, fall back to main if dev doesn't exist
# 4. Watch GitHub Actions checks until they complete
```

## Environment Variables

Set one of the following in your environment or `.claude/settings.json`:

- `GH_TOKEN` - GitHub personal access token (recommended)
- `GITHUB_TOKEN` - Alternative GitHub token variable

Example `.claude/settings.json`:

```json
{
  "env": {
    "GH_TOKEN": "ghp_your_token_here"
  }
}
```

## What To Report

- Branch pushed status
- PR URL (created or reused)
- PR title and description
- GitHub Actions check statuses
- Final CI/CD result summary
