---
id: EPIC-125
ssot_type: epic
title: SSOT 文档链逆向承接与物化规则升级
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties: {}
frozen_at: '2026-03-13T20:43:28.831468'
---

# SSOT 文档链逆向承接与物化规则升级

## 目标

构建逆向工作流对现行 SSOT 文档链的完整承接能力，确保 SRC/EPIC/FEAT formal object 准确物化，其余对象按 seed/view 规则生成，实现治理合规。

## 范围

- 逆向工作流与 SSOT 目录路径对齐逻辑实现
- SRC/EPIC/FEAT 正式对象物化规则定义与开发
- UI/TECH/TASK 等非正式对象 seed/view/handoff 生成机制
- 现有 reverse workflow 关键路径兼容性改造
- 治理审查员对 SSOT 链完整性的校验工具集成

## 非目标

- 新增平行 workflow key 或改变现有 workflow 拓扑
- 修改 canonical SSOT 目录结构规范
- 业务功能逻辑变更（如用户登录、权限业务等）
- 非 SSOT 链相关的独立工具开发

## 成功标准

- 逆向生成物与 SSOT 目录路径对齐率 100%
- SRC/EPIC/FEAT 物化对象治理审查通过率 >= 95%
- 非正式对象 seed/view 生成自动化覆盖率 100%
- 逆向工作流执行异常率降低至 1% 以下
