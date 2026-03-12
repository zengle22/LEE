"""Tests for L2/L3 workflow template and instantiation system (P0)."""

import pytest
import asyncio
from pathlib import Path

from lee.orchestrator.storage.models import Complexity, Point
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.core.workflow_generator import (
    WorkflowGenerator,
    L2InstanceConfig,
    L3InstanceConfig,
)
from lee.orchestrator.execution.pm_agent.task_splitter import (
    SimpleTaskSplitter,
    TaskSplitResult,
)


class TestComplexityAndPoint:
    """Tests for Complexity enum and Point dataclass."""

    def test_complexity_enum(self):
        """Test Complexity enum values."""
        assert Complexity.S == "S"
        assert Complexity.M == "M"
        assert Complexity.L == "L"

    def test_point_creation(self):
        """Test Point dataclass creation."""
        point = Point(
            id="test-point-1",
            title="Test Point",
            desc="Test description",
            layer="ui",
            estimated_complexity=Complexity.M,
            files_hint=["src/App.vue"],
            depends_on=["other-point"]
        )
        assert point.id == "test-point-1"
        assert point.layer == "ui"
        assert point.estimated_complexity == Complexity.M
        assert len(point.files_hint) == 1
        assert len(point.depends_on) == 1


class TestL2InstanceGeneration:
    """Tests for L2 instance generation from templates."""

    def test_l2_config_creation(self):
        """Test L2InstanceConfig creation."""
        config = L2InstanceConfig(
            id="instance.dev.test_feature",
            name="Test Feature",
            project="Test Project",
            module="test",
            module_version="v1",
            prd_path="specs/test.md",
            repos=[{"id": "fe-repo", "type": "frontend"}],
            phase_complexities={"tech_design": "S", "frontend_dev": "L"}
        )
        assert config.id == "instance.dev.test_feature"
        assert config.phase_complexities["tech_design"] == "S"
        assert config.phase_complexities["frontend_dev"] == "L"

    def test_generate_l2_instance(self, tmp_path):
        """Test L2 instance generation."""
        template_path = Path("spec-global/departments/dev/workflows/templates")
        if not template_path.exists():
            pytest.skip("Template path not found")

        generator = WorkflowGenerator(
            template_path=str(template_path / "feature-delivery-l2-template.yaml")
        )

        config = L2InstanceConfig(
            id="instance.dev.test_l2",
            name="Test L2 Instance",
            project="Test",
            module="test",
            repos=[],
        )

        output_path = tmp_path / "test-l2-instance.yaml"
        result = generator.generate_l2_instance(config, str(output_path))

        assert result.success
        assert output_path.exists()
        assert result.generated_workflow is not None
        assert result.generated_workflow["kind"] == "l2_workflow_instance"
        assert len(result.generated_workflow["phases"]) == 7  # 7 phases in canonical template
        phases = {phase["id"]: phase for phase in result.generated_workflow["phases"]}
        assert phases["tech_design"]["l3_template_id"] == "template.dev.tech_design_l3"
        assert phases["contract_design"]["gate_id"] == "gate.dev.contract_freeze_gate"
        assert phases["smoke_gate"]["gate_id"] == "gate.dev.smoke_gate"


class TestL3InstanceGeneration:
    """Tests for L3 instance generation from Points."""

    def test_l3_config_creation(self):
        """Test L3InstanceConfig creation."""
        point = Point(
            id="test-point",
            title="Test",
            desc="Test desc",
            layer="ui",
            estimated_complexity=Complexity.M,
        )
        config = L3InstanceConfig(
            point=point,
            parent_l2_id="l2-123",
            parent_phase_id="frontend_dev",
            repo_id="fe-repo",
        )
        assert config.point.id == "test-point"
        assert config.parent_l2_id == "l2-123"

    def test_generate_l3_instance(self, tmp_path):
        """Test L3 instance generation."""
        template_candidates = [
            Path("lee/spec-global/departments/dev/workflows/templates/l3/task-l3-v3-template.yaml"),
            Path("spec-global/departments/dev/workflows/templates/l3/task-l3-v3-template.yaml"),
            Path("lee/spec-global/departments/dev/workflows/templates/task-l3-template.yaml"),
            Path("spec-global/departments/dev/workflows/templates/task-l3-template.yaml"),
        ]
        template_file = next((candidate for candidate in template_candidates if candidate.exists()), None)
        if template_file is None:
            pytest.skip("L3 template file not found")

        generator = WorkflowGenerator(template_path=str(template_file))

        point = Point(
            id="frontend_dev-p1",
            title="UI Component",
            desc="Build UI component",
            layer="ui",
            estimated_complexity=Complexity.M,
        )

        config = L3InstanceConfig(
            point=point,
            parent_l2_id="l2-test",
            parent_phase_id="frontend_dev",
            repo_id="fe-repo",
        )

        output_path = tmp_path / "test-l3-instance.yaml"
        result = generator.generate_l3_instance(config, str(output_path))

        assert result.success
        assert output_path.exists()
        assert result.generated_workflow is not None
        assert result.generated_workflow["kind"] == "l3_workflow_instance"
        assert result.generated_workflow["point_id"] == "frontend_dev-p1"
        assert len(result.generated_workflow["steps"]) == 6  # 6 steps in L3 template


class TestTaskSplitter:
    """Tests for SimpleTaskSplitter."""

    def test_split_result_creation(self):
        """Test TaskSplitResult creation."""
        points = [
            Point(
                id="p1",
                title="Point 1",
                desc="Desc 1",
                layer="ui",
                estimated_complexity=Complexity.M,
            )
        ]
        result = TaskSplitResult(
            points=points,
            confidence=0.9,
            original_estimate="8h",
            split_estimate="6h",
        )
        assert len(result.points) == 1
        assert result.confidence == 0.9

    def test_splitter_fallback_points(self):
        """Test fallback point generation when parsing fails."""
        splitter = SimpleTaskSplitter(llm_executor=None)
        points = splitter._create_fallback_points("frontend_dev")
        assert len(points) >= 2
        assert points[0].id == "frontend_dev-p1"
        assert points[1].id == "frontend_dev-p2"
        # Check dependency
        assert "frontend_dev-p1" in points[1].depends_on

    def test_splitter_validate_points(self):
        """Test point validation."""
        splitter = SimpleTaskSplitter(llm_executor=None)

        # Create points with circular dependency
        points = [
            Point(
                id="p1",
                title="P1",
                desc="D1",
                layer="ui",
                estimated_complexity=Complexity.M,
                depends_on=["p2"],
            ),
            Point(
                id="p2",
                title="P2",
                desc="D2",
                layer="ui",
                estimated_complexity=Complexity.M,
                depends_on=["p1"],  # Circular
            ),
        ]

        validated = splitter._validate_and_fix_points(points)
        # Circular dependency should be removed
        assert len(validated) == 2


class TestOrchestratorL2Methods:
    """Tests for Orchestrator L2 complexity routing methods."""

    @pytest.fixture
    def store(self, tmp_path):
        """Create a test SQLiteStore."""
        db_path = tmp_path / "test.db"
        return SQLiteStore(db_path=str(db_path))

    @pytest.fixture
    def orchestrator(self, store, tmp_path):
        """Create a test Orchestrator."""
        return Orchestrator(
            store=store,
            project_root=str(tmp_path),
        )

    def test_is_l2_instance(self, orchestrator):
        """Test L2 instance detection."""
        # Create mock instance data
        from lee.orchestrator.storage.models import WorkflowInstance, WorkflowLevel, WorkflowStatus

        l2_data = {"kind": "l2_workflow_instance", "phases": []}
        l2_instance = WorkflowInstance(
            id="l2-test",
            level=WorkflowLevel.DEPARTMENT,
            template_id="template.dev.feature_delivery_l2",
            status=WorkflowStatus.PENDING,
            data=l2_data,
        )

        assert orchestrator._is_l2_instance(l2_instance) is True

        # Non-L2 instance
        regular_data = {"kind": "workflow_instance"}
        regular_instance = WorkflowInstance(
            id="regular-test",
            level=WorkflowLevel.DEPARTMENT,
            template_id="some_template",
            status=WorkflowStatus.PENDING,
            data=regular_data,
        )

        assert orchestrator._is_l2_instance(regular_instance) is False

    def test_get_phase_complexity(self, orchestrator):
        """Test phase complexity retrieval."""
        from lee.orchestrator.storage.models import WorkflowInstance, WorkflowLevel, WorkflowStatus

        data = {
            "kind": "l2_workflow_instance",
            "phases": [
                {"id": "tech_design", "complexity": "S"},
                {"id": "frontend_dev", "complexity": "L"},
            ]
        }
        instance = WorkflowInstance(
            id="l2-test",
            level=WorkflowLevel.DEPARTMENT,
            template_id="template.dev.feature_delivery_l2",
            status=WorkflowStatus.PENDING,
            data=data,
        )

        assert orchestrator._get_phase_complexity(instance, "tech_design") == Complexity.S
        assert orchestrator._get_phase_complexity(instance, "frontend_dev") == Complexity.L
        # Non-existent phase defaults to M
        assert orchestrator._get_phase_complexity(instance, "backend_dev") == Complexity.M

    def test_get_next_pending_phase(self, orchestrator):
        """Test getting next pending phase."""
        from lee.orchestrator.storage.models import WorkflowInstance, WorkflowLevel, WorkflowStatus

        data = {
            "kind": "l2_workflow_instance",
            "phases": [
                {"id": "tech_design", "status": "completed"},
                {"id": "contract_design", "status": "pending"},
                {"id": "backend_dev", "status": "pending"},
            ]
        }
        instance = WorkflowInstance(
            id="l2-test",
            level=WorkflowLevel.DEPARTMENT,
            template_id="template.dev.feature_delivery_l2",
            status=WorkflowStatus.PENDING,
            data=data,
        )

        phase = orchestrator._get_next_pending_phase(instance)
        assert phase is not None
        assert phase["id"] == "contract_design"

    def test_get_repo_id_for_phase(self, orchestrator):
        """Test repo ID selection for phase."""
        repos = [
            {"id": "fe-repo", "type": "frontend"},
            {"id": "be-repo", "type": "backend"},
        ]

        assert orchestrator._get_repo_id_for_phase("frontend_dev", repos) == "fe-repo"
        assert orchestrator._get_repo_id_for_phase("backend_dev", repos) == "be-repo"
        assert orchestrator._get_repo_id_for_phase("api_align", repos) == "be-repo"
        assert orchestrator._get_repo_id_for_phase("tech_design", repos) == "fe-repo"
        assert orchestrator._get_repo_id_for_phase("contract_design", repos) == "be-repo"

    def test_get_layer_for_phase(self, orchestrator):
        """Test layer mapping for phase."""
        assert orchestrator._get_layer_for_phase("frontend_dev") == "ui"
        assert orchestrator._get_layer_for_phase("backend_dev") == "service"
        assert orchestrator._get_layer_for_phase("api_align") == "api"
        assert orchestrator._get_layer_for_phase("tech_design") == "service"
        assert orchestrator._get_layer_for_phase("contract_design") == "api"
        assert orchestrator._get_layer_for_phase("evidence_pack") == "service"

    def test_get_repo_id_for_layer(self, orchestrator):
        """Test repo ID selection for layer."""
        repos = [
            {"id": "fe-repo", "type": "frontend"},
            {"id": "be-repo", "type": "backend"},
        ]

        assert orchestrator._get_repo_id_for_layer("ui", repos) == "fe-repo"
        assert orchestrator._get_repo_id_for_layer("state", repos) == "fe-repo"
        assert orchestrator._get_repo_id_for_layer("api", repos) == "be-repo"
        assert orchestrator._get_repo_id_for_layer("service", repos) == "be-repo"


class TestYamlTemplates:
    """Tests for YAML template files."""

    def test_l2_template_exists(self):
        """Test L2 template file exists."""
        template_path = Path("spec-global/departments/dev/workflows/templates/feature-delivery-l2-template.yaml")
        if not template_path.exists():
            # Try absolute path
            template_path = Path("/Users/zengle/git/ai/lee/spec-global/departments/dev/workflows/templates/feature-delivery-l2-template.yaml")

        assert template_path.exists(), "L2 template file not found"

        # Verify content
        import yaml
        with open(template_path) as f:
            data = yaml.safe_load(f)

        assert data["kind"] == "l2_workflow_template"
        assert "phases" in data
        assert len(data["phases"]) == 7

    def test_l3_template_exists(self):
        """Test L3 template file exists."""
        template_candidates = [
            Path("spec-global/departments/dev/workflows/templates/tech-design-l3-template.yaml"),
            Path("spec-global/departments/dev/workflows/templates/evidence-pack-l3-template.yaml"),
            Path("spec-global/departments/dev/workflows/templates/l3/task-l3-v3-template.yaml"),
            Path("spec-global/departments/dev/workflows/templates/task-l3-template.yaml"),
            Path("spec-global/departments/dev/workflows/templates/feature-fe-l3-template.yaml"),
        ]
        template_path = next((candidate for candidate in template_candidates if candidate.exists()), None)
        if template_path is None:
            pytest.skip("L3 template file not found")

        import yaml
        with open(template_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["kind"] == "l3_workflow_template"
        assert "steps" in data or "stages" in data
        items = data.get("steps") or data.get("stages") or []
        assert len(items) >= 4

    def test_l2_example_instance_exists(self):
        """Test example L2 instance exists."""
        instance_path = Path("spec-global/departments/dev/workflows/instances/l2/feature-timing-v1.yaml")
        if not instance_path.exists():
            pytest.skip("Example L2 instance not found")

        import yaml
        with open(instance_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["kind"] == "l2_workflow_instance"
        assert data["id"] == "instance.dev.feature_timing_v1"
        assert "phases" in data
