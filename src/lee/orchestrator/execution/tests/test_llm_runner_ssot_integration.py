import shutil
import tempfile
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lee.orchestrator.execution.runners.base import RunnerContext, StepRunnerBase
from lee.orchestrator.execution.runners.llm_runner import ClaudeCodeRunner, LLMRunner
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


def test_claude_code_runner_merges_forbidden_read_paths():
    merged = ClaudeCodeRunner._merge_forbidden_read_paths([".tmp/", "output/", "pytest-temp/"])

    assert merged == [
        "output/",
        "evidence/",
        ".workflow/claude-code/",
        ".tmp/",
        "pytest-temp/",
    ]


def test_claude_code_runner_merges_context_files():
    merged = ClaudeCodeRunner._merge_context_files(
        ["spec/requirements/epics/EPIC-001.md"],
        ["spec/requirements/epics/EPIC-001.md", "spec/adr/ADR-007.md"],
    )

    assert merged == [
        "spec/requirements/epics/EPIC-001.md",
        "spec/adr/ADR-007.md",
    ]


def test_claude_code_runner_collects_authoritative_context_files():
    step = SimpleNamespace(
        inputs=[
            {"source": "business_opportunity", "required": True},
        ]
    )

    collected = ClaudeCodeRunner._collect_authoritative_context_files(
        step,
        {
            "params": {
                "business_opportunity": {
                    "path": "spec/adr/ADR-007__qa-department-ssot-alignment-and-workflow-reframe.md"
                }
            }
        },
    )

    assert collected == [
        "spec/adr/ADR-007__qa-department-ssot-alignment-and-workflow-reframe.md"
    ]


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


@pytest.mark.asyncio
async def test_llm_runner_does_not_fail_after_successful_schema_repair(temp_project_root):
    runner = LLMRunner()
    schema_path = temp_project_root / "review.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["review_id", "review_type", "subject_refs", "summary", "decision", "findings", "risks", "recommendations"],
                "properties": {
                    "review_id": {"type": "string"},
                    "review_type": {"type": "string"},
                    "subject_refs": {"type": "array", "items": {"type": "string"}},
                    "summary": {"type": "string"},
                    "decision": {"type": "string"},
                    "findings": {"type": "array", "items": {"type": "string"}},
                    "risks": {"type": "array", "items": {"type": "string"}},
                    "recommendations": {"type": "array", "items": {"type": "string"}},
                },
            }
        ),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        id="feat_review",
        agent_id="agent.product.feat_reviewer",
        executor_type="llm",
        config={"output_contract": str(schema_path), "strict_output_validation": True},
        input={},
        outputs=[],
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
        "generated_text": json.dumps(
            {
                "review_id": "RVW-001",
                "review_type": "feat_review",
                "subject_refs": ["FEAT-001"],
                "summary": "ok",
                "findings": [],
                "risks": [],
                "recommendations": [],
            },
            ensure_ascii=False,
        ),
    }
    executor = MagicMock()
    executor.execute = AsyncMock(return_value=llm_payload)
    file_handler = MagicMock()
    file_handler.handle = AsyncMock(return_value=[])
    store = MagicMock()
    store.get_workflow = AsyncMock(
        return_value=SimpleNamespace(
            data={"run_id": "run-001"},
            level="task",
            template_id="template.product.epic_to_feat",
        )
    )
    store.create_task_execution = AsyncMock(return_value="exec-001")
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
    state_machine.fail_step = AsyncMock()
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

    async def fake_attempt_schema_repair(**kwargs):
        return {
            "output": {"generated_text": json.dumps({"decision": "pass"}, ensure_ascii=False)},
            "business_output": {
                "review_id": "RVW-001",
                "review_type": "feat_review",
                "subject_refs": ["FEAT-001"],
                "summary": "ok",
                "decision": "pass",
                "findings": [],
                "risks": [],
                "recommendations": [],
            },
            "structured_payload": None,
        }

    runner._attempt_schema_repair = fake_attempt_schema_repair

    result = await runner.execute("wf-001", step, ctx)

    assert result.status == "completed"
    state_machine.fail_step.assert_not_called()
    state_machine.complete_step.assert_awaited_once()


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


def test_expected_feat_review_subject_refs_reads_bundle_feat_ids(runner):
    instance_data = {
        "step_outputs": {
            "feat_spec_generation": {
                "generated_text": json.dumps(
                    {
                        "business_output": {
                            "epic_ref": "EPIC-001",
                            "feat_specs": [
                                {"feat_id": "FEAT-901", "title": "能力 A"},
                                {"feat_id": "FEAT-902", "title": "能力 B"},
                            ],
                        }
                    },
                    ensure_ascii=False,
                )
            }
        }
    }

    refs = runner._expected_feat_review_subject_refs(instance_data)

    assert refs == ["FEAT-901", "FEAT-902"]


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


def test_normalize_prd_writer_feat_bundle_payload_repairs_nested_feat_fields(runner):
    step = SimpleNamespace(agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-001",
        "epic_title": "训练能力升级",
        "feat_specs": [
            {
                "feat_id": "FEAT-900",
                "title": "训练计划智能调整",
                "source_refs": ["EPIC-001#scope"],
                "ssot": {
                    "parent": "EPIC-001",
                    "derived_from": "EPIC-001",
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

    feat = normalized_business["feat_specs"][0]
    assert set(normalized_business.keys()) == {"epic_ref", "feat_specs"}
    assert feat["ssot"]["identity_kind"] == "ssot"
    assert feat["ssot"]["ssot_type"] == "FEAT"
    assert feat["derived_object_expectations"]["task_required"] is True
    assert feat["derived_object_expectations"]["testset_required"] is True
    assert feat["derived_object_expectations"]["testset_owner"] == "qa"
    assert feat["derived_object_expectations"]["qa_seed_required"] is True
    assert normalized_structured["ssot_output_contract"]["contract_version"] == "1.0"


def test_claude_code_validation_prefers_written_business_file(temp_project_root):
    schema_path = temp_project_root / "feat.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["feat_id", "title", "ssot"],
                "properties": {
                    "feat_id": {"type": "string"},
                    "title": {"type": "string"},
                    "ssot": {"type": "object"},
                },
            }
        ),
        encoding="utf-8",
    )
    written_path = temp_project_root / "feat-spec-20250310-001.json"
    written_path.write_text(
        json.dumps(
            {
                "business_output": [
                    {
                        "feat_id": "FEAT-001",
                        "title": "基础用户认证与账户管理",
                        "ssot": {
                            "parent": "EPIC-001",
                            "derived_from": "EPIC-001#breakdown",
                        },
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        id="feat_spec_generation",
        agent_id="agent.product.prd_writer",
        config={"output_contract": str(schema_path), "strict_output_validation": True},
        outputs=[SimpleNamespace(path="feat-spec-20250310-001.json", type="file")],
    )
    output = {
        "raw_output": json.dumps(
            {
                "status": "success",
                "changed_files": ["feat-spec-20250310-001.json"],
            }
        )
    }

    business_output, structured_payload = ClaudeCodeRunner._extract_business_output_for_validation(
        step=step,
        workflow_id="wf-001",
        output=output,
        written_files=[str(written_path)],
    )
    validation = ClaudeCodeRunner._validate_step_output(step, business_output)

    assert isinstance(structured_payload, dict)
    assert isinstance(business_output, dict)
    assert business_output["feat_id"] == "FEAT-001"
    assert business_output["ssot"]["ssot_type"] == "FEAT"
    assert validation is not None
    assert validation.passed is True


def test_claude_code_validation_reads_changed_file_for_symbol_outputs(temp_project_root):
    schema_path = temp_project_root / "feat-bundle.schema.json"
    schema_path.write_text(
        json.dumps(
            {
                "type": "object",
                "required": ["epic_ref", "feat_specs"],
                "properties": {
                    "epic_ref": {"type": "string"},
                    "feat_specs": {"type": "array"},
                },
            }
        ),
        encoding="utf-8",
    )
    written_path = temp_project_root / "feat-spec-20250310-001.yaml"
    written_path.write_text(
        "\n".join(
            [
                "business_output:",
                "  epic_ref: EPIC-001",
                "  feat_specs:",
                "    - feat_id: FEAT-001",
                "      title: 基础用户认证与账户管理",
                "      goal: goal",
                "      user_value: user_value",
                "      inputs: [a]",
                "      processing: [b]",
                "      outputs: [c]",
                "      acceptance_criteria: [d]",
                "      acceptance_checks:",
                "        - id: AC-1",
                "          scenario: s",
                "          given: g",
                "          when: w",
                "          then: t",
                "          trace_hints: [UI]",
                "        - id: AC-2",
                "          scenario: s2",
                "          given: g2",
                "          when: w2",
                "          then: t2",
                "          trace_hints: [TECH]",
                "      dependencies: []",
                "      non_goals: []",
                "      priority: P0",
                "      delivery_slice: mvp",
                "      lifecycle_status: draft",
                "      ssot:",
                "        parent: EPIC-001",
                "        derived_from: EPIC-001#breakdown",
            ]
        ),
        encoding="utf-8",
    )
    step = SimpleNamespace(
        id="feat_spec_generation",
        agent_id="agent.product.prd_writer",
        config={"output_contract": str(schema_path), "strict_output_validation": True},
        outputs=[SimpleNamespace(path="", type="symbol")],
    )
    output = {
        "raw_output": json.dumps(
            {
                "status": "success",
                "changed_files": ["feat-spec-20250310-001.yaml"],
            }
        )
    }

    business_output, _ = ClaudeCodeRunner._extract_business_output_for_validation(
        step=step,
        workflow_id="wf-001",
        output=output,
        written_files=[str(written_path)],
    )
    validation = ClaudeCodeRunner._validate_step_output(step, business_output)

    assert isinstance(business_output, dict)
    assert business_output["epic_ref"] == "EPIC-001"
    assert validation is not None
    assert validation.passed is True


def test_parse_structured_output_accepts_fenced_json_with_leading_prose():
    output_text = """
评审已完成。

```json
{
  "review_id": "RVW-001",
  "review_type": "feat_review",
  "subject_refs": ["FEAT-001"],
  "summary": "ok",
  "findings": [],
  "decision": "pass",
  "risks": [],
  "recommendations": []
}
```
"""

    parsed = StepRunnerBase._parse_structured_output(output_text)

    assert isinstance(parsed, dict)
    assert parsed["review_id"] == "RVW-001"
    assert parsed["decision"] == "pass"


def test_parse_structured_output_prefers_yaml_body_before_status_fence():
    output_text = """
business_output:
  epic_ref: EPIC-001
  feat_specs:
    - feat_id: FEAT-001
      title: 标题
      goal: 目标
      user_value: 用户价值
      inputs: [a]
      processing: [b]
      outputs: [c]
      acceptance_criteria: [d]
      acceptance_checks:
        - id: AC-1
          scenario: s
          given: g
          when: w
          then: t
          trace_hints: [UI]
      dependencies: []
      non_goals: []
      priority: P0
      delivery_slice: mvp
      lifecycle_status: draft
      ssot:
        parent: EPIC-001
        derived_from: EPIC-001#breakdown
ssot_output_contract:
  contract_version: "1.0"
  run_id: run-001
  outputs: []

```json
{"status":"success","changed_files":["foo.yaml"],"error":null}
```
"""

    parsed = StepRunnerBase._parse_structured_output(output_text)

    assert isinstance(parsed, dict)
    assert parsed["business_output"]["epic_ref"] == "EPIC-001"
    assert parsed["ssot_output_contract"]["run_id"] == "run-001"


def test_parse_structured_output_strips_leading_think_block():
    output_text = """<think>Now I need to output the final JSON result according to the task requirements.</think>

{
  "review_id": "RVW-001",
  "review_type": "feat_review",
  "subject_refs": ["FEAT-001"],
  "decision": "pass"
}
"""

    parsed = StepRunnerBase._parse_structured_output(output_text)

    assert isinstance(parsed, dict)
    assert parsed["review_id"] == "RVW-001"
    assert parsed["decision"] == "pass"


def test_materialize_symbolic_workspace_outputs_writes_to_workflow_workspace(temp_project_root, runner):
    step = SimpleNamespace(
        id="feat_spec_generation",
        outputs=[SimpleNamespace(path="")],
    )

    files = runner._materialize_symbolic_workspace_outputs(
        step=step,
        workflow_id="wf-task-001",
        project_root=str(temp_project_root),
        business_output={"epic_ref": "EPIC-001", "feat_specs": []},
        structured_payload={"business_output": {"epic_ref": "EPIC-001", "feat_specs": []}},
    )

    assert len(files) >= 1
    business_path = temp_project_root / ".workflow" / "workspace" / "wf-task-001" / "feat_spec_generation" / "business_output.yaml"
    assert business_path.exists()
    assert "epic_ref: EPIC-001" in business_path.read_text(encoding="utf-8")
