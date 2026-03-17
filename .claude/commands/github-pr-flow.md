---
name: github-pr-flow
description: Push the current branch, create or reuse a GitHub PR to dev/main, and watch GitHub Actions checks until they finish.
author: LEE Team
date: 2026-03-17
version: 1.0
---

# GitHub PR Flow

Push current branch to GitHub, create or reuse a pull request, and monitor GitHub Actions checks.

## Workflow

1. **Verify prerequisites:**
   - Check `gh` CLI is available
   - Verify GitHub token is set (`GH_TOKEN` or `GITHUB_TOKEN`)
   - Confirm current branch exists and has a remote `origin`

2. **Push current branch:**
   ```bash
   git push -u origin <current-branch>
   ```

3. **Determine target branch:**
   - Check if `dev` branch exists remotely → use as PR target
   - Otherwise, fall back to `main` or `master`

4. **Create or reuse PR:**
   - Check if a PR already exists for this branch
   - If yes: reuse existing PR, report URL
   - If no: create new PR with branch name as title
   ```bash
   gh pr create --base <target-branch> --title "<branch-name>" --body "Auto-generated PR"
   ```

5. **Watch GitHub Actions checks:**
   - List checks for the PR
   - Poll until all checks complete (success/failure/skipped)
   - Report final status

6. **Report results:**
   - PR URL
   - All check names and their final statuses
   - Overall CI result (all passed / some failed)

## Commands Reference

```bash
# Check gh CLI availability
gh --version

# Verify authentication
gh auth status

# Get current branch
git branch --show-current

# Push branch
git push -u origin HEAD

# Check for existing PR
gh pr view --json url,title,status

# Create PR
gh pr create --base <target> --title "<title>" --body "<body>"

# List checks
gh pr checks <pr-number>

# Watch checks (polling)
gh pr checks <pr-number> --watch
```

## Environment Setup

Add GitHub token to `.claude/settings.json`:

```json
{
  "env": {
    "GH_TOKEN": "ghp_your_personal_access_token"
  }
}
```

## Token Requirements

The GitHub token should have these scopes:
- `repo` - Full control of private repositories
- `read:org` - Read org membership (for org projects)
- `workflow` - Update GitHub Action workflows

## Rules

- Always push to `origin` remote
- Prefer `dev` as PR target, fall back to `main`/`master`
- Do not force push unless explicitly requested
- Report check failures clearly with links to logs
- Wait for user confirmation before destructive operations
