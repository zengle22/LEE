---
id: UI-FEAT-082-002
ssot_type: ui
title: Formal Object 元数据自动继承机制 UI 原型
status: active
version: v1
parent_id: FEAT-082
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: ui_prototype
  identity_kind: ssot
---

contract_type: frozen-ui-prototype
contract_version: '1.0'
metadata:
  contract_id: FUIP-20260313-001
  is_frozen: true
  frozen_at: '2026-03-13'
  feat_ref: FEAT-082
  title: Formal Object 元数据自动继承机制 UI 原型
  designer: UI/UX Designer
  review_status: pending_human_approval
design_specs:
  interaction_principles:
  - name: 元数据可视化原则
    description: 自动继承的元数据必须对用户可见，不可完全隐藏
    rules:
    - 透明可见：所有自动继承的元数据在界面上可见
    - 区分呈现：自动填充与手动输入字段需视觉区分
    - 可追溯性：任何元数据都应能追溯到其来源
    - 可干预性：关键继承逻辑允许用户确认或调整
  - name: 状态一致性原则
    description: 四级状态定义确保用户清晰理解数据来源
    state_levels:
    - level: L1
      name: 系统预填充态
      visual: 浅蓝底色 + 锁形图标
      interaction: 不可直接编辑，需"解锁"操作
      scenarios:
      - 自动继承的 source_refs
      - 自动继承的 parent_id
    - level: L2
      name: 系统建议态
      visual: 虚线边框 + 提示文字
      interaction: 可接受/拒绝/修改
      scenarios:
      - 智能推断的 derived_from_ids
    - level: L3
      name: 用户确认态
      visual: 实线边框 + 勾选标记
      interaction: 正常编辑
      scenarios:
      - 用户确认后的元数据
    - level: L4
      name: 用户输入态
      visual: 标准输入样式
      interaction: 完全可编辑
      scenarios:
      - 用户手动输入的字段
  - name: 反馈即时性原则
    description: 不同操作类型的反馈延迟标准
    standards:
    - operation: 选择 Source 对象
      max_delay: 100ms
      feedback_form: 卡片高亮 + 继承预览
    - operation: 确认创建对象
      max_delay: 300ms
      feedback_form: 加载动画 + 进度提示
    - operation: 元数据注入完成
      max_delay: 即时
      feedback_form: Toast 提示 + 摘要展示
    - operation: 追溯链加载
      max_delay: 500ms
      feedback_form: 骨架屏 + 渐进式渲染
  - name: 导航一致性原则
    description: 对象间导航规则统一
    navigation_rules:
    - source: 追溯链中的任何对象
      action: 点击对象名称
      target: 该对象详情页
    - source: 追溯链中的任何对象
      action: 点击"向上"箭头
      target: 父级对象详情
    - source: 有子对象的对象
      action: 点击"向下"箭头
      target: 子对象列表
    - source: Source 对象
      action: 点击"来源"标签
      target: Source 详情
  core_paths:
  - name: 对象创建时的元数据自动继承主流程
    prototype_link: ./prototypes/main-flow.html
    description: '1. 启动 Workflow → 2. 选择 Source (SRC/ADR) → 3. 填写对象信息 (EPIC/FEAT)

      4. 确认创建 → 5. 系统注入元数据 (自动继承) → 6. 创建成功 (成功提示)

      7. 查看详情 (追溯链展示)

      '
    critical_states:
    - S1
    - S2
    - S3
    state_mapping:
      S1: 对象创建页 - 继承预览态
      S2: 对象创建页 - 层级继承态
      S3: 对象详情页 - 追溯链展开态
  - name: EPIC 创建时的 source_refs 绑定子流程
    prototype_link: ./prototypes/epic-source-binding.html
    description: '用户选择 SRC → 系统读取信息 → SRC 卡片高亮 → 触发创建 EPIC

      → 自动提取 source_refs → 继承信息预览区显示来源标识

      → 提交创建 → 元数据注入对象 → 成功提示包含来源追溯摘要

      '
    critical_states:
    - S1
    parent_flow: 对象创建时的元数据自动继承主流程
  - name: FEAT 创建时的层级关系维护子流程
    prototype_link: ./prototypes/feat-hierarchy.html
    description: '用户在 EPIC 下创建 FEAT → 读取 EPIC 信息 → parent_id = EPIC.id

      → 父级对象卡片显示为上下文 → 填写 FEAT 信息 → 继承 EPIC.source_refs

      → 继承链预览显示层级路径 → 提交创建 → 成功提示包含层级关系图示

      '
    critical_states:
    - S2
    parent_flow: 对象创建时的元数据自动继承主流程
  - name: 来源追溯信息查看子流程
    prototype_link: ./prototypes/provenance-view.html
    description: '用户进入对象详情页 → 加载对象元数据 → 检查 parent_id → 加载父级对象

      → 检查 derived_from → 构建追溯链 → 渲染追溯链视图 (层级树/时间线)

      '
    critical_states:
    - S3
    - S4
    - S5
    state_mapping:
      S3: 对象详情页 - 追溯链展开态
      S4: 追溯链 - 加载中态
      S5: 追溯链 - 空状态/异常态
  key_page_states:
  - state_id: S1
    name: 对象创建页 - 继承预览态
    trigger: 用户已选择 Source 对象，准备创建新对象
    visual_layout: '┌─────────────────────────────────────────────────────────────────┐

      │ 创建 EPIC                                                        │

      ├─────────────────────────────────────────────────────────────────┤

      │ 📎 继承来源 (自动填充)                                           │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │ 🔗 来源：SRC-001 市场需求分析报告                           │   │

      │ │    类型：Source Object        状态：Frozen                 │   │

      │ │    ├─ source_refs: []         (根级来源)                   │   │

      │ │    └─ 将继承至当前 EPIC                                     │   │

      │ └───────────────────────────────────────────────────────────┘   │

      │ 📝 基本信息                                                      │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │ 标题*          [                                   ]       │   │

      │ │ 描述           [                                   ]       │   │

      │ │ 负责人         [                                   ]       │   │

      │ └───────────────────────────────────────────────────────────┘   │

      │ 🔒 元数据继承预览 (只读)                                          │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │ source_refs    ["SRC-001"]              🔒 自动填充        │   │

      │ │ parent_id      null                     🔒 根级对象        │   │

      │ │ derived_from   []                       🔒 无上游依赖      │   │

      │ └───────────────────────────────────────────────────────────┘   │

      │                                    [取消]  [确认创建]            │

      └─────────────────────────────────────────────────────────────────┘

      '
    interactions:
    - 继承来源区域可折叠/展开
    - 元数据预览区为只读，悬停显示来源解释
    - 创建按钮启用条件：标题必填且不为空
    data_binding:
      source_refs: 自动从选择的 SRC 提取
      parent_id: null (EPIC 为根级对象)
      derived_from: 空数组
  - state_id: S2
    name: 对象创建页 - 层级继承态
    trigger: 用户在 EPIC 下创建 FEAT
    visual_layout: '┌─────────────────────────────────────────────────────────────────┐

      │ 在 EPIC-003 下创建 FEAT                                          │

      ├─────────────────────────────────────────────────────────────────┤

      │ ⬆️ 父级上下文 (自动关联)                                          │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │ 📁 父级：EPIC-003 元数据自动继承机制                         │   │

      │ │    状态：Active                                            │   │

      │ │    继承链：SRC-001 → EPIC-003 → [当前 FEAT]                  │   │

      │ └───────────────────────────────────────────────────────────┘   │

      │ 📝 基本信息                                                      │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │ 标题*          [                                   ]       │   │

      │ │ 描述           [                                   ]       │   │

      │ │ 优先级         [高 ▼]                                      │   │

      │ └───────────────────────────────────────────────────────────┘   │

      │ 🔒 元数据继承预览 (只读)                                          │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │ source_refs    ["SRC-001", "EPIC-003"]   🔒 合并继承       │   │

      │ │ parent_id      "EPIC-003"                🔒 自动填充       │   │

      │ │ derived_from   []                       🔒 待确认         │   │

      │ └───────────────────────────────────────────────────────────┘   │

      │ 💡 系统建议 (可选)                                                │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │ 建议的 derived_from: FEAT-001 (相似度 85%)                  │   │

      │ │ [接受建议] [忽略]                                           │   │

      │ └───────────────────────────────────────────────────────────┘   │

      │                                    [取消]  [确认创建]            │

      └─────────────────────────────────────────────────────────────────┘

      '
    interactions:
    - 父级上下文区域固定显示，不可折叠
    - 继承链可视化展示完整路径
    - 系统建议区为可选，接受后更新 derived_from
    data_binding:
      source_refs: 合并继承：SRC-001 + EPIC-003
      parent_id: EPIC-003
      derived_from: 可选，系统建议
  - state_id: S3
    name: 对象详情页 - 追溯链展开态
    trigger: 用户查看对象详情，展开追溯信息面板
    visual_layout: '┌─────────────────────────────────────────────────────────────────┐

      │ FEAT-082 Formal Object 元数据自动继承机制           [编辑] [更多] │

      ├─────────────────────────────────────────────────────────────────┤

      │ 📋 基本信息                                                      │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │ ID:        FEAT-082                                        │   │

      │ │ 标题：Formal Object 元数据自动继承机制                       │   │

      │ │ 状态：🟢 Active                                             │   │

      │ │ 负责人：-                                                  │   │

      │ └───────────────────────────────────────────────────────────┘   │

      │ 🔗 来源追溯 (可展开)                                              │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │    层级树视图                                               │   │

      │ │         ┌─────────┐                                        │   │

      │ │         │ SRC-001 │ ◀── 根来源                              │   │

      │ │         └────┬────┘                                        │   │

      │ │              │ source_ref                                  │   │

      │ │              ▼                                              │   │

      │ │         ┌─────────┐                                        │   │

      │ │         │EPIC-003 │ ◀── 父级 (parent_id)                     │   │

      │ │         └────┬────┘                                        │   │

      │ │              ▼                                              │   │

      │ │    ┌─────────┬─────────┐                                   │   │

      │ │    │FEAT-082 │ FEAT-083│ ◀── 同级对象                        │   │

      │ │    │【当前】  │         │                                   │   │

      │ │    └─────────┴─────────┘                                   │   │

      │ │    元数据详情：                                              │   │

      │ │    ┌─────────────┬────────────────────────────┐            │   │

      │ │    │ source_refs │ ["SRC-001", "EPIC-003"]    │            │   │

      │ │    │ parent_id   │ "EPIC-003"                 │            │   │

      │ │    │derived_from │ []                         │            │   │

      │ │    └─────────────┴────────────────────────────┘            │   │

      │ └───────────────────────────────────────────────────────────┘   │

      │ 📊 关联对象                                                     │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │ 上游：无                                                    │   │

      │ │ 下游：TASK-FEAT-082-001, TASK-FEAT-082-002                 │   │

      │ └───────────────────────────────────────────────────────────┘   │

      └─────────────────────────────────────────────────────────────────┘

      '
    interactions:
    - 追溯链支持树形/列表/时间线三种视图切换
    - 点击任意节点跳转至该对象详情
    - 元数据详情支持一键复制
    data_binding:
      source_refs: 完整显示绑定值
      parent_id: 可点击跳转父级
      derived_from: 显示派生链
  - state_id: S4
    name: 追溯链 - 加载中态
    trigger: 系统正在加载层级关系数据
    visual_layout: '┌─────────────────────────────────────────────────────────────────┐

      │ 🔗 来源追溯                                                      │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │    正在加载追溯链...                                        │   │

      │ │         ┌─────────┐                                        │   │

      │ │         │ ▓▓▓░░░░ │  SRC-001                               │   │

      │ │         └────┬────┘                                        │   │

      │ │              │                                              │   │

      │ │              ▼                                              │   │

      │ │         ┌─────────┐                                        │   │

      │ │         │ ▓▓▓▓░░░ │  EPIC-003  加载中...                    │   │

      │ │         └────┬────┘                                        │   │

      │ │              ▼                                              │   │

      │ │         ┌─────────┐                                        │   │

      │ │         │ ▓▓▓▓▓▓▓ │  FEAT-082  ✓                           │   │

      │ │         └─────────┘                                        │   │

      │ │    [████░░░░░░░░░░░░] 40%                                  │   │

      │ └───────────────────────────────────────────────────────────┘   │

      └─────────────────────────────────────────────────────────────────┘

      '
    interactions:
    - 渐进式加载，已加载节点可交互
    - 加载失败时显示重试按钮
    - 超时提示并提供"仅显示本地数据"选项
  - state_id: S5
    name: 追溯链 - 空状态/异常态
    trigger: 对象无来源追溯信息或加载失败
    visual_layout_empty: '┌─────────────────────────────────────────────────────────────────┐

      │ 🔗 来源追溯                                                      │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │                    ┌─────────┐                            │   │

      │ │                    │   🌱   │                             │   │

      │ │                    └─────────┘                            │   │

      │ │              这是一个根级对象                               │   │

      │ │         该对象没有父级或来源引用                             │   │

      │ │              [查看相关对象]  [绑定来源]                      │   │

      │ └───────────────────────────────────────────────────────────┘   │

      └─────────────────────────────────────────────────────────────────┘

      '
    visual_layout_error: '┌─────────────────────────────────────────────────────────────────┐

      │ 🔗 来源追溯                                                      │

      │ ┌───────────────────────────────────────────────────────────┐   │

      │ │                    ┌─────────┐                            │   │

      │ │                    │   ⚠️   │                             │   │

      │ │                    └─────────┘                            │   │

      │ │              无法加载完整追溯链                             │   │

      │ │         部分父级对象可能已被删除或不可访问                     │   │

      │ │              [重试加载]  [显示本地数据]                      │   │

      │ └───────────────────────────────────────────────────────────┘   │

      └─────────────────────────────────────────────────────────────────┘

      '
    interactions:
    - 空状态提供快捷操作绑定来源
    - 异常状态支持重试和降级查看
  components:
  - name: InheritanceChain
    description: 继承链可视化组件
    props:
    - name: nodes
      type: Array<{id, type, title, status, level}>
    - name: currentId
      type: string
    - name: viewMode
      type: '''tree'' | ''list'' | ''timeline'''
    - name: onNodeClick
      type: (id) => void
    - name: loading
      type: boolean
    - name: error
      type: Error | null
    states:
    - expanded
    - selectedView
    - highlightPath
  - name: MetadataPreview
    description: 元数据预览组件
    props:
    - name: sourceRefs
      type: string[]
    - name: parentId
      type: string | null
    - name: derivedFromIds
      type: string[]
    - name: mode
      type: '''preview'' | ''detail'' | ''edit'''
    - name: inherited
      type: boolean
    states:
    - expanded
    - showRaw
    - editing
  - name: SourceReferenceCard
    description: 继承来源卡片
    props:
    - name: objectId
      type: string
    - name: objectType
      type: '''SRC'' | ''ADR'' | ''EPIC'' | ''FEAT'''
    - name: title
      type: string
    - name: status
      type: '''frozen'' | ''active'' | ''archived'''
    - name: relationship
      type: '''source'' | ''parent'' | ''derived'''
    - name: clickable
      type: boolean
    styles:
    - relationship: source
      style: 蓝色边框 + 链接图标
    - relationship: parent
      style: 紫色边框 + 层级图标
    - relationship: derived
      style: 橙色边框 + 分支图标
  responsive_design:
    desktop:
      breakpoint: '>=1280px'
      layout: 三栏布局
      description: 左侧导航 | 中间内容 | 右侧追溯面板，完整追溯链可视化
    tablet:
      breakpoint: 768px-1279px
      layout: 两栏布局
      description: 内容区 + 可折叠追溯抽屉，简化追溯链支持横向滚动
    mobile:
      breakpoint: <768px
      layout: 单栏布局
      description: 追溯链作为独立页面，垂直堆叠的节点视图
  acceptance_criteria:
    functional:
    - 创建表单正确显示继承的元数据
    - 追溯链可视化完整展示层级关系
    - 状态区分符合 L1-L4 定义
    - 导航规则统一且可预测
    performance:
    - 页面首次渲染 < 1s
    - 追溯链加载 < 500ms (5 层深度)
    - 交互反馈延迟符合即时性原则
    accessibility:
    - 键盘导航支持
    - 屏幕阅读器兼容
    - 颜色对比度符合 WCAG 2.1 AA
  secondary_paths_description: '次要流程包括：

    1. 元数据编辑流程 - 用户手动修改继承的元数据，需解锁操作

    2. 批量创建流程 - 批量创建对象时的元数据继承处理

    3. 历史对象追溯 - 为已有对象补充追溯信息的手动流程

    4. 来源解绑流程 - 移除或修改 source_refs 的确认流程

    '
metadata_inheritance_rules_ui:
- target_type: EPIC
  when:
    workflow: product.src-to-epic
  ui_behavior:
    source_refs: 自动填充为选择的 SRC，显示为 L1 状态
    parent_id: 显示为 null，标注"根级对象"
    derived_from: 隐藏或显示为"无"
- target_type: FEAT
  when:
    workflow: product.epic-to-feat
  ui_behavior:
    source_refs: 合并父级 EPIC 的 source_refs，显示为 L1 状态
    parent_id: 自动填充为 EPIC.id，显示为 L1 状态
    derived_from: 显示为 L2 建议态，可接受/拒绝
- target_type: TECH
  when:
    workflow: dev.feature_delivery_l2
    phase: tech_design
  ui_behavior:
    source_refs: 解析关联 FEAT 的 source_refs
    parent_id: 自动填充为 feat_ref
    derived_from: 继承 FEAT.derived_from_ids
freeze_statement:
  scope: FEAT-082 UI/UX 设计规范
  version: 1.0.0
  frozen_at: '2026-03-13'
  frozen_by: UI/UX Designer
  unfreeze_conditions:
  - 需求范围重大调整
  - 交互原则需要重构
  - 关键页面状态定义错误
  approved_by: []
