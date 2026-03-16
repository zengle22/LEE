from pathlib import Path

import click
import pytest

import lee.cli.commands.run as run_module


def test_scope_run_lock_blocks_same_scope(tmp_path: Path) -> None:
    if run_module.fcntl is None:  # pragma: no cover
        pytest.skip("fcntl unavailable on this platform")

    scope_info = run_module.ConcurrencyScopeInfo(
        workflow_key="product.epic-to-feat",
        concurrency_scope="epic:EPIC-123",
        concurrency_key="product.epic-to-feat::epic:EPIC-123",
        scope_source="test",
    )

    lock_dir = tmp_path / ".workflow" / "locks"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / run_module._scope_lock_name(scope_info.concurrency_key)

    holder = open(lock_path, "a+", encoding="utf-8")
    run_module.fcntl.flock(holder.fileno(), run_module.fcntl.LOCK_EX | run_module.fcntl.LOCK_NB)
    holder.seek(0)
    holder.truncate()
    holder.write("pid=1234")
    holder.flush()

    try:
        with pytest.raises(click.ClickException) as ex:
            run_module._acquire_run_scope_lock(tmp_path, scope_info)
        assert "same concurrency scope" in str(ex.value).lower()
    finally:
        run_module.fcntl.flock(holder.fileno(), run_module.fcntl.LOCK_UN)
        holder.close()
