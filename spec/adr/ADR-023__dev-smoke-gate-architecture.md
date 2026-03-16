---
id: ADR-023
ssot_type: adr
title: Dev Smoke Gate 架构与测试职责分层
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs:
  - ADR-005#1
  - ADR-007
  - ADR-008
  - ADR-011
owner: governance
tags: [testing, smoke-gate, dev-workflow, qa-workflow, governance]
workflow_instance_id: wf-adr-023-20260316
properties:
  adr_kind: governance_policy
  frozen_at: 2026-03-16T00:00:00+08:00
  issue_class: test_architecture
---

# Problem

LEE 当前测试流程存在以下问题：

1. **职责边界模糊**：Dev 开发和 QA 测试执行完全分离，导致 Dev 跑完自测后 QA 还要再跑一遍，重复劳动。

2. **流程过于复杂**：Test Plan Execution L2 有 9 个 Phase，对 Dev 场景过于沉重，且需要部署到独立测试环境，增加了环境维护成本。

3. **测试资产不互通**：Dev 和 QA 各自维护测试资产，同一功能被多次测试，效率低下。

4. **门禁位置靠后**：Smoke Gate 在开发流程末端，问题发现晚，修复成本高。

5. **Handoff 过多**：从开发到 QA 执行需要多次 Handoff，流程冗长，沟通成本高。

如果不重构测试门禁架构，Dev 和 QA 的协作效率将持续低下，且无法实现快速反馈的质量保障。

# Decision

LEE 采用 **Dev 主导的 Smoke Gate 架构**，明确 Dev 和 QA 的测试职责分层：

## 1. 职责分层

| 职责 | QA 部门 | Dev 部门 |
|------|---------|----------|
| **Test Set 设计** | 负责：将 FEAT/PRD 转化为 Test Set YAML | 使用：基于 Test Set 执行 Smoke |
| **测试执行** | 独立 QA Test Run（可选全量回归） | 强制 Dev Smoke（开发后必须执行） |
| **门禁决策** | 不直接阻塞 merge | Dev Smoke 是强制门禁（blocker） |
| **环境** | 独立测试环境（可选） | 本地 dev 环境 |

## 2. 核心流程

```
┌─────────────┐
│ SSOT Ready  │
│ FEAT 冻结    │
└──────┬──────┘
       │
       ▼
┌───────────────────────┐
│ QA: Test Set Production│ ← QA 职责边界
│                       │
│ /lee-qa-test-set      │
│                       │
│ 产出：ts-{module}.yaml │
│ (Test Set 设计资产)    │
└──────────┬────────────┘
           │ Test Set
           ▼
┌───────────────────────┐
│ Dev: Feature Dev L2   │
│                       │
│ /lee-feature          │
│                       │
│ - Contract Design     │
│ - Backend Dev         │
│ - Frontend Dev        │
│ - Integration         │
└──────────┬────────────┘
           │ 代码就绪
           ▼
┌───────────────────────┐
│ Dev: Smoke Test L3    │ ← 新增轻量级流程
│                       │
│ /lee-dev-smoke        │
│ --test-set <ts.yaml>  │
│                       │
│ 1. Env Check (本地)    │
│ 2. Case Generation    │
│ 3. Script Execution   │
│ 4. Result Judgment    │
│ 5. Evidence Pack      │
└──────────┬────────────┘
           │ Smoke 结果
           ▼
┌───────────────────────┐
│ Smoke Gate (Auto)     │ ← 强制门禁
│                       │
│ 检查：                 │
│ - pass_rate == 100%   │
│ - coverage >= 80%     │
│                       │
│ PASS → Merge OK       │
│ FAIL → Fix & Retry    │
└───────────────────────┘
```

## 3. Dev Smoke L3 设计

### 流程定义

```yaml
kind: l3_workflow_template
version: "1.0"
id: template.dev.smoke_l3
name: Dev Smoke Test L3
description: |
  轻量级 Smoke Test 流程，5 Steps，专注于快速反馈。

  设计原则：
  - 快速：只执行必要步骤，无冗余 Phase
  - 本地：使用 dev 本地环境，无需独立测试环境
  - 强制：Smoke Gate 是 blocker 优先级，不过不能 merge

phases:
  - id: env_check
    name: "Environment Check"
    description: "检查本地 dev 环境可用性"

  - id: case_generation
    name: "Test Case Generation"
    description: "根据 Test Set 动态生成测试用例"

  - id: script_execution
    name: "Script Execution"
    description: "执行测试脚本，收集 evidence"

  - id: result_judgment
    name: "Result Judgment"
    description: "判定测试结果（Pass/Fail）"

  - id: evidence_pack
    name: "Evidence Packaging"
    description: "打包证据，移交 Smoke Gate"
```

### Smoke Gate 配置

```yaml
id: gate.dev.smoke_gate
type: automated
priority: blocker

trigger:
  event: "smoke_test_complete"
  source: "agent.dev.smoke_tester"

checks:
  - id: smoke_test_pass
    rule: "smoke_result.pass_rate == 100"
    severity: blocker
    required: true

  - id: coverage_threshold
    rule: "smoke_result.coverage >= 80"
    severity: major
    required: true

pass_criteria:
  all_required: true
  max_blocker: 0
  max_major: 0

on_fail:
  action: "block_merge"
  priority: highest
  message: "Smoke Gate 未通过，不允许 merge。"
```

## 4. QA Test Run 独立流程

QA Test Run 与 Dev 解耦，作为独立的质量保障流程：

```
┌───────────────────────┐
│ QA: Test Plan Exec L2 │
│                       │
│ /lee-qa-test-run      │
│                       │
│ - 全量回归测试         │
│ - 专项测试             │
│ - 性能测试             │
│ - 验收测试             │
└───────────────────────┘
```

**QA Test Run 的定位**：
- 不阻塞 Dev merge
- 作为发布前的最终质量确认
- 可配置为定期执行（如每日/每周回归）

## 5. Test Set 设计原则

**单一 Test Set 原则**：
- 不区分 `smoke` 和 `full`
- 一次设计，全量执行
- 通过 `priority` 字段区分用例优先级

```yaml
test_plan:
  test_suites:
    - suite_id: "TS-001"
      test_cases:
        - test_id: "TC-0001"
          priority: "P0"  # 核心流程，Dev Smoke 必跑
        - test_id: "TC-0002"
          priority: "P1"  # 重要功能，Dev Smoke 必跑
        - test_id: "TC-0003"
          priority: "P2"  # 边缘场景，QA 回归可选
```

**Dev Smoke 执行策略**：
- 默认执行 P0 + P1 用例
- 可通过配置执行全量（含 P2）

## 6. 关键约束

1. **Dev Smoke 是强制门禁**：
   - 未通过 Smoke Gate 的代码不允许 merge
   - 优先级为 `blocker`，不允许绕过

2. **QA 负责 Test Set 设计**：
   - QA 在 FEAT freeze 后生成 Test Set
   - Test Set 是 Dev 和 QA 共享的测试资产

3. **本地环境优先**：
   - Dev Smoke 使用本地 dev 环境
   - 减少环境依赖，加快反馈速度

4. **动态生成测试用例**：
   - Test Case 是 ephemeral 的，运行时生成
   - Test Set 是持久化的设计资产

# Consequences

## 正面影响

1. **流程简化**：从 6 个阶段减少到 4 个步骤，Handoff 从 3 次减少到 1 次。

2. **职责清晰**：
   - QA 负责 Test Set 设计
   - Dev 负责 Smoke 执行
   - 无重复劳动

3. **快速反馈**：
   - Dev 在本地环境直接跑 Smoke
   - 问题早发现，早修复

4. **资产统一**：
   - Dev 和 QA 共享同一套 Test Set
   - 避免测试资产分裂

5. **门禁前移**：
   - Smoke Gate 在开发结束后立即执行
   - 减少问题流入下游

## 负面影响

1. **QA Test Run 定位需明确**：
   - QA 团队需要接受 Test Run 不直接阻塞 merge
   - 需要建立 QA 反馈机制（如定期回归报告）

2. **本地环境一致性**：
   - Dev 本地环境可能与生产环境有差异
   - 需要加强环境一致性检查

3. **初期适应成本**：
   - Dev 需要适应新的 Smoke 执行流程
   - 需要培训和教育

## 待办事项

- [ ] 创建 Dev Smoke L3 工作流模板
- [ ] 创建 Smoke Tester Agent
- [ ] 更新 Smoke Gate 配置
- [ ] 更新 `/lee-feature` 流程，集成 Smoke 执行
- [ ] 创建用户技能 `/lee-dev-smoke`
- [ ] 更新 QA 部门工作流文档
- [ ] 更新 Dev 部门工作流文档

# References

- ADR-005: Gate 三分类治理模型
- ADR-007: QA Department SSOT Alignment and Workflow Reframe
- ADR-008: Dev Department SSOT Alignment and Workflow Reframe
- ADR-011: 需求联测一致性测试体系建设
