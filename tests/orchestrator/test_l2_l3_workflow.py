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
        assert result.generated_workflow["lifecycle_state"] == "Ready"
        assert [phase["id"] for phase in result.generated_workflow["phases"]] == [
            "tech_design",
            "contract_design",
            "backend_dev",
            "frontend_dev",
            "integration",
            "evidence_pack",
            "smoke_gate",
        ]
        phases = {phase["id"]: phase for phase in result.generated_workflow["phases"]}
        assert phases["tech_design"]["l3_template_id"] == "template.dev.tech_design_l3"
        assert phases["contract_design"]["gate_id"] == "gate.dev.contract_freeze_gate"
        assert phases["smoke_gate"]["gate_id"] == "gate.dev.smoke_gate"
        assert phases["backend_dev"]["depends_on"] == ["contract_design"]
        assert phases["frontend_dev"]["depends_on"] == ["backend_dev"]


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

    def test_derive_l2_lifecycle_state(self, orchestrator):
        """Test canonical L2 lifecycle state derivation."""
        ready = {"phases": [{"id": "tech_design", "status": "pending"}]}
        in_progress = {"phases": [{"id": "tech_design", "status": "running"}]}
        evidence = {
            "phases": [
                {"id": "evidence_pack", "status": "completed"},
                {"id": "smoke_gate", "status": "pending"},
            ]
        }
        closed = {
            "phases": [
                {"id": "evidence_pack", "status": "completed"},
                {"id": "smoke_gate", "status": "completed"},
            ]
        }

        assert orchestrator._derive_l2_lifecycle_state(ready) == "Ready"
        assert orchestrator._derive_l2_lifecycle_state(in_progress) == "In Progress"
        assert orchestrator._derive_l2_lifecycle_state(evidence) == "Evidence Pack Produced"
        assert orchestrator._derive_l2_lifecycle_state(closed) == "Closed"

    def test_extract_l3_handoff_refs_collects_contract_outputs(self, orchestrator):
        """Test runtime handoff extraction preserves canonical contract refs for downstream phases."""
        instance_data = {
            "step_outputs": {
                "api_contract_design": {"api_contract_ref": "CONTRACT-API-001"},
                "data_contract_design": {"data_contract_ref": "CONTRACT-DATA-001"},
                "event_contract_design": {"event_contract_ref": "CONTRACT-EVENT-001"},
                "contract_self_review": {"contract_review_ref": "REPORT-REVIEW-001"},
                "contract_freeze": {
                    "contract_freeze_ref": "CONTRACT-FREEZE-001",
                    "contract_hash": "sha256:test",
                },
            }
        }

        refs = orchestrator._extract_l3_handoff_refs(instance_data)

        assert refs == {
            "api_contract_ref": "CONTRACT-API-001",
            "data_contract_ref": "CONTRACT-DATA-001",
            "event_contract_ref": "CONTRACT-EVENT-001",
            "contract_review_ref": "REPORT-REVIEW-001",
            "contract_freeze_ref": "CONTRACT-FREEZE-001",
            "contract_hash": "sha256:test",
        }


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
            Path("spec-global/departments/dev/workflows/templates/bugfix-triage-l3-template.yaml"),
            Path("spec-global/departments/dev/workflows/templates/bugfix-root-cause-l3-template.yaml"),
            Path("spec-global/departments/dev/workflows/templates/bugfix-fix-design-l3-template.yaml"),
            Path("spec-global/departments/dev/workflows/templates/bugfix-fix-impl-l3-template.yaml"),
            Path("spec-global/departments/dev/workflows/templates/bugfix-verification-l3-template.yaml"),
            Path("spec-global/departments/dev/workflows/templates/bugfix-evidence-pack-l3-template.yaml"),
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

    def test_feature_delivery_template_contract_and_evidence_hooks(self):
        """Test canonical L2 template declares required input contract and evidence closure."""
        import yaml

        template_path = Path("spec-global/departments/dev/workflows/templates/feature-delivery-l2-template.yaml")
        if not template_path.exists():
            pytest.skip("Feature delivery L2 template not found")

        with open(template_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["shared_input_contract"]["required_fields"] == [
            "formal_ssot_id",
            "source_refs",
            "governing_adrs",
            "repo_context",
        ]
        assert data["status_hooks"]["states"] == [
            "Ready",
            "In Progress",
            "Evidence Pack Produced",
            "Closed",
        ]
        evidence_handoff = next(
            handoff for handoff in data["phase_data_flow"]["handoffs"]
            if handoff["from"] == "evidence_pack"
        )
        assert evidence_handoff["to"] == "smoke_gate"
        assert evidence_handoff["outputs"] == ["evidence_pack_ref"]

    def test_bugfix_delivery_template_exists_and_structure(self):
        """Test canonical bugfix L2 template exists and declares required structure."""
        import yaml

        template_path = Path("spec-global/departments/dev/workflows/templates/bugfix-delivery-l2-template.yaml")
        if not template_path.exists():
            pytest.skip("Bugfix delivery L2 template not found")

        with open(template_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["kind"] == "l2_workflow_template"
        assert data["id"] == "template.dev.bugfix_delivery_l2"
        assert [phase["id"] for phase in data["phases"]] == [
            "triage",
            "root_cause",
            "fix_design",
            "fix_implementation",
            "verification",
            "evidence_pack",
            "merge_or_reject",
        ]
        assert data["shared_input_contract"]["required_fields"] == [
            "bug_ssot_id",
            "severity",
            "reproduction_evidence",
        ]
        assert data["granularity_control"]["default_mode"] == "single_bug"

    def test_bugfix_l3_templates_exist_and_bind_agents(self):
        """Test canonical bugfix L3 template family exists and binds to active agents/gates."""
        import yaml

        expected = {
            "bugfix-triage-l3-template.yaml": ("template.dev.bugfix_triage_l3", "agent.dev.bug_triage"),
            "bugfix-root-cause-l3-template.yaml": ("template.dev.bugfix_root_cause_l3", "agent.dev.bug_root_cause_analyst"),
            "bugfix-fix-design-l3-template.yaml": ("template.dev.bugfix_fix_design_l3", "agent.dev.bug_fix_planner"),
            "bugfix-fix-impl-l3-template.yaml": ("template.dev.bugfix_fix_impl_l3", "agent.dev.bug_fix_implementer"),
            "bugfix-verification-l3-template.yaml": ("template.dev.bugfix_verification_l3", "agent.dev.bug_fix_verifier"),
            "bugfix-evidence-pack-l3-template.yaml": ("template.dev.bugfix_evidence_pack_l3", "agent.dev.bug_fix_verifier"),
        }

        for filename, (template_id, agent_id) in expected.items():
            path = Path("spec-global/departments/dev/workflows/templates") / filename
            assert path.exists(), f"{filename} not found"
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert data["id"] == template_id
            steps = data["steps"]
            assert len(steps) >= 4
            assert any(step.get("agent_id") == agent_id for step in steps)

    def test_evidence_pack_l3_templates_align_with_evidence_contract(self):
        """Test feature and bugfix evidence pack L3 templates reference the canonical evidence contract."""
        import yaml

        feature_path = Path("spec-global/departments/dev/workflows/templates/evidence-pack-l3-template.yaml")
        bugfix_path = Path("spec-global/departments/dev/workflows/templates/bugfix-evidence-pack-l3-template.yaml")

        for path in (feature_path, bugfix_path):
            with open(path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            assert data["contracts"]["input_schema"] == "../../contracts/evidence-pack/v1/schema.json"
            assert data["contracts"]["integration_spec"] == "../../contracts/evidence-pack/v1/integration-spec.md"

        with open(feature_path, encoding="utf-8") as f:
            feature_data = yaml.safe_load(f)
        assert "integration_outputs" in feature_data["instance_schema"]["required_fields"]
        assert "verification_results" in feature_data["instance_schema"]["required_fields"]
        assert "smoke_gate_inputs" in feature_data["instance_schema"]["output_fields"]

        with open(bugfix_path, encoding="utf-8") as f:
            bugfix_data = yaml.safe_load(f)
        assert "bug_ssot_id" in bugfix_data["instance_schema"]["required_fields"]
        assert "verification_results" in bugfix_data["instance_schema"]["required_fields"]
        assert "merge_or_reject_input" in bugfix_data["instance_schema"]["output_fields"]

    def test_contract_design_stage_definition_covers_three_contract_families(self):
        """Test contract design stage definition locks canonical inputs, outputs, and handoff rules."""
        definition_path = Path("spec/workflow/definitions/contract-design-stage-definition.md")
        if not definition_path.exists():
            pytest.skip("Contract design stage definition not found")

        content = definition_path.read_text(encoding="utf-8")

        assert "State: frozen" in content
        assert "`tech_spec_ref`" in content
        assert "api_contract_design" in content
        assert "data_contract_design" in content
        assert "event_contract_design" in content
        assert "`contract_freeze_ref`" in content
        assert "Backend implementation consumes" in content
        assert "Frontend implementation consumes" in content

    def test_feature_contract_l3_template_covers_api_data_event_and_freeze(self):
        """Test canonical feature contract template binds the three contract families and freeze handoff."""
        import yaml

        template_path = Path("spec-global/departments/dev/workflows/templates/feature-contract-l3-template.yaml")
        if not template_path.exists():
            pytest.skip("Feature contract L3 template not found")

        with open(template_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)

        assert data["id"] == "template.dev.feature_contract_l3"
        assert data["contracts"]["stage_definition"] == "../../../../../spec/workflow/definitions/contract-design-stage-definition.md"
        assert data["contracts"]["freeze_gate"] == "../../gates/contract-freeze-gate/v1/gate.yaml"
        assert [step["id"] for step in data["steps"]] == [
            "api_contract_design",
            "data_contract_design",
            "event_contract_design",
            "contract_self_review",
            "contract_freeze",
        ]
        assert data["instance_schema"]["required_fields"][-1] == "tech_spec_ref"
        assert data["handoff_rules"]["backend_dev"]["required_inputs"] == [
            "tech_spec_ref",
            "contract_freeze_ref",
            "contract_hash",
        ]

    def test_contract_design_testset_tracks_acceptance_coverage(self):
        """Test Contract Design TestSet formalizes all acceptance checks for the stage."""
        testset_path = Path("spec/testing/testsets/TESTSET-FEAT-SRC-009-005-001__contract-design-stage-testset.md")
        if not testset_path.exists():
            pytest.skip("Contract design TestSet not found")

        content = testset_path.read_text(encoding="utf-8")

        assert "id: TESTSET-FEAT-SRC-009-005-001" in content
        assert "status: frozen" in content
        assert "TC-CD-001" in content
        assert "TC-CD-002" in content
        assert "TC-CD-003" in content
        assert "TC-CD-004" in content
        assert "template.dev.feature_contract_l3" in content

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
