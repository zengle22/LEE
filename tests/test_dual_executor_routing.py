"""
双执行器路由测试

测试用例：
1. claude_code kind 路由到 ClaudeCodeRunner
2. agent + executor_type=claude_code 仍然路由正确
3. patch_apply kind 路由到 PatchApplyRunner
4. 模板解析 type: claude_code 产生正确的 kind + executor_type
5. 模板解析 type: patch_apply 产生正确的 kind + executor_type
6. ExecutorConfig 读取 coding_executor / coding_fallback
7. StepRunnerRegistry 包含 PatchApplyRunner
"""

from __future__ import annotations

import os
import sys

import pytest

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, src_dir)


class TestTemplateParserClaudeCode:
    """测试模板解析器对 claude_code 和 patch_apply 的支持"""

    def test_parse_claude_code_type(self):
        """type: claude_code 应产出 kind=claude_code, executor_type=claude_code"""
        from lee.orchestrator.execution.template_manager import TemplateManager

        manager = TemplateManager("specs/workflows")
        step = manager._parse_step({
            "id": "test_step",
            "type": "claude_code",
            "inputs": {"goal": "test"},
        })
        assert step.kind == "claude_code"
        assert step.executor_type == "claude_code"

    def test_parse_patch_apply_type(self):
        """type: patch_apply 应产出 kind=patch_apply, executor_type=patch_apply"""
        from lee.orchestrator.execution.template_manager import TemplateManager

        manager = TemplateManager("specs/workflows")
        step = manager._parse_step({
            "id": "test_step",
            "type": "patch_apply",
            "config": {"patch_source": "test.patch"},
        })
        assert step.kind == "patch_apply"
        assert step.executor_type == "patch_apply"

    def test_parse_agent_type_unchanged(self):
        """type: agent 应保持 kind=agent, executor_type=llm"""
        from lee.orchestrator.execution.template_manager import TemplateManager

        manager = TemplateManager("specs/workflows")
        step = manager._parse_step({
            "id": "test_step",
            "type": "agent",
            "inputs": {"prompt": "test"},
        })
        assert step.kind == "agent"
        assert step.executor_type == "llm"

    def test_parse_agent_with_executor_override(self):
        """type: agent + executor: claude_code 应保持 kind=agent, executor_type=claude_code"""
        from lee.orchestrator.execution.template_manager import TemplateManager

        manager = TemplateManager("specs/workflows")
        step = manager._parse_step({
            "id": "test_step",
            "type": "agent",
            "executor": "claude_code",
            "inputs": {"prompt": "test"},
        })
        assert step.kind == "agent"
        assert step.executor_type == "claude_code"

    def test_parse_skill_type_unchanged(self):
        """type: skill 应保持 kind=skill, executor_type=shell"""
        from lee.orchestrator.execution.template_manager import TemplateManager

        manager = TemplateManager("specs/workflows")
        step = manager._parse_step({
            "id": "test_step",
            "type": "skill",
            "inputs": {"command": "echo hello"},
        })
        assert step.kind == "skill"
        assert step.executor_type == "shell"


class TestExecutorConfig:
    """测试 ExecutorConfig 的新字段"""

    def test_default_coding_executor(self):
        """默认 coding_executor 为 claude_code"""
        from lee.orchestrator.config_loader import ExecutorConfig

        config = ExecutorConfig()
        assert config.coding_executor == "claude_code"
        assert config.coding_fallback == "llm_patch"

    def test_from_dict_coding_executor(self):
        """从字典创建配置时读取 coding_executor"""
        from lee.orchestrator.config_loader import ExecutorConfig

        config = ExecutorConfig.from_dict({
            "coding_executor": "llm",
            "coding_fallback": "manual",
        })
        assert config.coding_executor == "llm"
        assert config.coding_fallback == "manual"

    def test_from_dict_defaults(self):
        """从空字典创建配置时使用默认值"""
        from lee.orchestrator.config_loader import ExecutorConfig

        config = ExecutorConfig.from_dict({})
        assert config.coding_executor == "claude_code"
        assert config.coding_fallback == "llm_patch"
        assert config.default_type == "llm"

    def test_full_config_load(self):
        """LeeConfig 应正确加载嵌套的 executor 配置"""
        from lee.orchestrator.config_loader import LeeConfig

        config = LeeConfig.from_dict({
            "executor": {
                "default_type": "llm",
                "coding_executor": "claude_code",
                "coding_fallback": "llm_patch",
                "timeout_seconds": 600,
            }
        })
        assert config.executor.coding_executor == "claude_code"
        assert config.executor.coding_fallback == "llm_patch"
        assert config.executor.timeout_seconds == 600


class TestRunnerRegistryDualExecutor:
    """测试 Runner 注册表包含新的 runner"""

    def test_registry_has_patch_apply_runner(self):
        """注册表应包含 PatchApplyRunner"""
        from lee.orchestrator.execution.runners.registry import StepRunnerRegistry

        registry = StepRunnerRegistry()
        registry.register_defaults()

        runner = registry.get_runner("patch_apply")
        assert runner is not None

        from lee.orchestrator.execution.runners.patch_apply_runner import PatchApplyRunner
        assert isinstance(runner, PatchApplyRunner)

    def test_registry_still_has_claude_code_runner(self):
        """注册表仍然包含 ClaudeCodeRunner"""
        from lee.orchestrator.execution.runners.registry import StepRunnerRegistry

        registry = StepRunnerRegistry()
        registry.register_defaults()

        runner = registry.get_runner("claude_code")
        assert runner is not None

    def test_registry_still_has_llm_runner(self):
        """注册表仍然包含 LLMRunner"""
        from lee.orchestrator.execution.runners.registry import StepRunnerRegistry

        registry = StepRunnerRegistry()
        registry.register_defaults()

        runner = registry.get_runner("agent")
        assert runner is not None

    def test_registry_still_has_skill_runner(self):
        """注册表仍然包含 SkillRunner"""
        from lee.orchestrator.execution.runners.registry import StepRunnerRegistry

        registry = StepRunnerRegistry()
        registry.register_defaults()

        runner = registry.get_runner("skill")
        assert runner is not None

    def test_registry_registered_kinds(self):
        """注册表应列出所有已注册的 kind"""
        from lee.orchestrator.execution.runners.registry import StepRunnerRegistry

        registry = StepRunnerRegistry()
        registry.register_defaults()

        kinds = registry.registered_kinds
        assert "LLMRunner" in kinds
        assert "ClaudeCodeRunner" in kinds
        assert "PatchApplyRunner" in kinds
        assert "SkillRunner" in kinds
