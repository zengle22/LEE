---
id: EPIC-011
ssot_type: epic
title: QA部门SSOT对齐与工作流重构 - 建立三轴真源验证体系
status: frozen
version: v1
parent_id: null
derived_from_ids:
- SRC-007
source_refs:
- SRC-007#scope
owner: null
tags: []
properties: {}
frozen_at: '2026-03-12T16:09:06.194137'
---

# QA部门SSOT对齐与工作流重构 - 建立三轴真源验证体系

## 目标

重构QA部门的SSOT主链完整性，建立需求轴、交付轴、证据轴三轴真源模型，
使TESTPLAN/TASK/REPORT正式绑定RELEASE成为验证承诺，确保所有QA执行产出
具备端到端可追溯性，满足发布门禁与合规审计要求。


## 范围

- 明确8个核心QA对象（FEAT/TESTSET/TESTPLAN/TASK/REPORT/BUG/TSE/EVI）的边界与关系
- 建立TESTPLAN→RELEASE绑定语义，使其成为正式验证承诺
- 统一TASK创建与执行入口，要求所有QA执行通过TASK-TESTPLAN-*发起
- 建立BUG完整可追溯链路，强制source_report_id和found_in_release引用
- 设计5类标准化workflow template（测试集生产、发布测试计划、测试任务执行、缺陷分流与回归、出测评估与发布门禁）
- 定义TR-001至TR-008追踪规则，确保链路完整性可验证
- 提供一个完整项目级样本验证三轴模型可行性

## 非目标

- 不解决技术架构选型与具体实现方案（validator/CLI/CI细节）
- 不涉及研发排期与资源分配的项目管理范畴
- 不提供历史数据迁移工具的具体实现
- 不定义第三方测试工具集成方案
- 不扩展至性能测试与容量规划SSOT（可作为独立SRC）
- 不要求一次性完成自动化测试完全托管

## 成功标准

- TESTPLAN具备RELEASE绑定语义，可作为发布门禁正式输入
- TASK成为唯一规范的QA执行入口，非规范执行可被识别和阻断
- BUG100%具备source_report_id和found_in_release引用，可追溯链完整
- 5类workflow template覆盖QA部门标准作业程序
- 项目级样本验证通过，单FEAT trace链路端到端可验证
- 合规审计链路验证通过率100%，抽样BUG可反查完整链路
