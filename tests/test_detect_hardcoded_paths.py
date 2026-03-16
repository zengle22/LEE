from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


def _load_detector_module():
    script_path = Path(__file__).resolve().parent.parent / "scripts" / "detect-hardcoded-paths.py"
    spec = spec_from_file_location("detect_hardcoded_paths_script", script_path)
    module = module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_detect_hardcoded_paths_for_directory(tmp_path: Path) -> None:
    detector = _load_detector_module()
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    target = source_dir / "sample.py"
    target.write_text('workspace_path = ".workflow/logs/run.log"\n', encoding="utf-8")

    findings = detector.detect_hardcoded_paths(source_dir)

    assert findings == [(Path("sample.py"), 1, 'workspace_path = ".workflow/logs/run.log"')]


def test_detect_hardcoded_paths_for_file_does_not_crash_on_relative_paths(tmp_path: Path) -> None:
    detector = _load_detector_module()
    source_dir = tmp_path / "src"
    source_dir.mkdir()
    target = source_dir / "runner.py"
    target.write_text('workspace = ".artifacts/cache"\n', encoding="utf-8")

    findings = detector.detect_hardcoded_paths_for_file(target)

    assert findings == [(Path("runner.py"), 1, 'workspace = ".artifacts/cache"')]
