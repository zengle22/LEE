from __future__ import annotations

import importlib.util
from pathlib import Path


def load_pr_flow_module():
    module_path = Path(__file__).resolve().parents[3] / "scripts" / "pr_flow.py"
    spec = importlib.util.spec_from_file_location("pr_flow", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_parse_github_repo_supports_ssh_remote() -> None:
    module = load_pr_flow_module()

    assert module.parse_github_repo("git@github.com:zengle22/LEE.git") == ("zengle22", "LEE")


def test_parse_github_repo_supports_https_remote() -> None:
    module = load_pr_flow_module()

    assert module.parse_github_repo("https://github.com/zengle22/LEE.git") == ("zengle22", "LEE")


def test_summarize_checks_splits_pending_failed_and_passed() -> None:
    module = load_pr_flow_module()

    pending, failed, passed = module.summarize_checks(
        [
            {"name": "chain-test", "status": "in_progress", "conclusion": None},
            {"name": "validate-yaml", "status": "completed", "conclusion": "success"},
            {"name": "pr-check", "status": "completed", "conclusion": "failure"},
        ]
    )

    assert [check["name"] for check in pending] == ["chain-test"]
    assert [check["name"] for check in failed] == ["pr-check"]
    assert [check["name"] for check in passed] == ["validate-yaml"]


def test_get_pr_body_prefers_default_description_file(tmp_path, monkeypatch) -> None:
    module = load_pr_flow_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pr_description.md").write_text("hello\n", encoding="utf-8")

    # Pass the file path explicitly since function doesn't auto-read .pr_description.md
    assert module.get_pr_body(str(tmp_path / ".pr_description.md"), None, False) == "hello"


def test_get_pr_body_prefers_inline_text_over_file(tmp_path, monkeypatch) -> None:
    module = load_pr_flow_module()
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".pr_description.md").write_text("file-body\n", encoding="utf-8")

    assert module.get_pr_body(None, "inline-body", False) == "inline-body"
