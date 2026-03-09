# System Map

- System: `LEE`
- Generated At: `2026-03-07T10:59:16.599722+00:00`

## Modules

### cli
- Path Prefix: `src/lee/cli/`
- Responsibility: 命令行入口与用户操作命令

### orchestrator
- Path Prefix: `src/lee/orchestrator/`
- Responsibility: 工作流编排、执行、状态机与 gate

### spec_global
- Path Prefix: `spec-global/`
- Responsibility: 全局 workflow/agent/contract 模板

## Entry Points

- Workflow Registry: `config/workflow-registry.yaml`
- CLI Commands:
  - `approve`
  - `artifacts`
  - `behavior_compliance_checker`
  - `chat`
  - `check_env`
  - `context`
  - `demo`
  - `diagram_gen`
  - `diagram_insert`
  - `gates_cmd`
- Workflow Templates:
  - `spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml`
  - `spec-global/core/workflows/templates/spec-governance-l3-template.yaml`
  - `spec-global/cross/workflows/product-pipeline/v1/workflow.yaml`
  - `spec-global/cross/workflows/project/product-mvp/v1/workflow.yaml`
  - `spec-global/departments/dev/workflows/phase-openspec-flow/v1/workflow.yaml`
  - `spec-global/departments/dev/workflows/templates/bug-fix-l3-template.yaml`
  - `spec-global/departments/dev/workflows/templates/feature-be-l3-template.yaml`
  - `spec-global/departments/dev/workflows/templates/feature-contract-l3-template.yaml`

## Core Flows

### Workflow Run Flow
- CLI loads workflow registry
- run.py renders workflow template
- template_manager parses rendered workflow
- orchestrator schedules steps and gates

### Spec Governance Flow
- workflow spec maintainer updates spec templates
- spec-review validates governance rules
- SSOT contracts constrain generated artifacts

## Evidence Refs

- `README.md`
- `config/workflow-registry.yaml`
- `src/lee/cli/commands/run.py`
- `src/lee/orchestrator/execution/template_manager.py`
- `src/lee/orchestrator/execution/orchestrator.py`
- `src/lee/orchestrator/execution/state_machine.py`
- `src/lee/orchestrator/execution/runners/auto_check_gate_runner.py`
- `src/lee/orchestrator/execution/runners/shell_runner.py`
- `spec-global/core/contracts/ssot-agent-output/v1/schema.json`
- `spec-global/core/agents/workflow-spec-maintainer/v1/agent.yaml`
- `spec-global/core/agents/spec-review/v1/agent.yaml`
