from pathlib import Path
import importlib

from click.testing import CliRunner
import yaml

from lee.cli.commands.qa import qa
from lee.orchestrator.api import pm_workflow
from lee.orchestrator.execution.artifacts.manager import ArtifactManager
from lee.orchestrator.execution.artifacts.types import SSOTType


def _seed_valid_chain(project_root: Path) -> None:
    manager = ArtifactManager(root_path=project_root / ".artifacts", project_root=project_root)
    manager.create_ssot(
        ssot_type=SSOTType.RELEASE,
        title="Release 1.4.0",
        content="# release",
        run_id="qa-cli",
        formal_id="REL-1.4.0",
        properties={
            "release_version": "1.4.0",
            "build_version": "build-20260313",
            "build_commit": "abc1234",
            "base_url": "https://staging.example.test",
        },
        derived_from=[{"id": "FEAT-143", "version": "v1"}],
    )
    manager.create_ssot(
        ssot_type=SSOTType.TESTPLAN,
        title="Plan 1.4.0",
        content="# plan",
        run_id="qa-cli",
        formal_id="TESTPLAN-REL-1.4.0",
        parent_id="REL-1.4.0",
        derived_from=[
            {"id": "FEAT-143", "version": "v1"},
            {"id": "TESTSET-FEAT-143", "version": "v1"},
        ],
        properties={"environment_matrix": ["staging"]},
    )
    manager.create_ssot(
        ssot_type=SSOTType.TASK,
        title="Task",
        content="# task",
        run_id="qa-cli",
        formal_id="TASK-TESTPLAN-REL-1.4.0-001",
        parent_id="TESTPLAN-REL-1.4.0",
        derived_from=[{"id": "FEAT-143", "version": "v1"}],
        properties={"slice_key": "qa-entry"},
    )


def _seed_execution_prerequisites(
    project_root: Path,
    *,
    environment: str = "staging",
    test_set_ids: tuple[str, ...] = ("TESTSET-FEAT-143",),
) -> None:
    lee_dir = project_root / ".lee"
    lee_dir.mkdir(parents=True, exist_ok=True)
    (lee_dir / "repos.yaml").write_text(
        yaml.safe_dump(
            {
                "version": "1.0",
                "repos": {
                    "frontend": {"path": "./.", "type": "frontend"},
                    "backend": {"path": "./.", "type": "backend"},
                },
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    sut_path = project_root / "tests" / "runtime" / environment / "sut.yaml"
    sut_path.parent.mkdir(parents=True, exist_ok=True)
    sut_path.write_text(
        yaml.safe_dump(
            {
                "template_status": "ready",
                "sut_type": "web",
                "name": f"{environment}-sut",
                "base_url": "https://staging.example.test",
                "base_path": "",
                "protocol": "https",
                "enabled": True,
            },
            allow_unicode=True,
            sort_keys=False,
        ),
        encoding="utf-8",
    )

    test_set_dir = project_root / "spec" / "qa" / "test-sets"
    test_set_dir.mkdir(parents=True, exist_ok=True)
    for test_set_id in test_set_ids:
        test_set_path = test_set_dir / f"ts-{test_set_id.lower().replace('_', '-')}.yaml"
        test_set_path.write_text(
            yaml.safe_dump(
                {
                    "test_set_id": test_set_id,
                    "module": "feat-143",
                    "title": "QA regression set",
                    "status": "ready",
                    "cases": [{"case_id": "CASE-001", "title": "smoke"}],
                },
                allow_unicode=True,
                sort_keys=False,
            ),
            encoding="utf-8",
        )


def test_execute_command_accepts_valid_taskplan_task(tmp_path: Path, monkeypatch):
    _seed_valid_chain(tmp_path)
    _seed_execution_prerequisites(tmp_path)
    runner = CliRunner()
    calls = []

    def fake_pm_workflow(action: str, **kwargs):
        calls.append((action, kwargs))
        if action == "create":
            return {"workflow_id": "wf_task_qa_001"}
        if action == "run_until_blocked":
            return {"status": "running", "current_step": "env_provision"}
        raise AssertionError(f"unexpected action: {action}")

    execute_module = importlib.import_module("lee.cli.commands.qa.execute")
    monkeypatch.setattr(execute_module, "pm_workflow", fake_pm_workflow)

    result = runner.invoke(
        qa,
        [
            "execute",
            "TASK-TESTPLAN-REL-1.4.0-001",
            "--project-dir",
            str(tmp_path),
            "--triggered-by",
            "qa-user",
        ],
    )

    assert result.exit_code == 0
    assert "status=RUNNING" in result.output
    assert "release_ref=REL-1.4.0" in result.output
    assert "workflow_id=wf_task_qa_001" in result.output
    create_call = next(kwargs for action, kwargs in calls if action == "create")
    assert create_call["data"]["params"]["test_plan_id"] == "TESTPLAN-REL-1.4.0"
    assert create_call["data"]["params"]["build_version"] == "build-20260313"
    assert create_call["data"]["params"]["build_commit"] == "abc1234"
    assert create_call["data"]["params"]["environment"] == "staging"
    assert create_call["data"]["params"]["target_test_sets"] == ["TESTSET-FEAT-143"]
    run_call = next(kwargs for action, kwargs in calls if action == "run_until_blocked")
    assert run_call["workflow_id"] == "wf_task_qa_001"


def test_execute_command_blocks_bypass_request(tmp_path: Path):
    runner = CliRunner()

    result = runner.invoke(
        qa,
        [
            "execute",
            "TASK-FEAT-143-001",
            "--project-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "status=BLOCKED" in result.output
    assert "QA-ENTRY-011" in result.output


def test_execute_command_reports_chain_validation_error_code(tmp_path: Path):
    _seed_valid_chain(tmp_path)
    runner = CliRunner()
    manager = ArtifactManager(root_path=tmp_path / ".artifacts", project_root=tmp_path)

    manager.create_ssot(
        ssot_type=SSOTType.RELEASE,
        title="Draft Release",
        content="# release",
        run_id="qa-cli",
        formal_id="REL-1.4.1",
        properties={"release_version": "1.4.1", "plan_status": "draft"},
        derived_from=[{"id": "FEAT-143", "version": "v1"}],
    )
    manager.create_ssot(
        ssot_type=SSOTType.TESTPLAN,
        title="Draft Plan",
        content="# plan",
        run_id="qa-cli",
        formal_id="TESTPLAN-REL-1.4.1",
        parent_id="REL-1.4.1",
        derived_from=[
            {"id": "FEAT-143", "version": "v1"},
            {"id": "TESTSET-FEAT-143", "version": "v1"},
        ],
        properties={"environment_matrix": ["staging"]},
    )
    manager.create_ssot(
        ssot_type=SSOTType.TASK,
        title="Task",
        content="# task",
        run_id="qa-cli",
        formal_id="TASK-TESTPLAN-REL-1.4.1-001",
        parent_id="TESTPLAN-REL-1.4.1",
        derived_from=[{"id": "FEAT-143", "version": "v1"}],
        properties={"slice_key": "qa-entry"},
    )

    result = runner.invoke(
        qa,
        [
            "execute",
            "TASK-TESTPLAN-REL-1.4.1-001",
            "--project-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 1
    assert "status=BLOCKED" in result.output
    assert "QA-ENTRY-008" in result.output


def test_execute_command_respects_max_steps(tmp_path: Path, monkeypatch):
    _seed_valid_chain(tmp_path)
    _seed_execution_prerequisites(tmp_path)
    runner = CliRunner()
    calls = []

    def fake_pm_workflow(action: str, **kwargs):
        calls.append((action, kwargs))
        if action == "create":
            return {"workflow_id": "wf_task_qa_002"}
        if action == "run_until_blocked":
            return {"status": "paused"}
        raise AssertionError(f"unexpected action: {action}")

    execute_module = importlib.import_module("lee.cli.commands.qa.execute")
    monkeypatch.setattr(execute_module, "pm_workflow", fake_pm_workflow)

    result = runner.invoke(
        qa,
        [
            "execute",
            "TASK-TESTPLAN-REL-1.4.0-001",
            "--project-dir",
            str(tmp_path),
            "--max-steps",
            "7",
        ],
    )

    assert result.exit_code == 0
    run_call = next(kwargs for action, kwargs in calls if action == "run_until_blocked")
    assert run_call["max_steps"] == 7


def test_execute_command_renders_l2_workflow_with_canonical_tail_phases(tmp_path: Path, monkeypatch):
    _seed_valid_chain(tmp_path)
    _seed_execution_prerequisites(tmp_path)
    runner = CliRunner()
    calls = []

    def fake_pm_workflow(action: str, **kwargs):
        calls.append((action, kwargs))
        if action == "create":
            return {"workflow_id": "wf_task_qa_003"}
        if action == "run_until_blocked":
            return {"status": "running", "current_step": "test_run_init"}
        raise AssertionError(f"unexpected action: {action}")

    execute_module = importlib.import_module("lee.cli.commands.qa.execute")
    monkeypatch.setattr(execute_module, "pm_workflow", fake_pm_workflow)

    result = runner.invoke(
        qa,
        [
            "execute",
            "TASK-TESTPLAN-REL-1.4.0-001",
            "--project-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    create_call = next(kwargs for action, kwargs in calls if action == "create")
    rendered_path = Path(create_call["template_id"])
    rendered_doc = yaml.safe_load(rendered_path.read_text(encoding="utf-8"))

    phase_ids = [phase["id"] for phase in rendered_doc["phases"]]
    context_fields = rendered_doc["instance_schema"]["context_fields"]
    metrics = {
        metric["name"]: metric["labels"]
        for metric in rendered_doc["observability"]["metrics"]
    }

    assert phase_ids[-4:] == ["bug_summary", "test_report", "exit_evaluation", "retrospective"]
    assert "release_ref" in context_fields
    assert "task_ref" in context_fields
    assert metrics["l2_execution_duration"][:2] == ["release_ref", "test_plan_id"]
    assert create_call["data"]["execution_entry"]["release_ref"] == "REL-1.4.0"
    assert create_call["data"]["execution_entry"]["task_ref"] == "TASK-TESTPLAN-REL-1.4.0-001"


def test_audit_log_command_reads_written_entries(tmp_path: Path):
    _seed_valid_chain(tmp_path)
    _seed_execution_prerequisites(tmp_path)
    runner = CliRunner()
    execute_result = runner.invoke(
        qa,
        [
            "execute",
            "TASK-TESTPLAN-REL-1.4.0-001",
            "--project-dir",
            str(tmp_path),
            "--triggered-by",
            "qa-user",
        ],
    )

    result = runner.invoke(
        qa,
        [
            "audit",
            "log",
            "--task-ref",
            "TASK-TESTPLAN-REL-1.4.0-001",
            "--project-dir",
            str(tmp_path),
        ],
    )

    assert execute_result.exit_code == 0
    assert "status=RUNNING" in execute_result.output
    assert result.exit_code == 0
    assert "TASK-TESTPLAN-REL-1.4.0-001" in result.output
    assert "qa-user" in result.output


def test_execute_command_creates_real_workflow_instance(tmp_path: Path):
    _seed_valid_chain(tmp_path)
    _seed_execution_prerequisites(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        qa,
        [
            "execute",
            "TASK-TESTPLAN-REL-1.4.0-001",
            "--project-dir",
            str(tmp_path),
            "--triggered-by",
            "qa-user",
            "--max-steps",
            "1",
        ],
    )

    assert result.exit_code == 0
    workflow_line = next(line for line in result.output.splitlines() if line.startswith("workflow_id="))
    workflow_id = workflow_line.split("=", 1)[1].strip()

    state = pm_workflow(
        "get_state",
        project_dir=str(tmp_path),
        workflow_id=workflow_id,
    )
    ready_steps = pm_workflow(
        "list_ready_steps",
        project_dir=str(tmp_path),
        workflow_id=workflow_id,
    )

    assert state["workflow_id"] == workflow_id
    assert state["level"] == "department"
    assert state["status"] == "running"
    assert state["data"]["params"]["release_ref"] == "REL-1.4.0"
    assert state["data"]["params"]["task_ref"] == "TASK-TESTPLAN-REL-1.4.0-001"
    assert state["data"]["execution_entry"]["release_ref"] == "REL-1.4.0"
    assert state["data"]["execution_entry"]["task_ref"] == "TASK-TESTPLAN-REL-1.4.0-001"
    assert state["data"]["kind"] == "l2_workflow_instance"
    assert state["data"]["phases"][0]["id"] == "test_run_init"
    assert state["data"]["phases"][0]["status"] == "completed"
    assert state["template_id"].endswith(".yaml")
    assert Path(tmp_path / ".workflow" / "orchestrator.db").exists()
    assert isinstance(ready_steps["ready_steps"], list)

    rendered_doc = yaml.safe_load(Path(state["template_id"]).read_text(encoding="utf-8"))
    phase_ids = [phase["id"] for phase in rendered_doc["phases"]]
    context_fields = rendered_doc["instance_schema"]["context_fields"]

    assert phase_ids[-4:] == ["bug_summary", "test_report", "exit_evaluation", "retrospective"]
    assert "release_ref" in context_fields
    assert "task_ref" in context_fields


def test_audit_log_command_filters_by_release(tmp_path: Path):
    _seed_valid_chain(tmp_path)
    _seed_execution_prerequisites(tmp_path)
    runner = CliRunner()
    runner.invoke(
        qa,
        [
            "execute",
            "TASK-TESTPLAN-REL-1.4.0-001",
            "--project-dir",
            str(tmp_path),
            "--triggered-by",
            "qa-user",
        ],
    )

    result = runner.invoke(
        qa,
        [
            "audit",
            "log",
            "--release-ref",
            "REL-1.4.0",
            "--project-dir",
            str(tmp_path),
        ],
    )

    assert result.exit_code == 0
    assert "release=REL-1.4.0" in result.output


def test_execute_command_advances_to_qa_l3_spawn_state(tmp_path: Path):
    _seed_valid_chain(tmp_path)
    _seed_execution_prerequisites(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        qa,
        [
            "execute",
            "TASK-TESTPLAN-REL-1.4.0-001",
            "--project-dir",
            str(tmp_path),
            "--triggered-by",
            "qa-user",
            "--max-steps",
            "20",
        ],
    )

    assert result.exit_code == 0
    assert "status=RUNNING" in result.output
    workflow_line = next(line for line in result.output.splitlines() if line.startswith("workflow_id="))
    workflow_id = workflow_line.split("=", 1)[1].strip()
    state = pm_workflow(
        "get_state",
        project_dir=str(tmp_path),
        workflow_id=workflow_id,
    )

    assert state["status"] == "running"
    assert state["level"] == "department"
    test_set_phase = next(phase for phase in state["data"]["phases"] if phase["id"] == "test_set_execution")
    assert test_set_phase["status"] == "running"
    assert len(test_set_phase["l3_instance_ids"]) == 1
    assert test_set_phase["l3_template_id"] == "template.qa.test_set_execute"
    assert state["children"] == test_set_phase["l3_instance_ids"]


def test_execute_command_blocks_on_missing_prerequisites_and_generates_templates(tmp_path: Path):
    _seed_valid_chain(tmp_path)
    runner = CliRunner()

    result = runner.invoke(
        qa,
        [
            "execute",
            "TASK-TESTPLAN-REL-1.4.0-001",
            "--project-dir",
            str(tmp_path),
            "--triggered-by",
            "qa-user",
        ],
    )

    assert result.exit_code == 1
    assert "status=BLOCKED error_code=QA-PREFLIGHT-001" in result.output
    assert "[repo_registry]" in result.output
    assert "[sut_config]" in result.output
    assert "[test_set]" in result.output
    assert (tmp_path / ".lee" / "repos.yaml").exists()
    assert (tmp_path / "tests" / "runtime" / "staging" / "sut.yaml").exists()
    assert (tmp_path / "spec" / "qa" / "test-sets" / "ts-testset-feat-143.yaml").exists()


def test_legacy_test_run_entry_is_blocked():
    runner = CliRunner()

    result = runner.invoke(qa, ["test-run", "start", "TESTPLAN-REL-1.4.0"])

    assert result.exit_code != 0
    assert "lee qa execute" in result.output


def test_legacy_qa_run_shortcut_is_blocked():
    runner = CliRunner()

    result = runner.invoke(
        qa,
        ["run", "TESTPLAN-REL-1.4.0", "--build", "1", "--commit", "abc"],
    )

    assert result.exit_code != 0
    assert "lee qa execute" in result.output
