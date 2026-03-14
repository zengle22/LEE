# Bugfix Batch Approval Process

## Status

- State: frozen
- Governing Spec: `governance/bugfix-granularity-control-spec.yaml`
- Governing ADR: `ADR-008`

## Trigger

仅当 `batch_mode=true` 且默认五同原则不能直接放行时，才进入例外审批流程。

不需要审批的情况：

- 单 bug 执行
- 五同原则全部通过的标准 batch

必须审批的情况：

- 至少一个五同维度未通过，但业务上仍要求并行修复
- 需要在同一发布窗口强制合并多个 bugfix

## Approval Flow

1. `triage` 产出 `granularity_decision_ref`
2. `root_cause` 补齐受影响范围和根因分类
3. 发起 `batch_exception_request`
4. 由 `dev-process-owner` 审查流程与风险
5. 由 `dev-architecture-owner` 审查结构边界和回滚面
6. 若包含高风险发布，再由 `release-owner` 追加确认
7. 审批结果写入 `batch_approval_record`

## Approval Conditions

审批通过前必须同时满足：

- 已明确列出所有 `bug_refs`
- 已说明哪几个五同维度失败
- 已解释为什么仍要 batch
- 已定义共享验证面和共享回滚策略
- 已声明同一发布窗口

以下任一命中必须拒绝：

- 根因尚未确认
- 验证面不同且不能统一
- 回滚策略需要分别执行
- 包含跨模块且无共同 owner 的修复

## Approval Record

审批记录必须至少包含：

- `request_id`
- `bug_refs`
- `failed_dimensions`
- `justification`
- `shared_verification_scope`
- `rollback_strategy`
- `approver_refs`
- `decision`
- `decision_time`

## Output Contract

审批通过后，下游至少要消费：

- `batch_approval_record`
- `verification_scope_ref`
- `rollback_strategy_ref`

审批拒绝后，运行时必须回退为单 bug 拆分执行。
