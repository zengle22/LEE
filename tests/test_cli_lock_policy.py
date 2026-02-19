from lee.cli.main import _should_lock


def test_should_not_lock_for_status() -> None:
    assert _should_lock(["status", "wf_task_x"]) is False


def test_should_not_lock_for_watch() -> None:
    assert _should_lock(["watch", "wf_task_x"]) is False


def test_should_lock_for_run() -> None:
    assert _should_lock(["run", "office.workspace-cleanup"]) is True
