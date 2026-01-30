"""
实现类任务 Graph (l3.impl.coding)

处理代码实现任务：读取设计文档 -> LLM 生成代码 -> 安全写入文件。

工作流程：
1. load_inputs: 加载 PRD、设计文档、实现契约
2. llm_impl: 调用 LLM 生成实现代码
3. apply_changes: 安全写入代码文件
4. build_result: 构建执行结果
"""

from typing import Dict, Any, List, Tuple
from datetime import datetime
from pathlib import Path

from langgraph.graph import StateGraph, END

from ..types import (
    ExecutorTaskSpec,
    ExecutionResult,
    TaskStatus,
    ImplCodingState,
)
from ..tools import fs_tools, llm_tools
from ..tools.security import safe_join
from .common import should_continue, add_log


# LLM System Prompt
IMPL_SYSTEM_PROMPT = """你是一个严格遵守约束的资深工程师。
请根据 PRD、设计和实现契约，生成完整的实现代码。

输出格式要求：
每个文件使用以下格式标记：

===FILE:path/to/file.ext===
<file content here>
===END===

规则：
1. 只输出代码文件，不要包含解释性文字
2. 文件路径使用相对路径
3. 确保代码完整、可运行
4. 遵循项目的代码规范
5. 包含必要的类型注解和文档字符串
"""


def build_impl_coding_graph(task: ExecutorTaskSpec) -> Any:
    """
    构建实现类任务 LangGraph

    Args:
        task: 任务规格

    Returns:
        编译后的 LangGraph
    """
    graph = StateGraph(ImplCodingState)

    # ============================================
    # 节点定义
    # ============================================

    def load_inputs(state: ImplCodingState) -> ImplCodingState:
        """加载输入文件"""
        t = state["task"]
        logs = add_log(state, "[load_inputs] Loading inputs...")
        errors = state.get("errors", []).copy()
        metrics = state.get("metrics", {}).copy()

        prd = ""
        design = ""
        contract = ""

        # 加载 PRD
        if "frozen_prd" in t.inputs:
            try:
                prd = fs_tools.read_file(t.inputs["frozen_prd"])
                logs = [*logs, f"  Loaded PRD from {t.inputs['frozen_prd']}"]
                metrics["prd_size"] = len(prd)
            except Exception as e:
                logs = [*logs, f"  Failed to load PRD: {e}"]
                errors = [*errors, f"Failed to load PRD: {e}"]

        # 加载设计文档
        if "design_spec" in t.inputs:
            try:
                design = fs_tools.read_file(t.inputs["design_spec"])
                logs = [*logs, f"  Loaded design from {t.inputs['design_spec']}"]
                metrics["design_size"] = len(design)
            except Exception as e:
                logs = [*logs, f"  Failed to load design: {e}"]
                errors = [*errors, f"Failed to load design: {e}"]

        # 加载实现契约
        if "impl_contract" in t.inputs:
            try:
                contract = fs_tools.read_file(t.inputs["impl_contract"])
                logs = [*logs, f"  Loaded contract from {t.inputs['impl_contract']}"]
                metrics["contract_size"] = len(contract)
            except Exception as e:
                logs = [*logs, f"  Failed to load contract: {e}"]
                errors = [*errors, f"Failed to load contract: {e}"]

        # 至少需要一个输入
        inputs_loaded = sum([1 for x in [prd, design, contract] if x])
        metrics["inputs_loaded"] = inputs_loaded

        if inputs_loaded == 0:
            logs = [*logs, "  Warning: No inputs loaded"]
            # 不作为致命错误，允许 LLM 根据 params 中的信息生成

        return {
            **state,
            "logs": logs,
            "errors": errors,
            "metrics": metrics,
            "prd": prd,
            "design": design,
            "contract": contract,
            "current_step": "load_inputs",
        }

    def llm_impl(state: ImplCodingState) -> ImplCodingState:
        """调用 LLM 生成实现"""
        t = state["task"]
        logs = add_log(state, "[llm_impl] Calling LLM for implementation...")
        errors = state.get("errors", []).copy()
        metrics = state.get("metrics", {}).copy()
        tokens_used = state.get("tokens_used", 0)

        # 构建 User Prompt
        user_prompt = _build_user_prompt(
            prd=state.get("prd", ""),
            design=state.get("design", ""),
            contract=state.get("contract", ""),
            extra_instructions=t.params.get("instructions", ""),
        )

        code_changes: Dict[str, str] = {}
        impl_plan = ""

        try:
            # 调用 LLM
            response = llm_tools.call_llm(
                profile=t.llm_profile or "default",
                messages=[{"role": "user", "content": user_prompt}],
                system=IMPL_SYSTEM_PROMPT,
                temperature=t.llm_temperature,
                max_tokens=t.llm_max_tokens,
            )

            tokens_used += response.tokens_used

            # 解析 FILE 标记
            code_changes = _parse_file_markers(response.content)

            # 记录摘要
            impl_plan = (
                response.content[:500] + "..."
                if len(response.content) > 500
                else response.content
            )

            logs = [*logs, f"  Generated {len(code_changes)} file(s)"]
            logs = [*logs, f"  Tokens used: {response.tokens_used}"]
            logs = [*logs, f"  Duration: {response.duration_seconds:.2f}s"]

            for path in code_changes.keys():
                logs = [*logs, f"    - {path}"]

            metrics["llm_tokens"] = response.tokens_used
            metrics["llm_duration"] = response.duration_seconds
            metrics["files_generated"] = len(code_changes)

        except Exception as e:
            logs = [*logs, f"  LLM call failed: {e}"]
            errors = [*errors, f"LLM call failed: {e}"]

        return {
            **state,
            "logs": logs,
            "errors": errors,
            "metrics": metrics,
            "tokens_used": tokens_used,
            "code_changes": code_changes,
            "impl_plan": impl_plan,
            "current_step": "llm_impl",
        }

    def apply_changes(state: ImplCodingState) -> ImplCodingState:
        """应用代码变更（带安全边界）"""
        t = state["task"]
        logs = add_log(state, "[apply_changes] Applying code changes...")
        errors = state.get("errors", []).copy()
        metrics = state.get("metrics", {}).copy()

        # 确定工作目录
        repo_root = t.inputs.get("repo_workspace", ".")
        workspace_root = t.workspace_root or repo_root
        allowed_patterns = t.allowed_write_patterns or []

        files_written = 0
        files_skipped = 0

        code_changes = state.get("code_changes", {})

        if not code_changes:
            logs = [*logs, "  No code changes to apply"]
        else:
            for rel_path, content in code_changes.items():
                try:
                    # 使用安全路径拼接
                    abs_path = safe_join(repo_root, rel_path)
                    if abs_path is None:
                        logs = [*logs, f"  Security: Path traversal attempt: {rel_path}"]
                        errors = [*errors, f"Path traversal: {rel_path}"]
                        files_skipped += 1
                        continue

                    # 写入文件（带安全检查）
                    fs_tools.write_file(
                        abs_path,
                        content,
                        workspace_root=workspace_root,
                        allowed_patterns=allowed_patterns if allowed_patterns else None,
                    )
                    logs = [*logs, f"  Written: {rel_path}"]
                    files_written += 1

                except ValueError as e:
                    # 安全检查失败
                    logs = [*logs, f"  Security blocked: {rel_path} - {e}"]
                    errors = [*errors, f"Security blocked {rel_path}: {e}"]
                    files_skipped += 1

                except Exception as e:
                    logs = [*logs, f"  Failed to write {rel_path}: {e}"]
                    errors = [*errors, f"Failed to write {rel_path}: {e}"]
                    files_skipped += 1

        metrics["files_written"] = files_written
        metrics["files_skipped"] = files_skipped

        return {
            **state,
            "logs": logs,
            "errors": errors,
            "metrics": metrics,
            "current_step": "apply_changes",
        }

    def build_result(state: ImplCodingState) -> ImplCodingState:
        """构建执行结果"""
        t = state["task"]
        logs = add_log(state, "[build_result] Building execution result...")

        # 收集 artifacts
        artifacts: Dict[str, str] = {}
        for logical_name, real_path in t.outputs.items():
            if Path(real_path).exists():
                artifacts[logical_name] = real_path

        # 决定最终状态
        errors = state.get("errors", [])
        metrics = state.get("metrics", {})

        # 如果有文件写入且没有致命错误，认为成功
        files_written = metrics.get("files_written", 0)
        files_generated = metrics.get("files_generated", 0)

        if files_generated == 0:
            status = TaskStatus.FAILED
            message = "No code generated by LLM"
        elif files_written == 0 and files_generated > 0:
            status = TaskStatus.FAILED
            message = f"Generated {files_generated} files but none were written (security or I/O errors)"
        elif errors:
            # 有错误但部分成功
            status = TaskStatus.SUCCESS  # 部分成功也算成功
            message = f"Implementation completed with warnings: {files_written} files written, {len(errors)} error(s)"
        else:
            status = TaskStatus.SUCCESS
            message = f"Implementation completed successfully: {files_written} files written"

        exec_result = ExecutionResult(
            task_id=t.task_id,
            status=status,
            message=message,
            artifacts=artifacts,
            logs=logs,
            error_details="\n".join(errors) if errors else None,
            metrics={
                **metrics,
                "error_count": len(errors),
            },
            tokens_used=state.get("tokens_used", 0),
            completed_at=datetime.now(),
        )

        return {
            **state,
            "logs": logs,
            "exec_result": exec_result,
            "current_step": "build_result",
        }

    # ============================================
    # 添加节点
    # ============================================
    graph.add_node("load_inputs", load_inputs)
    graph.add_node("llm_impl", llm_impl)
    graph.add_node("apply_changes", apply_changes)
    graph.add_node("build_result", build_result)

    # ============================================
    # 连接图
    # ============================================
    graph.set_entry_point("load_inputs")

    # load_inputs -> (条件) -> llm_impl 或 build_result
    graph.add_conditional_edges(
        "load_inputs",
        should_continue,
        {
            "continue": "llm_impl",
            "stop": "build_result",
        }
    )

    # llm_impl -> (条件) -> apply_changes 或 build_result
    graph.add_conditional_edges(
        "llm_impl",
        should_continue,
        {
            "continue": "apply_changes",
            "stop": "build_result",
        }
    )

    # apply_changes -> build_result
    graph.add_edge("apply_changes", "build_result")

    # build_result -> END
    graph.add_edge("build_result", END)

    return graph.compile()


# ============================================
# 辅助函数
# ============================================

def _build_user_prompt(
    prd: str,
    design: str,
    contract: str,
    extra_instructions: str = "",
) -> str:
    """构建 User Prompt"""
    sections = []

    if prd:
        sections.append(f"[PRD - 产品需求文档]\n{prd}")

    if design:
        sections.append(f"[DESIGN - 设计文档]\n{design}")

    if contract:
        sections.append(f"[IMPLEMENTATION CONTRACT - 实现契约]\n{contract}")

    if extra_instructions:
        sections.append(f"[ADDITIONAL INSTRUCTIONS]\n{extra_instructions}")

    if not sections:
        sections.append("[NOTE] No input documents provided. Please generate a minimal implementation.")

    return "\n\n---\n\n".join(sections)


def _parse_file_markers(content: str) -> Dict[str, str]:
    """
    解析 LLM 输出中的文件标记

    格式:
    ===FILE:path/to/file.ext===
    <content>
    ===END===
    """
    code_changes: Dict[str, str] = {}
    current_path: str | None = None
    current_lines: List[str] = []

    for line in content.splitlines():
        if line.startswith("===FILE:") and line.endswith("==="):
            # 保存之前的文件
            if current_path is not None:
                code_changes[current_path] = "\n".join(current_lines).strip()

            # 开始新文件
            current_path = line[len("===FILE:"):-len("===")].strip()
            current_lines = []

        elif line.strip() == "===END===":
            # 结束当前文件
            if current_path is not None:
                code_changes[current_path] = "\n".join(current_lines).strip()
                current_path = None
                current_lines = []

        elif current_path is not None:
            current_lines.append(line)

    # 处理最后一个文件（如果没有 ===END===）
    if current_path is not None:
        code_changes[current_path] = "\n".join(current_lines).strip()

    return code_changes
