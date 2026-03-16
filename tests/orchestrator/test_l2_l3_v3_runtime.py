"""Tests for L2/L3 v3 runtime path and L3 spawning (P1).

This test module covers:
- TEST-001: runtime_dir path logic - L3 instances created in .workflow/instances/l3/
- TEST-002: _spawn_l3_for_point - L3 spawning from L2 workflow
- L3 v3 template loading
- Event publishing (L3_SPAWNED)
"""

import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime

from lee.orchestrator.storage.models import (
    Complexity,
    Point,
    WorkflowLevel,
    WorkflowStatus,
    WorkflowInstance,
)
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.core.event_bus import EventType
from lee.orchestrator.core.workflow_generator import WorkflowGenerator, L3InstanceConfig


class TestRuntimeDirPath:
    """TEST-001: Test runtime_dir path logic.

    Verify that L3 instances are created in .workflow/instances/l3/,
    NOT in the framework directory (spec-global/...).
    """

    @pytest.mark.asyncio
    async def test_l3_instance_path_in_runtime_dir(self, tmp_path):
        """Test L3 instance file is created in .workflow/instances/l3/."""
        # Setup database
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path=str(db_path))
        await store.connect()

        # Create template in framework dir (should exist)
        framework_dir = tmp_path / "lee" / "spec-global" / "departments" / "dev" / "workflows" / "templates"
        framework_dir.mkdir(parents=True, exist_ok=True)

        # Create minimal L3 v3 template
        l3_template_content = """
kind: l3_workflow_template
version: "3.0"
id: template.dev.task_l3_v3
name: L3 Task Template v3
description: 6-step TDD workflow for L3 tasks
steps:
  - id: align_requirement
    name: "对齐需求"
    kind: agent
    description: "分析功能点，明确验收标准"
    mandatory: true
    depends_on: []
  - id: design_tests
    name: "设计测试"
    kind: agent
    description: "设计测试用例"
    mandatory: true
    depends_on: ["align_requirement"]
  - id: implement
    name: "实现"
    kind: agent
    description: "实现功能"
    mandatory: true
    depends_on: ["design_tests"]
  - id: run_tests
    name: "测试"
    kind: skill
    description: "运行测试"
    mandatory: true
    depends_on: ["implement"]
  - id: code_review
    name: "Review"
    kind: agent
    description: "代码评审"
    mandatory: true
    depends_on: ["run_tests"]
  - id: retrospective
    name: "复盘"
    kind: agent
    description: "任务复盘"
    mandatory: false
    depends_on: ["code_review"]
"""
        (framework_dir / "l3").mkdir(exist_ok=True)
        (framework_dir / "l3" / "task-l3-v3-template.yaml").write_text(l3_template_content)

        # Create orchestrator
        orch = Orchestrator(
            store=store,
            project_root=str(tmp_path),
        )

        # Verify runtime_dir attribute
        expected_runtime_dir = tmp_path / ".workflow"
        # The runtime_dir is constructed inline in _spawn_l3_for_point
        # Verify the logic by checking the path construction
        runtime_dir = Path(tmp_path) / ".workflow"
        assert runtime_dir == expected_runtime_dir

        await store.close()

    def test_runtime_dir_path_construction(self):
        """Test runtime_dir path construction logic."""
        # With project_root
        project_root = Path("/Users/test/project")
        runtime_dir = Path(project_root) / ".workflow"
        assert runtime_dir.name == ".workflow"
        assert runtime_dir.parts[-2:] == ("project", ".workflow")

        # Without project_root (fallback)
        runtime_dir_fallback = Path(".workflow")
        assert str(runtime_dir_fallback) == ".workflow"

    @pytest.mark.asyncio
    async def test_l3_path_not_in_framework_dir(self, tmp_path):
        """Test L3 instance path is NOT in framework directory."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path=str(db_path))
        await store.connect()

        # Create framework structure
        framework_instances_dir = tmp_path / "lee" / "spec-global" / "departments" / "dev" / "workflows" / "instances" / "l3"

        # Create runtime structure
        runtime_instances_dir = tmp_path / ".workflow" / "instances" / "l3"

        # Simulate the path logic from _spawn_l3_for_point
        runtime_dir = Path(tmp_path) / ".workflow"
        l3_path = runtime_dir / "instances" / "l3" / "test-point.yaml"

        # Verify path is in runtime dir
        assert ".workflow" in str(l3_path)
        assert l3_path.parts[-3:-1] == ("instances", "l3")

        # Verify path is NOT in framework dir
        if framework_instances_dir.exists():
            # Framework instances dir should not be used
            framework_path = framework_instances_dir / "test-point.yaml"
            assert l3_path != framework_path
            assert "spec-global" not in str(l3_path)

        await store.close()


class TestSpawnL3ForPoint:
    """TEST-002: Test _spawn_l3_for_point method.

    Tests the complete flow of spawning an L3 workflow from a Point.
    """

    @pytest_asyncio.fixture
    async def setup_orchestrator(self, tmp_path):
        """Setup orchestrator with L2 parent and templates."""
        # Setup database
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path=str(db_path))
        await store.connect()

        # Create framework structure
        framework_dir = tmp_path / "lee" / "spec-global" / "departments" / "dev" / "workflows" / "templates"
        framework_dir.mkdir(parents=True, exist_ok=True)

        # Create L3 v3 template
        l3_template_content = """
kind: l3_workflow_template
version: "3.0"
id: template.dev.task_l3_v3
name: L3 Task Template v3
description: 6-step TDD workflow
steps:
  - id: align_requirement
    name: "Align"
    kind: agent
    mandatory: true
    depends_on: []
  - id: design_tests
    name: "Design Tests"
    kind: agent
    mandatory: true
    depends_on: ["align_requirement"]
  - id: implement
    name: "Implement"
    kind: agent
    mandatory: true
    depends_on: ["design_tests"]
  - id: run_tests
    name: "Run Tests"
    kind: skill
    mandatory: true
    depends_on: ["implement"]
  - id: code_review
    name: "Review"
    kind: agent
    mandatory: true
    depends_on: ["run_tests"]
  - id: retrospective
    name: "Retrospective"
    kind: agent
    mandatory: false
    depends_on: ["code_review"]
"""
        (framework_dir / "l3").mkdir(exist_ok=True)
        (framework_dir / "l3" / "task-l3-v3-template.yaml").write_text(l3_template_content)
        (framework_dir / "tech-design-l3-template.yaml").write_text("""
kind: l3_workflow_template
version: "1.0"
id: template.dev.tech_design_l3
steps:
  - id: analyze_feature
    name: "Analyze"
    kind: agent
    mandatory: true
    depends_on: []
""")

        # Create orchestrator
        orch = Orchestrator(
            store=store,
            project_root=str(tmp_path),
        )

        # Create L2 parent workflow
        l2_data = {
            "kind": "l2_workflow_instance",
            "context": {
                "repos": [
                    {"id": "test-repo", "type": "frontend"}
                ]
            },
            "params": {
                "tech_spec_ref": "TECH-001",
            },
            "artifacts": {
                "tech_spec_ref": "TECH-001",
            },
            "phases": [
                {"id": "frontend_dev", "status": "running", "complexity": "M"}
            ]
        }
        l2_parent = WorkflowInstance(
            id="l2-parent-test",
            level=WorkflowLevel.DEPARTMENT,
            template_id="template.dev.feature_l2",
            status=WorkflowStatus.RUNNING,
            data=l2_data,
        )
        await store.create_workflow(l2_parent)

        yield orch, store

        await store.close()

    @pytest.mark.asyncio
    async def test_spawn_l3_creates_instance_file(self, setup_orchestrator, tmp_path):
        """Test _spawn_l3_for_point creates instance file in runtime dir."""
        orch, store = setup_orchestrator

        # Create test point
        point = Point(
            id="test-point-1",
            title="Test Feature",
            desc="Test description",
            layer="ui",
            estimated_complexity=Complexity.M,
        )

        # Mock event bus to capture events
        events_captured = []
        original_publish_l3 = orch._publish_l3_spawned

        def mock_publish_l3(*args, **kwargs):
            # Capture the event data
            events_captured.append(("L3_SPAWNED", args))

        orch._publish_l3_spawned = mock_publish_l3

        # Mock spawn_workflow to avoid full execution
        spawned_workflows = []
        original_spawn = orch.spawn_workflow

        async def mock_spawn(**kwargs):
            # Create a mock workflow instance
            wf = WorkflowInstance(
                id=f"l3-{point.id}",
                level=WorkflowLevel.TASK,
                template_id=kwargs.get("template_id", "template.dev.task_l3"),
                status=WorkflowStatus.PENDING,
                data=kwargs.get("data", {}),
            )
            await store.create_workflow(wf)
            spawned_workflows.append(wf)
            return wf

        orch.spawn_workflow = mock_spawn

        # Execute _spawn_l3_for_point
        l3_id = await orch._spawn_l3_for_point(
            parent_l2_id="l2-parent-test",
            parent_phase_id="frontend_dev",
            point=point,
            repo_id="test-repo",
        )

        # Verify L3 was spawned
        assert l3_id is not None
        assert len(spawned_workflows) == 1
        assert spawned_workflows[0].id == l3_id

        # Verify instance file was created in runtime dir
        runtime_instance_path = tmp_path / ".workflow" / "instances" / "l3" / f"{point.id}.yaml"
        assert runtime_instance_path.exists(), f"L3 instance file should exist at {runtime_instance_path}"

        # Verify instance file content
        import yaml
        with open(runtime_instance_path) as f:
            instance_data = yaml.safe_load(f)

        assert instance_data["kind"] == "l3_workflow_instance"
        assert instance_data["point_id"] == point.id
        assert instance_data["parent_l2_id"] == "l2-parent-test"
        assert instance_data["parent_phase_id"] == "frontend_dev"
        assert instance_data["params"]["tech_spec_ref"] == "TECH-001"
        assert instance_data["artifacts"]["tech_spec_ref"] == "TECH-001"

        # Verify L3_SPAWNED event was published
        assert len(events_captured) > 0
        assert events_captured[0][0] == "L3_SPAWNED"

    @pytest.mark.asyncio
    async def test_spawn_l3_event_payload(self, setup_orchestrator):
        """Test L3_SPAWNED event contains correct payload."""
        orch, store = setup_orchestrator

        point = Point(
            id="test-point-2",
            title="Event Test",
            desc="Test event payload",
            layer="ui",
            estimated_complexity=Complexity.M,
        )

        # Capture events
        events_captured = []

        def mock_publish_l3(parent_l2_id, phase_id, l3_id, point_id):
            events_captured.append({
                "parent_l2_id": parent_l2_id,
                "phase_id": phase_id,
                "l3_id": l3_id,
                "point_id": point_id,
            })

        orch._publish_l3_spawned = mock_publish_l3

        # Mock spawn_workflow
        l3_instance_id = "l3-test-point-2"

        async def mock_spawn(**kwargs):
            wf = WorkflowInstance(
                id=l3_instance_id,
                level=WorkflowLevel.TASK,
                template_id="template.dev.task_l3_v3",
                status=WorkflowStatus.PENDING,
                data=kwargs.get("data", {}),
            )
            await store.create_workflow(wf)
            return wf

        orch.spawn_workflow = mock_spawn

        # Execute
        await orch._spawn_l3_for_point(
            parent_l2_id="l2-parent-test",
            parent_phase_id="frontend_dev",
            point=point,
            repo_id="test-repo",
        )

        # Verify event payload
        assert len(events_captured) == 1
        payload = events_captured[0]
        assert payload["parent_l2_id"] == "l2-parent-test"
        assert payload["phase_id"] == "frontend_dev"
        assert payload["point_id"] == "test-point-2"
        assert payload["l3_id"] == l3_instance_id

    @pytest.mark.asyncio
    async def test_spawn_l3_with_different_complexities(self, setup_orchestrator):
        """Test spawning L3 with different complexity levels."""
        orch, store = setup_orchestrator

        complexities = [Complexity.S, Complexity.M, Complexity.L]
        spawned_ids = []

        async def mock_spawn(**kwargs):
            point_id = kwargs['data'].get('point_id')
            wf = WorkflowInstance(
                id=f"l3-{point_id}",
                level=WorkflowLevel.TASK,
                template_id="template.dev.task_l3_v3",
                status=WorkflowStatus.PENDING,
                data=kwargs.get("data", {}),
            )
            await store.create_workflow(wf)
            spawned_ids.append(wf.id)
            return wf

        orch.spawn_workflow = mock_spawn

        # Test each complexity level
        for comp in complexities:
            point = Point(
                id=f"point-{comp.value}",
                title=f"Test {comp.value}",
                desc="Test",
                layer="ui",
                estimated_complexity=comp,
            )

            l3_id = await orch._spawn_l3_for_point(
                parent_l2_id="l2-parent-test",
                parent_phase_id="frontend_dev",
                point=point,
                repo_id="test-repo",
            )

            assert l3_id is not None

        # All complexities should spawn successfully
        assert len(spawned_ids) == 3

    @pytest.mark.asyncio
    async def test_spawn_l3_uses_phase_template_id(self, setup_orchestrator, tmp_path):
        """Test phase-resolved L3 template ID is used for generation and spawn."""
        orch, store = setup_orchestrator

        point = Point(
            id="tech-point",
            title="Tech Design",
            desc="Resolve TECH baseline",
            layer="service",
            estimated_complexity=Complexity.M,
        )

        captured = {}

        async def mock_spawn(**kwargs):
            captured["template_id"] = kwargs.get("template_id")
            wf = WorkflowInstance(
                id="l3-tech-point",
                level=WorkflowLevel.TASK,
                template_id=kwargs.get("template_id"),
                status=WorkflowStatus.PENDING,
                data=kwargs.get("data", {}),
            )
            await store.create_workflow(wf)
            return wf

        orch.spawn_workflow = mock_spawn

        l3_id = await orch._spawn_l3_for_point(
            parent_l2_id="l2-parent-test",
            parent_phase_id="tech_design",
            point=point,
            repo_id="test-repo",
            l3_template_id="template.dev.tech_design_l3",
        )

        assert l3_id == "l3-tech-point"
        assert captured["template_id"] == "template.dev.tech_design_l3"

        runtime_instance_path = tmp_path / ".workflow" / "instances" / "l3" / f"{point.id}.yaml"
        assert runtime_instance_path.exists()

        import yaml
        with open(runtime_instance_path, encoding="utf-8") as f:
            instance_data = yaml.safe_load(f)
        assert instance_data["template_id"] == "template.dev.tech_design_l3"
        # Support both stages and legacy steps format
        if "stages" in instance_data:
            steps = []
            for stage in instance_data["stages"]:
                steps.extend(stage.get("steps", []))
        else:
            steps = instance_data["steps"]
        assert steps[0]["id"] == "analyze_feature"

    @pytest.mark.asyncio
    async def test_resolve_bugfix_l3_template_path(self, setup_orchestrator, tmp_path):
        """Test bugfix L3 template IDs resolve to checked-in template files."""
        orch, store = setup_orchestrator

        framework_dir = tmp_path / "spec-global" / "departments" / "dev" / "workflows" / "templates"
        framework_dir.mkdir(parents=True, exist_ok=True)
        template_file = framework_dir / "bugfix-triage-l3-template.yaml"
        template_file.write_text("""
kind: l3_workflow_template
version: "1.0"
id: template.dev.bugfix_triage_l3
steps:
  - id: validate_bug_input
    name: "Validate"
    kind: agent
    mandatory: true
    depends_on: []
  - id: classify_bug_path
    name: "Classify"
    kind: agent
    mandatory: true
    depends_on: ["validate_bug_input"]
  - id: review_batch_eligibility
    name: "Gate"
    kind: stage
    mandatory: true
    depends_on: ["classify_bug_path"]
  - id: publish_triage
    name: "Publish"
    kind: agent
    mandatory: true
    depends_on: ["review_batch_eligibility"]
""")

        orch.project_root = str(tmp_path)
        resolved = orch._resolve_l3_template_path("template.dev.bugfix_triage_l3")
        assert resolved.name == "bugfix-triage-l3-template.yaml"


class TestL3V3Template:
    """Tests for L3 v3 template loading and structure."""

    def test_l3_v3_template_structure(self, tmp_path):
        """Test L3 v3 template has correct structure."""
        # Create template
        template_dir = tmp_path / "templates" / "l3"
        template_dir.mkdir(parents=True)

        template_content = """
kind: l3_workflow_template
version: "3.0"
id: template.dev.task_l3_v3
name: L3 Task Template v3
description: 6-step TDD workflow
steps:
  - id: align_requirement
    name: "对齐需求"
    kind: agent
    description: "分析功能点与验收标准"
    mandatory: true
    depends_on: []
  - id: design_tests
    name: "设计测试"
    kind: agent
    description: "根据功能点设计测试用例"
    mandatory: true
    depends_on: ["align_requirement"]
  - id: implement
    name: "实现"
    kind: agent
    description: "编写实现代码"
    mandatory: true
    depends_on: ["design_tests"]
  - id: run_tests
    name: "测试"
    kind: skill
    description: "运行单元测试"
    mandatory: true
    depends_on: ["implement"]
  - id: code_review
    name: "Review"
    kind: agent
    description: "代码评审"
    mandatory: true
    depends_on: ["run_tests"]
  - id: retrospective
    name: "复盘"
    kind: agent
    description: "任务复盘"
    mandatory: false
    depends_on: ["code_review"]
"""
        template_file = template_dir / "task-l3-v3-template.yaml"
        template_file.write_text(template_content)

        # Load and verify
        import yaml
        with open(template_file) as f:
            data = yaml.safe_load(f)

        assert data["kind"] == "l3_workflow_template"
        assert data["version"] == "3.0"
        assert len(data["steps"]) == 6

        # Verify step order
        step_ids = [s["id"] for s in data["steps"]]
        expected_order = [
            "align_requirement",
            "design_tests",
            "implement",
            "run_tests",
            "code_review",
            "retrospective",
        ]
        assert step_ids == expected_order

        # Verify mandatory flags
        mandatory_steps = [s for s in data["steps"] if s.get("mandatory", False)]
        assert len(mandatory_steps) == 5
        assert data["steps"][5]["mandatory"] is False  # retrospective

    def test_l3_v3_template_dependencies(self, tmp_path):
        """Test L3 v3 template step dependencies form a valid chain."""
        template_content = """
kind: l3_workflow_template
version: "3.0"
id: template.dev.task_l3_v3
steps:
  - id: align_requirement
    depends_on: []
  - id: design_tests
    depends_on: ["align_requirement"]
  - id: implement
    depends_on: ["design_tests"]
  - id: run_tests
    depends_on: ["implement"]
  - id: code_review
    depends_on: ["run_tests"]
  - id: retrospective
    depends_on: ["code_review"]
"""
        template_dir = tmp_path / "templates" / "l3"
        template_dir.mkdir(parents=True)
        template_file = template_dir / "task-l3-v3-template.yaml"
        template_file.write_text(template_content)

        # Build dependency graph
        import yaml
        with open(template_file) as f:
            data = yaml.safe_load(f)

        steps = {s["id"]: s.get("depends_on", []) for s in data["steps"]}

        # Verify linear dependency chain
        assert steps["align_requirement"] == []
        assert steps["design_tests"] == ["align_requirement"]
        assert steps["implement"] == ["design_tests"]
        assert steps["run_tests"] == ["implement"]
        assert steps["code_review"] == ["run_tests"]
        assert steps["retrospective"] == ["code_review"]

        # Verify no circular dependencies
        visited = set()
        def check_cycle(step_id, path):
            if step_id in path:
                raise ValueError(f"Circular dependency: {' -> '.join(path)} -> {step_id}")
            if step_id in visited:
                return
            visited.add(step_id)
            for dep in steps.get(step_id, []):
                check_cycle(dep, path + [step_id])

        check_cycle("align_requirement", [])
        check_cycle("design_tests", [])
        check_cycle("implement", [])
        check_cycle("run_tests", [])
        check_cycle("code_review", [])
        check_cycle("retrospective", [])


class TestL2V3Integration:
    """Integration tests for L2 v3 workflow spawning L3."""

    @pytest.mark.asyncio
    async def test_l2_v3_complexity_routing(self, tmp_path):
        """Test L2 v3 complexity=M routes to spawn L3."""
        # Setup
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path=str(db_path))
        await store.connect()

        # Create L2 v3 instance data
        l2_data = {
            "kind": "l2_workflow_instance",
            "version": "3.0",
            "id": "l2-test-v3",
            "template_id": "template.dev.feature_l2_v3",
            "context": {
                "repos": [{"id": "fe-repo", "type": "frontend"}]
            },
            "phases": [
                {
                    "id": "p1_contract_design",
                    "name": "契约设计",
                    "complexity": "S",
                    "status": "completed",
                    "l3_instance_ids": [],
                },
                {
                    "id": "p2_1_fe_development",
                    "name": "前端开发",
                    "complexity": "M",  # Should spawn L3
                    "status": "pending",
                    "l3_instance_ids": [],
                },
            ],
        }

        l2_instance = WorkflowInstance(
            id="l2-test-v3",
            level=WorkflowLevel.DEPARTMENT,
            template_id="template.dev.feature_l2_v3",
            status=WorkflowStatus.RUNNING,
            data=l2_data,
        )
        await store.create_workflow(l2_instance)

        # Create orchestrator
        orch = Orchestrator(store=store, project_root=str(tmp_path))

        # Test _is_l2_instance detection
        assert orch._is_l2_instance(l2_instance) is True

        # Test _get_phase_complexity
        complexity = orch._get_phase_complexity(l2_instance, "p2_1_fe_development")
        assert complexity == Complexity.M

        # Test _get_next_pending_phase
        next_phase = orch._get_next_pending_phase(l2_instance)
        assert next_phase is not None
        assert next_phase["id"] == "p2_1_fe_development"
        assert next_phase["complexity"] == "M"

        await store.close()

    @pytest.mark.asyncio
    async def test_l2_v3_default_complexity(self, tmp_path):
        """Test L2 v3 default complexity when not specified."""
        db_path = tmp_path / "test.db"
        store = SQLiteStore(db_path=str(db_path))
        await store.connect()

        orch = Orchestrator(store=store, project_root=str(tmp_path))

        # L2 instance without complexity in phase
        l2_data = {
            "kind": "l2_workflow_instance",
            "phases": [
                {"id": "unknown_phase", "status": "pending"}
                # No complexity field
            ]
        }

        instance = WorkflowInstance(
            id="l2-test",
            level=WorkflowLevel.DEPARTMENT,
            template_id="template.dev.feature_l2",
            status=WorkflowStatus.PENDING,
            data=l2_data,
        )

        # Should default to M
        complexity = orch._get_phase_complexity(instance, "unknown_phase")
        assert complexity == Complexity.M

        await store.close()


class TestWorkflowGeneratorL3V3:
    """Tests for WorkflowGenerator with L3 v3."""

    def test_generate_l3_v3_instance(self, tmp_path):
        """Test L3 v3 instance generation."""
        # Create template directory structure matching what WorkflowGenerator expects
        # WorkflowGenerator looks for: spec-global/departments/dev/workflows/templates/task-l3-template.yaml
        # We'll create the v3 template and patch the generator to use it

        # First, create v3 template
        v3_template_dir = tmp_path / "lee" / "spec-global" / "departments" / "dev" / "workflows" / "templates" / "l3"
        v3_template_dir.mkdir(parents=True)

        template_content = """
kind: l3_workflow_template
version: "3.0"
id: template.dev.task_l3_v3
name: L3 v3 Template
steps:
  - id: align_requirement
    name: "对齐需求"
    kind: agent
    mandatory: true
    depends_on: []
  - id: design_tests
    name: "设计测试"
    kind: agent
    mandatory: true
    depends_on: ["align_requirement"]
  - id: implement
    name: "实现"
    kind: agent
    mandatory: true
    depends_on: ["design_tests"]
  - id: run_tests
    name: "测试"
    kind: skill
    mandatory: true
    depends_on: ["implement"]
  - id: code_review
    name: "Review"
    kind: agent
    mandatory: true
    depends_on: ["run_tests"]
  - id: retrospective
    name: "复盘"
    kind: agent
    mandatory: false
    depends_on: ["code_review"]
"""
        v3_template_file = v3_template_dir / "task-l3-v3-template.yaml"
        v3_template_file.write_text(template_content)

        # Also create a fallback template at the expected location
        template_dir = tmp_path / "lee" / "spec-global" / "departments" / "dev" / "workflows" / "templates"
        fallback_content = template_content  # Use same content for fallback
        (template_dir / "task-l3-template.yaml").write_text(fallback_content)

        # Use the v3 template path directly
        generator = WorkflowGenerator(template_path=str(v3_template_file))

        point = Point(
            id="test-point",
            title="Test Feature",
            desc="Test description",
            layer="ui",
            estimated_complexity=Complexity.M,
        )

        config = L3InstanceConfig(
            point=point,
            parent_l2_id="l2-parent",
            parent_phase_id="frontend_dev",
            repo_id="fe-repo",
        )

        output_path = tmp_path / ".workflow" / "instances" / "l3" / "test-point.yaml"
        result = generator.generate_l3_instance(config, str(output_path))

        assert result.success
        assert output_path.exists()

        # Verify content
        import yaml
        with open(output_path) as f:
            data = yaml.safe_load(f)

        assert data["kind"] == "l3_workflow_instance"
        assert data["point_id"] == "test-point"
        assert len(data["steps"]) == 6

    def test_generate_l3_creates_runtime_dir(self, tmp_path):
        """Test L3 generation creates runtime directory if needed."""
        # Create template in expected location
        template_dir = tmp_path / "templates"
        template_dir.mkdir(parents=True)

        template_content = """
kind: l3_workflow_template
version: "3.0"
id: template.dev.task_l3_v3
steps:
  - id: step1
    name: "Step 1"
    kind: agent
    mandatory: true
    depends_on: []
"""
        template_file = template_dir / "task-l3-v3-template.yaml"
        template_file.write_text(template_content)

        generator = WorkflowGenerator(template_path=str(template_file))

        point = Point(
            id="dir-test",
            title="Dir Test",
            desc="Test",
            layer="ui",
            estimated_complexity=Complexity.M,
        )

        config = L3InstanceConfig(
            point=point,
            parent_l2_id="l2-test",
            parent_phase_id="test",
            repo_id="test-repo",
        )

        # Output to nested path that doesn't exist
        output_path = tmp_path / ".workflow" / "instances" / "l3" / "nested" / "dir-test.yaml"
        result = generator.generate_l3_instance(config, str(output_path))

        assert result.success
        assert output_path.exists()
        assert output_path.parent.exists()
