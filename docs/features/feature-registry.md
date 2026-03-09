# Feature Registry

- Generated At: `2026-03-07T10:59:16.866069+00:00`

## FEAT-001 注册工作流模板
- Capability: `CAP-001`
- Key: `feat_register_workflow_templates`
- Summary: 通过 workflow registry 暴露模板定义与参数约束。
- Acceptance Boundary: 独立可验收的业务能力单元
- Code Refs:
  - `config/workflow-registry.yaml`
  - `src/lee/cli/commands/run.py`

## FEAT-002 解析 L3 workflow 模板
- Capability: `CAP-001`
- Key: `feat_parse_l3_workflow_templates`
- Summary: 将 L3 模板中的 stages/steps 解析为可调度步骤与依赖关系。
- Acceptance Boundary: 独立可验收的业务能力单元
- Code Refs:
  - `src/lee/orchestrator/execution/template_manager.py`
  - `src/lee/orchestrator/ir/converter.py`

## FEAT-003 渲染运行时 workflow instance
- Capability: `CAP-001`
- Key: `feat_render_runtime_instances`
- Summary: 通过 CLI 将模板与参数渲染为运行时 workflow instance 文件并创建实例。
- Acceptance Boundary: 独立可验收的业务能力单元
- Code Refs:
  - `src/lee/cli/commands/run.py`

## FEAT-004 执行工作流步骤 DAG
- Capability: `CAP-002`
- Key: `feat_execute_step_dag`
- Summary: 根据 depends_on 选择 ready step 并顺序推进 workflow。
- Acceptance Boundary: 独立可验收的业务能力单元
- Code Refs:
  - `src/lee/orchestrator/execution/orchestrator.py`
  - `src/lee/orchestrator/execution/state_machine.py`

## FEAT-005 执行自动检查门禁
- Capability: `CAP-002`
- Key: `feat_evaluate_auto_check_gates`
- Summary: 把 step_outputs 扁平化并执行 blocker/major 表达式。
- Acceptance Boundary: 独立可验收的业务能力单元
- Code Refs:
  - `src/lee/orchestrator/execution/runners/auto_check_gate_runner.py`
  - `spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml`

## FEAT-006 持久化步骤输出与证据路径
- Capability: `CAP-002`
- Key: `feat_persist_step_outputs`
- Summary: 完成步骤时把 output dict 与 output paths 写入 workflow data。
- Acceptance Boundary: 独立可验收的业务能力单元
- Code Refs:
  - `src/lee/orchestrator/execution/state_machine.py`
  - `src/lee/orchestrator/execution/runners/shell_runner.py`

## FEAT-007 通过 CLI 运行 workflow
- Capability: `CAP-003`
- Key: `feat_run_workflow_from_cli`
- Summary: 支持 `lee run` 加载 registry、渲染模板并执行 workflow。
- Acceptance Boundary: 独立可验收的业务能力单元
- Code Refs:
  - `src/lee/cli/commands/run.py`
  - `src/lee/cli/main.py`

## FEAT-008 查询 workflow 状态
- Capability: `CAP-003`
- Key: `feat_query_workflow_status`
- Summary: 查看 workflow 当前状态、完成步骤与 gate 信息。
- Acceptance Boundary: 独立可验收的业务能力单元
- Code Refs:
  - `src/lee/cli/commands/status.py`
  - `src/lee/cli/main.py`

## FEAT-009 审批人工门禁
- Capability: `CAP-003`
- Key: `feat_approve_human_gates`
- Summary: 通过 CLI 审批 gate 并推动 workflow 继续执行。
- Acceptance Boundary: 独立可验收的业务能力单元
- Code Refs:
  - `src/lee/cli/commands/approve.py`
  - `src/lee/orchestrator/execution/gate_api.py`

## FEAT-010 定义 SSOT 输出契约
- Capability: `CAP-004`
- Key: `feat_define_ssot_output_contract`
- Summary: 使用统一 schema 描述 EPIC/FEAT 等 SSOT 输出对象。
- Acceptance Boundary: 独立可验收的业务能力单元
- Code Refs:
  - `spec-global/core/contracts/ssot-agent-output/v1/schema.json`
  - `src/lee/cli/commands/ssot.py`

## FEAT-011 维护模板与实例边界
- Capability: `CAP-004`
- Key: `feat_enforce_template_instance_boundary`
- Summary: 在 workflow spec 维护与评审中强制区分 checked-in 模板和 runtime instance。
- Acceptance Boundary: 独立可验收的业务能力单元
- Code Refs:
  - `spec-global/core/agents/workflow-spec-maintainer/v1/agent.yaml`
  - `spec-global/core/agents/spec-review/v1/agent.yaml`
