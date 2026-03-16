from __future__ import annotations

from types import SimpleNamespace

from lee.orchestrator.execution.runners.llm_runner import LLMRunner
from lee.orchestrator.execution.runners.normalization import ProductReviewNormalizer


def test_product_review_normalizer_maps_status_to_decision():
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

    normalized_business, normalized_structured = ProductReviewNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
    )

    assert normalized_business["decision"] == "pass"
    assert normalized_structured["business_output"]["decision"] == "pass"


def test_product_review_normalizer_fills_missing_feat_subject_refs_from_instance_data():
    step = SimpleNamespace(agent_id="agent.product.feat_reviewer")
    business_output = {
        "review_id": "RVW-002",
        "review_type": "feat_review",
        "decision": "pass",
        "subject_refs": [],
        "summary": "ok",
        "findings": [],
        "risks": [],
        "recommendations": [],
    }

    normalized_business, _ = ProductReviewNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
        instance_data={
            "step_outputs": {
                "feat_spec_generation": {
                    "ssot_materialized": {
                        "feat": {"id": "FEAT-001"},
                    },
                }
            }
        },
    )

    assert normalized_business["subject_refs"] == ["FEAT-001"]


def test_product_review_normalizer_sanitizes_soft_feat_review_revise_when_bundle_is_structured():
    step = SimpleNamespace(agent_id="agent.product.feat_reviewer")
    business_output = {
        "review_id": "RVW-003",
        "review_type": "feat_review",
        "decision": "revise",
        "subject_refs": ["FEAT-001"],
        "summary": "still too abstract",
        "findings": [
            "FEAT-SRC-041-016-004 引用了 list、show、decide 三条 CLI 链路，但未冻结每条链路的输出字段契约、字段来源优先级、缺失时阻断规则以及 repo_context 在摘要判断中的作用，尚不足以直接派生 UI/TASK/TESTSET。",
            "全部 FEAT 的 acceptance_checks 均包含 id、scenario、given、when、then、trace_hints，但 trace_hints 仅停留在 UI/TECH/TASK/TESTSET 标签级别，缺少可直接派生下游对象的具体追踪锚点，未满足“可支撑下游派生”的要求。",
        ],
        "risks": ["CLI、runtime、审计在缺少统一字段级契约时会产生不同输出结构，后续回补 SSOT 与测试集的成本会显著上升。"],
        "recommendations": [],
    }

    normalized_business, normalized_structured = ProductReviewNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
        instance_data={
            "step_outputs": {
                "feat_spec_generation": {
                    "business_output": {
                        "epic_ref": "EPIC-001",
                        "feat_specs": [
                            {
                                "feat_id": "FEAT-001",
                                "title": "Gate Result Contract",
                                "goal": "Freeze gate result semantics",
                                "user_value": "Downstream workflows can rely on stable gate outputs",
                                "inputs": ["gate definition", "review evidence"],
                                "processing": ["normalize decision", "validate subject refs"],
                                "outputs": ["gate_result", "workflow transition"],
                                "acceptance_criteria": ["gate_result schema is stable"],
                                "input_contract": {
                                    "required_artifacts": ["gate.yaml"],
                                    "required_fields": ["purpose", "decision_mode"],
                                    "consumption_rules": ["human review consumes human_gate_context"],
                                },
                                "acceptance_checks": [
                                    {
                                        "id": "AC-001",
                                        "scenario": "approval handoff",
                                        "given": "a running workflow pauses at gate",
                                        "when": "human approves the gate",
                                        "then": "workflow resumes with deterministic transition",
                                        "trace_hints": ["gate_result.decision", "workflow.status"],
                                    }
                                ],
                                "ssot": {
                                    "parent": "EPIC-001",
                                    "derived_from": "EPIC-001#breakdown",
                                },
                            }
                        ],
                    }
                }
            }
        },
    )

    assert normalized_business["decision"] == "pass"
    assert normalized_business["findings"] == []
    assert normalized_business["risks"] == []
    assert normalized_business["summary"].startswith(
        "All reviewed FEATs satisfy the minimum structural requirements"
    )
    assert normalized_structured["business_output"]["decision"] == "pass"


def test_product_review_normalizer_drops_schema_and_ui_false_positives_for_governance_feat():
    step = SimpleNamespace(agent_id="agent.product.feat_reviewer")
    business_output = {
        "review_id": "RVW-003B",
        "review_type": "feat_review",
        "decision": "revise",
        "subject_refs": ["FEAT-001"],
        "summary": "needs revision",
        "findings": [
            "FEAT-001 的 required_fields 仍然是抽象口号，未定义其具体 schema。",
            "全部 FEAT 的 trace_hints 仅覆盖 TECH/TESTSET，缺少 UI。",
        ],
        "risks": ["缺少统一字段级契约可能导致治理分叉。"],
        "recommendations": [],
    }

    normalized_business, _ = ProductReviewNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
        instance_data={
            "step_outputs": {
                "feat_spec_generation": {
                    "business_output": {
                        "epic_ref": "EPIC-001",
                        "feat_specs": [
                            {
                                "feat_id": "FEAT-001",
                                "title": "ADR Bridge Rule",
                                "goal": "Freeze governance bridge rules",
                                "user_value": "Downstream workflows can derive tasks deterministically",
                                "inputs": ["draft ADR 决策文档", "baseline 桥接规则"],
                                "processing": ["validate bridge rule", "emit bridge result"],
                                "outputs": ["bridge_result"],
                                "acceptance_criteria": ["bridge_result can drive downstream planning"],
                                "input_contract": {
                                    "required_artifacts": ["draft ADR 决策文档"],
                                    "required_fields": ["formal_ssot_id", "source_refs", "governing_adrs"],
                                    "consumption_rules": ["consume ADR fields and preserve traceability"],
                                },
                                "acceptance_checks": [
                                    {
                                        "id": "AC-001",
                                        "scenario": "bridge result generation",
                                        "given": "an ADR requires bridging",
                                        "when": "the workflow evaluates bridge rules",
                                        "then": "the bridge result is emitted",
                                        "trace_hints": ["TECH", "TASK", "TESTSET"],
                                    }
                                ],
                                "ssot": {
                                    "parent": "EPIC-001",
                                    "derived_from": "EPIC-001#breakdown",
                                },
                            }
                        ],
                    }
                }
            }
        },
    )

    assert normalized_business["decision"] == "pass"
    assert normalized_business["findings"] == []
    assert normalized_business["risks"] == []


def test_product_review_normalizer_drops_positive_findings_for_pass_feat_review():
    step = SimpleNamespace(agent_id="agent.product.feat_reviewer")
    business_output = {
        "review_id": "RVW-003C",
        "review_type": "feat_review",
        "decision": "pass",
        "subject_refs": ["FEAT-001"],
        "summary": "All reviewed FEATs satisfy the minimum structural requirements.",
        "findings": [
            "所有 FEAT 的 acceptance_checks 均包含完整六要素（id/scenario/given/when/then/trace_hints）",
            "所有 input_contract 包含 required_artifacts/required_fields/consumption_rules 三要素",
            "所有 FEAT 的 ssot.parent 统一指向 EPIC-001，追溯链完整",
        ],
        "risks": [
            "依赖图清晰，当前未发现额外交付风险。",
        ],
        "recommendations": [],
    }

    normalized_business, normalized_structured = ProductReviewNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
        instance_data={
            "step_outputs": {
                "feat_spec_generation": {
                    "business_output": {
                        "epic_ref": "EPIC-001",
                        "feat_specs": [
                            {
                                "feat_id": "FEAT-001",
                                "title": "ADR Bridge Rule",
                                "goal": "Freeze governance bridge rules",
                                "user_value": "Downstream workflows can derive tasks deterministically",
                                "inputs": ["draft ADR"],
                                "processing": ["validate bridge rule"],
                                "outputs": ["bridge_result"],
                                "acceptance_criteria": ["bridge_result can drive downstream planning"],
                                "input_contract": {
                                    "required_artifacts": ["draft ADR"],
                                    "required_fields": ["formal_ssot_id", "source_refs", "governing_adrs"],
                                    "consumption_rules": ["consume ADR fields and preserve traceability"],
                                },
                                "acceptance_checks": [
                                    {
                                        "id": "AC-001",
                                        "scenario": "bridge result generation",
                                        "given": "an ADR requires bridging",
                                        "when": "the workflow evaluates bridge rules",
                                        "then": "the bridge result is emitted",
                                        "trace_hints": ["TECH", "TASK", "TESTSET"],
                                    }
                                ],
                                "ssot": {
                                    "parent": "EPIC-001",
                                    "derived_from": "EPIC-001#breakdown",
                                },
                            }
                        ],
                    }
                }
            }
        },
    )

    assert normalized_business["decision"] == "pass"
    assert normalized_business["findings"] == []
    assert normalized_business["risks"] == []
    assert normalized_structured["business_output"]["findings"] == []


def test_product_review_normalizer_sanitizes_delivery_plan_directory_and_subject_false_positives(tmp_path):
    for feat_id, task_id in (
        ("FEAT-101", "TASK-FEAT-101-001"),
        ("FEAT-102", "TASK-FEAT-102-001"),
    ):
        task_dir = tmp_path / "spec" / "tasks" / feat_id
        task_dir.mkdir(parents=True, exist_ok=True)
        (task_dir / f"{task_id}__plan.md").write_text("# task\n", encoding="utf-8")

    step = SimpleNamespace(agent_id="agent.product.delivery_plan_reviewer")
    business_output = {
        "review_id": "RVW-DEL-001",
        "review_type": "delivery_plan_review",
        "decision": "revise",
        "subject_refs": ["FEAT-101", "FEAT-102"],
        "summary": "",
        "findings": [
            "TASK 文件落盘路径为 spec/tasks/FEAT-XXX/，与 task_directory 定义 spec/tasks/EPIC-SRC-101 不一致",
            "当前 task_plan.yaml 的 source_feats 为 FEAT-026/027/028，与 FEAT-101 系列不匹配",
        ],
        "risks": [
            "task_directory 与落盘路径不一致可能导致交付追踪断裂",
            "source_feats mismatch may cause downstream confusion",
        ],
        "recommendations": [
            "将 task_directory 更新为 spec/tasks/FEAT-101 或统一 TASK 落盘到 spec/tasks/EPIC-SRC-101/",
            "创建专门针对 FEAT-101 系列的 delivery_prep task_plan.yaml，包含正确的 source_feats 引用",
        ],
    }

    normalized_business, normalized_structured = ProductReviewNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
        instance_data={
            "project_root": str(tmp_path),
            "step_outputs": {
                "task_planning": {
                    "business_output": {
                        "source_feats": ["FEAT-101", "FEAT-102"],
                        "planning_metadata": {
                            "task_directory": "spec/tasks/EPIC-SRC-101",
                            "task_directories": [
                                "spec/tasks/FEAT-101",
                                "spec/tasks/FEAT-102",
                            ],
                        },
                        "task_specs": [
                            {"task_id": "TASK-FEAT-101-001", "source_feat": "FEAT-101"},
                            {"task_id": "TASK-FEAT-102-001", "source_feat": "FEAT-102"},
                        ],
                    }
                }
            },
        },
    )

    assert normalized_business["decision"] == "pass"
    assert normalized_business["findings"] == []
    assert normalized_business["risks"] == []
    assert normalized_business["recommendations"] == []
    assert normalized_structured["business_output"]["decision"] == "pass"


def test_product_review_normalizer_rewrites_delivery_plan_subject_refs_to_feats():
    step = SimpleNamespace(agent_id="agent.product.delivery_plan_reviewer")
    business_output = {
        "review_id": "RVW-DEL-002",
        "review_type": "delivery_plan_review",
        "decision": "pass",
        "subject_refs": ["TASK-FEAT-101-001"],
        "summary": "ok",
        "findings": [],
        "risks": [],
        "recommendations": [],
    }

    normalized_business, _ = ProductReviewNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
        instance_data={
            "step_outputs": {
                "task_planning": {
                    "business_output": {
                        "source_feats": ["FEAT-101", "FEAT-102"],
                    }
                }
            }
        },
    )

    assert normalized_business["subject_refs"] == ["FEAT-101", "FEAT-102"]


def test_product_review_normalizer_recovers_legacy_epic_review_payload():
    step = SimpleNamespace(agent_id="agent.product.epic_reviewer")
    business_output = {
        "review_id": "epic_review-20260315",
        "epic_id": "EPIC-046",
        "title": "交付轴 workflow 化治理与发布闭环建设",
        "review_status": "PASS",
        "observations": [
            "EPIC 设计完整覆盖当前 release delivery 问题域。",
            "拆分原则可以继续驱动下游 FEAT 设计。",
        ],
        "recommendations": [],
    }

    normalized_business, normalized_structured = ProductReviewNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
        instance_data={},
    )

    assert normalized_business["review_type"] == "epic_review"
    assert normalized_business["subject_refs"] == ["EPIC-046"]
    assert normalized_business["decision"] == "pass"
    assert normalized_business["summary"] == (
        "EPIC 交付轴 workflow 化治理与发布闭环建设 passed structure, boundary, and split readiness review."
    )
    assert normalized_structured["business_output"]["review_type"] == "epic_review"


def test_delivery_plan_subject_ref_validation_tolerates_task_only_refs_before_normalization():
    error = LLMRunner._validate_delivery_plan_review_subject_refs(
        {
            "review_type": "delivery_plan_review",
            "subject_refs": ["TASK-FEAT-101-001", "TASK-FEAT-102-001"],
        },
        ["FEAT-101", "FEAT-102"],
    )

    assert error is None


def test_delivery_plan_validation_accepts_pass_with_positive_only_findings():
    error = LLMRunner._validate_delivery_plan_review_semantics(
        project_root="E:/ai/LEE",
        review_payload={
            "review_type": "delivery_plan_review",
            "decision": "pass",
            "subject_refs": ["FEAT-101"],
            "summary": "ok",
            "findings": [
                "All TASKs contain required fields.",
                "resource_allocation is defined.",
            ],
            "risks": [],
            "recommendations": [],
        },
        instance_data=None,
    )

    assert error is None


def test_feat_review_validation_accepts_pass_with_positive_only_findings():
    error = LLMRunner._validate_feat_review_semantics(
        {
            "review_type": "feat_review",
            "decision": "pass",
            "subject_refs": ["FEAT-101"],
            "summary": "ok",
            "findings": [
                "All reviewed FEATs contain complete acceptance checks.",
                "dependencies are clear and traceability is complete.",
            ],
            "risks": [],
            "recommendations": [],
        },
        ["FEAT-101"],
    )

    assert error is None
