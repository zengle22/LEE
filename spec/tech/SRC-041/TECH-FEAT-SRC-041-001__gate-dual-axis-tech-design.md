---
id: TECH-FEAT-SRC-041-001
ssot_type: tech
title: Gate 双轴模型技术架构设计
status: active
version: v1
parent_id: FEAT-SRC-041-001
derived_from_ids:
- FEAT-SRC-041-001
- ADR-017
source_refs:
- FEAT-SRC-041-001
- EPIC-SRC-041-016
- ADR-017
owner: dev-architecture-owner
tags:
- tech
- ssot
- dev
- adr-017
- gate-governance
properties:
  contract_key: tech_spec
  identity_kind: ssot
workflow_instance_id: wf_task_851b68f0
---

# Gate 双轴模型技术架构设计

基于 FEAT-SRC-041-001 和 ADR-017，本技术规格定义 Gate 职责语义从单轴分类模型收敛到双轴模型（purpose + decision_mode）的技术实现方案。

## Architecture Decisions

### AD-001
- decision: 引入 purpose（review/approval）和 decision_mode（auto/conditional_human/human_required）双轴模型
- reason: 现有三套未对齐的 gate 心智模型（ADR 层、workflow 层、runtime 层）导致语义混淆和职责边界模糊
- impact:
  - GateApproval 数据模型需扩展双轴字段
  - Runner 路由逻辑需支持双轴解析
  - 历史配置需提供兼容映射

### AD-002
- decision: approval purpose 只能与 human_required decision_mode 组合
- reason: ADR-017 约束，正式责任确认、freeze、release 必须由人类决策
- impact:
  - 需在 Runner 层和 Store 层双重验证组合合法性
  - 工作流模板配置需校验

### AD-003
- decision: 历史分类仅作为映射到双轴模型的兼容入口
- reason: 保持向后兼容性，同时收敛到统一的双轴语义
- impact:
  - 需提供完整的默认值映射表
  - legacy_gate_type 字段标记为废弃中

## Feat Mapping

### Goal Mapping

- FEAT clause: 将 gate 的分类从单一 gate_type 轴收敛到二维模型（purpose + decision_mode）
  TECH response: 引入 GatePurpose 和 GateDecisionMode 枚举，扩展 GateApproval 模型
- FEAT clause: purpose 轴定义为 review（质量判断）和 approval（正式责任确认）
  TECH response: GatePurpose 枚举定义 REVIEW 和 APPROVAL 两个值
- FEAT clause: decision_mode 轴定义为 auto、conditional_human、human_required
  TECH response: GateDecisionMode 枚举定义三个值，支持条件触发逻辑
- FEAT clause: 禁止 approval + auto 的非法组合
  TECH response: 在 HumanGateRunner 和 SQLiteStore 两处进行组合验证

### Acceptance Mapping

- acceptance_id: AC-FEAT-SRC-041-001-01
  implementation_unit: GateApproval 模型包含 purpose 和 decision_mode 必填字段
  evidence_ref: src/lee/orchestrator/storage/models.py:GateApproval
- acceptance_id: AC-FEAT-SRC-041-001-02
  implementation_unit: GatePurpose 和 GateDecisionMode 枚举定义完整
  evidence_ref: src/lee/orchestrator/storage/models.py:GatePurpose,GateDecisionMode
- acceptance_id: AC-FEAT-SRC-041-001-03
  implementation_unit: HumanGateRunner 支持双轴解析和组合验证
  evidence_ref: src/lee/orchestrator/execution/runners/gate_runner.py:HumanGateRunner
- acceptance_id: AC-FEAT-SRC-041-001-04
  implementation_unit: 历史分类映射逻辑完整
  evidence_ref: src/lee/orchestrator/execution/runners/gate_runner.py:_get_legacy_mapping

## Implementation Rules

### Required Inputs

- FEAT-SRC-041-001 规格文档
- ADR-017 治理决策文档
- 现有 GateApproval 模型定义
- 现有 HumanGateRunner 实现

### Required Outputs

- 扩展后的 GateApproval 数据模型
- GatePurpose 和 GateDecisionMode 枚举定义
- HumanGateRunner 双轴解析逻辑
- AutoCheckGateRunner 双轴标注
- 审计日志扩展（log_gate_triggered 添加双轴字段）

### Forbidden Shortcuts

- 不得重新引入第三条分类轴表达 gate 职责或决策方式
- 不得创建 approval + auto 或 approval + conditional_human 的非法组合
- 不得把历史分类值作为正式治理语义发布
- 不得绕过组合验证逻辑直接写入数据库

## Delivery Handoffs

- from: `TECH`
  to: `TASK`
  artifacts:
    - 数据模型改造任务清单
    - Runner 改造任务清单
    - CLI 改造任务清单
- from: `TECH`
  to: `DEVPLAN`
  artifacts:
    - 实现优先级说明（P0/P1/P2）
    - 技术风险与缓解策略
- from: `TECH`
  to: `TESTPLAN`
  artifacts:
    - 组合验证测试用例
    - 历史配置兼容性测试用例

## Validation Rules

- rule: purpose 必须是 review 或 approval
  description: 验证 purpose 字段值合法性，防止非法值污染
  severity: blocker
- rule: decision_mode 必须是 auto、conditional_human 或 human_required
  description: 验证 decision_mode 字段值合法性
  severity: blocker
- rule: approval purpose 必须与 human_required decision_mode 组合
  description: ADR-017 强制约束，禁止 approval 自动路径
  severity: blocker
- rule: 历史配置必须能映射到双轴模型
  description: 确保向后兼容性，旧工作流模板可正常执行
  severity: major
- rule: 审计日志必须包含双轴字段
  description: 确保审计追溯完整性
  severity: major

## Implementation Priority

### P0: 核心改造（必须）

1. 新增枚举定义（GatePurpose, GateDecisionMode）
2. 扩展 GateApproval 数据模型
3. 扩展 SQLiteStore 方法
4. HumanGateRunner 双轴解析
5. 组合验证逻辑
6. 旧字段映射逻辑

### P1: 增强改造（推荐）

1. CLI 双轴信息展示
2. 审计日志扩展
3. 数据库迁移脚本
4. Workflow 模板示例更新

### P2: 可选改造（延后）

1. 历史数据自动迁移
2. 运行时执行逻辑改造
3. CLI 展示细节重构

## Risks And Fallback

### 风险 1: 历史数据迁移

**风险描述**: 现有数据库中的 gate_approvals 记录没有 purpose/decision_mode 字段

**缓解措施**: 在 `_row_to_gate_approval` 中提供默认值，旧记录返回 `purpose=REVIEW, decision_mode=HUMAN_REQUIRED`

### 风险 2: 组合验证遗漏

**风险描述**: 未正确验证 `approval + auto` 的非法组合

**缓解措施**: 在 HumanGateRunner 和 SQLiteStore 两处都进行验证

### 风险 3: 旧配置兼容性问题

**风险描述**: 现有 workflow.yaml 中的 gate 配置未包含双轴字段

**缓解措施**: 提供完整的默认值映射，旧配置自动推导双轴字段

## Review Checklist

- 技术选型是否支撑 FEAT 目标而非引入新的平级入口
- 输入契约和输出边界是否可被下游 workflow 直接消费
- 风险、fallback 和删除条件是否清晰且可执行
- 是否保留对 FEAT-SRC-041-001 和 ADR-017 的可追溯引用

## Out Of Scope

- 运行时执行逻辑改造（本次仅收敛语义）
- CLI 展示细节重构
- 历史数据自动迁移（提供迁移脚本但不强制）

## Metadata

- TECH ID: `TECH-FEAT-SRC-041-001`
- Parent FEAT: `FEAT-SRC-041-001`
- Source Refs: `FEAT-SRC-041-001`, `EPIC-SRC-041-016`, `ADR-017`
- Workflow Instance: `wf_task_851b68f0`
