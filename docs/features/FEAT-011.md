# FEAT-011 维护模板与实例边界

## Summary
在 workflow spec 维护与评审中强制区分 checked-in 模板和 runtime instance。

## Parent EPIC
- `EPIC-004`

## Capability Linkage
- `CAP-004 SSOT 与治理规则维护`

## Scope
- 在维护 agent 与 review agent 中加入规则。
- 防止 spec 被误描述为运行时实例。

## Inputs
- workflow spec change request
- review context

## Outputs
- template-boundary compliant spec review result

## Business Rules
- checked-in workflow spec 只能描述模板语义。
- 运行时 instance 只能在执行阶段动态生成。

## Acceptance Criteria
- AC-001 workflow spec maintainer 会纠正模板/实例混淆描述。
- AC-002 spec-review 会将该混淆识别为 review finding。

## Code Refs
- `spec-global/core/agents/workflow-spec-maintainer/v1/agent.yaml`
- `spec-global/core/agents/spec-review/v1/agent.yaml`

## Evidence Refs
- `spec-global/core/agents/workflow-spec-maintainer/v1/agent.yaml`
- `spec-global/core/agents/spec-review/v1/agent.yaml`

## Inference
- 基于现有代码结构和 CLI/Orchestrator 路径归纳 capability 与 feature 边界。
