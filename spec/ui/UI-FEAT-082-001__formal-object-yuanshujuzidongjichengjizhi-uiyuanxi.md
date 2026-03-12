---
id: UI-FEAT-082-001
ssot_type: ui
title: Formal Object 元数据自动继承机制 UI原型
status: active
version: v1
parent_id: FEAT-082
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: ui
  identity_kind: ssot
---

design_specs:
  core_paths:
  - 对象创建时的元数据自动继承主流程
  - EPIC创建时的source_refs绑定子流程
  - FEAT创建时的层级关系维护子流程
  - 来源追溯信息查看子流程
  interaction_principles:
  - 元数据可视化原则：透明可见、区分呈现、可追溯性、可干预性
  - 状态一致性原则：L1系统预填充态、L2系统建议态、L3用户确认态、L4用户输入态
  - 反馈即时性原则：操作反馈延迟标准
  - 导航一致性原则：对象间导航规则
  key_page_states:
  - 'S1: 对象创建页 - 继承预览态'
  - 'S2: 对象创建页 - 层级继承态'
  - 'S3: 对象详情页 - 追溯链展开态'
  - 'S4: 追溯链 - 加载中态'
  - 'S5: 追溯链 - 空状态/异常态'
  components:
  - InheritanceChain 继承链可视化组件
  - MetadataPreview 元数据预览组件
  - SourceReferenceCard 继承来源卡片
metadata:
  is_frozen: true
  frozen_at: '2026-03-12'
  contract_id: FUIP-082-001
  feat_ref: FEAT-082
