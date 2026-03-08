# FEAT-010 定义 SSOT 输出契约

## Summary
使用统一 schema 描述 EPIC/FEAT 等 SSOT 输出对象。

## Parent EPIC
- `EPIC-004`

## Capability Linkage
- `CAP-004 SSOT 与治理规则维护`

## Scope
- 约束 key、identity_kind、ssot_type 与关系字段。
- 让 materialization 与下游工具共享相同 contract。

## Inputs
- ssot artifact metadata
- content

## Outputs
- contract-compliant ssot-agent-output bundle

## Business Rules
- ssot output 必须声明 ssot_type。
- 本 workflow 只允许 epic 与 feat 两种 ssot_type。

## Acceptance Criteria
- AC-001 生成的 bundle 满足 contract_version=1.0。
- AC-002 outputs 中只出现 epic/feat 两类 SSOT。

## Code Refs
- `spec-global/core/contracts/ssot-agent-output/v1/schema.json`
- `src/lee/cli/commands/ssot.py`

## Evidence Refs
- `spec-global/core/contracts/ssot-agent-output/v1/schema.json`
- `src/lee/cli/commands/ssot.py`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
