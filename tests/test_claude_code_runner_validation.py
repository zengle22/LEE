from __future__ import annotations

import pytest

from lee.orchestrator.execution.runners.llm_runner import ClaudeCodeRunner, LLMRunner
from types import SimpleNamespace


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
