from pathlib import Path

import click
import pytest

import lee.cli.commands.run as run_module


def test_project_run_lock_blocks_concurrent_run(tmp_path: Path) -> None:
    if run_module.fcntl is None:  # pragma: no cover
        pytest.skip("fcntl unavailable on this platform")

    lock_dir = tmp_path / ".workflow"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "run.lock"

    holder = open(lock_path, "a+", encoding="utf-8")
    run_module.fcntl.flock(holder.fileno(), run_module.fcntl.LOCK_EX | run_module.fcntl.LOCK_NB)
    holder.seek(0)
    holder.truncate()
    holder.write("pid=1234")
    holder.flush()

    try:
        with pytest.raises(click.ClickException) as ex:
            run_module._acquire_project_run_lock(tmp_path)
        assert "another active `lee run`" in str(ex.value).lower()
    finally:
        run_module.fcntl.flock(holder.fileno(), run_module.fcntl.LOCK_UN)
        holder.close()
