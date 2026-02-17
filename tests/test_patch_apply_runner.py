"""
PatchApplyRunner 单元测试

测试用例：
1. can_handle 注册匹配
2. 应用有效的 unified diff
3. 应用 git diff 格式的补丁
4. 处理无效补丁（格式错误）
5. 处理空补丁文件
6. 处理不存在的补丁文件
7. skip_if_executor 跳过逻辑
8. patch 格式检测
9. git apply --stat 输出解析
10. patch 命令输出解析
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

import pytest

from lee.orchestrator.execution.runners.patch_apply_runner import PatchApplyRunner


# ========================================================================
# Helpers
# ========================================================================

@dataclass
class MockStep:
    """模拟 Step 对象"""
    id: str = "test_patch_step"
    kind: str = "patch_apply"
    executor_type: str = "patch_apply"
    input: Dict[str, Any] = field(default_factory=dict)
    outputs: list = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MockOutputSpec:
    path: str = ""
    type: str = "file"
    format: str = "text"
    required: bool = True
    description: str = ""


def make_mock_ctx(project_root: str):
    """创建 mock RunnerContext"""
    ctx = MagicMock()
    ctx.project_root = project_root
    ctx.store = MagicMock()
    mock_instance = MagicMock()
    mock_instance.data = {"run_id": "RUN-TEST1234"}
    ctx.store.get_workflow = AsyncMock(return_value=mock_instance)
    ctx.store.update_workflow_data = AsyncMock()
    ctx.state_machine = MagicMock()
    ctx.state_machine.complete_step = AsyncMock(
        return_value=MagicMock(status="success", step_id="test_patch_step", output={})
    )
    ctx.state_machine.fail_step = AsyncMock(
        return_value=MagicMock(status="failed", step_id="test_patch_step", output={})
    )
    ctx.evidence_collector = MagicMock()
    ctx.evidence_collector.collect = MagicMock()
    return ctx


# ========================================================================
# Tests
# ========================================================================

class TestPatchApplyRunner:
    """PatchApplyRunner 测试套件"""

    def test_can_handle(self):
        """测试 runner 匹配 patch_apply kind"""
        runner = PatchApplyRunner()
        assert runner.can_handle("patch_apply") is True
        assert runner.can_handle("agent") is False
        assert runner.can_handle("skill") is False
        assert runner.can_handle("claude_code") is False

    def test_detect_git_diff_format(self):
        """测试 git diff 格式检测"""
        content = """diff --git a/main.py b/main.py
index abc123..def456 100644
--- a/main.py
+++ b/main.py
@@ -1,3 +1,4 @@
 import os
+import sys
 print("hello")
"""
        assert PatchApplyRunner._detect_patch_format(content) == "git_diff"

    def test_detect_unified_diff_format(self):
        """测试 unified diff 格式检测"""
        content = """--- a/main.py
+++ b/main.py
@@ -1,3 +1,4 @@
 import os
+import sys
 print("hello")
"""
        assert PatchApplyRunner._detect_patch_format(content) == "unified_diff"

    def test_detect_hunk_only_format(self):
        """测试仅有 hunk header 的格式检测"""
        content = """@@ -1,3 +1,4 @@
 import os
+import sys
 print("hello")
"""
        assert PatchApplyRunner._detect_patch_format(content) == "hunk_only"

    def test_detect_unknown_format(self):
        """测试未知格式检测"""
        content = "just some random text\nno patch here"
        assert PatchApplyRunner._detect_patch_format(content) == "unknown"

    def test_parse_git_stat(self):
        """测试 git apply --stat 输出解析"""
        stat_output = """ main.py    | 2 +-
 utils.py   | 5 +++++
 2 files changed, 6 insertions(+), 1 deletion(-)
"""
        files = PatchApplyRunner._parse_git_stat(stat_output)
        assert "main.py" in files
        assert "utils.py" in files
        assert len(files) == 2

    def test_parse_patch_output(self):
        """测试 patch 命令输出解析"""
        output = """patching file main.py
patching file utils.py
"""
        files = PatchApplyRunner._parse_patch_output(output)
        assert files == ["main.py", "utils.py"]

    def test_manual_apply_unified_diff(self):
        """测试手动 Python 实现的 patch 应用"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            target = workspace / "hello.py"
            target.write_text("line1\nline2\nline3\n")

            patch_content = """--- a/hello.py
+++ b/hello.py
@@ -1,3 +1,4 @@
 line1
+inserted
 line2
 line3
"""
            result = PatchApplyRunner._manual_apply(patch_content, workspace)
            assert result["status"] == "success"
            assert "hello.py" in result["modified_files"]

            # Verify file content
            new_content = target.read_text()
            assert "inserted" in new_content

    def test_manual_apply_empty_patch(self):
        """测试手动应用空 patch"""
        with tempfile.TemporaryDirectory() as tmpdir:
            workspace = Path(tmpdir)
            result = PatchApplyRunner._manual_apply("", workspace)
            assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_execute_missing_patch_file(self):
        """测试缺少 patch 文件时失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = PatchApplyRunner()
            step = MockStep(config={
                "patch_source": "nonexistent.patch",
            })
            ctx = make_mock_ctx(tmpdir)

            await runner.execute("wf-1", step, ctx)
            ctx.state_machine.fail_step.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_empty_patch_file(self):
        """测试空 patch 文件时失败"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create empty patch file
            patch_path = Path(tmpdir) / "empty.patch"
            patch_path.write_text("")

            runner = PatchApplyRunner()
            step = MockStep(config={
                "patch_source": str(patch_path),
            })
            ctx = make_mock_ctx(tmpdir)

            await runner.execute("wf-1", step, ctx)
            ctx.state_machine.fail_step.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_skip_when_claude_code_ran(self):
        """测试当前序步骤使用 claude_code 时跳过"""
        with tempfile.TemporaryDirectory() as tmpdir:
            runner = PatchApplyRunner()
            step = MockStep(config={
                "patch_source": "some.patch",
                "skip_if_executor": "claude_code",
            })
            ctx = make_mock_ctx(tmpdir)

            # Mock workflow instance with last_executor_type
            mock_instance = MagicMock()
            mock_instance.data = {"last_executor_type": "claude_code"}
            ctx.store.get_workflow = AsyncMock(return_value=mock_instance)

            await runner.execute("wf-1", step, ctx)
            ctx.state_machine.complete_step.assert_called_once()
            call_args = ctx.state_machine.complete_step.call_args
            assert call_args[0][2]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_execute_no_skip_when_llm_ran(self):
        """测试当前序步骤使用 llm 时不跳过"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create a valid patch file
            patch_path = Path(tmpdir) / "test.patch"
            patch_content = (
                "--- a/hello.py\n"
                "+++ b/hello.py\n"
                "@@ -1,1 +1,2 @@\n"
                " line1\n"
                "+line2\n"
            )
            patch_path.write_text(patch_content)
            # Create the target file
            (Path(tmpdir) / "hello.py").write_text("line1\n")

            runner = PatchApplyRunner()
            step = MockStep(config={
                "patch_source": str(patch_path),
                "skip_if_executor": "claude_code",
            })
            ctx = make_mock_ctx(tmpdir)

            mock_instance = MagicMock()
            mock_instance.data = {"last_executor_type": "llm"}
            ctx.store.get_workflow = AsyncMock(return_value=mock_instance)

            await runner.execute("wf-1", step, ctx)
            # Should not skip — should either succeed or fail, but not skip
            # (git apply or manual apply may be called)

    def test_find_patch_from_inputs_context_files(self):
        """测试从 context_files 中查找 patch"""
        step = MockStep(input={
            "context_files": [
                {"path": "output/code.patch", "required": True},
            ]
        })
        result = PatchApplyRunner._find_patch_from_inputs(step)
        assert result == "output/code.patch"

    def test_find_patch_from_inputs_outputs(self):
        """测试从 outputs 中查找 patch"""
        step = MockStep(
            input={},
            outputs=[MockOutputSpec(path="output/changes.diff")],
        )
        result = PatchApplyRunner._find_patch_from_inputs(step)
        assert result == "output/changes.diff"

    def test_find_patch_returns_none(self):
        """测试找不到 patch 时返回 None"""
        step = MockStep(input={}, outputs=[])
        result = PatchApplyRunner._find_patch_from_inputs(step)
        assert result is None
