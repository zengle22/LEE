"""
Unit tests for lee.runtime.repo_registry
"""

import os
import tempfile
from unittest.mock import patch

import pytest
import yaml

from lee.runtime.repo_registry import RepoEntry, RepoRegistry, RepoStatus


# ── RepoEntry ─────────────────────────────────────────────────────


class TestRepoEntry:
    def test_from_dict_basic(self):
        data = {
            "path": "./repos/backend",
            "type": "git",
            "default_branch": "main",
            "description": "Backend service",
        }
        entry = RepoEntry.from_dict("backend", data)
        assert entry.repo_id == "backend"
        assert entry.path == "./repos/backend"
        assert entry.type == "git"
        assert entry.default_branch == "main"
        assert entry.description == "Backend service"

    def test_from_dict_full(self):
        data = {
            "path": "/abs/path",
            "type": "git",
            "url": "https://example.com/repo.git",
            "default_branch": "develop",
            "description": "Full entry",
            "path_policy": ["src/**", "tests/**"],
            "owner": "team-a",
            "tags": ["backend", "go"],
        }
        entry = RepoEntry.from_dict("full", data)
        assert entry.url == "https://example.com/repo.git"
        assert entry.path_policy == ["src/**", "tests/**"]
        assert entry.owner == "team-a"
        assert entry.tags == ["backend", "go"]

    def test_from_dict_defaults(self):
        entry = RepoEntry.from_dict("minimal", {"path": ".", "type": "git"})
        assert entry.default_branch == "main"
        assert entry.path_policy == []
        assert entry.tags == []
        assert entry.owner == ""


# ── RepoRegistry Loading ─────────────────────────────────────────


class TestRepoRegistryLoading:
    def test_from_yaml_file(self, tmp_path):
        registry_data = {
            "version": "1.0",
            "repos": {
                "backend": {
                    "path": "./repos/backend",
                    "type": "git",
                    "description": "Backend",
                },
                "frontend": {
                    "path": "./repos/frontend",
                    "type": "git",
                    "description": "Frontend",
                },
            },
        }
        yaml_path = tmp_path / "registry.yaml"
        yaml_path.write_text(yaml.dump(registry_data))

        registry = RepoRegistry.from_yaml(
            str(yaml_path), workspace_root=str(tmp_path)
        )
        assert len(registry) == 2
        assert "backend" in registry
        assert "frontend" in registry

    def test_from_yaml_missing_file(self, tmp_path):
        registry = RepoRegistry.from_yaml(
            str(tmp_path / "nonexistent.yaml"),
            workspace_root=str(tmp_path),
        )
        assert len(registry) == 0

    def test_from_dict(self):
        data = {
            "repos": {
                "api": {"path": "/api", "type": "git"},
            }
        }
        registry = RepoRegistry.from_dict(data)
        assert len(registry) == 1
        assert registry.get_repo("api") is not None


# ── RepoRegistry Query Methods ───────────────────────────────────


class TestRepoRegistryQuery:
    @pytest.fixture
    def registry(self, tmp_path):
        repos = {
            "backend": RepoEntry(
                repo_id="backend",
                path="./repos/backend",
                type="git",
                tags=["backend", "go"],
                path_policy=["cmd/**", "internal/**", "tests/**"],
            ),
            "frontend": RepoEntry(
                repo_id="frontend",
                path="/abs/frontend",
                type="git",
                tags=["frontend"],
                path_policy=["src/**"],
            ),
        }
        return RepoRegistry(repos=repos, workspace_root=str(tmp_path))

    def test_get_repo(self, registry):
        repo = registry.get_repo("backend")
        assert repo is not None
        assert repo.repo_id == "backend"

    def test_get_repo_missing(self, registry):
        assert registry.get_repo("nonexistent") is None

    def test_get_repo_or_raise(self, registry):
        repo = registry.get_repo_or_raise("backend")
        assert repo.repo_id == "backend"

    def test_get_repo_or_raise_missing(self, registry):
        with pytest.raises(ValueError, match="Unknown repo_id"):
            registry.get_repo_or_raise("nonexistent")

    def test_list_repos(self, registry):
        repos = registry.list_repos()
        assert len(repos) == 2

    def test_list_repo_ids(self, registry):
        ids = registry.list_repo_ids()
        assert ids == ["backend", "frontend"]

    def test_contains(self, registry):
        assert "backend" in registry
        assert "missing" not in registry

    def test_len(self, registry):
        assert len(registry) == 2


# ── Path Resolution ───────────────────────────────────────────────


class TestPathResolution:
    def test_resolve_relative_path(self, tmp_path):
        repos = {
            "svc": RepoEntry(
                repo_id="svc", path="./repos/svc", type="git",
            ),
        }
        registry = RepoRegistry(repos=repos, workspace_root=str(tmp_path))
        resolved = registry.resolve_path("svc")
        expected = str((tmp_path / "repos" / "svc").resolve())
        assert resolved == expected

    def test_resolve_absolute_path(self, tmp_path):
        repos = {
            "abs": RepoEntry(
                repo_id="abs", path="/absolute/path", type="git",
            ),
        }
        registry = RepoRegistry(repos=repos, workspace_root=str(tmp_path))
        resolved = registry.resolve_path("abs")
        assert resolved == "/absolute/path"


# ── Path Policy ───────────────────────────────────────────────────


class TestPathPolicy:
    @pytest.fixture
    def registry(self):
        repos = {
            "svc": RepoEntry(
                repo_id="svc",
                path="/svc",
                type="git",
                path_policy=["src/**", "tests/**", "config/*"],
            ),
            "open": RepoEntry(
                repo_id="open",
                path="/open",
                type="git",
                path_policy=[],  # no restrictions
            ),
        }
        return RepoRegistry(repos=repos)

    def test_allowed_path(self, registry):
        assert registry.check_path_allowed("svc", "src/main.go") is True
        assert registry.check_path_allowed("svc", "tests/unit/foo_test.go") is True
        assert registry.check_path_allowed("svc", "config/app.yaml") is True

    def test_disallowed_path(self, registry):
        assert registry.check_path_allowed("svc", "vendor/lib.go") is False
        assert registry.check_path_allowed("svc", "Makefile") is False
        assert registry.check_path_allowed("svc", "go.mod") is False

    def test_empty_policy_allows_all(self, registry):
        assert registry.check_path_allowed("open", "anything/goes.txt") is True

    def test_extra_allowlist_overrides(self, registry):
        # extra_allowlist 覆盖 repo 级 policy
        assert registry.check_path_allowed(
            "svc", "vendor/lib.go", extra_allowlist=["vendor/**"]
        ) is True
        # extra_allowlist 限制
        assert registry.check_path_allowed(
            "svc", "src/main.go", extra_allowlist=["tests/**"]
        ) is False

    def test_path_normalization(self, registry):
        # leading slash stripped
        assert registry.check_path_allowed("svc", "/src/main.go") is True
        # backslash normalized
        assert registry.check_path_allowed("svc", "src\\main.go") is True
