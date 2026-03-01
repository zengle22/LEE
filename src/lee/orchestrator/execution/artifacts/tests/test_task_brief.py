"""
Tests for Task Brief - Task Brief 单元测试
"""

import shutil
import tempfile
import yaml
from datetime import datetime
from pathlib import Path

import pytest

from lee.orchestrator.execution.artifacts import (
    ArtifactManager,
    ArtifactType,
    GovernanceKind,
)
from lee.orchestrator.execution.artifacts.task_brief import (
    TaskBrief,
    TaskBriefGenerator,
)


@pytest.fixture
def temp_artifacts_dir():
    """创建临时 artifacts 目录"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def artifact_manager(temp_artifacts_dir):
    """创建 ArtifactManager 实例"""
    manager = ArtifactManager(root_path=temp_artifacts_dir)
    yield manager


@pytest.fixture
def task_brief_generator(artifact_manager):
    """创建 TaskBriefGenerator 实例"""
    return TaskBriefGenerator(artifact_manager)


class TestTaskBrief:
    """测试 TaskBrief 类"""

    def test_task_brief_creation(self):
        """测试 TaskBrief 基本创建"""
        brief = TaskBrief(
            id="TB-001",
            run_id="RUN-001",
            department="backend",
            task_type="feature",
        )

        assert brief.id == "TB-001"
        assert brief.run_id == "RUN-001"
        assert brief.department == "backend"
        assert brief.task_type == "feature"
        assert brief.status == "draft"
        assert brief.created_by == "system"

    def test_task_brief_default_values(self):
        """测试 TaskBrief 默认值"""
        brief = TaskBrief(
            id="TB-002",
            run_id="RUN-002",
            department="frontend",
        )

        assert brief.task_type == "feature"  # 默认值
        assert brief.related_ssot == {}
        assert brief.scope == {}
        assert brief.acceptance == []
        assert brief.risks == []
        assert brief.body_markdown == ""
        assert brief.status == "draft"

    def test_task_brief_auto_created_at(self):
        """测试 created_at 自动创建"""
        brief = TaskBrief(
            id="TB-003",
            run_id="RUN-003",
            department="qa",
        )

        assert brief.created_at is not None
        assert isinstance(brief.created_at, datetime)

    def test_task_brief_to_dict(self):
        """测试 TaskBrief 转换为字典"""
        brief = TaskBrief(
            id="TB-004",
            run_id="RUN-004",
            department="backend",
            task_type="bugfix",
            related_ssot={"prd": "FDPRD-001", "bug_report": "BUG-001"},
            scope={"include": ["Fix bug"], "exclude": ["No refactor"]},
            acceptance=["Tests pass"],
            risks=["Risk 1"],
            body_markdown="## Description\n\nContent",
            status="confirmed",
        )

        result = brief.to_dict()

        assert result["id"] == "TB-004"
        assert result["task_type"] == "bugfix"
        assert result["related_ssot"]["prd"] == "FDPRD-001"
        assert result["scope"]["include"] == ["Fix bug"]
        assert result["acceptance"] == ["Tests pass"]
        assert result["risks"] == ["Risk 1"]
        assert result["status"] == "confirmed"

    def test_task_brief_to_yaml(self):
        """测试 TaskBrief 转换为 YAML"""
        brief = TaskBrief(
            id="TB-005",
            run_id="RUN-005",
            department="backend",
            task_type="feature",
            body_markdown="## Hello\n\nWorld",
        )

        yaml_str = brief.to_yaml()
        data = yaml.safe_load(yaml_str)

        assert data["id"] == "TB-005"
        assert data["body_markdown"] == "## Hello\n\nWorld"


class TestTaskBriefGenerator:
    """测试 TaskBriefGenerator 类"""

    def test_generate_id(self, task_brief_generator):
        """测试 ID 生成"""
        id1 = task_brief_generator.generate_id()
        id2 = task_brief_generator.generate_id()

        assert id1.startswith("TB-")
        assert id2.startswith("TB-")
        assert id1 != id2  # 每次生成应该不同

    def test_create_manual(self, task_brief_generator):
        """测试手动创建 Task Brief"""
        brief = task_brief_generator.create_manual(
            run_id="RUN-001",
            department="backend",
            title="Test Feature",
            description="Test description",
            task_type="feature",
            related_ssot={"prd": "FDPRD-001"},
            scope_include=["Include 1", "Include 2"],
            scope_exclude=["Exclude 1"],
            acceptance=["Accept 1"],
            risks=["Risk 1"],
        )

        assert brief.run_id == "RUN-001"
        assert brief.department == "backend"
        assert brief.task_type == "feature"
        assert brief.related_ssot == {"prd": "FDPRD-001"}
        assert brief.scope["include"] == ["Include 1", "Include 2"]
        assert brief.scope["exclude"] == ["Exclude 1"]
        assert brief.acceptance == ["Accept 1"]
        assert brief.risks == ["Risk 1"]
        assert brief.created_by == "user"

    def test_create_manual_minimal(self, task_brief_generator):
        """测试手动创建 Task Brief (最小参数)"""
        brief = task_brief_generator.create_manual(
            run_id="RUN-002",
            department="frontend",
            title="Minimal Feature",
            description="Minimal description",
        )

        assert brief.related_ssot == {}
        assert brief.scope == {"include": [], "exclude": []}
        assert brief.acceptance == []
        assert brief.risks == []

    def test_save_brief_creates_artifact(self, task_brief_generator, artifact_manager):
        """测试保存 Task Brief 创建 artifact"""
        brief = task_brief_generator.create_manual(
            run_id="RUN-003",
            department="backend",
            title="Test Brief",
            description="Test description",
        )

        artifact = task_brief_generator.save_brief(brief, workflow_id="wf-test")

        assert artifact is not None
        assert artifact.category == "task_brief"
        assert artifact.governance_kind == GovernanceKind.TRANSFER
        assert artifact.run_id == "RUN-003"

        # 验证文件内容
        content_path = artifact_manager.root_path / artifact.path
        assert content_path.exists()

        content = yaml.safe_load(content_path.read_text(encoding="utf-8"))
        assert content["id"] == brief.id
        assert content["title"] == "Test Brief"

    def test_create_and_save(self, task_brief_generator, artifact_manager):
        """测试快捷方法：创建并保存"""
        artifact = task_brief_generator.create_and_save(
            run_id="RUN-004",
            department="qa",
            title="Quick Brief",
            description="Quick description",
            task_type="bugfix",
            related_ssot={"bug_report": "BUG-001"},
        )

        assert artifact is not None
        assert artifact.category == "task_brief"

        # 验证内容
        content_path = artifact_manager.root_path / artifact.path
        content = yaml.safe_load(content_path.read_text(encoding="utf-8"))
        assert content["task_type"] == "bugfix"
        assert content["related_ssot"]["bug_report"] == "BUG-001"


class TestTaskBriefGeneratorFromTaskCard:
    """测试从 Task Card 生成 Task Brief"""

    def test_create_from_task_card(self, task_brief_generator, artifact_manager):
        """测试从 Task Card 创建 Task Brief"""
        # 先创建 Task Card
        task_card = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="task_card",
            content=yaml.dump({
                "title": "Fix Bug",
                "description": "Bug description",
                "related_prd": "FDPRD-001",
                "bug_report": "BUG-001",
            }),
            run_id="RUN-005",
            governance_kind=GovernanceKind.TRANSFER,
            title="Fix Bug",
        )

        # 从 Task Card 生成 Task Brief
        brief = task_brief_generator.create_from_task_card(
            task_card_id=task_card.id,
            run_id="RUN-005",
            department="backend",
            task_type="bugfix",
        )

        assert brief.run_id == "RUN-005"
        assert brief.department == "backend"
        assert brief.task_type == "bugfix"
        assert brief.related_ssot["prd"] == "FDPRD-001"
        assert brief.related_ssot["bug_report"] == "BUG-001"

    def test_create_from_task_card_not_found(self, task_brief_generator):
        """测试从不存在的 Task Card 创建 (应该抛出异常)"""
        with pytest.raises(ValueError, match="Task Card not found"):
            task_brief_generator.create_from_task_card(
                task_card_id="NONEXISTENT-001",
                run_id="RUN-006",
                department="backend",
            )


class TestTaskBriefGeneratorFromPRD:
    """测试从 PRD 生成 Task Brief"""

    def test_create_from_prd(self, task_brief_generator, artifact_manager):
        """测试从 PRD 创建 Task Brief"""
        # 先创建 PRD
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content=yaml.dump({
                "title": "New Feature PRD",
                "description": "PRD description",
                "acceptance_criteria": ["Criterion 1", "Criterion 2"],
            }),
            run_id="RUN-007",
            governance_kind=GovernanceKind.TRANSFER,
            title="New Feature PRD",
        )

        # 从 PRD 生成 Task Brief
        brief = task_brief_generator.create_from_prd(
            prd_id=prd.id,
            run_id="RUN-007",
            department="backend",
            task_type="feature",
        )

        assert brief.run_id == "RUN-007"
        assert brief.department == "backend"
        assert brief.task_type == "feature"
        assert brief.related_ssot["prd"] == prd.id
        assert "PRD description" in brief.body_markdown

    def test_create_from_prd_with_acceptance(self, task_brief_generator, artifact_manager):
        """测试从 PRD 创建 Task Brief 并继承验收标准"""
        # 先创建 PRD
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content=yaml.dump({
                "title": "Feature PRD",
                "description": "Description",
                "acceptance_criteria": ["AC 1", "AC 2", "AC 3"],
            }),
            run_id="RUN-008",
            governance_kind=GovernanceKind.TRANSFER,
        )

        brief = task_brief_generator.create_from_prd(
            prd_id=prd.id,
            run_id="RUN-008",
            department="backend",
        )

        assert brief.acceptance == ["AC 1", "AC 2", "AC 3"]

    def test_create_from_prd_not_found(self, task_brief_generator):
        """测试从不存在的 PRD 创建 (应该抛出异常)"""
        with pytest.raises(ValueError, match="PRD not found"):
            task_brief_generator.create_from_prd(
                prd_id="NONEXISTENT-PRD",
                run_id="RUN-009",
                department="backend",
            )


class TestTaskBriefTaskTypes:
    """测试不同任务类型"""

    def test_task_brief_feature(self, task_brief_generator):
        """测试 feature 类型 Task Brief"""
        brief = task_brief_generator.create_manual(
            run_id="RUN-010",
            department="backend",
            title="New Feature",
            description="Feature description",
            task_type="feature",
        )

        assert brief.task_type == "feature"

    def test_task_brief_bugfix(self, task_brief_generator):
        """测试 bugfix 类型 Task Brief"""
        brief = task_brief_generator.create_manual(
            run_id="RUN-011",
            department="backend",
            title="Bug Fix",
            description="Bug description",
            task_type="bugfix",
        )

        assert brief.task_type == "bugfix"

    def test_task_brief_incident(self, task_brief_generator):
        """测试 incident 类型 Task Brief"""
        brief = task_brief_generator.create_manual(
            run_id="RUN-012",
            department="ops",
            title="Incident Response",
            description="Incident description",
            task_type="incident",
        )

        assert brief.task_type == "incident"

    def test_task_brief_refactor(self, task_brief_generator):
        """测试 refactor 类型 Task Brief"""
        brief = task_brief_generator.create_manual(
            run_id="RUN-013",
            department="backend",
            title="Code Refactor",
            description="Refactor description",
            task_type="refactor",
        )

        assert brief.task_type == "refactor"


class TestTaskBriefStatus:
    """测试 Task Brief 状态"""

    def test_task_brief_draft_status(self, task_brief_generator):
        """测试 draft 状态"""
        brief = task_brief_generator.create_manual(
            run_id="RUN-014",
            department="backend",
            title="Draft Brief",
            description="Draft description",
        )

        assert brief.status == "draft"

    def test_task_brief_status_transitions(self):
        """测试状态流转"""
        brief = TaskBrief(
            id="TB-015",
            run_id="RUN-015",
            department="backend",
            status="draft",
        )

        # draft -> confirmed
        brief.status = "confirmed"
        assert brief.status == "confirmed"

        # confirmed -> completed
        brief.status = "completed"
        assert brief.status == "completed"
