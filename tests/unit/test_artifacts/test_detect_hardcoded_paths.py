import importlib.util
from pathlib import Path

import pytest


def _load_detector_module():
    module_path = Path(__file__).resolve().parents[3] / "scripts" / "detect-hardcoded-paths.py"
    spec = importlib.util.spec_from_file_location("detect_hardcoded_paths", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_main_handles_single_file_path_without_relative_to_error(tmp_path, monkeypatch, capsys):
    repo_root = tmp_path
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True, exist_ok=True)
    target = scripts_dir / "sample.py"
    target.write_text('bad_path = ".workflow/runs"\n', encoding="utf-8")

    detector = _load_detector_module()
    monkeypatch.chdir(repo_root)
    monkeypatch.setattr("sys.argv", ["detect-hardcoded-paths.py", "--fail", "scripts/sample.py"])

    with pytest.raises(SystemExit) as exc:
        detector.main()

    captured = capsys.readouterr()
    assert exc.value.code == 1
    assert "sample.py" in captured.out
    assert "sample.py/sample.py" not in captured.out
