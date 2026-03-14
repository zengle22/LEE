# System Map

- System: `LEE`
- Generated At: `2026-03-14T04:21:19.643061+00:00`

## Modules

### requirements
- Path Prefix: `spec/requirements/`
- Responsibility: 需求与冻结契约 SSOT

### cli
- Path Prefix: `src/lee/cli/`
- Responsibility: 命令行入口与用户操作命令

### orchestrator
- Path Prefix: `src/lee/orchestrator/`
- Responsibility: 工作流编排、执行、状态机与 gate

### scripts
- Path Prefix: `scripts/`
- Responsibility: 仓库维护与 workflow 辅助脚本

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
  - `doctor`
- Workflow Templates:

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
