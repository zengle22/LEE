"""
Unit tests for WorkflowTemplate.get_step_order() and get_steps_after()

Gate Improvement v1.1 - Phase 1
"""

import pytest
from lee.orchestrator.execution.template_manager import WorkflowTemplate
from lee.orchestrator.storage.models import Step, WorkflowLevel


class TestStepOrder:
    """测试步骤执行顺序计算"""

    def test_linear_workflow(self):
        """测试线性工作流的步骤顺序"""
        template = WorkflowTemplate(
            id="test_linear",
            level=WorkflowLevel.TASK,
            name="Linear Workflow",
            description="Test linear workflow",
            steps=[
                Step(id="s1", name="Step 1", kind="task", depends_on=[]),
                Step(id="s2", name="Step 2", kind="task", depends_on=["s1"]),
                Step(id="s3", name="Step 3", kind="task", depends_on=["s2"]),
            ],
        )

        order = template.get_step_order()
        assert order == ["s1", "s2", "s3"]

    def test_parallel_branches(self):
        """测试并行分支工作流的步骤顺序"""
        template = WorkflowTemplate(
            id="test_parallel",
            level=WorkflowLevel.TASK,
            name="Parallel Workflow",
            description="Test parallel workflow",
            steps=[
                Step(id="s1", name="Step 1", kind="task", depends_on=[]),
                Step(id="s2a", name="Step 2A", kind="task", depends_on=["s1"]),
                Step(id="s2b", name="Step 2B", kind="task", depends_on=["s1"]),
                Step(id="s3", name="Step 3", kind="task", depends_on=["s2a", "s2b"]),
            ],
        )

        order = template.get_step_order()
        # s1 必须在第一个
        assert order[0] == "s1"
        # s3 必须在最后一个
        assert order[-1] == "s3"
        # s2a 和 s2b 在中间（顺序不确定）
        assert set(order[1:3]) == {"s2a", "s2b"}

    def test_complex_dag(self):
        """测试复杂 DAG 工作流"""
        template = WorkflowTemplate(
            id="test_dag",
            level=WorkflowLevel.TASK,
            name="DAG Workflow",
            description="Test DAG workflow",
            steps=[
                Step(id="s1", name="Step 1", kind="task", depends_on=[]),
                Step(id="s2a", name="Step 2A", kind="task", depends_on=["s1"]),
                Step(id="s2b", name="Step 2B", kind="task", depends_on=["s1"]),
                Step(id="s3a", name="Step 3A", kind="task", depends_on=["s2a"]),
                Step(id="s3b", name="Step 3B", kind="task", depends_on=["s2b"]),
                Step(id="s4", name="Step 4", kind="task", depends_on=["s3a", "s3b"]),
            ],
        )

        order = template.get_step_order()
        # 验证依赖关系
        assert order[0] == "s1"
        assert order[-1] == "s4"
        # s2a 必须在 s3a 之前
        assert order.index("s2a") < order.index("s3a")
        # s2b 必须在 s3b 之前
        assert order.index("s2b") < order.index("s3b")

    def test_circular_dependency_detection(self):
        """测试循环依赖检测"""
        template = WorkflowTemplate(
            id="test_circular",
            level=WorkflowLevel.TASK,
            name="Circular Workflow",
            description="Test circular dependency",
            steps=[
                Step(id="s1", name="Step 1", kind="task", depends_on=["s3"]),
                Step(id="s2", name="Step 2", kind="task", depends_on=["s1"]),
                Step(id="s3", name="Step 3", kind="task", depends_on=["s2"]),
            ],
        )

        with pytest.raises(ValueError) as exc_info:
            template.get_step_order()

        assert "Circular dependency" in str(exc_info.value)
        assert "s1" in str(exc_info.value) or "s2" in str(exc_info.value) or "s3" in str(exc_info.value)

    def test_self_dependency(self):
        """测试自依赖检测"""
        template = WorkflowTemplate(
            id="test_self",
            level=WorkflowLevel.TASK,
            name="Self Dependency",
            description="Test self dependency",
            steps=[
                Step(id="s1", name="Step 1", kind="task", depends_on=["s1"]),
            ],
        )

        with pytest.raises(ValueError) as exc_info:
            template.get_step_order()

        assert "Circular dependency" in str(exc_info.value)


class TestGetStepsAfter:
    """测试 get_steps_after 方法"""

    def test_get_steps_after_linear(self):
        """测试线性工作流中获取后续步骤"""
        template = WorkflowTemplate(
            id="test_after",
            level=WorkflowLevel.TASK,
            name="After Test",
            description="Test get_steps_after",
            steps=[
                Step(id="s1", name="Step 1", kind="task", depends_on=[]),
                Step(id="s2", name="Step 2", kind="task", depends_on=["s1"]),
                Step(id="s3", name="Step 3", kind="task", depends_on=["s2"]),
                Step(id="s4", name="Step 4", kind="task", depends_on=["s3"]),
            ],
        )

        # 获取 s1 之后的步骤
        steps_after_s1 = template.get_steps_after("s1")
        assert steps_after_s1 == ["s2", "s3", "s4"]

        # 获取 s2 之后的步骤
        steps_after_s2 = template.get_steps_after("s2")
        assert steps_after_s2 == ["s3", "s4"]

        # 获取 s3 之后的步骤
        steps_after_s3 = template.get_steps_after("s3")
        assert steps_after_s3 == ["s4"]

        # 获取 s4 之后的步骤（空列表）
        steps_after_s4 = template.get_steps_after("s4")
        assert steps_after_s4 == []

    def test_get_steps_after_parallel(self):
        """测试并行工作流中获取后续步骤"""
        template = WorkflowTemplate(
            id="test_after_parallel",
            level=WorkflowLevel.TASK,
            name="After Parallel Test",
            description="Test get_steps_after with parallel",
            steps=[
                Step(id="s1", name="Step 1", kind="task", depends_on=[]),
                Step(id="s2a", name="Step 2A", kind="task", depends_on=["s1"]),
                Step(id="s2b", name="Step 2B", kind="task", depends_on=["s1"]),
                Step(id="s3", name="Step 3", kind="task", depends_on=["s2a", "s2b"]),
            ],
        )

        # 获取 s1 之后的步骤
        steps_after = template.get_steps_after("s1")
        assert set(steps_after) == {"s2a", "s2b", "s3"}

        # 获取 s2a 之后的步骤
        steps_after_s2a = template.get_steps_after("s2a")
        assert steps_after_s2a == ["s3"]

    def test_get_steps_after_invalid_step(self):
        """测试获取不存在的步骤之后"""
        template = WorkflowTemplate(
            id="test_invalid",
            level=WorkflowLevel.TASK,
            name="Invalid Step",
            description="Test with invalid step",
            steps=[
                Step(id="s1", name="Step 1", kind="task", depends_on=[]),
            ],
        )

        with pytest.raises(ValueError) as exc_info:
            template.get_steps_after("nonexistent")

        assert "not found" in str(exc_info.value)
        assert "nonexistent" in str(exc_info.value)


class TestCacheBehavior:
    """测试缓存行为"""

    def test_step_order_cache(self):
        """测试步骤顺序缓存"""
        template = WorkflowTemplate(
            id="test_cache",
            level=WorkflowLevel.TASK,
            name="Cache Test",
            description="Test caching",
            steps=[
                Step(id="s1", name="Step 1", kind="task", depends_on=[]),
                Step(id="s2", name="Step 2", kind="task", depends_on=["s1"]),
            ],
        )

        # 第一次调用
        order1 = template.get_step_order()
        # 第二次调用（应该使用缓存）
        order2 = template.get_step_order()

        assert order1 is order2  # 应该是同一个列表对象（缓存）

    def test_cache_invalidation(self):
        """测试缓存失效（未来实现）"""
        # 注意：当前实现缓存永久有效
        # 未来可以添加基于模板版本的缓存失效
        pass
