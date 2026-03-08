# FEAT-008 查询 workflow 状态

## Summary
查看 workflow 当前状态、完成步骤与 gate 信息。

## Parent EPIC
- `EPIC-003`

## Capability Linkage
- `CAP-003 CLI 工作流操作`

## Scope
- 读取 workflow instance 数据。
- 向终端输出状态摘要。

## Inputs
- workflow_id

## Outputs
- status summary

## Business Rules
- 状态查询不修改 workflow 数据。
- 需要兼容 blocked、paused、failed、completed 等状态。

## Acceptance Criteria
- AC-001 给定 workflow_id 可以输出当前状态与当前步骤。
- AC-002 blocked workflow 会显示 gate 指引。

## Code Refs
- `src/lee/cli/commands/status.py`
- `src/lee/cli/main.py`

## Evidence Refs
- `src/lee/cli/commands/status.py`
- `src/lee/cli/main.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
