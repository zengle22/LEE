from __future__ import annotations

import json
from typing import Any, Dict, Optional

from lee.orchestrator.execution.retry import AsyncRetryExecutor, RetryPolicy


class SchemaRepairHelper:
    @staticmethod
    def build_repair_prompt(
        *,
        step,
        validation_error: str,
        business_output: Any,
        structured_payload: Any,
    ) -> str:
        payload = business_output
        if not isinstance(payload, dict) and isinstance(structured_payload, dict):
            payload = structured_payload

        payload_text = json.dumps(
            payload if payload is not None else {},
            ensure_ascii=False,
            indent=2,
        )
        return (
            "修复下面这个结构化输出，使其满足当前 step 的 output contract。\n"
            "只允许返回最终 JSON 对象，不要输出解释、标题、代码块或额外包裹层。\n"
            f"step_id: {getattr(step, 'id', '')}\n"
            f"validation_error: {validation_error}\n"
            "要求：\n"
            "- 保留原始语义，不要重新发明业务内容\n"
            "- 仅补足缺失字段、修正字段名或枚举值、规范结构\n"
            "- 如果原输出里缺少必要结论字段，请基于已有 summary/findings/risks/recommendations 做最小修复\n"
            "- 返回内容必须是可直接通过 schema 校验的单个 JSON 对象\n"
            "原始 payload:\n"
            f"{payload_text}"
        )

    @classmethod
    def build_repair_input(
        cls,
        *,
        executor_type: str,
        input_data: Dict[str, Any],
        step,
        validation_error: str,
        business_output: Any,
        structured_payload: Any,
    ) -> Dict[str, Any]:
        repair_prompt = cls.build_repair_prompt(
            step=step,
            validation_error=validation_error,
            business_output=business_output,
            structured_payload=structured_payload,
        )
        repaired_input = dict(input_data)
        if executor_type in ("codex", "claude_code", "kimi"):
            repaired_input["goal"] = repair_prompt
            repaired_input["context_files"] = []
            repaired_input["write_scope"] = []
            repaired_input["max_iterations"] = 1
            repaired_input["allowed_commands"] = []
            repaired_input["system_prompt_extra"] = (
                "你正在执行 schema repair retry。"
                "不要修改文件，不要调用命令，只输出最终 JSON 对象。"
            )
            return repaired_input

        repaired_input["prompt"] = repair_prompt
        repaired_input["system_message"] = (
            "You are repairing structured output to satisfy a JSON schema. "
            "Return only a single JSON object."
        )
        repaired_input["temperature"] = 0
        return repaired_input

    @classmethod
    async def attempt_repair(
        cls,
        *,
        runner,
        executor,
        executor_type: str,
        input_data: Dict[str, Any],
        step,
        workflow_id: str,
        validation_error: str,
        business_output: Any,
        structured_payload: Any,
    ) -> Optional[Dict[str, Any]]:
        repair_input = cls.build_repair_input(
            executor_type=executor_type,
            input_data=input_data,
            step=step,
            validation_error=validation_error,
            business_output=business_output,
            structured_payload=structured_payload,
        )
        retry_executor = AsyncRetryExecutor(
            policy=RetryPolicy(max_retries=0, base_delay=0, jitter=False)
        )
        repair_result = await retry_executor.execute(executor.execute, repair_input)
        if not repair_result.success:
            return None

        repaired_output = repair_result.result
        if not isinstance(repaired_output, dict):
            return None

        if executor_type in ("codex", "claude_code", "kimi"):
            extractor = getattr(runner, "_extract_business_output_for_validation", None)
            if extractor is None:
                from lee.orchestrator.execution.runners.llm_runner import ClaudeCodeRunner

                extractor = ClaudeCodeRunner._extract_business_output_for_validation
            repaired_business_output, repaired_structured_payload = extractor(
                step=step,
                workflow_id=workflow_id,
                output=repaired_output,
                written_files=[],
            )
        else:
            repaired_generated_text = repaired_output.get("generated_text", "") or ""
            repaired_structured_payload = runner._parse_structured_output_if_possible(repaired_generated_text)
            repaired_business_output = runner._extract_business_output_payload(
                repaired_structured_payload,
                repaired_generated_text,
                step=step,
                written_files=[],
            )
            repaired_business_output, repaired_structured_payload = runner._normalize_business_payload(
                step=step,
                workflow_id=workflow_id,
                business_output=repaired_business_output,
                structured_payload=repaired_structured_payload,
            )

        if not isinstance(repaired_business_output, dict):
            return None
        return {
            "output": repaired_output,
            "business_output": repaired_business_output,
            "structured_payload": repaired_structured_payload,
        }
