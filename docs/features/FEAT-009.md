# FEAT-009 审批人工门禁

## Summary
通过 CLI 审批 gate 并推动 workflow 继续执行。

## Parent EPIC
- `EPIC-003`

## Capability Linkage
- `CAP-003 CLI 工作流操作`

## Scope
- 读取 gate id、approver 与审批动作。
- 调用 gate API 更新 gate 状态。

## Inputs
- workflow_id
- gate_id
- approver

## Outputs
- approved gate state

## Business Rules
- 只有 human gate 允许人工审批。
- 审批后 workflow 需可继续推进。

## Acceptance Criteria
- AC-001 approve 命令能更新 gate 记录。
- AC-002 审批成功后 workflow 不再停留在原 gate。

## Code Refs
- `src/lee/cli/commands/approve.py`
- `src/lee/orchestrator/execution/gate_api.py`

## Evidence Refs
- `src/lee/cli/commands/approve.py`
- `src/lee/orchestrator/execution/gate_api.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
