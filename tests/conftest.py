import shutil
import tempfile
import sys
import uuid
from pathlib import Path

import pytest


_TESTS_DIR = Path(__file__).resolve().parent
_WORKTREE_ROOT = _TESTS_DIR.parent
_SRC_DIR = _WORKTREE_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))

_WORKSPACE_TMP_ROOT = _WORKTREE_ROOT / "test-temp-pytest"
_WORKSPACE_TMP_ROOT.mkdir(parents=True, exist_ok=True)
_TEMPFILE_ROOT = _WORKTREE_ROOT / "test-temp-system"
_TEMPFILE_ROOT.mkdir(parents=True, exist_ok=True)
tempfile.tempdir = str(_TEMPFILE_ROOT)


@pytest.fixture
def tmp_path() -> Path:
    path = _WORKSPACE_TMP_ROOT / uuid.uuid4().hex
    path.mkdir(parents=True, exist_ok=False)
    try:
        yield path
    finally:
        shutil.rmtree(path, ignore_errors=True)
