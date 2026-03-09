import shutil
import tempfile
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lee.orchestrator.execution.runners.base import RunnerContext
from lee.orchestrator.execution.runners.llm_runner import LLMRunner
from lee.orchestrator.storage.models import StepResult


@pytest.fixture
def temp_project_root():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def runner():
    return LLMRunner()


@pytest.fixture
def ctx(temp_project_root):
    agent_spec = SimpleNamespace(
        contracts={
            "ssot_output_schema": str(
                (Path.cwd() / "spec-global" / "core" / "contracts" / "ssot-agent-output" / "v1" / "schema.json").resolve()
            )
        },
        governance={
            "acceptance_briefs": str((Path.cwd() / ".project" / "governance" / "ACCEPTANCE_BRIEFS").resolve()),
            "module_contracts": str((Path.cwd() / ".project" / "governance" / "MODULE_CONTRACTS").resolve()),
            "completion_template": str((Path.cwd() / ".project" / "governance" / "COMPLETION_TEMPLATE.md").resolve()),
        },
        tags=["product", "prd"],
        spec_path=str((Path.cwd() / "spec-global" / "departments" / "prd" / "agents" / "prd-writer" / "v1" / "agent.yaml").resolve()),
    )
    agent_loader = MagicMock()
    agent_loader.load.return_value = agent_spec
    agent_context_builder = SimpleNamespace(agent_loader=agent_loader)

    return RunnerContext(
        store=MagicMock(),
        state_machine=MagicMock(),
        event_log=MagicMock(),
        evidence_collector=MagicMock(),
        verifier_engine=MagicMock(),
        executor_factory=MagicMock(),
        agent_context_builder=agent_context_builder,
        contract_discovery=MagicMock(),
        file_output_handler=SimpleNamespace(project_root=temp_project_root),
        token_manager=MagicMock(),
        project_root=str(temp_project_root),
    )


@pytest.mark.asyncio
async def test_materialize_ssot_outputs_from_agent_contract(runner, ctx, temp_project_root):
    step = SimpleNamespace(
        id="write_prd",
        agent_id="agent.product.prd_writer",
        config={},
    )

    generated_text = """
{
  "contract_version": "1.0",
  "run_id": "run-ssot-001",
  "outputs": [
    {
      "key": "epic",
      "identity_kind": "ssot",
      "ssot_type": "epic",
      "title": "增长基础设施",
      "source_refs": ["SRC-001#1.2"]
    },
    {
      "key": "feat",
      "identity_kind": "ssot",
      "ssot_type": "feat",
      "title": "用户注册",
      "parent": "epic",
      "source_refs": ["epic#scope"]
    }
  ]
}
""".strip()

    result = await runner._materialize_ssot_outputs(
        ctx=ctx,
        step=step,
        workflow_id="wf-001",
        generated_text=generated_text,
    )

    assert result is not None
    assert result["outputs"]["epic"]["id"] == "EPIC-001"
    assert result["outputs"]["feat"]["parent_id"] == "EPIC-001"
    assert len(result["materialized_files"]) == 2
    assert (temp_project_root / "spec" / "requirements" / "epics").exists()
    assert (temp_project_root / "spec" / "requirements" / "features").exists()


@pytest.mark.asyncio
async def test_materialize_ssot_outputs_from_envelope_payload(runner, ctx, temp_project_root):
    step = SimpleNamespace(
        id="write_prd",
        agent_id="agent.product.prd_writer",
        config={},
    )

    generated_text = """
{
  "business_output": {
    "metadata": {
      "is_frozen": true
    }
  },
  "ssot_output_contract": {
    "contract_version": "1.0",
    "run_id": "run-ssot-002",
    "outputs": [
      {
        "key": "feat",
        "identity_kind": "ssot",
        "ssot_type": "feat",
        "title": "用户注册"
      }
    ]
  }
}
""".strip()

    structured_payload = runner._parse_structured_output_if_possible(generated_text)
    business_output = runner._extract_business_output_payload(structured_payload, generated_text)

    assert business_output == {"metadata": {"is_frozen": True}}

    result = await runner._materialize_ssot_outputs(
        ctx=ctx,
        step=step,
        workflow_id="wf-001",
        generated_text=generated_text,
        structured_payload=structured_payload,
    )

    assert result is not None
    assert result["outputs"]["feat"]["id"] == "FEAT-001"
    assert len(result["materialized_files"]) == 1
    assert (temp_project_root / "spec" / "requirements" / "features").exists()


@pytest.mark.asyncio
async def test_materialize_ssot_outputs_ignores_self_referential_bundle_dependencies(
    runner, ctx, temp_project_root
):
    step = SimpleNamespace(
        id="write_prd",
        agent_id="agent.product.prd_writer",
        config={},
    )

    generated_text = """
{
  "business_output": {
    "epic_ref": "EPIC-DEMO-001",
    "feat_specs": [
      {
        "feat_id": "FEAT-900",
        "title": "训练计划智能调整",
        "goal": "根据用户参数生成训练计划",
        "user_value": "快速开始训练",
        "inputs": ["比赛目标"],
        "processing": ["生成周期化计划"],
        "outputs": ["训练计划"],
        "acceptance_criteria": ["系统生成训练计划"],
        "acceptance_checks": [
          {
            "id": "AC-001",
            "scenario": "系统生成训练计划",
            "given": "用户已填写参数",
            "when": "提交生成请求",
            "then": "系统返回训练计划",
            "trace_hints": ["TASK", "TESTSET"]
          },
          {
            "id": "AC-002",
            "scenario": "返回结构化计划",
            "given": "系统已完成计算",
            "when": "查看计划详情",
            "then": "结果包含按周拆分内容",
            "trace_hints": ["TECH", "TESTSET"]
          }
        ],
        "dependencies": [],
        "non_goals": [],
        "priority": "P1",
        "delivery_slice": "mvp",
        "lifecycle_status": "draft",
        "ssot": {
          "identity_kind": "ssot",
          "ssot_type": "FEAT",
          "parent": "EPIC-DEMO-001"
        }
      }
    ]
  },
  "ssot_output_contract": {
    "contract_version": "1.0",
    "run_id": "run-ssot-003",
    "outputs": [
      {
        "key": "feat_900",
        "identity_kind": "ssot",
        "ssot_type": "feat",
        "title": "训练计划智能调整",
        "parent": "feat_900",
        "derived_from": ["feat_900"],
        "source_refs": ["feat_900#scope"]
      }
    ]
  }
}
""".strip()

    structured_payload = runner._parse_structured_output_if_possible(generated_text)

    result = await runner._materialize_ssot_outputs(
        ctx=ctx,
        step=step,
        workflow_id="wf-001",
        generated_text=generated_text,
        structured_payload=structured_payload,
    )

    assert result is not None
    assert result["outputs"]["feat_900"]["id"] == "FEAT-001"
    assert len(result["materialized_files"]) == 1


@pytest.mark.asyncio
async def test_materialize_ssot_outputs_does_not_treat_source_file_refs_as_contract_dependencies(
    runner, ctx, temp_project_root
):
    step = SimpleNamespace(
        id="write_prd",
        agent_id="agent.product.prd_writer",
        config={},
    )

    generated_text = """
{
  "business_output": {
    "epic_ref": "EPIC-DEMO-001",
    "feat_specs": [
      {
        "feat_id": "FEAT-EPIC-DEMO-001-001",
        "title": "比赛目标与约束条件配置",
        "goal": "采集用户训练参数作为计划生成输入",
        "user_value": "用户可设定个性化训练基准参数",
        "inputs": ["比赛类型"],
        "processing": ["校验输入"],
        "outputs": ["结构化配置数据"],
        "acceptance_criteria": ["可保存配置"],
        "acceptance_checks": [
          {
            "id": "AC-001",
            "scenario": "保存配置",
            "given": "用户已填写参数",
            "when": "提交保存",
            "then": "系统保存成功",
            "trace_hints": ["UI", "TESTSET"]
          },
          {
            "id": "AC-002",
            "scenario": "日期校验",
            "given": "用户输入无效日期",
            "when": "提交保存",
            "then": "系统提示错误",
            "trace_hints": ["UI", "TECH"]
          }
        ],
        "dependencies": [],
        "non_goals": [],
        "priority": "P0",
        "delivery_slice": "core-config",
        "lifecycle_status": "draft",
        "ssot": {
          "identity_kind": "ssot",
          "ssot_type": "FEAT",
          "parent": "EPIC-DEMO-001"
        }
      }
    ]
  },
  "ssot_output_contract": {
    "contract_version": "1.0",
    "run_id": "run-ssot-004",
    "outputs": [
      {
        "key": "feat_epic_demo_001_001",
        "identity_kind": "ssot",
        "ssot_type": "feat",
        "title": "比赛目标与约束条件配置",
        "parent": "EPIC-DEMO-001",
        "source_refs": ["spec/requirements/requirements-frozen.md#R15"]
      }
    ]
  }
}
""".strip()

    structured_payload = runner._parse_structured_output_if_possible(generated_text)

    result = await runner._materialize_ssot_outputs(
        ctx=ctx,
        step=step,
        workflow_id="wf-001",
        generated_text=generated_text,
        structured_payload=structured_payload,
    )

    assert result is not None
    assert result["outputs"]["feat_epic_demo_001_001"]["id"] == "FEAT-001"
    assert len(result["materialized_files"]) == 1


def test_governance_preflight_requires_anchor_when_no_formal_ssot(temp_project_root, runner):
    agent_spec = SimpleNamespace(
        contracts={},
        governance={
            "acceptance_briefs": str((Path.cwd() / ".project" / "governance" / "ACCEPTANCE_BRIEFS").resolve()),
            "module_contracts": str((Path.cwd() / ".project" / "governance" / "MODULE_CONTRACTS").resolve()),
        },
        tags=["backend", "implementation"],
        spec_path=str((Path.cwd() / "spec-global" / "core" / "agents" / "agent-spec-maintainer" / "v1" / "agent.yaml").resolve()),
    )
    step = SimpleNamespace(id="impl_step", agent_id="agent.backend.impl", config={})

    result = runner._evaluate_governance_preflight(
        step=step,
        agent_spec=agent_spec,
        project_root=str(temp_project_root),
        structured_payload={"business_output": {"ok": True}},
    )

    assert result["implementation_facing"] is True
    assert result["formal_ssot_present"] is False
    assert result["allow_full_completion"] is False
    assert result["warnings"]


def test_governance_preflight_accepts_acceptance_brief_anchor(temp_project_root, runner):
    briefs_dir = temp_project_root / ".project" / "governance" / "ACCEPTANCE_BRIEFS"
    briefs_dir.mkdir(parents=True, exist_ok=True)
    brief_path = briefs_dir / "AB-20260307-demo-task.md"
    brief_path.write_text(
        "\n".join(
            [
                "---",
                "brief_id: demo-task",
                "title: Demo Task",
                "status: active",
                "task_type: implementation",
                "scope_in:",
                "  - demo scope",
                "scope_out:",
                "  - out of scope",
                "human_gate_required: true",
                "evidence_required:",
                "  - changed_files",
                "---",
                "",
                "# Acceptance Brief",
            ]
        ),
        encoding="utf-8",
    )

    agent_spec = SimpleNamespace(
        contracts={},
        governance={
            "acceptance_briefs": str(briefs_dir),
            "module_contracts": str((temp_project_root / ".project" / "governance" / "MODULE_CONTRACTS").resolve()),
        },
        tags=["backend", "implementation"],
        spec_path=str((Path.cwd() / "spec-global" / "core" / "agents" / "agent-spec-maintainer" / "v1" / "agent.yaml").resolve()),
    )
    step = SimpleNamespace(
        id="impl_step",
        agent_id="agent.backend.impl",
        config={"acceptance_brief_id": "demo-task"},
    )

    result = runner._evaluate_governance_preflight(
        step=step,
        agent_spec=agent_spec,
        project_root=str(temp_project_root),
        structured_payload={"business_output": {"ok": True}},
    )

    assert result["formal_ssot_present"] is False
    assert result["acceptance_brief_found"] is True
    assert result["allow_full_completion"] is True
    assert result["acceptance_brief_metadata"]["brief_id"] == "demo-task"


def test_parse_markdown_front_matter_for_acceptance_brief(temp_project_root, runner):
    brief_path = temp_project_root / "AB-20260307-login-refactor.md"
    brief_path.write_text(
        "\n".join(
            [
                "---",
                "brief_id: login-refactor",
                "title: Login Refactor",
                "status: active",
                "human_gate_required: false",
                "---",
                "",
                "# Acceptance Brief",
            ]
        ),
        encoding="utf-8",
    )

    metadata = runner._parse_markdown_front_matter(brief_path)

    assert metadata["brief_id"] == "login-refactor"
    assert metadata["status"] == "active"


def test_build_executor_input_bridges_agent_step_to_codex(temp_project_root, runner, ctx):
    instance = SimpleNamespace(data={"run_id": "run-001"})
    step = SimpleNamespace(
        id="spec_maintenance",
        agent_id="agent.governance.spec_maintainer",
        config={
            "claude_code": {
                "max_iterations": 3,
                "allowed_commands": ["Get-ChildItem"],
            }
        },
    )
    agent_ctx = SimpleNamespace(
        system_prompt="system rules",
        user_prompt="maintain the target spec",
        temperature=0.2,
        max_tokens=1200,
    )
    ctx.resolve_workdir = MagicMock(return_value=str(temp_project_root))
    ctx.token_manager.encode_token_for_context.return_value = "encoded-token"

    input_data = runner._build_executor_input(
        executor_type="codex",
        step=step,
        ctx=ctx,
        instance=instance,
        workflow_id="wf-001",
        agent_ctx=agent_ctx,
        step_token="raw-token",
    )

    assert input_data["goal"] == "maintain the target spec"
    assert input_data["workspace"] == str(temp_project_root)
    assert input_data["system_prompt_extra"] == "system rules"
    assert input_data["allowed_commands"] == ["Get-ChildItem"]
    assert input_data["token_context"] == "encoded-token"


def test_extract_declared_output_values_reads_scalar_files(temp_project_root, runner):
    scalar_path = temp_project_root / "blocker_count"
    scalar_path.write_text("1\n", encoding="utf-8")
    text_path = temp_project_root / "review_status"
    text_path.write_text("warning\n", encoding="utf-8")
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(path="blocker_count"),
            SimpleNamespace(path="review_status"),
            SimpleNamespace(path="docs/reports/review.json"),
        ]
    )

    values = runner._extract_declared_output_values(
        step=step,
        written_files=[str(scalar_path), str(text_path)],
        project_root=str(temp_project_root),
    )

    assert values["blocker_count"] == 1
    assert values["review_status"] == "warning"
    assert "review" not in values


def test_extract_declared_output_values_reads_named_markdown_sections(temp_project_root, runner):
    review_text = """
### **Outputs Generated**

#### **`blocker_count`**
```
1
```

---

#### **`major_count`**
```
2
```

---

#### **`review_status`**
```
blocked
```
""".strip()
    blocker_path = temp_project_root / "blocker_count"
    major_path = temp_project_root / "major_count"
    status_path = temp_project_root / "review_status"
    blocker_path.write_text(review_text, encoding="utf-8")
    major_path.write_text(review_text, encoding="utf-8")
    status_path.write_text(review_text, encoding="utf-8")
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(path="blocker_count"),
            SimpleNamespace(path="major_count"),
            SimpleNamespace(path="review_status"),
        ]
    )

    values = runner._extract_declared_output_values(
        step=step,
        written_files=[str(blocker_path), str(major_path), str(status_path)],
        project_root=str(temp_project_root),
    )

    assert values["blocker_count"] == 1
    assert values["major_count"] == 2
    assert values["review_status"] == "blocked"


def test_extract_declared_output_values_reads_numbered_markdown_sections(temp_project_root, runner):
    review_text = """
**Outputs Generated:**

### 2. `review_findings`
```markdown
# Summary
blocked
```

### 3. `blocker_count`
```text
1
```

### 4. `major_count`
```text
2
```
""".strip()
    blocker_path = temp_project_root / "blocker_count"
    major_path = temp_project_root / "major_count"
    blocker_path.write_text(review_text, encoding="utf-8")
    major_path.write_text(review_text, encoding="utf-8")
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(path="blocker_count"),
            SimpleNamespace(path="major_count"),
        ]
    )

    values = runner._extract_declared_output_values(
        step=step,
        written_files=[str(blocker_path), str(major_path)],
        project_root=str(temp_project_root),
    )

    assert values["blocker_count"] == 1
    assert values["major_count"] == 2


def test_extract_declared_output_values_reads_numbered_list_sections(temp_project_root, runner):
    review_text = """
**Output Files Generated:**

1. **`review_findings`**
```
blocked
```

2. **`blocker_count`**
```text
1
```

3. **`major_count`**
```text
2
```
""".strip()
    blocker_path = temp_project_root / "blocker_count"
    major_path = temp_project_root / "major_count"
    blocker_path.write_text(review_text, encoding="utf-8")
    major_path.write_text(review_text, encoding="utf-8")
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(path="blocker_count"),
            SimpleNamespace(path="major_count"),
        ]
    )

    values = runner._extract_declared_output_values(
        step=step,
        written_files=[str(blocker_path), str(major_path)],
        project_root=str(temp_project_root),
    )

    assert values["blocker_count"] == 1
    assert values["major_count"] == 2


def test_apply_spec_writeback_writes_target_file_and_diff(temp_project_root, runner):
    target_path = temp_project_root / "spec-global" / "core" / "agents" / "demo" / "v1" / "agent.yaml"
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text("kind: agent\nname: old-demo\n", encoding="utf-8")

    diff_path = temp_project_root / "docs" / "reports" / "governance" / "spec-review" / "demo-spec.diff"
    step = SimpleNamespace(
        config={
            "spec_writeback": {
                "enabled": True,
                "target_path": str(target_path),
                "diff_report_path": str(diff_path),
            }
        }
    )

    result = runner._apply_spec_writeback(
        step=step,
        project_root=str(temp_project_root),
        structured_payload={
            "maintained_spec_content": "kind: agent\nname: new-demo\n",
        },
        generated_text="",
    )

    assert result is not None
    assert result["applied"] is True
    assert result["changed"] is True
    assert target_path.read_text(encoding="utf-8") == "kind: agent\nname: new-demo"
    assert diff_path.exists()
    assert "-name: old-demo" in diff_path.read_text(encoding="utf-8")
    assert "+name: new-demo" in diff_path.read_text(encoding="utf-8")


def test_apply_spec_writeback_reads_markdown_section_fallback(temp_project_root, runner):
    target_path = temp_project_root / "spec-global" / "core" / "contracts" / "demo.yaml"
    diff_path = temp_project_root / "docs" / "reports" / "governance" / "spec-review" / "demo-section.diff"
    step = SimpleNamespace(
        config={
            "spec_writeback": {
                "enabled": True,
                "target_path": str(target_path),
                "diff_report_path": str(diff_path),
            }
        }
    )
    generated_text = """
#### **`maintained_spec_content`**
```yaml
kind: contract
version: "1.0"
```
""".strip()

    result = runner._apply_spec_writeback(
        step=step,
        project_root=str(temp_project_root),
        structured_payload=None,
        generated_text=generated_text,
    )

    assert result is not None
    assert result["applied"] is True
    assert target_path.read_text(encoding="utf-8") == 'kind: contract\nversion: "1.0"'


def test_apply_spec_writeback_reads_target_path_section_fallback(temp_project_root, runner):
    target_path = temp_project_root / "spec-global" / "core" / "agents" / "demo" / "v1" / "agent.yaml"
    diff_path = temp_project_root / "docs" / "reports" / "governance" / "spec-review" / "demo-target.diff"
    step = SimpleNamespace(
        config={
            "spec_writeback": {
                "enabled": True,
                "target_path": str(target_path),
                "diff_report_path": str(diff_path),
            }
        }
    )
    generated_text = f"""
### **Output 2: `{target_path}`**
```yaml
kind: agent
name: target-path-demo
```
""".strip()

    result = runner._apply_spec_writeback(
        step=step,
        project_root=str(temp_project_root),
        structured_payload=None,
        generated_text=generated_text,
    )

    assert result is not None
    assert result["applied"] is True
    assert target_path.read_text(encoding="utf-8") == "kind: agent\nname: target-path-demo"


def test_extract_declared_output_values_falls_back_to_generated_text(runner, temp_project_root):
    generated_text = """
### 3. `blocker_count`
```text
1
```

---

### 4. `major_count`
```text
2
```
""".strip()
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(path="blocker_count"),
            SimpleNamespace(path="major_count"),
        ]
    )

    values = runner._extract_declared_output_values(
        step=step,
        written_files=[],
        project_root=str(temp_project_root),
        generated_text=generated_text,
    )

    assert values["blocker_count"] == 1
    assert values["major_count"] == 2


def test_completion_summary_marks_missing_fields_explicitly(runner):
    step = SimpleNamespace(id="impl_step")
    summary = runner._build_completion_summary(
        step=step,
        written_files=[],
        structured_payload={"scope_completed": "implemented login flow"},
        governance_preflight={"human_gate_required": True},
    )

    assert summary["scope_completed"] == "implemented login flow"
    assert summary["evidence"] == "missing"
    assert summary["tests_executed"] == "missing"
    assert summary["known_limitations"] == "not declared"
    assert summary["human_gate_required"] is True


def test_extract_ssot_contract_payload_from_named_section(runner):
    generated_text = """
## spec/qa/test-sets/ts-demo-module.yaml
```yaml
test_set_id: TS-DEMO-MODULE
module: demo-module
strategy:
  focus:
    - happy path
test_focus:
  positive:
    - happy path
traceability:
  feature_ids:
    - FEAT-023
  acceptance_criteria_refs:
    - AC1
```

## ssot_output_contract
```json
{
  "contract_version": "1.0",
  "run_id": "qa-run-001",
  "outputs": [
    {
      "key": "testset",
      "identity_kind": "ssot",
      "ssot_type": "testset",
      "title": "Demo Module Test Set",
      "parent": "FEAT-023",
      "verifies": ["FEAT-023"]
    }
  ]
}
```
""".strip()

    payload = runner._extract_ssot_contract_payload(
        structured_payload=None,
        generated_text=generated_text,
    )

    assert payload is not None
    assert payload["run_id"] == "qa-run-001"
    assert payload["outputs"][0]["key"] == "testset"


def test_extract_ssot_contract_payload_from_plain_label_section(runner):
    generated_text = """
spec/qa/test-sets/ts-demo-module.yaml
```yaml
test_set_id: TS-DEMO-MODULE
module: demo-module
strategy:
  focus:
    - happy path
test_focus:
  positive:
    - happy path
traceability:
  feature_ids:
    - FEAT-023
  acceptance_criteria_refs:
    - AC1
```

ssot_output_contract
```yaml
contract_version: "1.0"
run_id: "qa-run-002"
outputs:
  - key: testset
    identity_kind: ssot
    ssot_type: testset
    title: Demo Module Test Set
```
""".strip()

    payload = runner._extract_ssot_contract_payload(
        structured_payload=None,
        generated_text=generated_text,
    )

    assert payload is not None
    assert payload["run_id"] == "qa-run-002"


def test_extract_ssot_contract_payload_from_code_block_mapping(runner):
    generated_text = """
```yaml
# spec/qa/test-sets/ts-demo-module.yaml
test_set_id: TS-DEMO-MODULE
module: demo-module
strategy:
  focus:
    - happy path
test_focus:
  positive:
    - happy path
traceability:
  feature_ids:
    - FEAT-023
  acceptance_criteria_refs:
    - AC1
```

```yaml
ssot_output_contract:
  contract_version: "1.0"
  run_id: "qa-run-003"
  outputs:
    - key: testset
      identity_kind: ssot
      ssot_type: testset
      title: Demo Module Test Set
```
""".strip()

    payload = runner._extract_ssot_contract_payload(
        structured_payload=None,
        generated_text=generated_text,
    )

    assert payload is not None
    assert payload["run_id"] == "qa-run-003"


def test_normalize_ssot_contract_payload_promotes_feat_parent_from_verifies(runner):
    payload = {
        "contract_version": "1.0",
        "run_id": "qa-run-004",
        "outputs": [
            {
                "key": "testset",
                "identity_kind": "ssot",
                "ssot_type": "testset",
                "title": "Demo Module Test Set",
                "parent": "feat",
                "verifies": ["FEAT-123"],
                "properties": {"feature_id": "FEAT-123"},
            }
        ],
    }

    normalized = runner._normalize_ssot_contract_payload(payload)

    assert normalized["outputs"][0]["parent"] == "FEAT-123"


def test_normalize_ssot_contract_payload_drops_extra_keys_and_repairs_verifies(runner):
    payload = {
        "contract_version": "1.0",
        "run_id": "qa-run-005",
        "outputs": [
            {
                "key": "testset",
                "identity_kind": "ssot",
                "ssot_type": "testset",
                "title": "Demo Module Test Set",
                "parent": "FEAT-123",
                "verifies": ["feat"],
                "artifact_ref": "spec/qa/test-sets/ts-demo-module.yaml",
            }
        ],
    }

    normalized = runner._normalize_ssot_contract_payload(payload)

    assert "artifact_ref" not in normalized["outputs"][0]
    assert normalized["outputs"][0]["verifies"] == ["FEAT-123"]


def test_normalize_ssot_contract_payload_coerces_contract_version_to_string(runner):
    payload = {
        "contract_version": 1.0,
        "run_id": 20240325,
        "outputs": [],
    }

    normalized = runner._normalize_ssot_contract_payload(payload)

    assert normalized["contract_version"] == "1.0"
    assert normalized["run_id"] == "20240325"


@pytest.mark.asyncio
async def test_llm_runner_only_sends_file_outputs_to_file_handler(temp_project_root):
    runner = LLMRunner()
    step = SimpleNamespace(
        id="feat_boundary_design",
        agent_id="agent.product.requirement_decomposer",
        executor_type="llm",
        config={},
        input={},
        outputs=[
            SimpleNamespace(path="", type="symbol", required=False),
            SimpleNamespace(path="spec/out.yaml", type="file", required=True),
        ],
    )
    llm_payload = {
        "status": "success",
        "provider": "test",
        "model": "test-model",
        "tokens_used": 1,
        "input_tokens": 1,
        "output_tokens": 1,
        "duration_seconds": 0.1,
        "stop_reason": "stop",
        "generated_text": "{}",
    }
    executor = MagicMock()
    executor.execute = AsyncMock(return_value=llm_payload)
    file_handler = MagicMock()
    file_handler.handle = AsyncMock(return_value=[str(temp_project_root / "spec" / "out.yaml")])
    store = MagicMock()
    store.get_workflow = AsyncMock(
        return_value=SimpleNamespace(
            data={"run_id": "run-001"},
            level="task",
            template_id="template.product.epic_to_feat",
        )
    )
    store.create_task_execution = AsyncMock()
    store.update_task_execution = AsyncMock()
    state_machine = MagicMock()
    state_machine.complete_step = AsyncMock(
        return_value=StepResult(
            status="completed",
            step_id=step.id,
            workflow_id="wf-001",
            message="ok",
        )
    )
    event_log = MagicMock()
    event_log.emit = AsyncMock()
    evidence_collector = MagicMock()
    evidence_collector.collect_task_execution = AsyncMock()
    verifier_engine = MagicMock()
    agent_loader = MagicMock()
    agent_loader.load.return_value = None
    agent_context_builder = MagicMock()
    agent_context_builder.build = AsyncMock(
        return_value=SimpleNamespace(
            system_prompt="system",
            user_prompt="user",
            temperature=0.1,
            max_tokens=100,
        )
    )
    agent_context_builder.agent_loader = agent_loader
    token_manager = MagicMock()
    token_manager.issue_token = MagicMock(return_value=None)
    ctx = RunnerContext(
        store=store,
        state_machine=state_machine,
        event_log=event_log,
        evidence_collector=evidence_collector,
        verifier_engine=verifier_engine,
        executor_factory=MagicMock(create=MagicMock(return_value=executor)),
        agent_context_builder=agent_context_builder,
        contract_discovery=MagicMock(get_workflow_inputs=MagicMock(return_value={})),
        file_output_handler=file_handler,
        token_manager=token_manager,
        project_root=str(temp_project_root),
    )

    await runner.execute("wf-001", step, ctx)

    passed_outputs = file_handler.handle.call_args.args[1]
    assert len(passed_outputs) == 1
    assert passed_outputs[0].path == "spec/out.yaml"


def test_extract_business_output_payload_uses_written_file_when_mixed_output(temp_project_root, runner):
    output_path = temp_project_root / "spec" / "qa" / "test-sets" / "ts-demo-module.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        """
test_set_id: TS-DEMO-MODULE
module: demo-module
strategy:
  focus:
    - happy path
test_focus:
  positive:
    - happy path
traceability:
  feature_ids:
    - FEAT-023
  acceptance_criteria_refs:
    - AC1
""".strip(),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(
                path="spec/qa/test-sets/ts-demo-module.yaml",
                type="file",
            )
        ]
    )

    payload = runner._extract_business_output_payload(
        structured_payload=None,
        fallback_text="## spec/qa/test-sets/ts-demo-module.yaml\n```yaml\nplaceholder: true\n```",
        step=step,
        written_files=[str(output_path)],
    )

    assert isinstance(payload, dict)
    assert payload["test_set_id"] == "TS-DEMO-MODULE"


def test_expected_feat_review_subject_refs_reads_generated_feat_id(runner):
    instance_data = {
        "step_outputs": {
            "feat_spec_generation": {
                "generated_text": json.dumps(
                    {
                        "business_output": {
                            "feat_id": "FEAT-900",
                            "title": "训练计划智能调整",
                        }
                    },
                    ensure_ascii=False,
                )
            }
        }
    }

    refs = runner._expected_feat_review_subject_refs(instance_data)

    assert refs == ["FEAT-900"]


def test_expected_feat_review_subject_refs_reads_generated_feat_bundle_ids(runner):
    instance_data = {
        "step_outputs": {
            "feat_spec_generation": {
                "generated_text": json.dumps(
                    {
                        "business_output": {
                            "epic_ref": "EPIC-001",
                            "feat_specs": [
                                {"feat_id": "FEAT-900", "title": "训练计划智能调整"},
                                {"feat_id": "FEAT-901", "title": "训练日程可视化"},
                            ],
                        }
                    },
                    ensure_ascii=False,
                )
            }
        }
    }

    refs = runner._expected_feat_review_subject_refs(instance_data)

    assert refs == ["FEAT-900", "FEAT-901"]


def test_normalize_feat_review_subject_refs_maps_generated_ids_to_materialized_ids(runner):
    instance_data = {
        "step_outputs": {
            "feat_spec_generation": {
                "generated_text": json.dumps(
                    {
                        "business_output": {
                            "epic_ref": "EPIC-001",
                            "feat_specs": [
                                {"feat_id": "FEAT-DEMO-001-1", "title": "训练计划智能调整"},
                                {"feat_id": "FEAT-DEMO-001-2", "title": "训练日程可视化"},
                            ],
                        }
                    },
                    ensure_ascii=False,
                ),
                "ssot_materialized": {
                    "feat_demo_001_1": {"id": "FEAT-027", "title": "训练计划智能调整"},
                    "feat_demo_001_2": {"id": "FEAT-028", "title": "训练日程可视化"},
                },
            }
        }
    }
    review_payload = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "subject_refs": ["FEAT-DEMO-001-1", "FEAT-DEMO-001-2"],
        "summary": "ok",
        "decision": "pass",
        "findings": [],
        "risks": [],
        "recommendations": [],
    }

    normalized = runner._normalize_feat_review_subject_refs(
        review_payload,
        instance_data,
        ["FEAT-027", "FEAT-028"],
    )

    assert normalized["subject_refs"] == ["FEAT-027", "FEAT-028"]


def test_normalize_feat_review_subject_refs_maps_generated_ids_via_materialized_keys(runner):
    instance_data = {
        "step_outputs": {
            "feat_spec_generation": {
                "generated_text": json.dumps(
                    {
                        "business_output": {
                            "epic_ref": "EPIC-001",
                            "feat_specs": [
                                {"feat_id": "FEAT-DEMO-001-1", "title": "训练计划智能调整"},
                                {"feat_id": "FEAT-DEMO-001-2", "title": "训练日程可视化"},
                            ],
                        }
                    },
                    ensure_ascii=False,
                ),
                "ssot_materialized": {
                    "feat_demo_001_1": {"id": "FEAT-031"},
                    "feat_demo_001_2": {"id": "FEAT-032"},
                },
            }
        }
    }
    review_payload = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "subject_refs": ["FEAT-DEMO-001-1", "FEAT-DEMO-001-2"],
        "summary": "ok",
        "decision": "pass",
        "findings": [],
        "risks": [],
        "recommendations": [],
    }

    normalized = runner._normalize_feat_review_subject_refs(
        review_payload,
        instance_data,
        ["FEAT-031", "FEAT-032"],
    )

    assert normalized["subject_refs"] == ["FEAT-031", "FEAT-032"]


def test_expected_feat_breakdown_epic_ref_reads_input_epic_id(runner):
    instance_data = {
        "params": {
            "epic_freeze": {
                "epic_id": "EPIC-DEMO-001",
                "title": "智能备赛计划生成",
            }
        }
    }

    epic_ref = runner._expected_feat_breakdown_epic_ref(instance_data)

    assert epic_ref == "EPIC-DEMO-001"


def test_validate_feat_breakdown_semantics_requires_exact_epic_ref(runner):
    payload = {
        "breakdown_id": "BKD-001",
        "epic_ref": "EPIC-OTHER-001",
        "feat_candidates": [
            {
                "title": "训练计划生成",
                "user_value": "快速生成训练计划",
                "acceptance_boundary": "用户可完成一次计划生成并查看结果",
            }
        ],
    }

    error = runner._validate_feat_breakdown_semantics(payload, "EPIC-DEMO-001")

    assert error == "FEAT breakdown epic_ref must exactly match the input EPIC ID: EPIC-DEMO-001"


def test_normalize_feat_breakdown_payload_flattens_object_acceptance_boundary(runner):
    payload = {
        "breakdown_id": "BKD-001",
        "epic_ref": "EPIC-DEMO-001",
        "feat_candidates": [
            {
                "title": "训练计划可视化",
                "user_value": "查看训练进度",
                "acceptance_boundary": {
                    "input": "已生成的训练计划框架",
                    "process": [
                        "展示12周训练强度曲线可视化",
                        "支持按周展开查看每日训练类型",
                    ],
                    "output": "可交互的图形化训练日历",
                },
            }
        ],
    }

    normalized = runner._normalize_feat_breakdown_payload(payload)

    assert normalized["feat_candidates"][0]["acceptance_boundary"] == (
        "已生成的训练计划框架；展示12周训练强度曲线可视化，支持按周展开查看每日训练类型；可交互的图形化训练日历"
    )


def test_expected_feat_review_subject_refs_prefers_materialized_feat_id(runner):
    instance_data = {
        "step_outputs": {
            "feat_spec_generation": {
                "generated_text": json.dumps(
                    {
                        "business_output": {
                            "feat_id": "FEAT-1",
                            "title": "训练计划智能调整",
                        }
                    },
                    ensure_ascii=False,
                ),
                "ssot_materialized": {
                    "feat": {
                        "id": "FEAT-900",
                    }
                },
            }
        }
    }

    refs = runner._expected_feat_review_subject_refs(instance_data)

    assert refs == ["FEAT-900"]


def test_expected_feat_review_subject_refs_prefers_materialized_feat_ids_for_bundle(runner):
    instance_data = {
        "step_outputs": {
            "feat_spec_generation": {
                "generated_text": json.dumps(
                    {
                        "business_output": {
                            "epic_ref": "EPIC-001",
                            "feat_specs": [
                                {"feat_id": "FEAT-1", "title": "训练计划智能调整"},
                                {"feat_id": "FEAT-2", "title": "训练日程可视化"},
                            ],
                        }
                    },
                    ensure_ascii=False,
                ),
                "ssot_materialized": {
                    "feat_feat_900": {"id": "FEAT-900"},
                    "feat_feat_901": {"id": "FEAT-901"},
                },
            }
        }
    }

    refs = runner._expected_feat_review_subject_refs(instance_data)

    assert refs == ["FEAT-900", "FEAT-901"]


def test_validate_feat_review_semantics_requires_exact_subject_refs(runner):
    payload = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "subject_refs": ["FEAT-123"],
        "summary": "review summary",
        "findings": [],
        "decision": "pass",
        "risks": [],
        "recommendations": [],
    }

    error = runner._validate_feat_review_semantics(payload, ["FEAT-900"])

    assert error == "FEAT review subject_refs must exactly match the reviewed FEAT ID(s): FEAT-900"


def test_validate_feat_review_semantics_rejects_pass_with_findings(runner):
    payload = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "subject_refs": ["FEAT-900"],
        "summary": "review summary",
        "findings": ["acceptance checks are incomplete"],
        "decision": "pass",
        "risks": [],
        "recommendations": [],
    }

    error = runner._validate_feat_review_semantics(payload, ["FEAT-900"])

    assert error == "FEAT review output with decision=pass must not include findings"


def test_validate_feat_review_semantics_rejects_pass_with_negative_summary(runner):
    payload = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "subject_refs": ["FEAT-900"],
        "summary": "存在阻塞问题，需修订后才能通过",
        "findings": [],
        "decision": "pass",
        "risks": [],
        "recommendations": [],
    }

    error = runner._validate_feat_review_semantics(payload, ["FEAT-900"])

    assert error == "FEAT review summary conflicts with decision=pass"


def test_validate_feat_review_semantics_requires_findings_for_revise(runner):
    payload = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "subject_refs": ["FEAT-900"],
        "summary": "需要修订",
        "findings": [],
        "decision": "revise",
        "risks": [],
        "recommendations": [],
    }

    error = runner._validate_feat_review_semantics(payload, ["FEAT-900"])

    assert error == "FEAT review output with decision=revise must include at least one finding"


def test_normalize_prd_writer_feat_payload_repairs_fixed_contract_fields(runner):
    step = SimpleNamespace(agent_id="agent.product.prd_writer")
    business_output = {
        "feat_id": "FEAT-900",
        "title": "训练计划智能调整",
        "source_refs": ["EPIC-001#scope"],
        "ssot": {
            "parent": "EPIC-001",
            "derived_from": "EPIC-001",
        },
    }
    structured_payload = {
        "business_output": business_output,
        "ssot_output_contract": {
            "outputs": [
                {
                    "key": "feat",
                }
            ]
        },
    }

    normalized_business, normalized_structured = runner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-task-001",
        business_output=business_output,
        structured_payload=structured_payload,
    )

    assert normalized_business["ssot"]["identity_kind"] == "ssot"
    assert normalized_business["ssot"]["ssot_type"] == "FEAT"
    assert normalized_business["derived_object_expectations"]["task_required"] is True
    assert normalized_business["derived_object_expectations"]["testset_required"] is True
    assert normalized_business["derived_object_expectations"]["testset_owner"] == "qa"
    assert normalized_business["derived_object_expectations"]["qa_seed_required"] is True
    assert normalized_structured["ssot_output_contract"]["contract_version"] == "1.0"
    assert normalized_structured["ssot_output_contract"]["run_id"] == "wf-task-001"
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["identity_kind"] == "ssot"
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["ssot_type"] == "feat"
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["parent"] == "EPIC-001"


def test_normalize_prd_writer_feat_payload_preserves_existing_acceptance_checks_only(runner):
    step = SimpleNamespace(agent_id="agent.product.prd_writer")
    business_output = {
        "feat_id": "FEAT-900",
        "title": "训练计划智能调整",
        "acceptance_criteria": [
            "支持输入所有核心训练约束参数",
            "输出参数对象包含完整元数据",
        ],
        "acceptance_checks": [
            {
                "id": "AC-001",
                "scenario": "用户提交完整训练约束",
                "given": "用户访问训练计划生成器",
                "when": "完成表单填写并提交",
                "then": "系统生成结构化参数对象",
                "trace_hints": ["UI", "TECH", "TASK", "TESTSET"],
            }
        ],
    }

    normalized_business, _ = runner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-task-001",
        business_output=business_output,
        structured_payload={"business_output": business_output},
    )

    assert len(normalized_business["acceptance_checks"]) == 1
    assert normalized_business["acceptance_checks"][0]["trace_hints"] == ["UI", "TECH", "TASK", "TESTSET"]


def test_normalize_prd_writer_feat_payload_drops_self_referential_feat_dependencies(runner):
    step = SimpleNamespace(agent_id="agent.product.prd_writer")
    business_output = {
        "feat_id": "FEAT-900",
        "title": "训练计划智能调整",
        "source_refs": ["spec/requirements/requirements-frozen.md#R15"],
        "ssot": {
            "parent": "EPIC-001",
            "derived_from": "EPIC-001",
        },
    }
    structured_payload = {
        "business_output": business_output,
        "ssot_output_contract": {
            "outputs": [
                {
                    "key": "feat",
                    "parent": "feat",
                    "source_refs": ["feat#scope", "EPIC-001#scope"],
                    "derived_from": ["feat", "EPIC-001"],
                    "verifies": ["feat"],
                    "implements": ["feat"],
                    "derived_from_ids": [{"id": "feat"}, {"id": "EPIC-001"}],
                }
            ]
        },
    }

    _, normalized_structured = runner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-task-001",
        business_output=business_output,
        structured_payload=structured_payload,
    )

    normalized_output = normalized_structured["ssot_output_contract"]["outputs"][0]
    assert normalized_output["parent"] == "EPIC-001"
    assert normalized_output["source_refs"] == ["EPIC-001#scope"]
    assert normalized_output["derived_from"] == ["EPIC-001"]
    assert normalized_output["verifies"] == []
    assert normalized_output["implements"] == []
    assert normalized_output["derived_from_ids"] == [{"id": "EPIC-001"}]


def test_normalize_prd_writer_feat_payload_normalizes_feat_bundle_items(runner):
    step = SimpleNamespace(agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-001",
        "feat_specs": [
            {
                "feat_id": "FEAT-900",
                "title": "训练计划智能调整",
                "source_refs": ["EPIC-001#scope"],
                "ssot": {
                    "parent": "EPIC-001",
                },
            },
            {
                "feat_id": "FEAT-901",
                "title": "训练日程可视化",
                "source_refs": ["EPIC-001#scope"],
                "ssot": {
                    "parent": "EPIC-001",
                },
            },
        ],
    }
    structured_payload = {
        "business_output": business_output,
        "ssot_output_contract": {
            "outputs": [
                {"key": "feat", "title": "训练计划智能调整"},
                {"key": "feat", "title": "训练日程可视化"},
            ]
        },
    }

    normalized_business, normalized_structured = runner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-task-001",
        business_output=business_output,
        structured_payload=structured_payload,
    )

    first_feat = normalized_business["feat_specs"][0]
    second_feat = normalized_business["feat_specs"][1]
    outputs = normalized_structured["ssot_output_contract"]["outputs"]

    assert first_feat["derived_object_expectations"]["qa_seed_required"] is True
    assert second_feat["derived_object_expectations"]["testset_owner"] == "qa"
    assert outputs[0]["key"] == "feat_900"
    assert outputs[1]["key"] == "feat_901"
    assert outputs[0]["parent"] == "EPIC-001"
    assert outputs[1]["parent"] == "EPIC-001"


def test_normalize_prd_writer_feat_payload_drops_bundle_self_refs_using_real_key(runner):
    step = SimpleNamespace(agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-DEMO-001",
        "feat_specs": [
            {
                "feat_id": "FEAT-900",
                "title": "训练计划智能调整",
                "source_refs": ["EPIC-DEMO-001#scope"],
                "ssot": {
                    "parent": "EPIC-DEMO-001",
                },
            }
        ],
    }
    structured_payload = {
        "business_output": business_output,
        "ssot_output_contract": {
            "outputs": [
                {
                    "key": "feat",
                    "title": "训练计划智能调整",
                    "parent": "feat_900",
                    "derived_from": ["feat_900"],
                    "source_refs": ["feat_900#scope", "EPIC-DEMO-001#scope"],
                }
            ]
        },
    }

    _, normalized_structured = runner._normalize_prd_writer_feat_payload(
        step=step,
        workflow_id="wf-task-001",
        business_output=business_output,
        structured_payload=structured_payload,
    )

    output = normalized_structured["ssot_output_contract"]["outputs"][0]

    assert output["key"] == "feat_900"
    assert output["parent"] == "EPIC-DEMO-001"
    assert output["derived_from"] == []
    assert output["source_refs"] == ["EPIC-DEMO-001#scope"]
