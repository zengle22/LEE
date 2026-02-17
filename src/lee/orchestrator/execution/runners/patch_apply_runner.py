"""
LEE Orchestrator — PatchApply Runner (Fallback Executor)

Applies LLM-generated patches (unified diff / git diff) to the workspace.
Used as fallback when claude_code executor is unavailable.

Execution flow:
1. Locate patch file from previous step's output or config
2. Validate patch format
3. Apply using `git apply` (primary) or manual Python-based apply (fallback)
4. Report modified files and status
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, Any, List, Optional

from lee.orchestrator.execution.runners.base import (
    StepRunnerBase,
    RunnerContext,
)
from lee.orchestrator.storage.models import StepResult

logger = logging.getLogger(__name__)


class PatchApplyRunner(StepRunnerBase):
    """
    补丁应用 Runner — LLM+Patch 降级方案

    处理 kind=patch_apply 的步骤，将前序 agent 步骤产生的
    patch 文件应用到工作区。

    Config 参数：
      - patch_source: str — patch 文件路径（相对于 project_root）
      - workspace: str — 工作区路径（可选，默认 project_root）
      - skip_if_executor: str — 当前序步骤使用此 executor 时跳过
      - auto_stage: bool — 应用后自动 git add（默认 False）
    """

    SUPPORTED_KINDS = ("patch_apply",)

    def can_handle(self, step_kind: str) -> bool:
        return step_kind in self.SUPPORTED_KINDS

    async def execute(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """执行补丁应用"""
        config = step.config or {}
        project_root = Path(ctx.project_root or ".").resolve()

        # ── 0. 检查是否应该跳过 ──
        skip_executor = config.get("skip_if_executor")
        if skip_executor:
            # 检查前序步骤是否使用了该 executor
            instance = await ctx.store.get_workflow(workflow_id)
            if instance:
                prev_executor = instance.data.get("last_executor_type")
                if prev_executor == skip_executor:
                    logger.info(
                        f"[PatchApply] Skipping — previous step used '{skip_executor}'"
                    )
                    result = await ctx.state_machine.complete_step(
                        workflow_id,
                        step.id,
                        {
                            "status": "skipped",
                            "reason": f"Previous step used {skip_executor}",
                        },
                    )
                    return result

        # ── 1. 定位 patch 文件 ──
        patch_source = config.get("patch_source")
        if not patch_source:
            # 尝试从前序步骤的 outputs 中获取
            patch_source = self._find_patch_from_inputs(step)

        if not patch_source:
            return await self._fail_step(
                ctx, workflow_id, step.id,
                "No patch source specified and none found in step inputs"
            )

        patch_path = Path(patch_source)
        if not patch_path.is_absolute():
            patch_path = project_root / patch_path

        if not patch_path.exists():
            return await self._fail_step(
                ctx, workflow_id, step.id,
                f"Patch file not found: {patch_path}"
            )

        # ── 2. 读取 patch 内容 ──
        try:
            patch_content = patch_path.read_text(encoding="utf-8")
        except Exception as e:
            return await self._fail_step(
                ctx, workflow_id, step.id,
                f"Failed to read patch file: {e}"
            )

        if not patch_content.strip():
            return await self._fail_step(
                ctx, workflow_id, step.id,
                "Patch file is empty"
            )

        # ── 3. 校验 patch 格式 ──
        patch_format = self._detect_patch_format(patch_content)
        if patch_format == "unknown":
            logger.warning("[PatchApply] Could not detect patch format, attempting raw apply")

        # ── 4. 应用 patch ──
        workspace = Path(config.get("workspace", str(project_root))).resolve()

        apply_result = await self._apply_patch(
            patch_content=patch_content,
            patch_format=patch_format,
            workspace=workspace,
        )

        # ── 5. 收集证据 ──
        evidence_artifacts = [str(patch_path)]
        if apply_result.get("modified_files"):
            for f in apply_result["modified_files"]:
                fpath = workspace / f
                if fpath.exists():
                    evidence_artifacts.append(str(fpath))

        await self._collect_evidence(ctx, workflow_id, step.id, evidence_artifacts)

        # ── 6. 可选 git add ──
        auto_stage = config.get("auto_stage", False)
        if auto_stage and apply_result.get("status") == "success":
            await self._git_add(workspace, apply_result.get("modified_files", []))

        # ── 7. 返回结果 ──
        output_data = {
            "status": apply_result["status"],
            "patch_format": patch_format,
            "patch_file": str(patch_path),
            "modified_files": apply_result.get("modified_files", []),
            "message": apply_result.get("message", ""),
        }

        if apply_result["status"] == "success":
            result = await ctx.state_machine.complete_step(
                workflow_id, step.id, output_data
            )
        else:
            result = await ctx.state_machine.fail_step(
                workflow_id, step.id,
                error_message=apply_result.get("message", "Patch apply failed"),
            )
            result.output = output_data

        return result

    # ==================================================================
    # Internal helpers
    # ==================================================================

    @staticmethod
    def _find_patch_from_inputs(step) -> Optional[str]:
        """从步骤的 input 或 config 中查找 patch 文件路径"""
        inputs = step.input or {}

        # 检查 context_files
        for ctx_file in inputs.get("context_files", []):
            path = ctx_file.get("path", "")
            if path.endswith(".patch") or path.endswith(".diff"):
                return path

        # 检查 outputs 的 from_step 引用
        for output in step.outputs:
            path = getattr(output, "path", "")
            if path.endswith(".patch") or path.endswith(".diff"):
                return path

        return None

    @staticmethod
    def _detect_patch_format(content: str) -> str:
        """检测 patch 格式"""
        lines = content.strip().split("\n")

        # Git diff format
        if any(line.startswith("diff --git") for line in lines[:10]):
            return "git_diff"

        # Unified diff format
        if any(line.startswith("---") for line in lines[:10]) and \
           any(line.startswith("+++") for line in lines[:10]):
            return "unified_diff"

        # Patch with hunk headers
        if any(re.match(r"^@@\s", line) for line in lines[:20]):
            return "hunk_only"

        return "unknown"

    async def _apply_patch(
        self,
        patch_content: str,
        patch_format: str,
        workspace: Path,
    ) -> Dict[str, Any]:
        """
        Apply patch to workspace.

        Strategy:
        1. Try `git apply` first (works for git repos)
        2. Fall back to `patch -p1` (Unix systems)
        3. Fall back to manual Python-based apply
        """
        # Strategy 1: git apply
        if patch_format in ("git_diff", "unified_diff"):
            result = await self._git_apply(patch_content, workspace)
            if result["status"] == "success":
                return result
            logger.info(f"[PatchApply] git apply failed: {result.get('message')}, trying patch command")

        # Strategy 2: patch -p1
        result = await self._unix_patch(patch_content, workspace)
        if result["status"] == "success":
            return result
        logger.info(f"[PatchApply] patch -p1 failed: {result.get('message')}, trying manual apply")

        # Strategy 3: manual Python apply
        return self._manual_apply(patch_content, workspace)

    async def _git_apply(
        self,
        patch_content: str,
        workspace: Path,
    ) -> Dict[str, Any]:
        """使用 git apply 应用补丁"""
        try:
            # Write patch to temp file
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".patch", delete=False, encoding="utf-8"
            ) as f:
                f.write(patch_content)
                temp_patch = f.name

            try:
                # Dry run first
                check_proc = await asyncio.create_subprocess_exec(
                    "git", "apply", "--check", temp_patch,
                    cwd=str(workspace),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, check_stderr = await check_proc.communicate()

                if check_proc.returncode != 0:
                    return {
                        "status": "failed",
                        "message": f"git apply --check failed: {check_stderr.decode('utf-8', errors='replace')}",
                    }

                # Apply for real
                apply_proc = await asyncio.create_subprocess_exec(
                    "git", "apply", "--stat", temp_patch,
                    cwd=str(workspace),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stat_stdout, _ = await apply_proc.communicate()

                apply_proc = await asyncio.create_subprocess_exec(
                    "git", "apply", temp_patch,
                    cwd=str(workspace),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                _, apply_stderr = await apply_proc.communicate()

                if apply_proc.returncode != 0:
                    return {
                        "status": "failed",
                        "message": f"git apply failed: {apply_stderr.decode('utf-8', errors='replace')}",
                    }

                # Parse modified files from stat output
                modified_files = self._parse_git_stat(stat_stdout.decode("utf-8", errors="replace"))

                return {
                    "status": "success",
                    "message": f"Applied patch via git apply ({len(modified_files)} files)",
                    "modified_files": modified_files,
                }
            finally:
                os.unlink(temp_patch)

        except FileNotFoundError:
            return {
                "status": "failed",
                "message": "git command not found",
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"git apply error: {e}",
            }

    async def _unix_patch(
        self,
        patch_content: str,
        workspace: Path,
    ) -> Dict[str, Any]:
        """使用 patch -p1 应用补丁"""
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".patch", delete=False, encoding="utf-8"
            ) as f:
                f.write(patch_content)
                temp_patch = f.name

            try:
                # Dry run
                check_proc = await asyncio.create_subprocess_exec(
                    "patch", "-p1", "--dry-run", "-i", temp_patch,
                    cwd=str(workspace),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                check_stdout, check_stderr = await check_proc.communicate()

                if check_proc.returncode != 0:
                    return {
                        "status": "failed",
                        "message": f"patch --dry-run failed: {check_stderr.decode('utf-8', errors='replace')}",
                    }

                # Apply
                apply_proc = await asyncio.create_subprocess_exec(
                    "patch", "-p1", "-i", temp_patch,
                    cwd=str(workspace),
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                apply_stdout, apply_stderr = await apply_proc.communicate()

                if apply_proc.returncode != 0:
                    return {
                        "status": "failed",
                        "message": f"patch -p1 failed: {apply_stderr.decode('utf-8', errors='replace')}",
                    }

                # Parse patched files
                modified_files = self._parse_patch_output(
                    apply_stdout.decode("utf-8", errors="replace")
                )

                return {
                    "status": "success",
                    "message": f"Applied patch via patch -p1 ({len(modified_files)} files)",
                    "modified_files": modified_files,
                }
            finally:
                os.unlink(temp_patch)

        except FileNotFoundError:
            return {
                "status": "failed",
                "message": "patch command not found",
            }
        except Exception as e:
            return {
                "status": "failed",
                "message": f"patch -p1 error: {e}",
            }

    @staticmethod
    def _manual_apply(patch_content: str, workspace: Path) -> Dict[str, Any]:
        """
        手动 Python 实现的 patch 应用（最后手段）

        仅支持基本的 unified diff 格式。
        """
        modified_files = []
        current_file = None
        hunks = []
        current_hunk_lines = []
        hunk_header = None

        for line in patch_content.split("\n"):
            # Detect target file
            if line.startswith("+++ "):
                # +++ b/path/to/file or +++ path/to/file
                path = line[4:].strip()
                if path.startswith("b/"):
                    path = path[2:]
                if path == "/dev/null":
                    continue
                # Apply any pending hunks to previous file
                if current_file and hunks:
                    success = PatchApplyRunner._apply_hunks_to_file(
                        workspace / current_file, hunks
                    )
                    if success:
                        modified_files.append(current_file)
                current_file = path
                hunks = []
                current_hunk_lines = []
                hunk_header = None
                continue

            if line.startswith("--- "):
                continue

            # Hunk header
            match = re.match(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@", line)
            if match:
                if hunk_header and current_hunk_lines:
                    hunks.append((hunk_header, current_hunk_lines))
                hunk_header = (
                    int(match.group(1)),
                    int(match.group(2) or 1),
                    int(match.group(3)),
                    int(match.group(4) or 1),
                )
                current_hunk_lines = []
                continue

            if hunk_header is not None:
                current_hunk_lines.append(line)

        # Apply last file
        if hunk_header and current_hunk_lines:
            hunks.append((hunk_header, current_hunk_lines))
        if current_file and hunks:
            success = PatchApplyRunner._apply_hunks_to_file(
                workspace / current_file, hunks
            )
            if success:
                modified_files.append(current_file)

        if not modified_files:
            return {
                "status": "failed",
                "message": "Manual apply found no valid hunks to apply",
                "modified_files": [],
            }

        return {
            "status": "success",
            "message": f"Applied patch manually ({len(modified_files)} files)",
            "modified_files": modified_files,
        }

    @staticmethod
    def _apply_hunks_to_file(
        filepath: Path,
        hunks: List,
    ) -> bool:
        """Apply hunks to a single file"""
        try:
            if filepath.exists():
                original = filepath.read_text(encoding="utf-8").split("\n")
            else:
                filepath.parent.mkdir(parents=True, exist_ok=True)
                original = []

            # Apply hunks in reverse order to maintain line offsets
            result_lines = list(original)
            for hunk_header, hunk_lines in reversed(hunks):
                old_start, old_count, new_start, new_count = hunk_header
                idx = old_start - 1  # 0-indexed

                # Find lines to remove and add
                remove_count = 0
                new_lines = []
                for hl in hunk_lines:
                    if hl.startswith("-"):
                        remove_count += 1
                    elif hl.startswith("+"):
                        new_lines.append(hl[1:])
                    elif hl.startswith(" ") or hl == "":
                        new_lines.append(hl[1:] if hl.startswith(" ") else "")

                # Replace old lines with new lines
                result_lines[idx:idx + old_count] = new_lines

            filepath.write_text("\n".join(result_lines), encoding="utf-8")
            return True

        except Exception as e:
            logger.error(f"[PatchApply] Manual apply failed for {filepath}: {e}")
            return False

    @staticmethod
    def _parse_git_stat(stat_output: str) -> List[str]:
        """Parse git apply --stat output to extract file names"""
        files = []
        for line in stat_output.strip().split("\n"):
            # Format: " path/to/file | N ++--"
            if "|" in line:
                filename = line.split("|")[0].strip()
                if filename:
                    files.append(filename)
        return files

    @staticmethod
    def _parse_patch_output(output: str) -> List[str]:
        """Parse patch command output to extract modified file names"""
        files = []
        for line in output.split("\n"):
            # Format: "patching file path/to/file"
            match = re.match(r"patching file (.+)", line)
            if match:
                files.append(match.group(1).strip())
        return files

    async def _git_add(
        self,
        workspace: Path,
        files: List[str],
    ) -> None:
        """Stage modified files with git add"""
        if not files:
            return
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "add", *files,
                cwd=str(workspace),
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
        except Exception as e:
            logger.warning(f"[PatchApply] git add failed: {e}")

    async def _fail_step(
        self,
        ctx: RunnerContext,
        workflow_id: str,
        step_id: str,
        message: str,
    ) -> StepResult:
        """标记步骤失败"""
        logger.error(f"[PatchApply] {message}")
        result = await ctx.state_machine.fail_step(
            workflow_id, step_id, error_message=message
        )
        return result
