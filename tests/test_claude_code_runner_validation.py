from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from lee.orchestrator.execution.runners.llm_runner import ClaudeCodeRunner, LLMRunner
from lee.orchestrator.execution.runners.base import RunnerContext


def test_validate_success_criteria_missing_required_command():
    error = ClaudeCodeRunner._validate_success_criteria(
        output={"commands_run": [{"cmd": "git status"}]},
        criteria={"require_commands": ["git commit"]},
        workspace=".",
        head_before=None,
    )
    assert error is not None
    assert "Missing required command" in error


def test_validate_success_criteria_detects_head_unchanged(monkeypatch):
    monkeypatch.setattr(
        ClaudeCodeRunner,
        "_git_head",
        staticmethod(lambda _workspace: "abc12345"),
    )
    error = ClaudeCodeRunner._validate_success_criteria(
        output={"commands_run": [{"cmd": "git commit -m 'x'"}]},
        criteria={"require_commands": ["git commit"], "require_new_commit": True},
        workspace=".",
        head_before="abc12345",
    )
    assert error is not None
    assert "No new commit detected" in error


def test_validate_success_criteria_pass(monkeypatch):
    monkeypatch.setattr(
        ClaudeCodeRunner,
        "_git_head",
        staticmethod(lambda _workspace: "def67890"),
    )
    error = ClaudeCodeRunner._validate_success_criteria(
        output={"commands_run": [{"cmd": "git commit -m 'x'"}]},
        criteria={"require_commands": ["git commit"], "require_new_commit": True},
        workspace=".",
        head_before="abc12345",
    )
    assert error is None


def test_normalize_product_review_payload_maps_status_to_decision():
    step = SimpleNamespace(agent_id="agent.product.feat_reviewer")
    business_output = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "status": "pass",
        "subject_refs": ["FEAT-001"],
        "summary": "ok",
        "findings": [],
        "risks": [],
        "recommendations": [],
    }
    structured_payload = {"business_output": dict(business_output)}

    normalized_business, normalized_structured = LLMRunner._normalize_product_review_payload(
        step=step,
        business_output=business_output,
        structured_payload=structured_payload,
    )

    assert normalized_business["decision"] == "pass"
    assert normalized_structured["business_output"]["decision"] == "pass"


def test_normalize_product_review_payload_preserves_existing_decision():
    step = SimpleNamespace(agent_id="agent.product.feat_reviewer")
    business_output = {
        "review_id": "RVW-002",
        "review_type": "feat_review",
        "status": "reject",
        "decision": "revise",
        "subject_refs": ["FEAT-001"],
        "summary": "needs changes",
        "findings": ["gap"],
        "risks": [],
        "recommendations": [],
    }

    normalized_business, _ = LLMRunner._normalize_product_review_payload(
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
    )

    assert normalized_business["decision"] == "revise"


def test_build_schema_repair_input_for_claude_code():
    step = SimpleNamespace(id="feat_review")
    original_input = {
        "goal": "original goal",
        "workspace": ".",
        "allowed_commands": ["cat"],
        "max_iterations": 5,
    }

    repaired_input = LLMRunner._build_schema_repair_input(
        executor_type="claude_code",
        input_data=original_input,
        step=step,
        validation_error="decision is required",
        business_output={"review_type": "feat_review"},
        structured_payload=None,
    )

    assert repaired_input["goal"] != original_input["goal"]
    assert "decision is required" in repaired_input["goal"]
    assert repaired_input["max_iterations"] == 1
    assert repaired_input["allowed_commands"] == []
    assert repaired_input["write_scope"] == []


def test_merge_forbidden_read_paths_includes_default_blacklist():
    merged = LLMRunner._merge_forbidden_read_paths(["output/", "custom-history/"])

    assert merged == [
        "output/",
        "evidence/",
        ".workflow/claude-code/",
        "custom-history/",
    ]


def test_collect_authoritative_context_files_from_epic_freeze():
    step = SimpleNamespace(
        inputs=[
            {
                "source": "epic_freeze",
                "required": True,
            }
        ]
    )
    instance_data = {
        "params": {
            "epic_freeze": {
                "artifact_id": "EPIC-003",
                "path": "spec/requirements/epics/EPIC-003__lee-cli-workflow-first-zhilirukouzhonggou.md",
            }
        }
    }

    context_files = LLMRunner._collect_authoritative_context_files(step, instance_data)

    assert context_files == [
        "spec/requirements/epics/EPIC-003__lee-cli-workflow-first-zhilirukouzhonggou.md"
    ]


def test_merge_context_files_prefers_deduplicated_authoritative_inputs():
    merged = LLMRunner._merge_context_files(
        ["spec/requirements/epics/EPIC-003.md"],
        ["spec/requirements/epics/EPIC-003.md", "spec/source/SRC-001.md"],
    )

    assert merged == [
        "spec/requirements/epics/EPIC-003.md",
        "spec/source/SRC-001.md",
    ]


def test_normalize_prd_writer_feat_payload_synthesizes_ssot_outputs():
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-001",
        "feat_specs": [
            {
                "feat_id": "FEAT-001",
                "title": "CLI 治理入口",
                "goal": "规范 CLI 主入口",
                "user_value": "用户不再绕过治理链",
                "inputs": ["源需求"],
                "processing": ["校验", "路由"],
                "outputs": ["正式 FEAT 文档"],
                "acceptance_criteria": ["只能通过 workflow 创建"],
                "acceptance_checks": [
                    {
                        "id": "AC-001",
                        "scenario": "workflow 创建",
                        "given": "输入合法",
                        "when": "运行 workflow",
                        "then": "生成正式 FEAT",
                        "trace_hints": ["TASK", "TESTSET"],
                    }
                ],
                "dependencies": [],
                "non_goals": ["不修改旧 registry"],
                "source_refs": ["EPIC-001#scope"],
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "FEAT",
                    "parent": "EPIC-001",
                },
            }
        ],
    }

    normalized_business, normalized_structured = LLMRunner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-test",
        business_output=business_output,
        structured_payload={"business_output": business_output, "ssot_output_contract": {}},
    )

    assert normalized_business["epic_ref"] == "EPIC-001"
    outputs = normalized_structured["ssot_output_contract"]["outputs"]
    assert len(outputs) == 1
    assert outputs[0]["key"] == "feat"
    assert outputs[0]["ssot_type"] == "feat"
    assert outputs[0]["parent"] == "EPIC-001"
    assert outputs[0]["properties"]["feat_id"] == "FEAT-001"
    assert "# Goal" in outputs[0]["content"]


def test_normalize_prd_writer_feat_payload_overrides_epic_ref_from_instance_data():
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-HALLUCINATED",
        "feat_specs": [
            {
                "feat_id": "FEAT-001",
                "title": "CLI 治理入口",
                "goal": "规范 CLI 主入口",
                "user_value": "用户不再绕过治理链",
                "inputs": ["源需求"],
                "processing": ["校验"],
                "outputs": ["正式 FEAT 文档"],
                "acceptance_criteria": ["只能通过 workflow 创建"],
                "acceptance_checks": [
                    {
                        "id": "AC-001",
                        "scenario": "workflow 创建",
                        "given": "输入合法",
                        "when": "运行 workflow",
                        "then": "生成正式 FEAT",
                        "trace_hints": ["TASK", "TESTSET"],
                    },
                    {
                        "id": "AC-002",
                        "scenario": "source refs 对齐",
                        "given": "已有 EPIC",
                        "when": "生成 FEAT",
                        "then": "继承真实 EPIC",
                        "trace_hints": ["TASK"],
                    },
                ],
                "dependencies": [],
                "non_goals": [],
                "source_refs": ["EPIC-HALLUCINATED#scope"],
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "FEAT",
                    "parent": "EPIC-HALLUCINATED",
                    "derived_from": "EPIC-HALLUCINATED",
                },
            }
        ],
    }

    normalized_business, normalized_structured = LLMRunner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-test",
        business_output=business_output,
        structured_payload={"business_output": business_output, "ssot_output_contract": {}},
        instance_data={"params": {"epic_freeze": {"artifact_id": "EPIC-003"}}},
    )

    assert normalized_business["epic_ref"] == "EPIC-003"
    feat_spec = normalized_business["feat_specs"][0]
    assert feat_spec["ssot"]["parent"] == "EPIC-003"
    assert feat_spec["source_refs"] == ["EPIC-003#scope"]
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["parent"] == "EPIC-003"


def test_normalize_prd_writer_feat_payload_truncates_schema_limited_lists():
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-003",
        "feat_specs": [
            {
                "feat_id": "FEAT-003-007",
                "title": "Spec Governance Tooling",
                "goal": "通过 skill 引导 spec 维护进入正确治理流程",
                "user_value": "避免 spec 改动绕过治理",
                "inputs": ["Spec 修改请求"],
                "processing": ["识别类型", "路由", "review"],
                "outputs": ["Review 结果"],
                "user_stories": [
                    {"as_a": "开发者", "i_want": "得到引导", "so_that": "走正确流程"},
                    {"as_a": "维护者", "i_want": "收到正确请求", "so_that": "减少返工"},
                    {"as_a": "系统管理员", "i_want": "保持边界", "so_that": "治理一致"},
                    {"as_a": "审计者", "i_want": "看到链路", "so_that": "可追溯"},
                ],
                "acceptance_criteria": [
                    "识别 workflow spec 修改",
                    "识别 agent spec 修改",
                    "识别 contract spec 修改",
                    "识别 gate spec 修改",
                    "识别 skill spec 修改",
                    "识别 review spec 修改",
                    "路由到正确的 core maintainer",
                    "执行 spec-review",
                ],
                "acceptance_checks": [
                    {"id": "AC-001", "scenario": "1", "given": "a", "when": "b", "then": "c", "trace_hints": ["TECH"]},
                    {"id": "AC-002", "scenario": "2", "given": "a", "when": "b", "then": "c", "trace_hints": ["TECH"]},
                    {"id": "AC-003", "scenario": "3", "given": "a", "when": "b", "then": "c", "trace_hints": ["TECH"]},
                    {"id": "AC-004", "scenario": "4", "given": "a", "when": "b", "then": "c", "trace_hints": ["TECH"]},
                    {"id": "AC-005", "scenario": "5", "given": "a", "when": "b", "then": "c", "trace_hints": ["TECH"]},
                    {"id": "AC-006", "scenario": "6", "given": "a", "when": "b", "then": "c", "trace_hints": ["TECH"]},
                ],
                "dependencies": [],
                "non_goals": [],
                "source_refs": ["EPIC-003#scope"],
                "ssot": {"identity_kind": "ssot", "ssot_type": "FEAT", "parent": "EPIC-003"},
            }
        ],
    }

    normalized_business, _ = LLMRunner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-test",
        business_output=business_output,
        structured_payload={"business_output": business_output, "ssot_output_contract": {}},
    )

    feat_spec = normalized_business["feat_specs"][0]
    assert len(feat_spec["user_stories"]) == 3
    assert len(feat_spec["acceptance_criteria"]) == 5
    assert feat_spec["acceptance_criteria"][-1] == "识别 skill spec 修改"
    assert len(feat_spec["acceptance_checks"]) == 5
    assert feat_spec["acceptance_checks"][-1]["id"] == "AC-005"


def test_normalize_prd_writer_feat_payload_backfills_acceptance_check_required_fields():
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-003",
        "feat_specs": [
            {
                "feat_id": "FEAT-003-001",
                "title": "CLI help 统一",
                "goal": "统一 help 文档",
                "user_value": "避免入口混乱",
                "inputs": ["CLI help"],
                "processing": ["扫描", "更新"],
                "outputs": ["新 help"],
                "acceptance_criteria": ["主入口一致"],
                "acceptance_checks": [
                    {
                        "id": "AC-001",
                        "scenario": "查看帮助文档",
                        "given": "用户执行 lee --help",
                        "then": "看到 workflow-first 入口",
                    }
                ],
                "dependencies": [],
                "non_goals": [],
                "source_refs": ["EPIC-003#scope"],
                "ssot": {"identity_kind": "ssot", "ssot_type": "FEAT", "parent": "EPIC-003"},
            }
        ],
    }

    normalized_business, _ = LLMRunner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-test",
        business_output=business_output,
        structured_payload={"business_output": business_output, "ssot_output_contract": {}},
    )

    acceptance_check = normalized_business["feat_specs"][0]["acceptance_checks"][0]
    assert acceptance_check["id"] == "AC-001"
    assert acceptance_check["scenario"] == "查看帮助文档"
    assert acceptance_check["given"] == "用户执行 lee --help"
    assert acceptance_check["when"] == ""
    assert acceptance_check["then"] == "看到 workflow-first 入口"
    assert acceptance_check["trace_hints"] == ["TECH"]


def test_normalize_prd_writer_feat_payload_converts_null_user_stories_to_empty_list():
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-003",
        "feat_specs": [
            {
                "feat_id": "FEAT-003-100",
                "title": "空 user stories 兼容",
                "goal": "兼容 null user_stories",
                "user_value": "避免 schema 校验失败",
                "inputs": ["input"],
                "processing": ["process"],
                "outputs": ["output"],
                "user_stories": None,
                "acceptance_criteria": ["schema 可通过"],
                "acceptance_checks": [
                    {
                        "id": "AC-001",
                        "scenario": "校验",
                        "given": "存在 null user_stories",
                        "when": "归一化",
                        "then": "输出空数组",
                        "trace_hints": ["TECH"],
                    }
                ],
                "dependencies": [],
                "non_goals": [],
                "priority": "P0",
                "delivery_slice": "mvp",
                "lifecycle_status": "draft",
                "ssot": {"identity_kind": "ssot", "ssot_type": "FEAT", "parent": "EPIC-003"},
            }
        ],
    }

    normalized_business, _ = LLMRunner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-test",
        business_output=business_output,
        structured_payload={"business_output": business_output},
    )

    assert normalized_business["feat_specs"][0]["user_stories"] == []


def test_normalize_prd_writer_feat_payload_rebuilds_feat_specs_from_feature_breakdown():
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-012",
        "features": [
            {
                "id": "feat-adr012-001-raw-intake",
                "title": "Raw Input Intake - 原始输入接收",
                "description": "接收并验证多种格式的原始输入，实现输入类型的自动识别和基本验证。",
                "priority": "p0",
                "status": "draft",
                "parent_epic": "EPIC-012",
                "parent_workflow": "raw_to_src",
                "business_context": {
                    "problem": "需要统一接收不同来源、不同格式的原始输入",
                },
                "scope_boundary": {
                    "in_scope": [
                        "支持 raw_requirement 输入",
                        "支持 business_opportunity 输入",
                    ],
                    "out_of_scope": [
                        "不进行主题抽象",
                    ],
                },
                "acceptance_criteria": [
                    {
                        "criterion": "输入类型识别",
                        "description": "能正确识别三种输入类型",
                        "validation": "每种类型输入都能被正确分类",
                    },
                    {
                        "criterion": "格式验证",
                        "description": "能验证输入格式是否符合 schema",
                        "validation": "无效格式输入被拒绝并返回错误",
                    },
                ],
                "dependencies": [
                    {
                        "id": "EPIC-DEPENDENCY-001",
                    }
                ],
            }
        ],
    }

    normalized_business, normalized_structured = LLMRunner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-epic-to-feat",
        business_output=business_output,
        structured_payload={"business_output": business_output},
    )

    assert normalized_business["epic_ref"] == "EPIC-012"
    feat_spec = normalized_business["feat_specs"][0]
    assert feat_spec["feat_id"] == "feat-adr012-001-raw-intake"
    assert feat_spec["priority"] == "P0"
    assert feat_spec["delivery_slice"] == "raw_to_src"
    assert feat_spec["source_refs"] == ["EPIC-012#scope"]
    assert feat_spec["acceptance_criteria"] == [
        "能正确识别三种输入类型",
        "能验证输入格式是否符合 schema",
    ]
    assert len(feat_spec["acceptance_checks"]) == 2
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["properties"]["feat_id"] == "feat-adr012-001-raw-intake"


def test_normalize_prd_writer_feat_payload_rebuilds_feat_specs_from_feats_shape():
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-099",
        "feats": [
            {
                "id": "feat-099-001",
                "title": "输入契约定义",
                "goal": "定义 raw_to_src workflow 支持的三种原始输入类型及其格式规范",
                "priority": "p0",
                "input": ["epic_freeze (epic-099)"],
                "processing": ["分析三种输入类型的特征"],
                "output": ["input_type_definitions"],
                "acceptance_boundaries": [
                    "所有三种输入类型都能被正确鉴别",
                    "验证规则可独立执行",
                ],
                "non_goals": ["不实现具体的解析器"],
            }
        ],
    }

    normalized_business, _ = LLMRunner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-epic-to-feat",
        business_output=business_output,
        structured_payload={"business_output": business_output},
    )

    feat_spec = normalized_business["feat_specs"][0]
    assert feat_spec["feat_id"] == "feat-099-001"
    assert feat_spec["inputs"] == ["epic_freeze (epic-099)"]
    assert feat_spec["outputs"] == ["input_type_definitions"]
    assert feat_spec["acceptance_criteria"] == [
        "所有三种输入类型都能被正确鉴别",
        "验证规则可独立执行",
    ]


def test_normalize_prd_writer_feat_payload_rebuilds_feat_specs_from_epic_breakdown_bundle():
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer")
    business_output = {
        "id": "feat-breakdown-adr012-001",
        "epic_breakdowns": [
            {
                "epic_id": "EPIC-012",
                "features": [
                    {
                        "feat_id": "feat-adr012-001-001",
                        "title": "RAW 输入契约定义",
                        "description": "定义 raw_input 对象的结构、必填字段、类型约束和验证规则",
                        "priority": "p0",
                        "acceptance_criteria": [
                            "raw_input 对象包含所有必要字段",
                            "类型约束完整定义",
                        ],
                    }
                ],
            }
        ],
    }

    normalized_business, _ = LLMRunner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-epic-to-feat",
        business_output=business_output,
        structured_payload={"business_output": business_output},
        instance_data={"params": {"epic_freeze": {"artifact_id": "EPIC-012"}}},
    )

    assert normalized_business["epic_ref"] == "EPIC-012"
    feat_spec = normalized_business["feat_specs"][0]
    assert feat_spec["feat_id"] == "feat-adr012-001-001"
    assert feat_spec["goal"] == "定义 raw_input 对象的结构、必填字段、类型约束和验证规则"
    assert feat_spec["source_refs"] == ["EPIC-012#scope"]


def test_normalize_requirement_decomposer_payload_overrides_epic_ref():
    step = SimpleNamespace(id="feat_boundary_design", agent_id="agent.product.requirement_decomposer")
    business_output = {
        "breakdown_id": "feat-boundary-001",
        "epic_ref": "EPIC-HALLUCINATED",
        "feat_candidates": [{"title": "CLI", "user_value": "清晰", "acceptance_boundary": "可验收"}],
    }

    normalized_business, normalized_structured = LLMRunner._normalize_requirement_decomposer_payload(
        step=step,
        business_output=business_output,
        structured_payload={"business_output": business_output},
        instance_data={"params": {"epic_freeze_ref": {"artifact_id": "EPIC-003"}}},
    )

    assert normalized_business["epic_ref"] == "EPIC-003"
    assert normalized_structured["business_output"]["epic_ref"] == "EPIC-003"


def test_resolve_epic_ref_from_instance_data_reads_path_file(tmp_path):
    epic_path = tmp_path / "epic-freeze.yaml"
    epic_path.write_text(
        "\n".join(
            [
                "id: EPIC-PATH-001",
                "title: 路径解析测试",
            ]
        ),
        encoding="utf-8",
    )

    epic_ref = LLMRunner._resolve_epic_ref_from_instance_data(
        {
            "params": {
                "epic_freeze": str(epic_path),
            }
        }
    )

    assert epic_ref == "EPIC-PATH-001"


def test_normalize_prd_writer_feat_payload_wraps_placeholder_into_bundle_for_feat_generation():
    step = SimpleNamespace(
        id="feat_spec_generation",
        agent_id="agent.product.prd_writer",
        config={
            "output_contract": "departments/product/contracts/feat-bundle-contract/v1/schema.json",
        },
    )
    business_output = {
        "status": "success",
        "changed_files": [],
        "commands_run": [],
        "test_results": {"passed": 0, "failed": 0},
        "error": None,
    }

    normalized_business, _ = LLMRunner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-test",
        business_output=business_output,
        structured_payload={"business_output": business_output},
        instance_data={"params": {"epic_freeze": {"artifact_id": "EPIC-PLACEHOLDER-001"}}},
    )

    assert normalized_business["epic_ref"] == "EPIC-PLACEHOLDER-001"
    assert len(normalized_business["feat_specs"]) == 1
    assert normalized_business["feat_specs"][0]["feat_id"] == "EPIC-PLACEHOLDER-001-feat"
    assert normalized_business["feat_specs"][0]["ssot"]["parent"] == "EPIC-PLACEHOLDER-001"


def test_normalize_prd_writer_feat_payload_builds_envelope_without_structured_payload():
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "epic_symbolic_ref",
        "feat_specs": [
            {
                "feat_id": "FEAT-001",
                "title": "raw_to_src workflow 独立化",
                "goal": "提供 raw 到 SRC 的独立入口",
                "user_value": "调用方可以只产出 SRC",
                "inputs": ["raw requirement"],
                "processing": ["normalize source"],
                "outputs": ["frozen src"],
                "acceptance_criteria": ["可以独立产出 SRC"],
                "acceptance_checks": [
                    {
                        "id": "AC-001",
                        "scenario": "单独运行",
                        "given": "有 raw 输入",
                        "when": "执行 workflow",
                        "then": "输出 SRC",
                        "trace_hints": ["TECH"],
                    },
                    {
                        "id": "AC-002",
                        "scenario": "不依赖 EPIC",
                        "given": "只需要 SRC",
                        "when": "运行 workflow",
                        "then": "不会强制进入 EPIC",
                        "trace_hints": ["TECH"],
                    },
                ],
                "dependencies": [],
                "non_goals": [],
                "source_refs": ["epic_symbolic_ref#scope"],
                "ssot": {"identity_kind": "ssot", "ssot_type": "FEAT", "parent": "epic_symbolic_ref"},
            }
        ],
    }

    normalized_business, normalized_structured = LLMRunner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-test",
        business_output=business_output,
        structured_payload=None,
    )

    assert normalized_business["epic_ref"] == "epic_symbolic_ref"
    assert normalized_structured["business_output"]["feat_specs"][0]["feat_id"] == "FEAT-001"
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["key"] == "feat"
    assert "parent" not in normalized_structured["ssot_output_contract"]["outputs"][0]


def test_normalize_pm_planner_task_payload_converts_legacy_task_planning_view():
    step = SimpleNamespace(id="task_planning", agent_id="agent.product.pm_planner")
    business_output = {
        "task_planning": {
            "epic_ref": "EPIC-001",
            "created_at": "2026-03-11",
            "feat_tasks": [
                {
                    "feat_id": "FEAT-001",
                    "priority": "P0",
                    "implementation_plan": {
                        "phases": [
                            {
                                "phase_id": "M1",
                                "name": "Runtime",
                                "tasks": [
                                    {
                                        "task_id": "FEAT-001-T1",
                                        "title": "实现 raw_to_src workflow",
                                        "description": "新增独立 raw_to_src L3 workflow",
                                        "effort": "2 days",
                                        "assignee_role": "backend",
                                        "acceptance_criteria": [
                                            "能独立接收 raw 输入",
                                            "输出符合 source-freeze-contract",
                                        ],
                                        "dependencies": [],
                                    }
                                ],
                            }
                        ]
                    },
                }
            ],
            "risks": [
                {
                    "risk_id": "R001",
                    "description": "迁移调用方时可能漏改",
                    "mitigation": "提供兼容期迁移指南",
                }
            ],
        }
    }

    normalized_business, normalized_structured = LLMRunner._normalize_pm_planner_task_payload(
        step=step,
        workflow_id="wf-task",
        business_output=business_output,
        structured_payload=None,
    )

    assert normalized_business["parent_epic"] == "EPIC-001"
    assert normalized_business["source_feats"] == ["FEAT-001"]
    assert normalized_business["task_specs"][0]["task_id"] == "FEAT-001-T1"
    assert normalized_business["task_specs"][0]["source_feat"] == "FEAT-001"
    assert normalized_business["task_specs"][0]["ssot"]["parent"] == "FEAT-001"
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["ssot_type"] == "task"
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["parent"] == "FEAT-001"


@pytest.mark.asyncio
async def test_materialize_ssot_outputs_without_agent_schema_uses_default_contract_schema(tmp_path):
    runner = LLMRunner()
    agent_spec = SimpleNamespace(contracts={}, spec_path=str((Path.cwd() / "spec-global" / "departments" / "product" / "agents" / "product-goal-analyzer" / "v1" / "agent.yaml").resolve()))
    agent_loader = MagicMock()
    agent_loader.load.return_value = agent_spec
    ctx = RunnerContext(
        store=MagicMock(),
        state_machine=MagicMock(),
        event_log=MagicMock(),
        evidence_collector=MagicMock(),
        verifier_engine=MagicMock(),
        executor_factory=MagicMock(),
        agent_context_builder=SimpleNamespace(agent_loader=agent_loader),
        contract_discovery=MagicMock(),
        file_output_handler=SimpleNamespace(project_root=tmp_path),
        token_manager=MagicMock(),
        project_root=str(tmp_path),
    )
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    structured_payload = {
        "business_output": {
            "ssot_type": "SRC",
            "title": "LEE 产品需求链 workflow 分层拆分",
        },
        "ssot_output_contract": {
            "contract_version": "1.0",
            "run_id": "wf-src",
            "outputs": [
                {
                    "key": "src",
                    "identity_kind": "ssot",
                    "ssot_type": "src",
                    "title": "LEE 产品需求链 workflow 分层拆分",
                    "content": "# Source\n\nCanonical SRC\n",
                }
            ],
        },
    }

    result = await runner._materialize_ssot_outputs(
        ctx=ctx,
        step=step,
        workflow_id="wf-src",
        generated_text="",
        structured_payload=structured_payload,
    )

    assert result is not None
    assert result["outputs"]["src"]["id"] == "SRC-001"
    assert (tmp_path / "spec" / "source").exists()


def test_extract_business_output_for_validation_prefers_generated_text_over_wrapper():
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer", outputs=[])
    output = {
        "raw_output": '{"status":"success","generated_text":"ignored wrapper field"}',
        "generated_text": "business_output:\n  epic_ref: EPIC-003\n  feat_specs: []\nssot_output_contract:\n  contract_version: \"1.0\"\n  run_id: wf-test\n  outputs: []\n",
    }

    business_output, structured_payload = ClaudeCodeRunner._extract_business_output_for_validation(
        step=step,
        workflow_id="wf-test",
        output=output,
        written_files=[],
    )

    assert isinstance(business_output, dict)
    assert business_output["epic_ref"] == "EPIC-003"
    assert structured_payload["business_output"]["epic_ref"] == "EPIC-003"


def test_extract_business_output_for_validation_prefers_feat_breakdown_file_over_generic_summary(tmp_path):
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer", outputs=[])
    generic_path = tmp_path / "business_output.yaml"
    generic_path.write_text(
        "\n".join(
            [
                "kind: business_output",
                "problem: EPIC 粒度过大",
                "target: 将 EPIC 拆成 FEAT",
            ]
        ),
        encoding="utf-8",
    )
    breakdown_path = tmp_path / "feat_breakdown.yaml"
    breakdown_path.write_text(
        "\n".join(
            [
                "kind: feat_breakdown",
                "epic_ref: EPIC-012",
                "features:",
                "  - id: feat-adr012-001-raw-intake",
                "    title: Raw Input Intake",
                "    description: 接收并验证原始输入",
                "    priority: p0",
                "    parent_workflow: raw_to_src",
                "    acceptance_criteria:",
                "      - criterion: 输入类型识别",
                "        description: 正确识别输入类型",
                "      - criterion: 格式验证",
                "        description: 拒绝无效格式",
            ]
        ),
        encoding="utf-8",
    )
    output = {
        "raw_output": json.dumps(
            {
                "status": "success",
                "changed_files": ["business_output.yaml", "feat_breakdown.yaml"],
            },
            ensure_ascii=False,
        )
    }

    business_output, structured_payload = ClaudeCodeRunner._extract_business_output_for_validation(
        step=step,
        workflow_id="wf-test",
        output=output,
        written_files=[str(generic_path), str(breakdown_path)],
    )

    assert isinstance(structured_payload, dict)
    assert business_output["epic_ref"] == "EPIC-012"
    assert business_output["feat_specs"][0]["feat_id"] == "feat-adr012-001-raw-intake"
    assert business_output["feat_specs"][0]["priority"] == "P0"


def test_extract_business_output_for_validation_aggregates_single_feat_spec_files(tmp_path):
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer", outputs=[])
    first_feat_path = tmp_path / "feat-001.yaml"
    first_feat_path.write_text(
        "\n".join(
            [
                "kind: feat_specification",
                "id: FEAT-001",
                "epic_ref: EPIC-777",
                "title: 输入契约定义",
                "priority: p0",
                "objective: 定义输入契约",
                "status: ready",
            ]
        ),
        encoding="utf-8",
    )
    second_feat_path = tmp_path / "feat-002.yaml"
    second_feat_path.write_text(
        "\n".join(
            [
                "kind: feat_specification",
                "id: FEAT-002",
                "epic_ref: EPIC-777",
                "title: 输出契约定义",
                "priority: p1",
                "objective: 定义输出契约",
                "status: ready",
            ]
        ),
        encoding="utf-8",
    )
    output = {
        "raw_output": json.dumps(
            {
                "status": "success",
                "changed_files": ["feat-001.yaml", "feat-002.yaml"],
            },
            ensure_ascii=False,
        )
    }

    business_output, _ = ClaudeCodeRunner._extract_business_output_for_validation(
        step=step,
        workflow_id="wf-test",
        output=output,
        written_files=[str(first_feat_path), str(second_feat_path)],
    )

    assert business_output["epic_ref"] == "EPIC-777"
    assert [item["feat_id"] for item in business_output["feat_specs"]] == ["FEAT-001", "FEAT-002"]
    assert business_output["feat_specs"][0]["priority"] == "P0"
    assert business_output["feat_specs"][1]["priority"] == "P1"


def test_extract_business_output_for_validation_aggregates_parent_feat_spec_files(tmp_path):
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer", outputs=[])
    first_feat_path = tmp_path / "feat_001_raw_to_src_spec.json"
    first_feat_path.write_text(
        json.dumps(
            {
                "symbol_id": "feat_001_raw_to_src_spec",
                "title": "raw_to_src L3 workflow 独立化 - 详细规格",
                "parent_feat": "feat_001_raw_to_src",
                "parent_epic": "epic_lee_workflow_split_adr012",
                "priority": "P0",
                "specification": {
                    "overview": {
                        "summary": "建立独立的 raw_to_src workflow",
                    },
                    "functional_requirements": [
                        {
                            "requirement": "原始输入解析器",
                            "acceptance_criteria": ["支持 ADR 解析"],
                        }
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    second_feat_path = tmp_path / "feat_002_src_to_epic_spec.json"
    second_feat_path.write_text(
        json.dumps(
            {
                "symbol_id": "feat_002_src_to_epic_spec",
                "title": "src_to_epic L3 workflow 职责收窄 - 详细规格",
                "parent_feat": "feat_002_src_to_epic",
                "parent_epic": "epic_lee_workflow_split_adr012",
                "priority": "P0",
                "specification": {
                    "overview": {
                        "summary": "只处理冻结 SRC 到 EPIC",
                    },
                    "functional_requirements": [
                        {
                            "requirement": "冻结 SRC 输入验证",
                            "acceptance_criteria": ["拒绝非冻结 SRC"],
                        }
                    ],
                },
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    output = {
        "raw_output": json.dumps(
            {
                "status": "success",
                "changed_files": [
                    "feat_001_raw_to_src_spec.json",
                    "feat_002_src_to_epic_spec.json",
                ],
            },
            ensure_ascii=False,
        )
    }

    business_output, _ = ClaudeCodeRunner._extract_business_output_for_validation(
        step=step,
        workflow_id="wf-test",
        output=output,
        written_files=[str(first_feat_path), str(second_feat_path)],
    )

    assert business_output["epic_ref"] == "epic_lee_workflow_split_adr012"
    assert [item["feat_id"] for item in business_output["feat_specs"]] == [
        "feat_001_raw_to_src",
        "feat_002_src_to_epic",
    ]


def test_extract_business_output_for_validation_follows_deliverable_reference_to_breakdown(tmp_path):
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer", outputs=[])
    boundary_dir = tmp_path / "feat_boundary_design"
    boundary_dir.mkdir()
    breakdown_path = boundary_dir / "feat_breakdown.yaml"
    breakdown_path.write_text(
        "\n".join(
            [
                "kind: feat_breakdown",
                "epic_ref: EPIC-909",
                "feats:",
                "  - id: FEAT-909-001",
                "    title: 输入契约定义",
                "    goal: 定义 raw_to_src 的输入契约",
                "    priority: p0",
                "    input: [epic_freeze]",
                "    processing: [定义字段规范]",
                "    output: [input_contract]",
                "    acceptance_boundaries:",
                "      - 输入类型可被正确鉴别",
                "      - 验证规则可独立执行",
            ]
        ),
        encoding="utf-8",
    )
    generation_dir = tmp_path / "feat_spec_generation"
    generation_dir.mkdir()
    summary_path = generation_dir / "business_output.yaml"
    summary_path.write_text(
        "\n".join(
            [
                "kind: business_output",
                "deliverables:",
                "  - id: feat_breakdown_confirmation",
                "    file_path: ../feat_boundary_design/feat_breakdown.yaml",
            ]
        ),
        encoding="utf-8",
    )
    output = {
        "raw_output": json.dumps(
            {
                "status": "success",
                "changed_files": ["business_output.yaml"],
            },
            ensure_ascii=False,
        )
    }

    business_output, _ = ClaudeCodeRunner._extract_business_output_for_validation(
        step=step,
        workflow_id="wf-test",
        output=output,
        written_files=[str(summary_path)],
    )

    assert business_output["epic_ref"] == "EPIC-909"
    assert business_output["feat_specs"][0]["feat_id"] == "FEAT-909-001"
    assert business_output["feat_specs"][0]["outputs"] == ["input_contract"]


def test_extract_business_output_for_validation_falls_back_to_upstream_boundary_dir(tmp_path):
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer", outputs=[])
    workflow_dir = tmp_path / "wf_task_demo"
    generation_dir = workflow_dir / "feat_spec_generation"
    boundary_dir = workflow_dir / "feat_boundary_design"
    generation_dir.mkdir(parents=True)
    boundary_dir.mkdir(parents=True)

    (boundary_dir / "feat-breakdown.yaml").write_text(
        "\n".join(
            [
                "kind: feat_breakdown",
                "epic_ref: EPIC-UPSTREAM",
                "feats:",
                "  - id: FEAT-UP-001",
                "    title: 上游边界定义",
                "    goal: 直接复用 feat_boundary_design 结果",
                "    priority: p0",
                "    input: [epic_freeze]",
                "    processing: [边界拆解]",
                "    output: [feat_breakdown]",
                "    acceptance_boundaries:",
                "      - FEAT 边界清晰",
                "      - 可继续生成规格",
            ]
        ),
        encoding="utf-8",
    )
    placeholder_path = generation_dir / "business_output.yaml"
    placeholder_path.write_text(
        "\n".join(
            [
                "# FEAT Breakdown Placeholder",
                "",
                "No explicit FEAT candidates were extracted by the upstream agent.",
            ]
        ),
        encoding="utf-8",
    )
    output = {
        "raw_output": json.dumps(
            {
                "status": "success",
                "changed_files": ["business_output.yaml"],
            },
            ensure_ascii=False,
        )
    }

    business_output, _ = ClaudeCodeRunner._extract_business_output_for_validation(
        step=step,
        workflow_id="wf-test",
        output=output,
        written_files=[str(placeholder_path)],
    )

    assert business_output["epic_ref"] == "EPIC-UPSTREAM"
    assert business_output["feat_specs"][0]["feat_id"] == "FEAT-UP-001"


def test_normalize_product_review_payload_maps_feat_reviewer_wrapper():
    step = SimpleNamespace(id="feat_review", agent_id="agent.product.feat_reviewer")
    business_output = {
        "epic_ref": "epic_lee_workflow_split_adr012",
        "review_id": "feat-review-adr012-20260311",
        "status": "approved_with_recommendations",
        "review_summary": "已完成对全部 FEAT 规格的审查。",
        "feat_reviews": [
            {
                "feat_id": "feat_001_raw_to_src",
                "status": "approved",
                "notes": "规格完整",
            },
            {
                "feat_id": "feat_004_feat_to_delivery_prep",
                "status": "approved_with_notes",
                "notes": "建议拆分实现",
            },
        ],
        "recommendations": ["FEAT-004 建议拆分为两个迭代"],
    }

    normalized_business, normalized_structured = LLMRunner._normalize_product_review_payload(
        step=step,
        business_output=business_output,
        structured_payload={"business_output": business_output},
    )

    assert normalized_business["review_type"] == "feat_review"
    assert normalized_business["decision"] == "pass"
    assert normalized_business["summary"] == "已完成对全部 FEAT 规格的审查。"
    assert normalized_business["subject_refs"] == [
        "feat_001_raw_to_src",
        "feat_004_feat_to_delivery_prep",
    ]
    assert normalized_business["findings"] == []
    assert "建议拆分实现" in normalized_business["recommendations"]
    assert normalized_structured["business_output"]["review_type"] == "feat_review"


@pytest.mark.asyncio
async def test_attempt_schema_repair_for_claude_code_returns_repaired_payload():
    step = SimpleNamespace(id="feat_review", agent_id="agent.product.feat_reviewer")

    class FakeExecutor:
        async def execute(self, input_data):
            return {
                "status": "success",
                "generated_text": '{"business_output":{"review_id":"RVW-001","review_type":"feat_review","subject_refs":["FEAT-001"],"summary":"ok","findings":[],"decision":"pass","risks":[],"recommendations":[]}}',
                "raw_output": "",
            }

    runner = LLMRunner()
    repaired = await runner._attempt_schema_repair(
        executor=FakeExecutor(),
        executor_type="claude_code",
        input_data={"goal": "x", "workspace": ".", "max_iterations": 5},
        step=step,
        workflow_id="wf-test",
        validation_error="decision is required",
        business_output={
            "review_id": "RVW-001",
            "review_type": "feat_review",
            "subject_refs": ["FEAT-001"],
            "summary": "ok",
            "findings": [],
            "risks": [],
            "recommendations": [],
        },
        structured_payload=None,
    )

    assert repaired is not None
    assert repaired["business_output"]["decision"] == "pass"
