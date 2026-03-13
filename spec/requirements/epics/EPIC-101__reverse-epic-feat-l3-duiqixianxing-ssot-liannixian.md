---
id: EPIC-101
ssot_type: epic
title: reverse-epic-feat-l3 对齐现行 SSOT 链逆向升级
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties: {}
frozen_at: '2026-03-13T13:33:46.028790'
---

# reverse-epic-feat-l3 对齐现行 SSOT 链逆向升级

## 目标

实现逆向工作流对现行 SSOT 文档链的完整承接，确保规范一致性与路径对齐

## 范围

- 对齐 reverse workflow 输出路径至 canonical SSOT 目录
- 仅直接物化 SRC / EPIC / FEAT 为 formal object
- UI / TECH / TASK 等辅助对象仅生成 seed / view / handoff 索引
- 维持现有 workflow key 体系，不新增平行键

## 非目标

- 新增平行 workflow key
- UI / TECH / TASK / TESTSET / TC / REPORT / BUG / EVI 完整物化
- 偏离当前 canonical SSOT 目录结构
- 涉及手机号登录等业务功能层改造

## 成功标准

- 逆向工作流产出路径 100% 匹配 canonical SSOT 目录
- 正式对象（SRC/EPIC/FEAT）物化成功率 100%
- 无平行 workflow key 产生
- 辅助对象仅存在索引引用而无冗余物化文件
