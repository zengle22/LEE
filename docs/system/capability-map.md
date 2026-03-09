# Capability Map

- Generated At: `2026-03-07T10:59:16.732223+00:00`

## CAP-001 工作流模板与实例生成
- Summary: 维护 workflow 模板、注册表，并将模板渲染为运行时 instance。
- Boundary: 覆盖模板文件、registry 与 template 渲染链，不包含具体业务步骤执行。
- Evidence Refs:
  - `config/workflow-registry.yaml`
  - `spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml`
  - `src/lee/cli/commands/run.py`
  - `src/lee/orchestrator/execution/template_manager.py`

## CAP-002 工作流执行与门禁控制
- Summary: 调度 workflow 步骤、持久化执行状态，并执行自动/人工 gate。
- Boundary: 覆盖执行、状态机与 gate，不包含业务文档生成策略本身。
- Evidence Refs:
  - `src/lee/orchestrator/execution/orchestrator.py`
  - `src/lee/orchestrator/execution/state_machine.py`
  - `src/lee/orchestrator/execution/runners/auto_check_gate_runner.py`
  - `src/lee/orchestrator/execution/runners/shell_runner.py`

## CAP-003 CLI 工作流操作
- Summary: 通过 CLI 触发运行、查询状态与审批 gate。
- Boundary: 覆盖命令入口与用户交互，不包含 orchestrator 内部执行细节。
- Evidence Refs:
  - `src/lee/cli/main.py`
  - `src/lee/cli/commands/run.py`
  - `src/lee/cli/commands/status.py`
  - `src/lee/cli/commands/approve.py`

## CAP-004 SSOT 与治理规则维护
- Summary: 维护 SSOT contract、spec review 规则与 workflow 模板治理边界。
- Boundary: 覆盖 SSOT artifact 约束和 review 规则，不包含下游 TECH/TESTSET 派生。
- Evidence Refs:
  - `spec-global/core/contracts/ssot-agent-output/v1/schema.json`
  - `spec-global/core/agents/workflow-spec-maintainer/v1/agent.yaml`
  - `spec-global/core/agents/spec-review/v1/agent.yaml`
  - `src/lee/cli/commands/ssot.py`
