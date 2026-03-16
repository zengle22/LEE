from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from lee.orchestrator.execution.runners.base import StepRunnerBase

from .models import ExtractionResult


class OutputExtractor:
    @staticmethod
    def parse_structured_output_if_possible(output_text: str) -> Optional[Any]:
        try:
            return StepRunnerBase._parse_structured_output(output_text)
        except ValueError:
            return None

    @staticmethod
    def looks_like_executor_wrapper(payload: Any) -> bool:
        if not isinstance(payload, dict):
            return False
        wrapper_keys = {
            "status",
            "changed_files",
            "commands_run",
            "test_results",
            "diff_summary",
            "evidence_bundle_path",
            "conversation_log_path",
            "debug_log_path",
            "prompt_system_path",
            "prompt_user_path",
            "generated_text",
            "error",
            "iterations_used",
        }
        return bool(wrapper_keys & set(payload.keys()))

    @classmethod
    def extract_ssot_contract_payload(
        cls,
        *,
        structured_payload: Optional[Any],
        generated_text: str,
        extract_structured_segment_payload: Callable[[str, str], Optional[Any]],
        extract_structured_payload_from_code_blocks: Callable[[str, str], Optional[Any]],
        coerce_ssot_contract_dict: Callable[[Optional[Any]], Optional[Dict[str, Any]]],
    ) -> Optional[Dict[str, Any]]:
        if not isinstance(structured_payload, dict):
            payload = extract_structured_segment_payload(generated_text, "ssot_output_contract")
            payload = coerce_ssot_contract_dict(payload)
            if isinstance(payload, dict):
                return payload
            block_payload = extract_structured_payload_from_code_blocks(
                generated_text,
                "ssot_output_contract",
            )
            block_payload = coerce_ssot_contract_dict(block_payload)
            return block_payload if isinstance(block_payload, dict) else None
        if "contract_version" in structured_payload and "outputs" in structured_payload:
            return structured_payload
        payload = coerce_ssot_contract_dict(structured_payload.get("ssot_output_contract"))
        if isinstance(payload, dict):
            return payload
        segment_payload = coerce_ssot_contract_dict(
            extract_structured_segment_payload(generated_text, "ssot_output_contract")
        )
        if isinstance(segment_payload, dict):
            return segment_payload
        block_payload = coerce_ssot_contract_dict(
            extract_structured_payload_from_code_blocks(
                generated_text,
                "ssot_output_contract",
            )
        )
        if isinstance(block_payload, dict):
            return block_payload
        return None

    @classmethod
    def extract_best_written_file_payload(
        cls,
        *,
        step,
        written_files: List[str],
        build_prd_writer_bundle_from_written_files: Callable[[List[str]], Optional[Dict[str, Any]]],
        build_pm_planner_bundle_from_written_files: Callable[[List[str]], Optional[Dict[str, Any]]],
        score_written_output_candidate: Callable[[Any, Any], int],
    ) -> Optional[Any]:
        if getattr(step, "agent_id", "") == "agent.product.prd_writer":
            aggregated_bundle = build_prd_writer_bundle_from_written_files(written_files)
            if aggregated_bundle is not None:
                return aggregated_bundle
        if getattr(step, "agent_id", "") == "agent.product.pm_planner":
            aggregated_bundle = build_pm_planner_bundle_from_written_files(written_files)
            if aggregated_bundle is not None:
                return aggregated_bundle

        best_payload: Optional[Any] = None
        best_score = -1
        for file_path in written_files:
            try:
                parsed_file = StepRunnerBase._parse_structured_output(
                    Path(file_path).read_text(encoding="utf-8")
                )
            except Exception:
                continue
            score = score_written_output_candidate(step, parsed_file)
            if score > best_score:
                best_score = score
                best_payload = parsed_file
        return best_payload

    @classmethod
    def extract_for_validation(
        cls,
        *,
        step,
        workflow_id: str,
        output: Dict[str, Any],
        written_files: List[str],
        extract_primary_file_output: Callable[[Any, List[str]], Optional[Any]],
        extract_best_written_file_payload: Callable[[Any, List[str]], Optional[Any]],
        normalize_business_payload: Callable[..., Any],
    ) -> tuple[Any, Any]:
        raw_output = output.get("raw_output", "") or ""
        generated_text = output.get("generated_text", "") or ""

        raw_structured_payload = cls.parse_structured_output_if_possible(raw_output)
        generated_structured_payload = cls.parse_structured_output_if_possible(generated_text)

        structured_payload = raw_structured_payload
        source_kind = "raw_output"
        if structured_payload is None or cls.looks_like_executor_wrapper(structured_payload):
            if generated_structured_payload is not None:
                structured_payload = generated_structured_payload
                source_kind = "generated_text"

        if isinstance(structured_payload, dict) and "business_output" in structured_payload:
            business_output = structured_payload["business_output"]
            source_kind = f"{source_kind}.business_output"
        elif isinstance(structured_payload, dict) and not cls.looks_like_executor_wrapper(structured_payload):
            business_output = structured_payload
        else:
            business_output = extract_primary_file_output(step, written_files)
            if business_output is not None:
                source_kind = "primary_written_file"
            if business_output is None:
                business_output = extract_best_written_file_payload(step, written_files)
                if business_output is not None:
                    source_kind = "best_written_file"
            if isinstance(business_output, dict) and "business_output" in business_output:
                business_output = business_output["business_output"]
                source_kind = f"{source_kind}.business_output"
            if business_output is None:
                business_output = raw_output or generated_text or json.dumps(output)
                source_kind = "raw_fallback"

        if isinstance(business_output, list):
            business_output = business_output[0] if business_output else {}

        extracted = ExtractionResult(
            raw_output=raw_output,
            generated_text=generated_text,
            structured_payload=structured_payload,
            business_output=business_output,
            source_kind=source_kind,
            written_files=list(written_files or []),
        )

        return normalize_business_payload(
            step=step,
            workflow_id=workflow_id,
            business_output=extracted.business_output,
            structured_payload=extracted.structured_payload,
            instance_data=None,
        )
