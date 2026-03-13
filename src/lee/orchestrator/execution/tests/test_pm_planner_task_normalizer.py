from __future__ import annotations

from types import SimpleNamespace

from lee.orchestrator.execution.runners.llm_runner import LLMRunner
from lee.orchestrator.execution.runners.normalization import PmPlannerTaskNormalizer


def test_pm_planner_task_normalizer_converts_task_plan_yaml_tasks(tmp_path):
    feat_freeze = tmp_path / "feat-freeze.yaml"
    feat_freeze.write_text(
        """
epic_ref: EPIC-012
feat_specs:
  - feat_specifications:
      - feat_id: FEAT-012-001
        title: raw_to_src L3 Workflow 定义
""".strip(),
        encoding="utf-8",
    )

    step = SimpleNamespace(agent_id="agent.product.pm_planner")
    business_output = {
        "metadata": {"epic_id": "EPIC-012"},
        "overview": {
            "groups": [
                {"group_id": "G1", "name": "基础能力", "tasks": ["T-001"]},
            ]
        },
        "tasks": [
            {
                "task_id": "T-001",
                "title": "实现 raw_to_src 核心服务",
                "feat_ref": "FEAT-012-001",
                "assignee_role": "backend_developer",
                "priority": "high",
                "story_points": 3,
                "description": "实现 workflow 运行时主逻辑。",
                "acceptance_criteria": ["raw_to_src workflow 可执行"],
                "dependencies": {"upstream": []},
            }
        ],
    }

    normalized_business, normalized_structured = PmPlannerTaskNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        workflow_id="wf-001",
        business_output=business_output,
        structured_payload={"business_output": business_output},
        instance_data={"params": {"feat_freeze": str(feat_freeze)}},
    )

    assert normalized_business["parent_epic"] == "EPIC-012"
    assert normalized_business["task_specs"][0]["title"] == "实现 raw_to_src 核心服务"
    assert normalized_business["task_specs"][0]["source_feat"] == "FEAT-012-001"
    assert normalized_business["task_specs"][0]["milestone"] == "G1"
    assert normalized_structured["ssot_output_contract"]["outputs"]


def test_pm_planner_task_normalizer_builds_task_markdown_content():
    step = SimpleNamespace(agent_id="agent.product.pm_planner")
    business_output = {
        "parent_epic": "EPIC-004",
        "source_feats": ["FEAT-085"],
        "task_specs": [
            {
                "task_id": "TASK-FEAT-085-001",
                "title": "流式输出引擎实现",
                "objective": "实现流式输出引擎",
                "description": "建立 stdout/stderr 流式输出管道",
                "source_feat": "FEAT-085",
                "workstream": "cli-execution-runtime",
                "task_kind": "implementation",
                "responsible_role": "cli-runtime-engineer",
                "acceptance_criteria_mapping": [
                    {
                        "feat": "FEAT-085",
                        "ac": "AC-00401-001",
                        "description": "首字节输出延迟 <= 500ms",
                    }
                ],
                "dependencies": ["TASK-FEAT-000-001"],
                "definition_of_done": ["核心类实现完成"],
                "priority": "P0",
                "milestone": "M1",
                "estimated_effort": "3 days",
                "lifecycle_status": "draft",
                "observability": {
                    "execution_unit": "task",
                    "log_scope": "streaming-execution",
                    "audit_fields": ["run_id"],
                },
                "evidence_requirements": {
                    "required_refs": ["TECH-FEAT-085"],
                    "review_required": True,
                },
                "rollback_strategy": {
                    "mode": "revert",
                    "restore_targets": ["src/lee/executor/streaming"],
                },
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "TASK",
                    "parent": "FEAT-085",
                    "derived_from": "FEAT-085#delivery",
                },
            }
        ],
    }

    normalized_business, normalized_structured = PmPlannerTaskNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        workflow_id="wf-task-004",
        business_output=business_output,
        structured_payload={"business_output": business_output},
    )

    assert normalized_business["task_specs"][0]["source_feat"] == "FEAT-085"
    outputs = normalized_structured["ssot_output_contract"]["outputs"]
    assert len(outputs) == 1
    assert outputs[0]["parent"] == "FEAT-085"
    assert outputs[0]["source_refs"] == ["FEAT-085#delivery"]
    assert "# Objective" in outputs[0]["content"]
    assert "## Acceptance Mapping" in outputs[0]["content"]
    assert "## Definition Of Done" in outputs[0]["content"]
