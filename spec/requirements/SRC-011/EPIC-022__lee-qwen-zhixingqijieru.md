---
id: EPIC-022
ssot_type: epic
title: LEE Qwen 执行器接入
status: frozen
version: v1
parent_id: null
derived_from_ids: []
source_refs:
- SRC-011
owner: null
tags:
- product
- qwen
properties:
  problem_ref: PD-SRC-011
  workflow_id: wf_task_4a43a969
---

# LEE Qwen 执行器接入

## 目标

扩展 LEE 工作流执行框架的执行器能力，引入 `qwen cli` 作为可选对话执行后端，使其能够与 `claude_code`、`codex`、`kimi` 并存，并通过配置在同一套 workflow / runner / executor factory 体系中切换。

## 范围

- `qwen cli` 对话执行后端设计与实现
- 执行器工厂对 `qwen_chat` 的注册与实例化支持
- Runner 对 `qwen cli` 的对话执行调度、结果归一化与日志追溯支持
- workflow instance / CLI / 配置文件的执行器选择能力
- 多执行器并存场景下的上下文传递与隔离
- `qwen cli` 无头模式的自动化调用适配
- 中文任务、文档生成与结构化评审等通用场景下的可用性验证

## 非目标

- 不替换或废弃 `claude_code`、`codex` 等现有执行器
- 不把 `qwen cli` 当成文件编辑型 coding executor 接入
- 不新增平行 workflow 或平行执行链
- 不在本阶段覆盖生产发布、灰度、监控或运维方案
- 不在本阶段展开 `src_to_epic` 之后全部业务功能建设

## 成功标准

- 用户可通过 CLI 显式指定 `--executor=qwen_chat` 启动工作流
- 用户可在配置文件中设置 `executor: qwen_chat` 作为默认对话执行后端
- workflow instance 能携带执行器类型并正确传递给 Runner
- `qwen cli` 与 `claude_code`、`codex`、`kimi` 可在同一部署内并存
- 执行器切换仅需修改配置，不需要调整 workflow 结构
- 所有执行结果继续保留统一的来源追溯标识
- code step 继续由 `claude_code`、`codex`、`kimi` 承接，不因 `qwen_chat` 被误路由

## 需求拆解

### 执行器配置层扩展

- 配置 schema 支持 `executor_type = "qwen_chat"`，并兼容历史别名 `qwen`
- CLI 参数支持 `--executor=qwen_chat`
- 配置文件支持 `executor: qwen_chat`

### Qwen 对话执行后端工厂实现

- 工厂可基于配置创建 `qwen cli` 对话执行实例
- `qwen cli` 与现有执行器共享统一接口
- 实例化失败时返回可定位的错误信息

### Runner 层对话执行适配

- Runner 能接收 `qwen cli` 对话执行实例并执行任务
- 执行结果格式与其他执行器保持一致
- 保留完整执行日志与来源追溯信息
- `qwen cli` 的无头执行方式被适配为统一 Runner 输入输出，但工具调用、文件修改和命令执行仍由 LEE runtime 负责

### Workflow 多执行器并存

- workflow 实例可携带执行器类型上下文
- 执行器切换不破坏 workflow 状态连续性
- 多执行器实例可在同一 workflow 中隔离运行

### 通用场景可用性验证

- `qwen cli` 可处理中文原始需求、结构化文档生成与评审类任务
- 归一化输出符合既有 SSOT / review / task contract 规范
- 质量不低于现有主流对话后端在同类输入上的可用水平

## 约束与风险

- 必须复用现有执行器工厂、Runner 与 workflow wiring
- 必须保留来源追溯性
- `qwen cli` 接口若与现有抽象不兼容，需要在工厂或执行器层引入适配器
- `qwen cli` 当前无头模式基于 `-p/--prompt` 与 `--output-format json|stream-json`，不能假定与 `claude --print` 参数完全同构
- 若中文处理效果不稳定，需要保留可回退到其他真正执行器的配置能力

## 追溯

- Source: `SRC-011`
- Problem Definition: `PD-SRC-011`
- Workflow: `wf_task_4a43a969`
