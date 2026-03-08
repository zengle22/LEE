from pathlib import Path
import importlib.util
import shutil
import subprocess
import sys


def test_install_git_hooks_status_mentions_ssot_checks(tmp_path, monkeypatch, capsys):
    repo_root = tmp_path
    (repo_root / ".git").mkdir()
    (repo_root / "scripts").mkdir()
    (repo_root / "scripts" / "git-pre-commit-hook.py").write_text("print('ok')\n", encoding="utf-8")
    (repo_root / "scripts" / "git-pre-push-hook.py").write_text("print('ok')\n", encoding="utf-8")

    module_path = Path(__file__).resolve().parents[3] / "scripts" / "install-git-hooks.py"
    spec = importlib.util.spec_from_file_location("install_git_hooks", module_path)
    install_hooks = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(install_hooks)

    original_git_dir = install_hooks.GIT_DIR
    original_hooks_dir = install_hooks.HOOKS_DIR
    original_scripts_dir = install_hooks.SCRIPTS_DIR
    monkeypatch.chdir(repo_root)
    install_hooks.GIT_DIR = Path(".git")
    install_hooks.HOOKS_DIR = install_hooks.GIT_DIR / "hooks"
    install_hooks.SCRIPTS_DIR = Path("scripts")
    monkeypatch.setattr(install_hooks, "is_git_repo", lambda: True)
    try:
        install_hooks.show_status()
        captured = capsys.readouterr()
        assert "SSOT lint" in captured.out
        assert "release gate" in captured.out
    finally:
        install_hooks.GIT_DIR = original_git_dir
        install_hooks.HOOKS_DIR = original_hooks_dir
        install_hooks.SCRIPTS_DIR = original_scripts_dir


def test_install_git_hooks_end_to_end_executes_generated_wrapper(tmp_path, monkeypatch):
    if shutil.which("sh") is None:
        import pytest
        pytest.skip("sh is not available in this environment")

    repo_root = tmp_path
    (repo_root / ".git").mkdir()
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "git-pre-commit-hook.py").write_text(
        "print('pre-commit-ok')\n",
        encoding="utf-8",
    )
    (scripts_dir / "git-pre-push-hook.py").write_text(
        "print('pre-push-ok')\n",
        encoding="utf-8",
    )

    module_path = Path(__file__).resolve().parents[3] / "scripts" / "install-git-hooks.py"
    spec = importlib.util.spec_from_file_location("install_git_hooks", module_path)
    install_hooks = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(install_hooks)

    original_git_dir = install_hooks.GIT_DIR
    original_hooks_dir = install_hooks.HOOKS_DIR
    original_scripts_dir = install_hooks.SCRIPTS_DIR
    monkeypatch.chdir(repo_root)
    install_hooks.GIT_DIR = Path(".git")
    install_hooks.HOOKS_DIR = install_hooks.GIT_DIR / "hooks"
    install_hooks.SCRIPTS_DIR = Path("scripts")
    try:
        assert install_hooks.install_all() is True
        hook_path = repo_root / ".git" / "hooks" / "pre-commit"
        assert hook_path.exists()
        hook_text = hook_path.read_text(encoding="utf-8")
        assert 'REPO_ROOT="${GIT_WORK_TREE:-}"' in hook_text
        assert Path(sys.executable).as_posix() in hook_text

        result = subprocess.run(
            ["sh", str(hook_path)],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0
        assert "pre-commit-ok" in result.stdout
    finally:
        install_hooks.GIT_DIR = original_git_dir
        install_hooks.HOOKS_DIR = original_hooks_dir
        install_hooks.SCRIPTS_DIR = original_scripts_dir
