"""
Tests for Workflow Instance modules (Plan Agent, Instance Generator, Workflow Runner)
"""

import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch
import yaml
import asyncio


class TestPlanAgent:
    """Tests for PlanAgent"""

    def test_plan_config_defaults(self):
        """Test PlanConfig default values"""
        from lee.orchestrator.execution.plan_agent import PlanConfig

        config = PlanConfig()
        assert config.mode == "suggest"
        assert config.skip_conditions == []
        assert config.review_criteria == []

    def test_plan_config_custom(self):
        """Test PlanConfig with custom values"""
        from lee.orchestrator.execution.plan_agent import PlanConfig

        config = PlanConfig(
            mode="force",
            skip_conditions=["steps.length <= 3"],
            review_criteria=["complexity == high"]
        )
        assert config.mode == "force"
        assert len(config.skip_conditions) == 1

    def test_plan_result_creation(self):
        """Test PlanResult creation"""
        from lee.orchestrator.execution.plan_agent import PlanResult

        instance = {"id": "wf_test", "status": "pending"}
        result = PlanResult(instance=instance, summary="# Test Plan")
        assert result.success is True
        assert result.version == 1
        assert result.error is None


class TestPlanAgentTemplateAnalysis:
    """Tests for template analysis"""

    def test_analyze_simple_template(self):
        """Test analysis of simple template"""
        from lee.orchestrator.execution.plan_agent import PlanAgent

        agent = PlanAgent()
        template = {
            "id": "test-workflow",
            "version": "1.0",
            "steps": [
                {"id": "step1", "name": "Step 1"},
                {"id": "step2", "name": "Step 2"},
                {"id": "step3", "name": "Step 3"},
            ]
        }

        analysis = agent._analyze_template(template)
        assert analysis["step_count"] == 3
        assert analysis["gate_count"] == 0

    def test_analyze_complex_template(self):
        """Test analysis of complex template with agents and gates"""
        from lee.orchestrator.execution.plan_agent import PlanAgent

        agent = PlanAgent()
        template = {
            "id": "complex-workflow",
            "version": "1.0",
            "steps": [
                {"id": "step1", "kind": "agent", "agent_id": "agent1"},
                {"id": "step2", "kind": "skill", "skill_id": "skill1"},
                {"id": "step3", "kind": "agent", "agent_id": "agent2"},
                {"id": "step4", "kind": "agent", "agent_id": "agent3"},
                {"id": "step5", "kind": "agent", "agent_id": "agent4"},
                {"id": "step6", "kind": "agent", "agent_id": "agent5"},
                {"id": "step7", "kind": "agent", "agent_id": "agent6"},
                {"id": "step8", "kind": "agent", "agent_id": "agent7"},
            ],
            "human_in_the_loop": [
                {"id": "gate1", "type": "approval"}
            ]
        }

        analysis = agent._analyze_template(template)
        assert analysis["step_count"] == 8
        assert analysis["agent_count"] == 7
        assert analysis["skill_count"] == 1
        assert analysis["gate_count"] == 1


class TestInstanceGenerator:
    """Tests for InstanceGenerator"""

    def test_instance_generator_init(self):
        """Test InstanceGenerator initialization"""
        from lee.orchestrator.core.instance_generator import InstanceGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = InstanceGenerator(Path(tmpdir))
            assert generator.workspace_root == Path(tmpdir)
            expected_dir = Path(tmpdir) / ".workflow" / "instances"
            assert generator.instances_dir == expected_dir

    def test_get_next_version_new(self):
        """Test version number for new workflow"""
        from lee.orchestrator.core.instance_generator import InstanceGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = InstanceGenerator(Path(tmpdir))
            version = generator._get_next_version("wf_test", "l2")
            assert version == 1

    def test_get_next_version_existing(self):
        """Test version number with existing files"""
        from lee.orchestrator.core.instance_generator import InstanceGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create existing version file
            instances_dir = Path(tmpdir) / ".workflow" / "instances" / "l2"
            instances_dir.mkdir(parents=True)
            (instances_dir / "wf_test-v1.yaml").write_text("version: 1")

            generator = InstanceGenerator(Path(tmpdir))
            version = generator._get_next_version("wf_test", "l2")
            assert version == 2

    def test_build_instance(self):
        """Test building instance data"""
        from lee.orchestrator.core.instance_generator import InstanceGenerator, InstanceMetadata
        from lee.orchestrator.execution.plan_agent import PlanResult

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_result = PlanResult(
                instance={"id": "wf_test", "template_ref": "test-template"},
                summary="# Test"
            )

            generator = InstanceGenerator(Path(tmpdir))
            instance = generator._build_instance(plan_result, "phase1", 1)

            assert instance["id"] == "wf_test"
            assert instance["phase_id"] == "phase1"
            assert instance["version"] == 1
            assert instance["status"] == "pending"

    def test_save_and_load_instance(self):
        """Test saving and loading instance"""
        from lee.orchestrator.core.instance_generator import InstanceGenerator
        from lee.orchestrator.execution.plan_agent import PlanResult

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_result = PlanResult(
                instance={
                    "id": "wf_save_test",
                    "template_ref": "test-template",
                    "template_version": "1.0",
                    "status": "pending",
                    "steps": []
                },
                summary="# Test"
            )

            generator = InstanceGenerator(Path(tmpdir))
            metadata = generator.generate(plan_result, "phase1", "l2")

            assert metadata.workflow_id == "wf_save_test"
            assert metadata.version == 1

            # Load it back
            loaded = generator.load_latest("wf_save_test", "l2")
            assert loaded is not None
            assert loaded["id"] == "wf_save_test"


class TestWorkflowRunner:
    """Tests for WorkflowRunner"""

    def test_workflow_run_config(self):
        """Test WorkflowRunConfig"""
        from lee.orchestrator.execution.workflow_runner import WorkflowRunConfig

        config = WorkflowRunConfig(
            workflow_key="test-workflow",
            template_path=Path("templates/test.yaml"),
            params={"phase_id": "p1"},
            project_root=Path(".")
        )
        assert config.workflow_key == "test-workflow"
        assert config.plan_mode == "simple"
        assert config.skip_plan is False

    def test_workflow_run_config_custom(self):
        """Test WorkflowRunConfig with custom values"""
        from lee.orchestrator.execution.workflow_runner import WorkflowRunConfig

        config = WorkflowRunConfig(
            workflow_key="test-workflow",
            template_path=Path("templates/test.yaml"),
            params={"phase_id": "p1"},
            project_root=Path("."),
            plan_mode="force",
            skip_plan=True,
            instance_id="wf_123"
        )
        assert config.plan_mode == "force"
        assert config.skip_plan is True
        assert config.instance_id == "wf_123"


class TestIntegration:
    """Integration tests"""

    def test_plan_to_instance_flow(self):
        """Test full Plan -> Instance flow"""
        from lee.orchestrator.execution.plan_agent import PlanAgent, PlanConfig
        from lee.orchestrator.core.instance_generator import InstanceGenerator

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a simple template
            template = {
                "id": "test-template",
                "version": "1.0",
                "name": "Test Workflow",
                "steps": [
                    {"id": "step1", "name": "Step 1"},
                    {"id": "step2", "name": "Step 2"},
                ]
            }

            # Run plan (without LLM for testing)
            agent = PlanAgent(llm_executor=None)
            import asyncio
            result = asyncio.run(
                agent.plan(template, {"phase_id": "test"}, PlanConfig(mode="simple"))
            )

            assert result.success is True
            assert result.instance is not None
            assert "steps" in result.instance

            # Generate instance
            generator = InstanceGenerator(Path(tmpdir))
            metadata = generator.generate(result, "test", "l2")

            assert metadata.version == 1

            # Load and verify
            loaded = generator.load_latest(metadata.workflow_id, "l2")
            assert loaded is not None
            assert len(loaded["steps"]) == 2


class TestReviewGate:
    """Tests for ReviewGate"""

    def test_review_gate_simple_auto_skip(self):
        """Test simple mode auto-skip for small workflows"""
        from lee.orchestrator.execution.review_gate import ReviewGate, ReviewMode
        from lee.orchestrator.execution.plan_agent import PlanResult

        gate = ReviewGate(auto_approve=True)

        # Simple template with <= 3 steps
        plan_result = PlanResult(
            instance={
                "id": "wf_test",
                "plan": {"mode": "simple", "needs_review": False},
                "steps": [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}]
            },
            summary="# Test"
        )

        import asyncio
        decision = asyncio.run(
            gate.check(plan_result, "simple")
        )

        assert decision.approved is True
        assert decision.mode == ReviewMode.SIMPLE

    def test_review_gate_force(self):
        """Test force mode always needs approval"""
        from lee.orchestrator.execution.review_gate import ReviewGate, ReviewMode
        from lee.orchestrator.execution.plan_agent import PlanResult

        gate = ReviewGate(auto_approve=True)

        plan_result = PlanResult(
            instance={
                "id": "wf_test",
                "plan": {"mode": "force", "needs_review": True},
                "steps": [{"id": "s1"}]
            },
            summary="# Test"
        )

        import asyncio
        decision = asyncio.run(
            gate.check(plan_result, "force")
        )

        # auto_approve=True means it passes
        assert decision.approved is True
        assert decision.mode == ReviewMode.FORCE


class TestInstanceLoader:
    """Tests for InstanceLoaderMixin"""

    def test_is_instance_path(self):
        """Test path detection"""
        from lee.orchestrator.execution.instance_loader import InstanceLoaderMixin

        class TestLoader(InstanceLoaderMixin):
            pass

        loader = TestLoader()

        # Test instance path detection
        assert loader._is_instance_path(".workflow/instances/l2/wf_test-v1.yaml") is True
        assert loader._is_instance_path("wf_test-v1.yaml") is True
        assert loader._is_instance_path("wf_test-v10.yaml") is True
        assert loader._is_instance_path("templates/my-template.yaml") is False

    def test_get_steps_from_instance(self):
        """Test extracting steps from instance"""
        from lee.orchestrator.execution.instance_loader import InstanceLoaderMixin

        class TestLoader(InstanceLoaderMixin):
            pass

        loader = TestLoader()

        instance = {
            "kind": "workflow-instance",
            "steps": [
                {"id": "step1", "name": "Step 1", "kind": "agent", "agent_id": "agent1"},
                {"id": "step2", "name": "Step 2", "kind": "skill", "skill_id": "skill1"},
            ]
        }

        steps = loader._get_steps_from_instance(instance)

        assert len(steps) == 2
        assert steps[0].id == "step1"
        assert steps[0].agent_id == "agent1"
        assert steps[1].skill_id == "skill1"

    def test_get_instance_config(self):
        """Test extracting config from instance"""
        from lee.orchestrator.execution.instance_loader import InstanceLoaderMixin

        class TestLoader(InstanceLoaderMixin):
            pass

        loader = TestLoader()

        instance = {
            "kind": "workflow-instance",
            "instance_config": {
                "success_criteria": {"simple": ["all_done"]},
                "retry": {"enabled": True}
            }
        }

        config = loader._get_instance_config(instance)

        assert "success_criteria" in config
        assert config["retry"]["enabled"] is True

    def test_get_plan_info(self):
        """Test extracting plan info from instance"""
        from lee.orchestrator.execution.instance_loader import InstanceLoaderMixin

        class TestLoader(InstanceLoaderMixin):
            pass

        loader = TestLoader()

        instance = {
            "kind": "workflow-instance",
            "plan": {
                "mode": "force",
                "complexity": "high",
                "needs_review": True
            }
        }

        plan = loader._get_plan_info(instance)

        assert plan["mode"] == "force"
        assert plan["needs_review"] is True


class TestContractScenarios:
    """Test contract scenarios - T1, T2, T3"""

    def test_t1_1_simple_template(self):
        """T1.1: Simple template generates Instance with simple mode"""
        from lee.orchestrator.execution.plan_agent import PlanAgent, PlanConfig

        agent = PlanAgent(llm_executor=None)

        template = {
            "id": "simple-workflow",
            "version": "1.0",
            "name": "Simple Workflow",
            "steps": [
                {"id": "step1", "name": "Step 1"},
                {"id": "step2", "name": "Step 2"},
                {"id": "step3", "name": "Step 3"},
            ]
        }

        import asyncio
        result = asyncio.run(
            agent.plan(template, {"phase_id": "test"}, PlanConfig(mode="simple"))
        )

        assert result.success is True
        # Simple mode with <=3 steps should skip LLM
        assert result.instance["plan"]["mode"] == "simple"

    def test_t1_2_complex_template(self):
        """T1.2: Complex template generates Instance with Summary"""
        from lee.orchestrator.execution.plan_agent import PlanAgent, PlanConfig

        agent = PlanAgent(llm_executor=None)

        # 13 step template - complex enough to not skip
        template = {
            "id": "complex-workflow",
            "version": "1.0",
            "name": "Complex Workflow",
            "steps": [
                {"id": f"step{i}", "name": f"Step {i}", "kind": "agent", "agent_id": f"agent{i}"}
                for i in range(1, 14)
            ],
            "human_in_the_loop": [
                {"id": "gate1", "type": "approval"}
            ]
        }

        import asyncio
        # Use force mode to ensure LLM is called
        result = asyncio.run(
            agent.plan(template, {"phase_id": "test"}, PlanConfig(mode="force"))
        )

        assert result.success is True
        assert result.summary is not None
        assert "Complex Workflow" in result.summary
        # With force mode, should have full plan info
        assert "plan" in result.instance

    def test_t2_1_generate_instance(self):
        """T2.1: Generate Instance from Plan result"""
        from lee.orchestrator.core.instance_generator import InstanceGenerator
        from lee.orchestrator.execution.plan_agent import PlanResult

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_result = PlanResult(
                instance={
                    "id": "wf_test",
                    "template_ref": "test-template",
                    "template_version": "1.0",
                    "status": "pending",
                    "plan": {"mode": "simple"},
                    "steps": [{"id": "s1"}]
                },
                summary="# Test"
            )

            generator = InstanceGenerator(Path(tmpdir))
            metadata = generator.generate(plan_result, "phase1", "l2")

            assert metadata.version == 1
            assert (Path(tmpdir) / ".workflow" / "instances" / "l2" / "wf_test-v1.yaml").exists()

    def test_t2_2_replan_version_increment(self):
        """T2.2: Re-plan creates v2.yaml"""
        from lee.orchestrator.core.instance_generator import InstanceGenerator
        from lee.orchestrator.execution.plan_agent import PlanResult

        with tempfile.TemporaryDirectory() as tmpdir:
            # Create v1
            plan_result_v1 = PlanResult(
                instance={
                    "id": "wf_replan",
                    "template_ref": "test-template",
                    "template_version": "1.0",
                    "status": "pending",
                    "steps": [{"id": "s1"}]
                },
                summary="# V1"
            )

            generator = InstanceGenerator(Path(tmpdir))
            metadata_v1 = generator.generate(plan_result_v1, "phase1", "l2")
            assert metadata_v1.version == 1

            # Create v2 (re-plan)
            plan_result_v2 = PlanResult(
                instance={
                    "id": "wf_replan",
                    "template_ref": "test-template",
                    "template_version": "1.0",
                    "status": "pending",
                    "steps": [{"id": "s1"}, {"id": "s2"}]
                },
                summary="# V2"
            )

            metadata_v2 = generator.generate(plan_result_v2, "phase1", "l2")
            assert metadata_v2.version == 2

            # Verify v2 loads correctly
            latest = generator.load_latest("wf_replan", "l2")
            assert latest["version"] == 2
            assert len(latest["steps"]) == 2

    def test_t2_3_load_latest_version(self):
        """T2.3: Load latest version correctly"""
        from lee.orchestrator.core.instance_generator import InstanceGenerator
        from lee.orchestrator.execution.plan_agent import PlanResult

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = InstanceGenerator(Path(tmpdir))

            # Create multiple versions
            for v in [1, 2, 3]:
                plan_result = PlanResult(
                    instance={
                        "id": "wf_multi",
                        "template_ref": "test",
                        "version": v,
                        "status": "pending",
                        "steps": [{"id": f"s{v}"}]
                    },
                    summary=f"# V{v}"
                )
                generator.generate(plan_result, "phase1", "l2")

            # Load latest should return v3
            latest = generator.load_latest("wf_multi", "l2")
            assert latest["version"] == 3

            # Load specific version
            v1 = generator.load_version("wf_multi", 1, "l2")
            assert v1["version"] == 1

    def test_t3_1_simple_auto_skip(self):
        """T3.1: simple mode auto-skips when conditions met"""
        from lee.orchestrator.execution.review_gate import ReviewGate
        from lee.orchestrator.execution.plan_agent import PlanResult

        gate = ReviewGate(auto_approve=True)

        # 3 steps - meets skip condition
        plan_result = PlanResult(
            instance={
                "plan": {"mode": "simple", "needs_review": False},
                "steps": [{"id": "s1"}, {"id": "s2"}, {"id": "s3"}]
            },
            summary="# Test"
        )

        import asyncio
        decision = asyncio.run(
            gate.check(plan_result, "simple")
        )

        assert decision.approved is True

    def test_t3_2_suggest_llm_judgment(self):
        """T3.2: suggest mode triggers based on LLM judgment"""
        from lee.orchestrator.execution.review_gate import ReviewGate
        from lee.orchestrator.execution.plan_agent import PlanResult

        gate = ReviewGate(auto_approve=True)

        # LLM says needs review
        plan_result = PlanResult(
            instance={
                "plan": {"mode": "suggest", "needs_review": True},
                "steps": [{"id": "s1"}]
            },
            summary="# Test"
        )

        import asyncio
        decision = asyncio.run(
            gate.check(plan_result, "suggest")
        )

        # With auto_approve=True, it approves
        assert decision.approved is True

    def test_t3_3_force_always_requires(self):
        """T3.3: force mode always triggers gate"""
        from lee.orchestrator.execution.review_gate import ReviewGate
        from lee.orchestrator.execution.plan_agent import PlanResult

        gate = ReviewGate(auto_approve=True)

        plan_result = PlanResult(
            instance={
                "plan": {"mode": "force"},
                "steps": [{"id": "s1"}]
            },
            summary="# Test"
        )

        import asyncio
        decision = asyncio.run(
            gate.check(plan_result, "force")
        )

        assert decision.approved is True  # auto_approve


class TestRetrySideEffects:
    """T5: Retry side effects tests"""

    def test_retry_config_in_instance(self):
        """T5.1: Retry config is stored in instance"""
        from lee.orchestrator.execution.plan_agent import PlanAgent, PlanConfig

        agent = PlanAgent(llm_executor=None)

        template = {
            "id": "test",
            "version": "1.0",
            "steps": [{"id": "s1"}]
        }

        import asyncio
        result = asyncio.run(
            agent.plan(template, {"phase_id": "test"}, PlanConfig(mode="simple"))
        )

        retry_config = result.instance.get("instance_config", {}).get("retry", {})

        assert "enabled" in retry_config
        assert "max_attempts" in retry_config
        assert retry_config["enabled"] is True

    def test_instance_status_update(self):
        """Test instance status can be updated"""
        from lee.orchestrator.core.instance_generator import InstanceGenerator
        from lee.orchestrator.execution.plan_agent import PlanResult

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_result = PlanResult(
                instance={
                    "id": "wf_status",
                    "template_ref": "test",
                    "template_version": "1.0",
                    "status": "pending",
                    "steps": [{"id": "s1"}]
                },
                summary="# Test"
            )

            generator = InstanceGenerator(Path(tmpdir))
            generator.generate(plan_result, "phase1", "l2")

            # Update status
            success = generator.update_status("wf_status", "running", "l2")
            assert success is True

            # Verify status updated
            instance = generator.load_latest("wf_status", "l2")
            assert instance["status"] == "running"

    def test_step_status_update(self):
        """Test step status can be updated"""
        from lee.orchestrator.core.instance_generator import InstanceGenerator
        from lee.orchestrator.execution.plan_agent import PlanResult

        with tempfile.TemporaryDirectory() as tmpdir:
            plan_result = PlanResult(
                instance={
                    "id": "wf_step",
                    "template_ref": "test",
                    "template_version": "1.0",
                    "status": "pending",
                    "steps": [
                        {"id": "s1", "status": "pending"},
                        {"id": "s2", "status": "pending"}
                    ]
                },
                summary="# Test"
            )

            generator = InstanceGenerator(Path(tmpdir))
            generator.generate(plan_result, "phase1", "l2")

            # Update step status
            success = generator.update_step_status("wf_step", "s1", "completed", {"result": "ok"})
            assert success is True

            # Verify step status updated
            instance = generator.load_latest("wf_step", "l2")
            s1 = next((s for s in instance["steps"] if s["id"] == "s1"), None)
            assert s1["status"] == "completed"
            assert s1["output"]["result"] == "ok"
