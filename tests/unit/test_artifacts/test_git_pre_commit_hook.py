from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest


def load_pre_commit_module():
    module_path = Path(__file__).resolve().parents[3] / "scripts" / "git-pre-commit-hook.py"
    spec = importlib.util.spec_from_file_location("git_pre_commit_hook", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_pre_commit_ssot_lint_uses_staged_scope(monkeypatch) -> None:
    module = load_pre_commit_module()

    monkeypatch.setattr(module, "check_staged_files", lambda: True)
    monkeypatch.setattr(
        module,
        "get_staged_files",
        lambda: [
            "src/lee/orchestrator/execution/artifacts/ssot_service.py",
            "README.md",
        ],
    )

    captured: dict[str, object] = {}

    def fake_run_ssot_lint(paths):
        captured["paths"] = paths
        return True, []

    monkeypatch.setattr(module, "run_ssot_lint", fake_run_ssot_lint)

    with pytest.raises(SystemExit) as exc:
        module.main()

    assert exc.value.code == 0
    assert captured["paths"] == ["src/lee/orchestrator/execution/artifacts/ssot_service.py"]
