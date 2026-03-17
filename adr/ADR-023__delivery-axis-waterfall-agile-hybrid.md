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

### SSOT 回流机制

```yaml
TASK 执行结果回流到 DEVPLAN:
  触发条件: TASK 完成 (通过 L3 DoD)
  回流内容:
    - TASK.status: "completed"
    - TASK.evidence_pack_ref: 证据包位置
    - TASK.actual_effort: 实际工时
    - TASK.blockers: 遇到的阻塞 (如有)
  更新频率: 实时 (TASK 完成时立即更新)
  责任方: TASK 执行者

Test Set 执行结果回流到 TESTPLAN:
  触发条件: Test Set 执行完成
  回流内容:
    - Test Set.status: "passed/failed/blocked"
    - Test Set.pass_rate: 通过率
    - Test Set.bugs: 发现的 Bug 列表
    - Test Set.execution_time: 执行时间
  更新频率: 实时 (Test Set 完成时立即更新)
  责任方: QA 执行者

DEVPLAN/TESTPLAN 状态汇总到 RELEASE:
  触发条件: DEVPLAN/TESTPLAN 更新
  汇总内容:
    - dev_completion_rate: Dev 完成率 (已完成任务/总任务)
    - qa_pass_rate: QA 通过率 (通过测试/总测试)
    - bug_summary: Bug 统计 (按优先级)
    - blocker_count: 当前阻塞数
  更新频率: 每次 L2 更新时自动汇总
  责任方: Workflow 系统自动计算

RELEASE 状态用于决策:
  触发条件: 达到计划完成时间或所有 FEAT 完成
  决策输入:
    - 所有 FEAT 的 L2 DoD 状态
    - Bug 摘要 (P0/P1 数量)
    - 风险清单
  决策输出: Go/No-Go/Conditional Go
  责任方: release_manager 组织决策
```

### L1/L2/L3 层级衔接规则

```yaml
L1 → L2 (Spawn 规则):
  触发条件:
    - Scope Freeze 完成后，自动触发 Plan Derivation L2
    - Plan Derivation 完成后，自动触发 Dev Execution L2 和 QA Execution L2

  L2 实例生成:
    - DEVPLAN Management L2: 1 个 (管所有 TASK)
    - TESTPLAN Management L2: 1 个 (管所有 Test Set)

  输入:
    - RELEASE 对象 (含冻结的 FEAT Bundle)
    - 已有 TASK 列表 (来自 Delivery Prep)
    - FEAT.AC + TECH (用于测试策略)

L2 → L3 (Spawn 规则):
  触发条件:
    - DEVPLAN Freeze 后，对每个 TASK 生成 Feature Dev L2
    - TESTPLAN Freeze 后，对每个 Test Set 生成 Test Run L2

  L3 实例生成:
    - Feature Dev L2: N 个 (每个 TASK 一个)
    - Test Run L2: M 个 (每个 Test Set 一个)

  输入:
    - TASK (含优先级、依赖、责任人)
    - Test Set (含测试策略、优先级)

L3 → L2 (上报规则):
  触发条件:
    - L3 完成：更新状态、证据、度量
    - L3 阻塞：立即上报，记录 blocker
    - L3 失败：创建 Bug，上报失败原因

  上报内容:
    - 状态更新 (completed/failed/blocked)
    - 证据包位置
    - 度量数据 (工时、覆盖率等)
    - 问题清单

L2 → L1 (汇总规则):
  触发条件:
    - 所有 L3 完成后
    - 或达到里程碑检查点

  汇总内容:
    - 完成率 (Dev/QA)
    - 质量指标 (Bug 数、覆盖率)
    - 进度风险
    - 推荐决策 (Go/No-Go)

  决策支持:
    - 自动计算覆盖度
    - 生成决策报告
    - 标记风险项
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
  - 代码审查通过 (至少 1 人审查，核心代码需 2 人)
  - 单元测试覆盖率 >= 80% (新代码)，存量代码不降低
  - 集成测试通过
  - Smoke Test 通过
  - evidence_pack 完整 (见 7.4 Evidence Pack 清单)

L2_DoD (FEAT 级):
  - 所有 TASK 通过 L3 DoD
  - Dev 完成率 = 100%
  - QA 完成率 = 100%
  - 无 P0/P1 Bug (定义见 7.3)

L1_DoD (RELEASE 级):
  - 所有 FEAT 通过 L2 DoD
  - Go/No-Go 决策通过 (标准见 7.2)
  - 发布说明完整
  - 回滚预案就绪

执行逻辑:
  - TASK 必须通过 L3 DoD 才能标记为"完成"
  - FEAT 必须通过 L2 DoD 才能进入 RELEASE 统计
  - RELEASE 必须通过 L1 DoD 才能关闭
```

### 7.2 Go/No-Go 决策标准

```yaml
Go/No-Go 决策矩阵:
  Go (允许发布):
    - 所有 FEAT 通过 L2 DoD
    - 无 P0 Bug
    - P1 Bug <= 3 个且有明确修复计划
    - 发布说明完整
    - 回滚预案已验证
    - 关键干系人确认 (release_manager + product_owner)

  Conditional Go (条件发布):
    - 所有 FEAT 通过 L2 DoD
    - 无 P0 Bug
    - P1 Bug <= 5 个
    - 满足以下至少 2 个条件:
      a) 有临时 workaround
      b) 影响范围有限 (仅影响非核心功能)
      c) 可在 48 小时内修复
    - 需要 release_manager + product_owner + tech_lead 共同批准
    - 必须创建 Bug 修复 RELEASE 在 7 天内关闭

  No-Go (禁止发布):
    - 任一 FEAT 未通过 L2 DoD
    - 存在 P0 Bug
    - P1 Bug > 5 个
    - 核心功能存在缺陷
    - 回滚预案未验证
    - 任一关键干系人反对

决策流程:
  1. release_manager 准备决策材料 (提前 24 小时)
  2. 召开 Go/No-Go 决策会议 (30 分钟)
  3. 干系人投票 (release_manager, product_owner, tech_lead)
  4. 记录决策结果和条件 (如有)
  5. 通知所有干系人
```

### 7.3 Bug 优先级定义

```yaml
Bug 分级标准:
  P0 (致命 - 立即修复):
    - 系统崩溃/无法启动
    - 核心功能完全不可用
    - 数据丢失/损坏
    - 安全漏洞
    - 响应：立即停止当前工作，24 小时内修复

  P1 (严重 - 高优先级修复):
    - 核心功能降级但不阻塞
    - 非核心功能完全不可用
    - 影响 50% 以上用户
    - 性能严重下降 (>50%)
    - 响应：当前 RELEASE 内修复

  P2 (一般 - 正常排期):
    - 非核心功能降级
    - 影响 <50% 用户
    - 轻微性能问题
    - UI/UX 问题不影响使用
    - 响应：3 个 RELEASE 内修复

  P3 (轻微 - 择机修复):
    - 轻微 UI 问题
    - 文档错误
    - 建议性改进
    - 响应： backlog 中优先级最低
```

### 7.4 Evidence Pack 清单

```yaml
Evidence Pack (每个 TASK 必须包含):
  代码证据:
    - 源代码文件 (已合并到主分支)
    - 单元测试文件
    - 集成测试文件 (如适用)

  测试证据:
    - 单元测试运行结果 (通过率 100%)
    - 代码覆盖率报告 (>=80%)
    - Smoke Test 运行结果
    - 集成测试结果 (如适用)

  审查证据:
    - Code Review 记录 (审查人、时间、意见)
    - 审查意见处理记录
    - 审查通过确认

  设计证据:
    - 技术设计文档 (如适用)
    - API 文档 (如有接口变更)
    - 数据库变更脚本 (如有)

  部署证据:
    - 构建成功记录
    - 部署成功记录
    - 回滚脚本 (如有)

  Evidence Pack 提交方式:
    - 位置：spec/evidence/{TASK-ID}/evidence_pack.yaml
    - 格式：YAML + 附件引用
    - 责任人：TASK 执行者
    - 验证人：Tech Lead
```

### 7.5 QA Execution 前置条件 (修复矛盾)

```yaml
Pre-conditions (必须同时满足):
  - dev_progress.dev_l2_ready_rate >= 80%
  - smoke_gate_pass_rate == 100% (所有已完成的 Dev L2 必须通过 Smoke)
  - critical_path_complete == true (关键路径 TASK 必须完成)

  说明:
    - dev_l2_ready_rate: Dev L2 完成且通过 L3 DoD 的比例
    - smoke_gate_pass_rate: 完成的 Dev L2 中通过 Smoke Test 的比例
    - critical_path: 在 DEVPLAN 中标记为 critical_path=true 的 TASK 集合

  例外处理:
    - 如 Smoke Test 失败，必须立即修复或回滚
    - 如关键路径阻塞，需 release_manager 批准调整计划
```

---

## 八、Bug 生命周期管理

### 8.1 Bug 生命周期

```
发现 → 报告 → 分类 → 分配 → 修复 → 验证 → 关闭
  │      │      │      │      │      │      │
  │      ▼      │      │      │      │      │
  │   记录     │      │      │      │      │
  │   环境     │      │      │      │      │
  │   信息     │      │      │      │      │
  │             ▼      │      │      │      │
  │          分级     │      │      │      │
  │          (P0-P3)  │      │      │      │
  │                    ▼      │      │      │
  │                 确定     │      │      │
  │                 责任方  │      │      │
  │                         ▼      │      │
  │                      创建    │      │
  │                      TASK   │      │
  │                              ▼      │
  │                           开发    │
  │                           修复    │
  │                                  ▼      │
  │                               QA      │
  │                               验证    │
  │                                      ▼
  └─────────────────────────────────── 重新打开 (如验证失败)
```

### 8.2 Bug 报告流程

```yaml
Bug 发现来源:
  - Dev 自测: 开发过程中发现问题
  - QA 测试：测试执行中发现问题
  - 自动化：CI/CD 流水线失败
  - 生产监控：线上问题告警
  - 用户反馈：内部/外部用户报告

Bug 报告要求 (必须包含):
  基本信息:
    - 标题：简洁描述问题
    - 优先级：P0/P1/P2/P3 (见 7.3)
    - 发现环境：Dev/QA/Staging/Prod
    - 发现时间
    - 报告人

  技术信息:
    - 复现步骤：详细、可执行
    - 预期结果
    - 实际结果
    - 错误日志/截图
    - 影响范围：用户比例、功能模块

  关联信息:
    - 关联 FEAT (如已知)
    - 关联 TASK (如已知)
    - 关联 RELEASE
    - 关联 Commit (如已知)

Bug 报告位置:
  - 文件：spec/bugs/BUG-{YYYYMMDD}-{序号}.yaml
  - 通知：立即通知 release_manager 和 tech_lead (P0/P1)
```

### 8.3 Bug 分类与分配

```yaml
Bug 分类流程:
  1. tech_lead 初步分类 (< 2 小时)
     - 确认优先级
     - 确认影响范围
     - 确认责任团队

  2. Bug Triage (P0/P1 立即，P2/P3 每周)
     参与者：release_manager, tech_lead, product_owner
     内容:
       - 确认优先级和调整 (如需要)
       - 分配修复责任
       - 确定修复时间目标

  3. 创建修复 TASK
     - 关联到原 BUG
     - 分配责任人
     - 设定完成时间

Bug 分配原则:
  - 谁引入谁修复 (如能确定)
  - 模块负责人优先
  - P0 Bug 由最资深人员处理
```

### 8.4 Bug 修复流程

```yaml
Bug 修复 SLA:
  P0:
    - 响应：< 30 分钟
    - 修复：< 24 小时
    - 验证：立即
    - 流程：紧急 Hotfix (见 9.1)

  P1:
    - 响应：< 4 小时
    - 修复：当前 RELEASE 内
    - 验证：QA 优先排期

  P2:
    - 响应：< 24 小时
    - 修复：3 个 RELEASE 内
    - 验证：正常流程

  P3:
    - 响应：< 1 周
    - 修复：backlog 优先级最低
    - 验证：可简化

Bug 修复步骤:
  1. 分析根因
  2. 设计修复方案 (P0/P1 需要 review)
  3. 实现修复
  4. 编写/更新测试
  5. 执行 Smoke Test
  6. 提交 Evidence Pack
  7. QA 验证
  8. 关闭 Bug

Bug 重新打开:
  条件：QA 验证失败
  流程:
    - 恢复 Bug 状态为"Open"
    - 记录失败原因
    - 重新分配 (可选)
    - 优先级上调 (可选)
```

### 8.5 Bug 度量

```yaml
Bug 度量指标:
  - Bug 密度：每千行代码 Bug 数
  - Bug 趋势：每周新增/关闭 Bug 数
  - 平均修复时间 (MTTR): 从报告到关闭的平均时间
  - 重新打开率：重新打开的 Bug 比例
  - 逃逸率：生产环境发现的 Bug 数 / 总 Bug 数

  目标值:
    - Bug 逃逸率 < 5%
    - P0/P1 Bug 平均修复时间 < 24 小时
    - Bug 重新打开率 < 10%
```

---

## 九、紧急 Hotfix 流程

### 9.1 Hotfix 触发条件

```yaml
Hotfix 适用场景:
  - P0 Bug 需要立即修复
  - 生产环境严重问题
  - 安全漏洞需要紧急修补
  - 法规合规要求

不适用场景:
  - 一般功能改进
  - UI/UX 优化
  - 非紧急的 P2/P3 Bug
```

### 9.2 Hotfix 流程

```
发现生产问题
     │
     ▼
确认 P0 级别 ────────────→ 非 P0：走正常流程
     │
     ▼
通知核心团队
(release_manager, tech_lead, product_owner)
     │
     ▼
创建 Hotfix RELEASE           ┐
     │                        │
     ▼                        │
快速修复实现                  │
(可简化文档，但必须保留)       │ 并
     │                        │ 行
     ▼                        │
快速验证                      │
(至少 Smoke Test)             │
     │                        │
     ▼                        │
紧急部署 ◄────────────────────┘
     │
     ▼
生产验证
     │
     ▼
补充完整文档
(24 小时内)
     │
     ▼
事后回顾
(48 小时内)
```

### 9.3 Hotfix 特殊规则

```yaml
简化但不省略:
  ✅ 必须：代码审查 (可简化为 1 人，但必须有)
  ✅ 必须：Smoke Test
  ✅ 必须：Evidence Pack (可简化，但必须包含核心测试)
  ✅ 必须：回滚预案
  ⚠️ 可简化：详细设计文档 (事后 24 小时内补充)
  ⚠️ 可简化：完整回归测试 (事后补充)
  ⚠️ 可简化：发布说明 (先发布，事后补充)

审批流程:
  - Hotfix 启动：release_manager 口头批准即可
  - Hotfix 部署：tech_lead 批准
  - 事后回顾：必须执行

事后回顾要求:
  - 时间：48 小时内
  - 参与者：所有参与 Hotfix 的人员
  - 内容:
    - 问题根因分析
    - 为何正常流程未能发现
    - 如何预防类似问题
    - 改进行动项
```

---

## 十、环境管理

### 10.1 环境定义

```yaml
环境层级:
  Dev (开发环境):
    用途：开发和单元测试
    数据：模拟数据
    访问：开发团队
    稳定性：低 (随时可能变化)
    部署：自动 (每次 commit)

  QA (测试环境):
    用途：功能测试和集成测试
    数据：脱敏生产数据 + 测试数据
    访问：QA 团队 + 产品团队
    稳定性：中 (测试期间稳定)
    部署：手动触发 (测试开始前)

  Staging (预发布环境):
    用途：发布前验证
    数据：生产数据脱敏
    访问：核心团队
    稳定性：高 (仅发布前更新)
    部署：发布流程中自动部署

  Production (生产环境):
    用途：真实用户
    数据：生产数据
    访问：受限
    稳定性：最高
    部署：Go/No-Go 决策后
```

### 10.2 环境责任

```yaml
环境责任矩阵:
                Dev      QA      Staging   Prod
  搭建维护      Dev      Dev     DevOps    DevOps
  部署执行      Auto     Auto    Auto      Auto
  环境验证      Dev      QA      Dev+QA    DevOps
  数据准备      Dev      QA      DevOps    N/A
  问题排查      Dev      Dev     Dev+Ops   Dev+Ops
  访问审批      Tech     Tech    Release   Change
              Lead     Lead    Manager   Board
```

### 10.3 环境准入标准

```yaml
Dev → QA:
  - 单元测试通过
  - 代码审查通过
  - Smoke Test 通过

QA → Staging:
  - 功能测试通过
  - 集成测试通过
  - 性能测试通过 (如适用)

Staging → Production:
  - Go/No-Go 决策通过
  - 回滚预案验证
  - 监控告警配置完成
```

---

## 十一、RELEASE 回滚流程

### 11.1 回滚触发条件

```yaml
必须回滚的场景:
  - P0 Bug 影响生产用户
  - 核心功能不可用
  - 数据损坏风险
  - 安全漏洞

酌情回滚的场景:
  - 多个 P1 Bug 影响用户体验
  - 性能严重下降
  - 非核心功能故障但有 workaround

不回滚的场景:
  - 轻微 UI 问题
  - 影响范围有限的 Bug
  - 已有有效 workaround
```

### 11.2 回滚流程

```
发现严重问题
     │
     ▼
评估是否需要回滚
(release_manager + tech_lead + product_owner)
     │
     ├── 是 ──→ 启动回滚
     │              │
     │              ▼
     │         执行回滚脚本
     │              │
     │              ▼
     │         验证回滚成功
     │              │
     │              ▼
     │         通知干系人
     │              │
     │              ▼
     │         创建修复 RELEASE
     │
     └── 否 ──→ 启动 Hotfix
                   │
                   ▼
              按 Hotfix 流程处理
```

### 11.3 回滚预案要求

```yaml
回滚预案必须包含:
  回滚条件:
    - 明确列出触发回滚的具体标准
    - 量化指标 (如错误率 > 5%)

  回滚步骤:
    - 详细的回滚操作命令
    - 每一步的验证方法
    - 预计耗时

  回滚验证:
    - 回滚后的验证测试清单
    - 关键功能检查点
    - 数据一致性检查

  沟通计划:
    - 通知干系人模板
    - 用户公告模板 (如需要)

  回滚演练:
    - 在 Staging 环境验证回滚脚本
    - 记录演练结果
    - 更新不完善之处
```

---

## 十二、开发阻塞上报流程

### 12.1 阻塞定义

```yaml
阻塞 (Blocker) 定义:
  开发无法继续推进的状态，包括:
  - 依赖的外部服务不可用
  - 关键信息缺失 (如需求不清晰)
  - 技术难题超出当前能力
  - 环境问题导致无法开发/测试
  - 等待其他团队/人员的交付物

  阻塞时间 > 2 小时必须上报
```

### 12.2 上报流程

```
发现阻塞
     │
     ▼
尝试自主解决 (< 30 分钟)
     │
     ├── 解决 ──→ 继续开发
     │
     └── 未解决
           │
           ▼
     上报 Tech Lead
           │
           ├── 解决 ──→ 继续开发
           │
           └── 未解决 (> 2 小时)
                 │
                 ▼
           上报 Release Manager
                 │
                 ├── 解决 ──→ 继续开发
                 │
                 └── 未解决 (> 4 小时)
                       │
                       ▼
                 升级处理
                 (重新评估计划/调整范围)
```

### 12.3 上报渠道

```yaml
上报方式:
  即时通讯 (推荐):
    - 频道：#dev-blockers
    - 格式：[BLOCKER] {TASK-ID} - 简短描述
    - 响应期望：< 30 分钟

  站会:
    - 每日站会同步
    - 适用于非紧急阻塞

  邮件 (仅用于记录):
    - 抄送核心团队
    - 适用于需要正式记录的阻塞

阻塞记录:
  - 位置：spec/blockers/BLOCKER-{TASK-ID}.yaml
  - 内容：阻塞原因、影响、解决过程、经验教训
```

---

## 十三、用户故事与端到端流程

### 13.1 端到端流程

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

### 13.2 Release Manager 用户故事

**故事**: 作为 Release Manager，我希望清晰地管理 RELEASE 从开启到关闭的全流程...

**完整体验流程**:

```yaml
1. RELEASE 开启 (迭代第 1 天)
   触发条件:
     - 上一个 RELEASE 已关闭
     - Delivery Prep 有新的 FEAT Bundle 就绪

   操作步骤:
     a) 创建 RELEASE 对象 (spec/releases/release-{N}.yaml)
     b) 设定迭代周期 (开始日期、结束日期)
     c) 关联 FEAT Bundle
     d) 邀请团队成员 (developers, QA, product_owner)

   产出:
     - RELEASE 对象 (status: open)
     - 团队通知已发送

2. Scope Freeze (迭代第 1-2 天)
   输入:
     - FEAT Bundle (来自 Delivery Prep)
     - 历史 Velocity 数据 (可选)

   操作步骤:
     a) 召开 Scope 评审会 (30 分钟)
     b) 确认 FEAT 优先级
     c) 评估容量 (基于团队可用性)
     d) 冻结 RELEASE scope

   门禁:
     - gate.dev.scope_freeze_gate (human_approval)
     - 参与者：release_manager, product_owner, tech_lead

   产出:
     - RELEASE (status: scope_frozen)
     - Scope 评审会议纪要

3. Plan Derivation (迭代第 2-3 天)
   输入:
     - RELEASE (scope_frozen)
     - TASK 列表 (来自 Delivery Prep)

   操作步骤:
     a) Dev 团队组织 TASK 执行顺序
     b) QA 团队定义测试策略
     c) 生成 DEVPLAN 和 TESTPLAN
     d) 验证覆盖度 (所有 FEAT 都有 TASK 和 Test Set)

   产出:
     - DEVPLAN (status: frozen)
     - TESTPLAN (status: frozen)

4. 进度跟踪 (迭代第 4 天 - 结束前 2 天)
   日常活动:
     - 每日站会同步进展 (15 分钟)
     - 查看进度看板 (自动更新)
     - 处理阻塞升级 (> 2 小时)

   进度看板内容:
     - dev_completion_rate: Dev 完成率
     - qa_pass_rate: QA 通过率
     - blocker_count: 当前阻塞数
     - bug_summary: Bug 统计

   异常处理:
     - 如进度滞后 (< 50% 在迭代中段): 调整计划或削减范围
     - 如阻塞 > 4 小时: 升级处理

5. Go/No-Go 决策 (迭代最后 1 天)
   准备材料:
     - 决策报告 (自动生成)
     - Bug 清单 (按优先级)
     - 覆盖度报告
     - 回滚预案

   决策会议 (30 分钟):
     - 参与者：release_manager, product_owner, tech_lead
     - 审议决策报告
     - 投票决策
     - 记录决策结果

   决策结果:
     - Go: 按计划发布
     - Conditional Go: 带条件发布
     - No-Go: 推迟发布

6. RELEASE 关闭
   Go 决策后:
     a) 执行发布 (自动部署)
     b) 验证发布成功
     c) 通知干系人
     d) 更新 RELEASE (status: closed)
     e) 开启下一个 RELEASE

   No-Go 决策后:
     a) 记录原因
     b) 创建修复计划
     c) 安排下一个 RELEASE
```

### 13.3 Developer 用户故事

**故事**: 作为 Developer，我希望清晰理解 TASK 执行要求和完成标准...

**完整体验流程**:

```yaml
1. 接收 TASK (迭代第 2-3 天)
   触发条件: DEVPLAN Freeze 完成

   TASK 通知内容:
     - TASK 描述和验收标准
     - 优先级 (P0/P1/P2)
     - 依赖关系 (前置 TASK)
     - 预估工时
     - 关联 FEAT

   操作步骤:
     a) 阅读 TASK 描述
     b) 确认理解 (如有疑问立即提出)
     c) 确认开始时间

2. 开发实现 (迭代第 3 天 - 第 X 天)
   开发前:
     a) 阅读 FEAT 验收标准
     b) 阅读 TECH 设计文档 (如有)
     c) 准备开发环境

   开发中:
     a) 编写代码
     b) 编写单元测试
     c) 本地验证

   遇到阻塞:
     - 尝试自主解决 (< 30 分钟)
     - 未解决 → 上报 Tech Lead (#dev-blockers)
     - 记录 BLOCKER

3. 代码审查 (开发完成后)
   提交审查:
     a) 创建 PR/MR
     b) 填写审查清单
     c) 指派审查人 (Tech Lead 或同事)

   审查标准:
     - 代码符合规范
     - 测试覆盖充分
     - 无安全隐患
     - 性能合理

   审查通过:
     - 合并到主分支
     - 触发自动化流水线

4. 证据提交 (审查通过后)
   Evidence Pack 内容:
     - 代码位置 (已合并)
     - 测试结果 (覆盖率报告)
     - Smoke Test 结果
     - 审查记录

   提交位置:
     - spec/evidence/{TASK-ID}/evidence_pack.yaml

5. TASK 完成
   完成标准 (L3 DoD):
     - ✅ 代码审查通过
     - ✅ 单元测试覆盖率 >= 80%
     - ✅ Smoke Test 通过
     - ✅ Evidence Pack 完整

   状态更新:
     - TASK.status = "completed"
     - DEVPLAN 自动更新进度
```

### 13.4 QA Engineer 用户故事

**故事**: 作为 QA Engineer，我希望基于 TESTPLAN 有效执行测试并报告结果...

**完整体验流程**:

```yaml
1. 接收 TESTPLAN (迭代第 2-3 天)
   触发条件: TESTPLAN Freeze 完成

   TESTPLAN 内容:
     - 测试策略 (smoke/regression/automation)
     - Test Set 列表
     - 优先级 (P0/P1/P2)
     - 覆盖范围

   操作步骤:
     a) 阅读测试策略
     b) 确认 Test Set 覆盖所有 FEAT
     c) 准备测试环境

2. Test Set 生产 (迭代第 3-4 天)
   输入:
     - FEAT.AC (验收标准)
     - TECH specs (技术实现)
     - TASK (开发任务)

   操作步骤:
     a) 为每个 FEAT 设计 Test Cases
     b) 定义测试数据
     c) 编写测试脚本 (如自动化)
     d) 验证覆盖度 (所有 AC 都有测试)

   产出:
     - Test Set YAML (spec/test-sets/ts-{module}.yaml)

3. 等待 Dev 完成 (迭代第 4 天 - 第 X 天)
   QA 前置条件:
     - dev_l2_ready_rate >= 80%
     - smoke_gate_pass_rate == 100%
     - critical_path_complete == true

   等待期间活动:
     - 完善测试脚本
     - 准备测试数据
     - 验证测试环境

4. 执行测试 (Dev 完成后)
   测试执行:
     a) 部署被测版本
     b) 执行 Smoke Test
     c) 执行功能测试
     d) 执行回归测试 (如适用)
     e) 记录测试结果

   发现 Bug:
     a) 记录 Bug (spec/bugs/BUG-{date}-{seq}.yaml)
     b) 定义优先级 (P0/P1/P2/P3)
     c) 通知相关人员
     d) 创建修复 TASK

5. 测试结果汇总
   测试完成标准:
     - 所有 Test Cases 执行完毕
     - 通过的测试 >= 目标值
     - 无 P0/P1 Bug (或有 Conditional Go 批准)

   产出:
     - 测试报告 (自动生成)
     - TESTPLAN 状态更新
```

### 13.5 Product Owner 用户故事

**故事**: 作为 Product Owner，我希望参与变更决策并了解 RELEASE 进展...

**完整体验流程**:

```yaml
1. Scope 评审 (迭代第 1-2 天)
   参与内容:
     - 确认 FEAT 优先级
     - 评估容量与范围匹配度
     - 批准 Scope Freeze

   决策输入:
     - FEAT Bundle
     - 团队可用性
     - 历史 Velocity

2. 变更审批 (迭代进行中)
   轻量变更 (不改变 RELEASE 目标):
     - 接收变更请求
     - 评估影响 (< 4 小时)
     - 口头/书面批准
     - 记录变更原因

   重量变更 (改变 RELEASE 目标):
     - 接收变更影响评估报告
     - 参与 CCB 审批
     - 投票决策
     - 通知干系人

3. 进度同步 (每日/每周)
   同步渠道:
     - 每日站会 (可选参加)
     - 进度看板 (随时查看)
     - 周报 (自动发送)

   进度看板内容:
     - dev_completion_rate
     - qa_pass_rate
     - bug_summary
     - risk_list

4. Go/No-Go 决策 (迭代最后 1 天)
   决策输入:
     - 决策报告
     - Bug 清单
     - 风险清单

   决策责任:
     - 评估业务影响
     - 权衡发布风险
     - 投票决策

5. 发布后回顾 (迭代结束后)
   参与内容:
     - 用户反馈收集
     - 业务指标评估
     - 改进建议提出
```

### 13.6 关键门禁

```yaml
gates:
  - gate.dev.scope_freeze_gate:
      type: human_approval
      reviewers: [release_manager, product_owner, tech_lead]
      输入：FEAT Bundle, 团队可用性
      输出：RELEASE.scope_frozen = true

  - gate.dev.scope_validate_gate:
      type: auto_check
      checks:
        - "FEAT Bundle 非空"
        - "所有 FEAT 已冻结"
        - "FEAT 依赖清晰"
        - "FEAT 有验收标准"

  - gate.dev.plan_validate_gate:
      type: auto_check
      checks:
        - "DEVPLAN 覆盖所有 FEAT"
        - "TESTPLAN 覆盖所有 FEAT"
        - "TASK 依赖清晰"
        - "Test Set 有明确优先级"

  - gate.dev.go_nogo_gate:
      type: human_approval
      options: [Go, Conditional Go, No-Go]
      输入：
        - dev_complete_rate
        - qa_pass_rate
        - bug_summary
        - risk_list
      决策标准：见 7.2 Go/No-Go 决策标准
```
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
