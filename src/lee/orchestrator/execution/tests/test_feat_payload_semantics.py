from lee.orchestrator.execution.runners.normalization.feat_payload_semantics import (
    align_inputs_with_required_artifacts,
    align_required_artifacts,
    refine_acceptance_checks,
    refine_feat_outputs,
)


def test_refine_feat_outputs_rewrites_meta_spec_outputs_into_concrete_deliverables():
    outputs = ["ADR 桥接触发规则判断逻辑 FEAT specification"]
    acceptance_criteria = [
        "输入 ADR 对象后输出是否需要桥接 SRC 的布尔判断结果",
        "包含完整的触发条件列表与判断规则文档",
    ]
    processing = [
        "匹配预定义的桥接触发条件规则集",
        "记录判断日志用于审计追踪",
    ]

    refined = refine_feat_outputs(
        outputs,
        title="ADR 桥接触发规则判断逻辑",
        goal="建立 ADR 桥接 SRC 的触发条件与判断规则引擎",
        acceptance_criteria=acceptance_criteria,
        processing=processing,
    )

    assert "是否需要桥接 SRC 的布尔判断结果" in refined
    assert "execution audit log" in refined
    assert all("FEAT specification" not in item for item in refined)


def test_align_required_artifacts_rewrites_schema_inputs_when_non_goals_reserve_final_freeze():
    artifacts = ["bridge SRC schema 定义", "冻结后的 ADR 对象"]
    non_goals = ["bridge SRC 的最终 schema 字段名冻结"]

    aligned = align_required_artifacts(artifacts, non_goals)

    assert aligned[0] == "bridge SRC schema 基线"
    assert aligned[1] == "冻结后的 ADR 对象"


def test_align_required_artifacts_rewrites_delivery_schema_to_draft_when_scope_is_not_final():
    artifacts = ["交付轴对象 schema 定义", "version pin 机制规格文档"]
    non_goals = ["交付轴对象的完整 schema 定义"]

    aligned = align_required_artifacts(artifacts, non_goals)

    assert aligned[0] == "交付轴对象 schema 草案"
    assert aligned[1] == "version pin 机制规格文档"


def test_align_inputs_with_required_artifacts_prefers_versioned_upstream_artifacts():
    inputs = ["EPIC 注册表 schema 定义", "校验规则配置", "新增 EPIC 注册请求"]
    required_artifacts = ["baseline EPIC 注册表 schema", "draft 校验规则配置"]

    aligned = align_inputs_with_required_artifacts(inputs, required_artifacts)

    assert aligned[0] == "baseline EPIC 注册表 schema"
    assert aligned[1] == "draft 校验规则配置"
    assert aligned[2] == "新增 EPIC 注册请求"


def test_refine_acceptance_checks_adds_scope_relevant_trace_hints_for_governance_feats():
    checks = [
        {
            "id": "AC-001",
            "scenario": "bridge validation",
            "given": "an ADR needs bridging",
            "when": "the workflow evaluates trigger rules",
            "then": "the bridge result is emitted",
            "trace_hints": ["TESTSET"],
        }
    ]

    refined = refine_acceptance_checks(
        checks,
        title="ADR 桥接触发条件规则定义",
        goal="建立 workflow 治理桥接规则",
        outputs=["桥接触发判断结果文档"],
        processing=["执行桥接规则校验"],
        derived_object_expectations={"task_required": True, "testset_required": True},
    )

    assert refined[0]["trace_hints"] == ["TECH", "TASK", "TESTSET"]
