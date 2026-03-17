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

## 二、三层架构设计

### 2.1 L1: 瀑布管控层 (对外承诺)

**定位**：面向干系人、客户、管理层的承诺层

```yaml
L1_Release_Delivery:
  特点：
    - 固定发布窗口 (Release Train)
    - 需求冻结点 (Scope Freeze)
    - 质量门禁 (Go/No-Go Gate)
    - 里程碑承诺

  关键管控点:
    - M0: Release Planning (发布计划)
    - M1: Scope Freeze (范围冻结)
    - M2: Plan Freeze (计划冻结)
    - M3: Code Freeze (代码冻结)
    - M4: Release Decision (发布决策)
    - M5: Release Close (发布关闭)

  产出物:
    - RELEASE SSOT (版本定义)
    - 发布计划 (含 Sprint 划分)
    - 质量报告 (DORA 指标)
    - 发布说明 (Release Notes)
```

**瀑布元素保留**：
- 需求冻结后不允许随意变更 (走变更控制流程)
- 里程碑日期固定
- 质量门禁严格执行
- 发布决策有据可查

---

### 2.2 L2: 敏捷迭代层 (对内灵活)

**定位**：面向开发团队的执行层

```yaml
L2_Sprint_Iteration:
  特点:
    - 固定周期 Sprint (2 周)
    - Sprint 内需求可协商
    - 每日站会同步
    - Sprint Review 演示
    - Sprint Retrospective 改进

  Sprint 结构:
    sprint_n:
      duration: 2 周
      commitment:
        - feat_subset: [FEAT-001, FEAT-002]  # 本 Sprint 承诺交付的 FEAT 子集
        - sprint_goal: "用户认证模块上线"
      ceremonies:
        - sprint_planning: "Sprint 第 1 天"
        - daily_standup: "每天 15 分钟"
        - sprint_review: "Sprint 最后 1 天"
        - retrospective: "Sprint 最后 1 天"
      deliverables:
        - working_software: "可工作的软件"
        - sprint_demo: "演示视频"
        - evidence_pack: "证据包"
```

**敏捷元素引入**：
- Sprint Planning：团队自己承诺本 Sprint 可完成的 FEAT 子集
- Daily Standup：快速同步进展和阻塞
- Sprint Review：演示可工作的软件，获取反馈
- Retrospective：持续改进流程

---

### 2.3 L3: 工程卓越层 (质量内建)

**定位**：面向工程师的具体实践层

```yaml
L3_Engineering_Excellence:
  敏捷工程实践:
    - TDD: 测试驱动开发
    - Code Review: 同伴代码评审
    - CI/CD: 持续集成/持续部署
    - 自动化测试：金字塔结构

  质量门禁:
    - 单元测试覆盖率 >= 80%
    - 代码审查通过率 = 100%
    - CI 构建通过率 = 100%
    - Smoke Test 通过率 = 100%

  证据包 (Evidence Pack):
    - 设计文档 (TECH spec)
    - 测试报告 (Unit/Integration test results)
    - 代码审查记录
    - 构建产物 (Artifact)
```

---

## 三、L1 与 L2 的衔接机制

### 3.1 RELEASE 与 Sprint 的映射

```yaml
RELEASE-001:
  release_window: 2026-03-01 ~ 2026-03-28 (4 周 = 2 个 Sprint)

  sprint_mapping:
    sprint_1:
      duration: 2026-03-01 ~ 2026-03-14
      feat_commitment:
        - FEAT-001: 用户登录
        - FEAT-002: 用户注册
        - FEAT-003: 密码重置
      status: completed

    sprint_2:
      duration: 2026-03-15 ~ 2026-03-28
      feat_commitment:
        - FEAT-004: 个人资料
        - FEAT-005: 头像上传
        - FEAT-006: 账号设置
      status: in_progress

  release_gate:
    code_freeze: 2026-03-26 (Sprint 2 倒数第 2 天)
    release_decision: 2026-03-28 (Sprint 2 最后 1 天)
```

### 3.2 变更控制机制

**Sprint 内变更**：
```yaml
变更场景：
  - 发现技术风险，无法按原计划完成
  - 产品需求理解有误，需要调整
  - 突发高优先级需求插入

变更流程:
  1. 团队评估影响 (4 小时内)
  2. Product Owner 批准 (24 小时内)
  3. 更新 Sprint Backlog
  4. 记录变更原因 (用于 Retrospective)

原则:
  - Sprint 内变更不影响 RELEASE 整体承诺
  - 通过调整后续 Sprint 范围来补偿
  - 重大变更 (影响 RELEASE 里程碑) 需走 CCB 流程
```

**RELEASE 级变更**：
```yaml
变更控制委员会 (CCB):
  成员:
    - release_manager (主席)
    - product_owner
    - tech_lead
    - 相关干系人

  变更门槛:
    - 影响 RELEASE 发布日期
    - 删减已承诺的 FEAT
    - 增加重大新 FEAT (>5 人天)

  决策机制:
    - 2/3 多数同意
    - 记录决策原因
    - 更新 RELEASE SSOT (新版本号)
```

---

### 3.3 质量管控机制

```yaml
质量分层:
  L1 质量门禁 (发布级):
    - 所有 FEAT 的 Dev + QA 完成率 = 100%
    - 所有 P0/P1 Bug 已修复
    - DORA 指标达标 (deployment_frequency, change_failure_rate, etc.)
    - Go/No-Go 决策通过

  L2 质量门禁 (Sprint 级):
    - 本 Sprint FEAT 子集完成率 = 100%
    - 本 Sprint 产生的 Bug 已关闭或降级
    - Sprint Demo 获得 PO 认可

  L3 质量门禁 (Feature 级):
    - 代码审查通过
    - 单元测试覆盖率 >= 80%
    - 集成测试通过
    - Smoke Test 通过

质量内建:
  - 每个 TASK 必须通过 L3 门禁才能标记为"完成"
  - 每个 FEAT 必须通过 L2 门禁才能进入 RELEASE 统计
  - RELEASE 必须通过 L1 门禁才能发布
```

---

## 四、沟通与可视机制

### 4.1 三层沟通计划

```yaml
沟通矩阵:
  L1_Stakeholder_Update:
    频率：每周
    受众：管理层、客户、业务干系人
    内容:
      - RELEASE 整体进度
      - 里程碑达成情况
      - 风险与问题
      - 需要决策的事项
    形式：状态报告 + 里程碑评审会

  L2_Sprint_Ceremonies:
    频率：每 Sprint
    受众：开发团队、Product Owner
    内容:
      - Sprint Planning (承诺)
      - Sprint Review (演示)
      - Retrospective (改进)
    形式：面对面会议 + Demo 演示

  L3_Team_Sync:
    频率：每日
    受众：开发团队
    内容:
      - 昨天做了什么
      - 今天计划做什么
      - 有什么阻塞
    形式：15 分钟站会
```

### 4.2 可视化看板

```yaml
RELEASE_Dashboard:
  进度视图:
    - RELEASE 里程碑时间轴
    - Sprint 燃尽图
    - FEAT 完成状态 (To Do / In Progress / Done)

  质量视图:
    - Bug 趋势图 (新增/关闭/存量)
    - 测试覆盖率趋势
    - DORA 指标仪表盘

  风险视图:
    - 风险登记册 (概率 x 影响)
    - 阻塞问题列表
    - 变更请求状态
```

---

## 五、度量指标体系

### 5.1 瀑布层指标 (L1)

```yaml
L1_Metrics:
  交付可预测性:
    - 计划偏差率：(实际完成日期 - 计划日期) / 计划日期
    - 范围偏差率：(实际 FEAT 数 - 计划 FEAT 数) / 计划 FEAT 数
    - 里程碑达成率：按时达成的里程碑数 / 总里程碑数

  质量指标:
    - 发布后缺陷密度：生产环境 Bug 数 / 千行代码
    - 逃逸缺陷率：生产环境 Bug 数 / 总 Bug 数
    - 客户满意度：NPS 评分
```

### 5.2 敏捷层指标 (L2)

```yaml
L2_Metrics:
  Sprint 健康度:
    - Sprint 目标达成率：承诺 FEAT 完成数 / 承诺 FEAT 总数
    - 速率 (Velocity): 每 Sprint 完成的 Story Points
    - 速率稳定性：速率的标准差

  流程效率:
    - 周期时间 (Cycle Time): TASK Start 到 Complete 的时间
    - 吞吐量 (Throughput): 每 Sprint 完成的 TASK 数
    - 累积流图 (CFD)
```

### 5.3 工程层指标 (L3)

```yaml
L3_Metrics:  # DORA Metrics
  部署频率: 每周/每日部署次数
  变更前置时间: Code Commit 到 Deploy 的时间
  变更失败率: 导致回滚/热修复的变更比例
  平均恢复时间: 故障发生到恢复的时间

  代码质量:
    - 单元测试覆盖率
    - 代码审查覆盖率
    - 技术债指数
```

---

## 六、实施路线图

### Phase 1: 基础框架 (第 1-2 周)

- [ ] 定义 RELEASE 与 Sprint 的映射关系
- [ ] 建立 Sprint 仪式模板
- [ ] 配置可视化看板
- [ ] 培训团队敏捷实践

### Phase 2: 试点运行 (第 3-6 周)

- [ ] 选择一个小型 RELEASE 试点
- [ ] 执行 2 个完整 Sprint
- [ ] 收集反馈并调整
- [ ] 建立度量基线

### Phase 3: 全面推广 (第 7 周起)

- [ ] 所有 RELEASE 采用混合模式
- [ ] 持续改进流程
- [ ] 优化度量指标
- [ ] 沉淀最佳实践

---

## 七、风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 团队抵触敏捷仪式 | 中 | 渐进式引入，解释价值，允许定制 |
| Sprint 内变更频繁 | 高 | 明确变更门槛，记录变更原因 |
| L1/L2 信息不同步 | 高 | 建立自动化报告机制 |
| 度量数据造假 | 高 | 数据自动采集，透明可视化 |
| 敏捷变成"小瀑布" | 中 | 定期 Retrospective，强调敏捷价值观 |

---

## 八、验收标准

### L1 验收 (瀑布层)

- [ ] RELEASE 发布日期可预测 (偏差 < 10%)
- [ ] 质量门禁有效拦截不合格发布
- [ ] 干系人对进度透明满意

### L2 验收 (敏捷层)

- [ ] Sprint 目标达成率 >= 80%
- [ ] 团队对流程满意度 >= 4/5
- [ ] Sprint Demo 获得 PO 认可

### L3 验收 (工程层)

- [ ] DORA 指标持续改进
- [ ] 代码审查覆盖率 = 100%
- [ ] 自动化测试覆盖率 >= 80%

---

## 九、与 SRC-046 的映射关系

```
SRC-046 交付轴           SRC-048 混合模式
────────────────────    ────────────────────
L1: Release Delivery  → L1: 瀑布管控层 (增强 Sprint 划分)
L2: DEVPLAN/TESTPLAN  → L2: 敏捷迭代层 (新增 Sprint 概念)
L3: Feature Dev/QA    → L3: 工程卓越层 (保持原有设计)

关键差异:
- L2 不再是单一的 DEVPLAN/TESTPLAN 执行
- L2 被重新组织为多个 Sprint 迭代
- 每个 Sprint 交付部分 FEAT 子集
- RELEASE 整体在所有 Sprint 完成后关闭
```
