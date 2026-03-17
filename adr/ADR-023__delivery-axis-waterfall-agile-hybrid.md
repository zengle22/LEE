---
id: ADR-023
title: 交付轴设计 - 瀑布 - 敏捷混合模式 (Delivery Axis Design)
status: accepted
version: v1
workflow_instance_id: wf-adr-023-20260317
source_refs: []
owner: dev-governance
tags:
  - delivery-axis
  - waterfall-agile-hybrid
  - workflow-architecture
  - release-management
properties:
  design_kind: architecture_decision_record
  supersedes:
    - SRC-046-delivery-axis-complete-flow-design
    - SRC-047-delivery-axis-design-review
    - SRC-048-waterfall-agile-hybrid
---

# ADR-023: 交付轴设计 - 瀑布 - 敏捷混合模式

## 一、决策背景

### 1.1 问题陈述

将当前"对象存在、命令存在、局部执行链存在"但尚未形成正式版本交付 workflow 的状态，收敛为一个稳定的源问题：建立以 RELEASE 为起点的正式交付主链和发布闭环，使版本交付、计划承接、任务执行、证据回流与发布关闭能够按统一治理路径运行。

### 1.2 业务动因

当前交付轴缺少正式 workflow，导致：
- 版本交付仍依赖命令式创建、局部链路拼接和历史兼容入口
- 难以保证交付对象绑定一致性、scope 完整性、缺陷回流路径和发布关闭标准
- QA 与研发执行入口对正式交付主链的绑定关系不明确

### 1.3 目标用户

- LEE 内部负责版本发布治理、需求承接治理、研发执行治理、QA 交付治理与流程审计的产品/治理负责人

### 1.4 关键约束

- ADR-001 三轴治理方向与交付链硬治理约束
- 现有 RELEASE、DEVPLAN、TESTPLAN、TASK 对象基础
- 现有 release-cut、plan-derive、plan-check、release-check、release-close 等命令基础
- QA 已部分切换到 TASK -> TESTPLAN -> RELEASE 的现状
- Python runtime 继续承担 workflow 执行编排责任

---

## 二、设计目标

**既要**：
- 瀑布模型的规范性和质量管控
- 可预测的交付承诺
- 清晰的里程碑和决策点

**又要**：
- 敏捷开发的灵活性和快速反馈
- 小步快跑的迭代交付
- 适应变化的能力

---

## 三、核心架构设计

### 3.1 完整 SSOT 交付链

```
Product 部门：RAW → SRC → EPIC → FEAT → Delivery Prep (UI/TECH/TASK)
                              │
                              ▼
Dev Governance:       FEAT Bundle → RELEASE → DEVPLAN → TASK
                                      │
                                      ▼
QA 部门：                        RELEASE → TESTPLAN → Test Set
```

### 3.2 瀑布 - 敏捷混合模式：精简模型

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
│  Retrospective         →  RELEASE Close 后执行                  │
│  Definition of Done    →  三层质量门禁 (L1/L2/L3)               │
│  Definition of Ready   →  Delivery Prep Freeze                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.3 核心设计原则

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

### 3.4 名与实的哲学

```yaml
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

## 四、交付轴三层 Workflow 架构

### 4.1 L1: Release Delivery DAG (版本交付主链)

```
┌─────────────────────────────────────────────────────────────────┐
│                    L1: Release Delivery                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Scope Management → Plan Derivation → Dev Execution            │
│        │                │                    │                  │
│        ▼                ▼                    ▼                  │
│     RELEASE         DEVPLAN              TASK L2s               │
│                      TESTPLAN             │                     │
│                         │                 ▼                     │
│                         └──────→ QA Execution ←────────────────┘│
│                                        │                        │
│                                        ▼                        │
│                                 Release Closure                 │
│                                 (Go/No-Go Gate)                 │
└─────────────────────────────────────────────────────────────────┘
```

**L1 五个阶段**:
1. **Scope Management**: RELEASE 初始化、范围验证、范围冻结
2. **Plan Derivation**: 派生 DEVPLAN、派生 TESTPLAN
3. **Dev Execution**: 对每个 TASK 生成 Feature Dev L2 并跟踪
4. **QA Execution**: 对每个 Test Set 生成 Test Plan L2 并跟踪
5. **Release Closure**: 覆盖度检查、Go/No-Go 决策、RELEASE 关闭

### 4.2 L2: DEVPLAN/TESTPLAN Management (计划执行)

```
L2: DEVPLAN Management          L2: TESTPLAN Management
─────────────────────           ───────────────────────
1. Dev Plan Init                1. Test Plan Init
2. Task Organization            2. Test Strategy Define
   (组织已有 TASK，                 (基于 FEAT.AC + TECH + TASK)
    非派生 TASK)                   3. Test Set Production
3. Task Validate                   (生产设计资产用于验证)
4. Devplan Freeze               4. Test Set Validate
5. Spawn Dev L2                 5. TESTPLAN Freeze
6. Track Progress               6. Spawn Test Run L2
7. Aggregate Results            7. Track Progress
                                8. Aggregate Results
```

**关键依赖关系**:
- DEVPLAN 不派生 TASK，而是组织/分配已有 TASK（TASK 在 Delivery Prep 已生成）
- Test Set 设计资产在 TESTPLAN Freeze 前生产（用于覆盖度验证）
- Test Set 执行在 TESTPLAN Freeze 后进行

### 4.3 L3: Feature Dev/Test Set Execution (详细实施)

```
L3: Feature Dev                 L3: Test Set Production
─────────────────               ───────────────────────
1. Tech Design (如需要)          1. 读取 FEAT.AC
2. Contract Design              2. 读取 TECH specs
3. BE/FE Implementation         3. 定义 Test Cases
4. Integration                  4. 定义优先级 (P0/P1/P2)
5. Evidence Pack                5. 建立可追溯性
6. Smoke Gate
```

---

## 五、SSOT 对象定义

| SSOT 类型 | 中文名 | 责任部门 | 输入 | 输出 | 备注 |
|-----------|--------|----------|------|------|------|
| **SRC** | Source | Product | ADR + Raw | EPIC | 聚焦的源问题 |
| **EPIC** | 史诗 | Product | SRC | FEAT Bundle | 不可直接交付 |
| **FEAT** | 特性 | Product | EPIC | Delivery Prep | 最小交付单元 |
| **RELEASE** | 版本 | Dev | FEAT Bundle | DEVPLAN + TESTPLAN | = Sprint |
| **DEVPLAN** | 开发计划 | Dev | RELEASE + TASK | Task Execution Order | = Dev Backlog |
| **TESTPLAN** | 测试计划 | QA | RELEASE + FEAT.AC | Test Strategy | = QA Backlog |
| **TASK** | 任务 | Dev/QA | FEAT + TECH | 执行结果 | 在 Delivery Prep 生成 |

**Test Set 生命周期**:
```yaml
phase1: "Test Set 设计资产生产 (TESTPLAN Freeze 前)"
  purpose: "用于覆盖度验证"
phase2: "Test Set 执行 (TESTPLAN Freeze 后)"
  purpose: "实际测试运行"
```

---

## 六、变更管理流程

### 6.1 RELEASE 内变更流程

```yaml
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

### 6.2 DEVPLAN/TESTPLAN 变更规则

```yaml
DEVPLAN 变更:
  - TASK 间顺序调整：团队自行决定，更新 task_execution_order.yaml
  - 新增 TASK：需评估是否影响 RELEASE 目标，更新 DEVPLAN 并记录原因
  - 删除 TASK：需 PO 批准，更新 DEVPLAN 并记录原因

TESTPLAN 变更:
  - Test Set 优先级调整：QA 自行决定，更新 TESTPLAN
  - 新增 Test Set：需评估是否影响覆盖度，更新 TESTPLAN
  - 删除 Test Set：需 QA Lead 批准，记录原因
```

---

## 七、质量门禁：Definition of Done

### 7.1 三层 DoD

```yaml
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

### 7.2 QA Execution 前置条件

```yaml
Pre-conditions:
  - dev_progress.dev_l2_ready_rate >= 80%  # 降低阈值
  - smoke_gate_pass_rate >= 100%           # Smoke Gate 必须通过
  - critical_path_complete: true           # 关键路径必须完成
```

---

## 八、完整用户故事线

### 8.1 端到端流程

```
1. Product Pipeline
   ├─ Raw Requirement → SRC (聚焦源问题)
   ├─ SRC → EPIC (史诗分解)
   ├─ EPIC → FEAT Bundle (特性冻结)
   └─ FEAT → Delivery Prep (UI/TECH/TASK 冻结)

2. Release Delivery L1
   ├─ Scope Management (RELEASE 初始化 + 冻结)
   ├─ Plan Derivation (DEVPLAN + TESTPLAN 派生)
   ├─ Dev Execution (TASK → Dev L2 → Evidence)
   ├─ QA Execution (Test Set → Test L2 → Results)
   └─ Release Closure (Go/No-Go → Close)

3. Dev Plan Management L2
   ├─ 读取 RELEASE + TASK (已有)
   ├─ 组织 TASK 执行顺序
   ├─ 验证 TASK 覆盖度
   ├─ 冻结 DEVPLAN
   └─ 生成 Dev L2 实例并跟踪

4. Test Plan Management L2
   ├─ 读取 RELEASE + FEAT.AC + TECH + TASK
   ├─ 定义测试策略
   ├─ 生产 Test Set 设计资产
   ├─ 验证 Test Set 覆盖度
   ├─ 冻结 TESTPLAN
   └─ 生成 Test Run L2 实例并跟踪
```

### 8.2 关键门禁

```yaml
gates:
  - gate.dev.scope_freeze_gate:
      type: human_approval
      reviewers: [release_manager, product_owner, tech_lead]

  - gate.dev.scope_validate_gate:
      type: auto_check
      checks: ["FEAT Bundle 非空", "FEAT 已冻结", "依赖清晰"]

  - gate.dev.plan_validate_gate:
      type: auto_check
      checks: ["DEVPLAN/TESTPLAN 覆盖所有 FEAT", "依赖清晰"]

  - gate.dev.go_nogo_gate:
      type: human_approval
      options: [Go, Conditional Go, No-Go]
      inputs: [dev_complete_rate, qa_pass_rate, bug_summary]
```

---

## 九、实施建议

### 9.1 实施阶段

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

### 9.2 度量指标 (DORA)

```yaml
delivery_metrics:
  - lead_time: "FEAT Freeze 到 RELEASE Close 的时间"
  - cycle_time: "TASK Start 到 TASK Complete 的时间"
  - throughput: "单位时间完成的 FEAT 数量"

quality_metrics:
  - defect_density: "每千行代码 Bug 数"
  - test_coverage: "代码覆盖率"
  - escape_rate: "生产环境 Bug 比例"

reliability_metrics:  # DORA
  - deployment_frequency
  - change_failure_rate
  - mttr
```

---

## 十、验收标准

### 10.1 团队认知验收

```yaml
团队认知验收:
  - 能说出 RELEASE = Sprint
  - 能说出 DEVPLAN/TESTPLAN = Sprint Backlog
  - 理解变更是允许的，但需要 SSOT 留痕
```

### 10.2 流程验收

```yaml
流程验收:
  - 首个 RELEASE 按固定周期完成
  - 变更流程被执行且留痕
  - 三层 DoD 被严格执行
```

### 10.3 价值验收

```yaml
价值验收:
  - 团队感受流程灵活 (非瀑布式僵化)
  - 干系人感受交付可预测 (非敏捷式随意)
  - DORA 指标有改进趋势
```

---

## 十一、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 团队抵触新流程 | 中 | 渐进式引入，强调 RELEASE=Sprint 的简单映射 |
| 变更频繁 | 中 | 明确轻量/重量流程门槛，SSOT 留痕 |
| SSOT 更新滞后 | 高 | 将 SSOT 更新纳入 DoD，不更新不算完成 |
| 形式大于内容 | 高 | 定期 Retrospective，强调敏捷价值观 |

---

## 十二、后续行动

### 12.1 立即行动 (本周)

1. **修正图示矛盾** - 确保图示与正文描述一致
2. **明确 QA 前置条件** - 降低完成率阈值，添加 Smoke Gate 要求
3. **澄清 Test Set 生命周期** - 区分设计资产生产和执行
4. **补充 Bug 管理流程** - 定义 Bug 生命周期和 SLA

### 12.2 短期行动 (本月)

1. **添加变更管理流程** - 正式化变更控制
2. **添加风险管理流程** - 风险识别、评估、应对
3. **添加度量指标体系** - DORA 指标集成

### 12.3 中期行动 (本季度)

1. **添加环境管理** - Dev/QA/Staging 环境配置
2. **添加回滚预案** - 发布安全保证
3. **添加依赖管理** - 跨团队依赖跟踪
4. **集成 CI/CD** - 持续集成/持续部署

---

## 十三、与 SRC-046 原始设计的关系

```
原始 SRC-046 (jiaofuzhou-workflow-huazhiliyufabubihuanjianshe.md):
  - 这是正式的 SRC 规范，已衍生完整的 EPIC/FEAT/TASK 链
  - 状态：frozen
  - 不能删除，保留作为实际交付源头

本 ADR-023:
  - 整合了 SRC-046 设计文档、SRC-047 审查报告、SRC-048 混合模式设计
  - 提供了完整的架构决策记录
  - 状态：accepted
  - 作为交付轴设计的权威参考
```

---

## 十四、结论

交付轴设计采用"瀑布 - 敏捷混合模式"，核心洞察是：

1. **RELEASE = Sprint**: 一个 RELEASE 就是一个完整的迭代周期 (2-4 周)
2. **DEVPLAN/TESTPLAN = Sprint Backlog**: 开发/测试任务的有序列表
3. **变更是常态**：RELEASE 内允许变更，但需要 SSOT 留痕
4. **三层 DoD**：TASK 级 → FEAT 级 → RELEASE 级的质量门禁
5. **形散而神不散**：瀑布式命名 (便于对外沟通) + 敏捷实质 (对内灵活)

该设计既保证了交付的规范性和可预测性，又保持了敏捷的灵活性和快速反馈能力。
