---
id: ADR-014
ssot_type: adr
title: 接入 Kimi 执行器原始需求说明
status: frozen
version: v1
parent_id: null
derived_from_ids:
- id: ADR-004
  version: v1
- id: ADR-012
  version: v1
source_refs: []
owner: product
tags:
- product
- executor
- kimi
- llm
- raw-input
properties:
  adr_kind: raw_requirement
  decision_scope: kimi_executor_integration
frozen_at: '2026-03-12T21:09:42.916071'
---

# 接入 Kimi 执行器原始需求说明

## 1. 背景

当前 LEE 已经具备多种执行路径：

- 通用 `llm` 执行器
- `qwen` 执行器别名
- `claude_code` 执行器
- `codex` 执行器

其中，编码类步骤当前主要围绕 `claude_code` 展开。现阶段系统缺少对 Kimi CLI 的明确接入能力，导致以下问题：

- 无法以显式、稳定、可配置的方式选择 Kimi CLI 作为通用执行器
- 用户无法通过统一配置把默认 coding executor 从 `claude_code` 替换为 Kimi
- 编码型工作流与步骤无法在不改业务模板的情况下切换到 Kimi
- 执行器能力矩阵与 CLI/配置能力不一致，用户心智不清晰

## 2. 目标

本需求希望在 LEE 中接入 Kimi CLI 作为通用执行器，使系统能够在编码类步骤中使用 Kimi，并可通过配置将默认的 `claude_code` 执行路径替换为 Kimi。

这里的重点不是新增一条新的业务工作流，而是在现有 canonical executor 架构上补足执行器能力与配置切换能力。

## 3. 预期用户故事

### 3.1 CLI 使用者

作为 LEE 使用者，我希望在运行需要 coding executor 的工作流时，可以通过统一命令或配置显式指定 Kimi，而不是依赖隐式配置。

示例预期：

- `lee run <workflow> --executor kimi`
- 在配置中将 `coding_executor` 从 `claude_code` 切换为 `kimi`

### 3.2 编码执行场景

作为需要执行代码实现、补丁生成或仓库内自动修改任务的使用者，我希望系统可以把 Kimi CLI 当作与 `claude_code` 同等级的通用执行器来调用。

### 3.3 系统维护者

作为系统维护者，我希望 Kimi 接入方式复用现有执行器架构，不新增平行链路，不破坏已有 `llm / qwen / claude_code / codex` 路由逻辑。

## 4. 范围

### 4.1 本次必须覆盖

- 在执行器体系中增加 `kimi` 的显式接入能力
- 允许 CLI 通过 `--executor kimi` 传递执行偏好
- 允许系统通过配置将默认 coding executor 从 `claude_code` 切换为 `kimi`
- 让运行时能够把 `kimi` 解析为实际可调用的 Kimi CLI 执行路径
- 保证现有 coding workflow / coding step 不需要改业务语义就可复用 Kimi

### 4.2 本次不要求覆盖

- 不要求新增独立的 `raw_to_kimi_src` 或其他平行 workflow
- 不要求修改 `raw_to_src`、`src_to_epic`、`epic_to_feat`、`feat_to_delivery_prep` 的业务语义
- 不要求引入新的 SSOT 对象类型
- 不要求重写现有 executor 架构
- 不要求完成 Kimi 与其他模型的质量对比评测体系

## 5. 问题陈述

当前系统在“模型/CLI 能力”和“执行器入口”之间存在一定认知割裂：

- 从架构角度看，Kimi 可能被实现为某种底层 provider 或 profile
- 从用户使用角度看，Kimi CLI 应该表现为一个可直接指定、可替换 `claude_code` 的执行器

如果系统不对这种认知差异做封装，用户就需要理解内部实现细节，才能正确切换执行器。这会降低 LEE 的可用性，也会让编码工作流的执行路径不稳定。

## 6. 关键约束

- 必须复用现有 canonical path，不创建并行 workflow
- 必须兼容现有 coding executor 路由逻辑
- 必须兼容当前 `qwen` 这类执行器别名或适配模式
- 必须支持通过配置替换默认 `claude_code`
- 不应要求业务 workflow 为了使用 Kimi 而新增分支模板
- 配置应通过环境变量和统一配置文件管理，避免硬编码敏感信息

## 7. 成功标准

满足以下条件可认为本需求闭环：

1. 用户可以通过显式命令选择 Kimi 作为通用执行器
2. 系统可以通过配置将默认 coding executor 从 `claude_code` 替换为 `kimi`
3. 现有 coding 类步骤在不改业务模板的前提下可复用 Kimi 执行
4. Kimi 接入方案不引入新的平行实现和额外工作流分叉
5. 执行器切换后，系统边界、治理约束和证据输出方式仍保持一致

## 8. 风险与关注点

### 8.1 CLI 接入风险

如果 Kimi CLI 的安装方式、调用参数、鉴权方式或输出格式假设不稳定，可能导致运行时失败。

### 8.2 用户心智风险

如果实现上只是底层接入 Kimi，但没有提供明确的执行器入口与配置替换能力，用户会误以为系统“不支持 Kimi 替换 Claude Code”。

### 8.3 架构漂移风险

如果为了接入 Kimi 而新建一套独立执行链路，会与现有 `qwen`、`llm`、`claude_code`、`codex` 的治理方式不一致，增加长期维护成本。

### 8.4 质量验证风险

即使 Kimi 成功接入，也不代表其编码效果一定优于 `claude_code`。当前阶段重点是“可接入、可切换、可执行”，不是“证明它在所有任务上最优”。

## 9. 建议的后续工作

当该原始需求被 `raw_to_src` 工作流收敛为正式 `SRC` 之后，下游可以继续决定：

- 是否将 Kimi 设为默认 coding executor
- 是否允许不同 workflow 按类型分别选择 `kimi`、`claude_code`、`codex`
- 是否补充 Kimi 与 `claude_code` 的编码质量基准测试

## 10. 一句话需求

在不新增平行工作流和执行链路的前提下，为 LEE 接入 Kimi CLI 作为通用执行器，并支持通过配置将默认 `claude_code` 替换为 `kimi`。
