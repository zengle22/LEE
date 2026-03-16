---
id: EPIC-008
ssot_type: epic
title: Workflow 分层解耦 - 建立 raw-to-src 独立流水线层级
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties: {}
frozen_at: '2026-03-12T13:45:47.774037'
---

# Workflow 分层解耦 - 建立 raw-to-src 独立流水线层级

## 目标

重构产品流水线 workflow 架构，建立清晰的 raw-to-src 与 src-to-epic 分层边界，
实现原始需求归一化与 EPIC 生成功能的完全解耦，提升系统的可维护性、可测试性和可观测性。


## 范围

- 设计并实现 raw-to-src workflow 作为独立入口，专责原始需求到 SRC 的归一化
- 重构 src-to-epic workflow，移除 raw input 处理能力，仅处理已标准化的 SRC
- 建立 SRC 标准输出格式与注册机制，支持独立 review 和版本控制
- 设计分层接口契约，确保 raw-to-src → src-to-epic 链路的纯净数据传递
- 更新 workflow 注册表，按清晰边界重新组织 raw-to-src 和 src-to-epic 条目
- 提供分层架构的部署配置，支持独立部署和回滚

## 非目标

- 不改变 EPIC -> FEAT -> TASK 的下游流程
- 不引入新的 workflow 编排引擎
- 不修改现有数据存储 schema
- 不扩展至产品流水线之外的 workflow
- 不解决非 workflow-engineering 领域的架构问题

## 成功标准

- raw-to-src 和 src-to-epic 可独立运行单元测试，无需依赖完整流水线
- SRC 产物可独立存储、review 和 replay，不携带 EPIC 语义
- workflow 注册表按分层边界清晰组织，认知负担降低 50% 以上
- 故障定位时间缩短，可按分层边界在 5 分钟内定位问题源
- 向后兼容 100%，现有 EPIC/FEAT 生成逻辑不受影响
