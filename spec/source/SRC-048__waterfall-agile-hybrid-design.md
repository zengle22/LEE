---
id: SRC-048
ssot_type: src
title: 瀑布 - 敏捷混合模式设计 (SRC-048)
status: draft
version: v1
workflow_instance_id: wf-src-048-20260317
source_refs:
  - SRC-046
  - SRC-047
owner: dev-governance
tags:
  - delivery-axis
  - hybrid-model
  - waterfall-agile
properties:
  design_kind: workflow_architecture
  governed_by_adrs:
    - ADR-001
---

# 瀑布 - 敏捷混合模式设计 (SRC-048)

## 一、设计目标

**既要**：
- 瀑布模型的规范性和质量管控
- 可预测的交付承诺
- 清晰的里程碑和决策点

**又要**：
- 敏捷开发的灵活性和快速反馈
- 小步快跑的迭代交付
- 适应变化的能力

---

## 二、精简模型：命名映射

您的理解是正确的。当前设计可以简化为以下映射关系：

```
┌─────────────────────────────────────────────────────────────────┐
│  敏捷术语          →    当前设计术语                            │
├─────────────────────────────────────────────────────────────────┤
│  Sprint                →  RELEASE                               │
│  Sprint Backlog        →  DEVPLAN + TESTPLAN                    │
│  Product Backlog       →  FEAT Bundle (来自 Delivery Prep)      │
│  Sprint Planning       →  Scope Management + Plan Derivation    │
│  Daily Standup         →  track_dev/qa_progress                 │
│  Sprint Review         →  Release Closure (Go/No-Go)            │
│  Retrospective         →  (待补充)                              │
│  Definition of Done    →  三层质量门禁 (L1/L2/L3)               │
│  Definition of Ready   →  Delivery Prep Freeze                  │
└─────────────────────────────────────────────────────────────────┘
```

### 核心设计原则

```yaml
单一 RELEASE = 单一 Sprint:
  - 不采用多 Sprint 累积模式
  - 一个 RELEASE 就是一个完整的迭代周期 (建议 2-4 周)
  - RELEASE 关闭后立即开启下一个 RELEASE

DEVPLAN/TESTPLAN = Sprint Backlog:
  - DEVPLAN: 开发任务的有序列表 (含优先级、依赖、责任人)
  - TESTPLAN: 测试任务的有序列表 (含测试策略、优先级、覆盖范围)
  - 两者共同构成完整的 Sprint Backlog

变更机制 = 敏捷协商 + SSOT 追溯:
  - RELEASE 内允许变更 (类似 Sprint 内协商)
  - 但必须同步更新 SSOT (保持追溯性)
  - 变更门槛由团队自定 (而非外部强加)

质量门禁 = Definition of Done:
  - L3: TASK 级 DoD (代码审查 + 测试通过)
  - L2: FEAT 级 DoD (Dev + QA 完成)
  - L1: RELEASE 级 DoD (Go/No-Go 决策)
```

---

## 三、单一 RELEASE 模型

### 3.1 RELEASE = Sprint

```yaml
单一 RELEASE 模型:
  周期：2-4 周 (团队自定，建议固定)
  输入：FEAT Bundle (来自 Delivery Prep，已冻结)
  产出：可工作的软件 + 证据包 + RELEASE Close 报告

  流程映射:
    ┌────────────────────────────────────────────────────┐
    │  敏捷 Sprint        →    交付轴 RELEASE            │
    ├────────────────────────────────────────────────────┤
    │  Sprint Planning    →    Scope Management          │
    │  (承诺 Sprint 目标)   →    (冻结 RELEASE Scope)      │
    │                         Plan Derivation            │
    │                         (生成 DEVPLAN/TESTPLAN)    │
    ├────────────────────────────────────────────────────┤
    │  Sprint Execution   →    Dev Execution + QA        │
    │  (开发 + 测试)       →    Execution                 │
    │                         (spawn L2 + track)         │
    ├────────────────────────────────────────────────────┤
    │  Sprint Review      →    Release Closure          │
    │  (演示 + 验收)       →    (Go/No-Go 决策 + Close)  │
    ├────────────────────────────────────────────────────┤
    │  Retrospective      →    (待补充)                 │
    │  (改进)             →    (RELEASE Close 后执行)     │
    └────────────────────────────────────────────────────┘
```

### 3.2 DEVPLAN/TESTPLAN = Sprint Backlog

```yaml
DEVPLAN (开发任务列表):
  结构:
    - task_refs: [TASK-001, TASK-002, ...]
    - task_execution_order: 定义执行顺序
    - workstream_grouping: 按工作流分组

  敏捷对应:
    - 相当于 Sprint Backlog 的开发任务部分
    - 团队在 Scope Management 阶段共同承诺
    - 执行过程中可调整顺序，但需更新 SSOT

  变更规则:
    - TASK 间顺序调整：团队自行决定，更新 task_execution_order.yaml
    - 新增 TASK：需评估是否影响 RELEASE 目标，更新 DEVPLAN 并记录原因
    - 删除 TASK：需 PO 批准，更新 DEVPLAN 并记录原因

TESTPLAN (测试任务列表):
  结构:
    - test_strategy: 测试策略 (smoke/regression/automation)
    - test_set_refs: [TestSet-001, TestSet-002, ...]
    - test_milestones: 测试里程碑

  敏捷对应:
    - 相当于 Sprint Backlog 的测试任务部分
    - QA 团队在 Plan Derivation 阶段承诺
    - 执行过程中可调整优先级，但需更新 SSOT

  变更规则:
    - Test Set 优先级调整：QA 自行决定，更新 TESTPLAN
    - 新增 Test Set：需评估是否影响覆盖度，更新 TESTPLAN
    - 删除 Test Set：需 QA Lead 批准，记录原因
```

### 3.3 变更控制：敏捷协商 + SSOT 追溯

```yaml
RELEASE 内变更流程:
  场景:
    - 技术风险：某 TASK 无法按原计划完成
    - 需求理解偏差：FEAT 范围需要调整
    - 优先级变化：需要插入新 TASK

  轻量流程 (不改变 RELEASE 目标):
    1. 团队评估影响 (< 4 小时)
    2. Product Owner 口头/书面批准
    3. 更新 DEVPLAN/TESTPLAN SSOT
    4. 记录变更原因 (用于 Retrospective)

  重量流程 (改变 RELEASE 目标):
    1. 变更影响评估报告
    2. CCB 审批 (release_manager + product_owner + tech_lead)
    3. 更新 RELEASE SSOT (新版本号)
    4. 通知所有干系人

  关键原则:
    - 变更是允许的 (敏捷思维)
    - 但必须留痕 (SSOT 追溯)
    - 团队共同承担变更后果
```

---

## 四、质量门禁：Definition of Done

```yaml
三层 DoD:
  L3_DoD (TASK 级):
    - 代码审查通过
    - 单元测试覆盖率 >= 80%
    - 集成测试通过
    - Smoke Test 通过
    - evidence_pack 完整

  L2_DoD (FEAT 级):
    - 所有 TASK 通过 L3 DoD
    - Dev 完成率 = 100%
    - QA 完成率 = 100%
    - 无 P0/P1 Bug

  L1_DoD (RELEASE 级):
    - 所有 FEAT 通过 L2 DoD
    - Go/No-Go 决策通过
    - 发布说明完整
    - 回滚预案就绪

  执行逻辑:
    - TASK 必须通过 L3 DoD 才能标记为"完成"
    - FEAT 必须通过 L2 DoD 才能进入 RELEASE 统计
    - RELEASE 必须通过 L1 DoD 才能关闭
```

---

## 五、关键设计思想

```yaml
名与实的哲学:
  我们使用"瀑布式"命名 (RELEASE/DEVPLAN/TESTPLAN) 的原因:
    - 符合传统软件工程的直观理解
    - 便于与非敏捷团队沟通
    - 强调交付的严肃性和承诺

  但实质是敏捷的:
    - RELEASE = Sprint (固定周期迭代)
    - DEVPLAN/TESTPLAN = Sprint Backlog (可协商的任务列表)
    - 变更是允许的，但需要留痕 (SSOT 追溯)
    - 质量门禁 = Definition of Done

  形散而神不散:
    - "形": 瀑布式文档和流程
    - "神": 敏捷的价值观和实践
    - 两者结合：对外可承诺，对内可灵活
```

---

## 六、与 SRC-046 的映射关系

```
SRC-046 交付轴           SRC-048 精简模型
────────────────────    ────────────────────
RELEASE                 →  RELEASE (= Sprint)
DEVPLAN                 →  开发 Sprint Backlog
TESTPLAN                →  测试 Sprint Backlog
Scope Management        →  Sprint Planning
Dev Execution           →  Sprint Execution (Dev 泳道)
QA Execution            →  Sprint Execution (QA 泳道)
Release Closure         →  Sprint Review + Go/No-Go
(待补充)                →  Retrospective

关键简化:
  - 不再区分"瀑布层"和"敏捷层"
  - RELEASE 本身就是完整的迭代
  - DEVPLAN/TESTPLAN 就是 Backlog 的结构化表达
  - 变更是常态，但需要 SSOT 追溯
```

---

## 七、实施建议

```yaml
Phase 1: 认知对齐 (第 1 周)
  - 团队理解 RELEASE=SPRINT 的映射
  - 理解 DEVPLAN/TESTPLAN=Backlog 的实质
  - 统一变更流程认知

Phase 2: 试点运行 (第 2-5 周)
  - 选择一个小型 RELEASE 试点
  - 执行 2 个完整迭代
  - 收集反馈并调整

Phase 3: 持续改进 (第 6 周起)
  - 添加 Retrospective 仪式
  - 优化度量指标
  - 沉淀最佳实践
```

---

## 八、风险与缓解 (精简版)

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 团队抵触新流程 | 中 | 渐进式引入，强调 RELEASE=Sprint 的简单映射 |
| 变更频繁 | 中 | 明确轻量/重量流程门槛，SSOT 留痕 |
| SSOT 更新滞后 | 高 | 将 SSOT 更新纳入 DoD，不更新不算完成 |
| 形式大于内容 | 高 | 定期 Retrospective，强调敏捷价值观 |

---

## 九、验收标准

```yaml
团队认知验收:
  - 能说出 RELEASE = Sprint
  - 能说出 DEVPLAN/TESTPLAN = Sprint Backlog
  - 理解变更是允许的，但需要 SSOT 留痕

流程验收:
  - 首个 RELEASE 按固定周期完成
  - 变更流程被执行且留痕
  - 三层 DoD 被严格执行

价值验收:
  - 团队感受流程灵活 (非瀑布式僵化)
  - 干系人感受交付可预测 (非敏捷式随意)
  - DORA 指标有改进趋势
```
