from pathlib import Path

from lee.orchestrator.api import pm_workflow, _orchestrators


def test_pm_workflow_releases_loop_scoped_orchestrator(tmp_path: Path) -> None:
    """pm_workflow should not leak cached orchestrators across asyncio.run calls."""
    project_dir = str(tmp_path)

    for _ in range(3):
        result = pm_workflow("get_state", project_dir=project_dir)
        assert "workflows" in result
        assert "timestamp" in result
        # Handler-level cleanup must drop loop-scoped cache entries.
        assert _orchestrators == {}
