# FEAT-004 执行工作流步骤 DAG

## Summary
根据 depends_on 选择 ready step 并顺序推进 workflow。

## Parent EPIC
- `EPIC-002`

## Capability Linkage
- `CAP-002 工作流执行与门禁控制`

## Scope
- 处理 step 调度、继续执行与完成汇总。
- 支持 skill、agent、gate 等步骤类型。

## Inputs
- workflow instance
- current step state

## Outputs
- completed_steps
- next ready step
- workflow summary

## Business Rules
- 只有所有依赖满足后步骤才可执行。
- 失败步骤必须显式标记 workflow 状态。

## Acceptance Criteria
- AC-001 多步 workflow 可按 depends_on 连续推进。
- AC-002 失败时 workflow 状态变为 failed。

## Code Refs
- `src/lee/orchestrator/execution/orchestrator.py`
- `src/lee/orchestrator/execution/state_machine.py`

## Evidence Refs
- `src/lee/orchestrator/execution/orchestrator.py`
- `src/lee/orchestrator/execution/state_machine.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
