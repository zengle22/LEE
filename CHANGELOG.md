---
title: 变更日志
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# 变更日志

本文文件记录 LEE 框架所有重要变更。

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| [v0.2.0](changelogs/v0.2.0.md) | 2026-02-26 | ✨ Workflow Instance |
| [v0.1.0](changelogs/v0.1.0.md) | 2026-01-22 | 🎉 初始版本 |

## 最新版本

### v0.2.0 - 2026-02-26

#### 新增特性

- **Workflow Instance** - 统一的 Plan → Instance → Execute 流程
  - Plan Agent: LLM 分析模板，生成执行计划
  - Instance Generator: Instance 文件生成和版本管理
  - Review Gate: simple/suggest/force 三种审批模式
  - Orchestrator 支持从 Instance 文件加载执行

- **CLI 新增选项**
  - `--plan-only`: 只生成 Plan，不执行
  - `--skip-plan`: 跳过 Plan，直接执行
  - `--plan-mode`: Plan 模式 (simple/suggest/force)
  - `--instance`: 从指定 Instance 运行

#### 文件变更

- `src/lee/orchestrator/core/instance_generator.py` (新增)
- `src/lee/orchestrator/execution/plan_agent.py` (新增)
- `src/lee/orchestrator/execution/workflow_runner.py` (新增)
- `src/lee/orchestrator/execution/instance_loader.py` (新增)
- `src/lee/orchestrator/execution/review_gate.py` (新增)
- `src/lee/cli/commands/run.py` (更新)

#### 测试

- 新增 30 个测试用例

---

### v0.1.0 - 2026-01-22

这是 LEE 框架的第一个正式版本。

#### 主要特性

- **核心代码包 - flowcore**
  - orchestrator/：工作流编排器
  - engines/：执行引擎系统
  - utils/：工具模块
  - cli/：命令行工具

- **Spec 全局规范**
  - core/：平台级基础规范
  - departments/：按部门组织（pm/dev/qa/ops）
  - cross/：跨部门流程和接口

- **文档体系**
  - 框架级文档（docs/）
  - 模块级文档（flowcore/*/README.md）
  - 变更日志（changelogs/）

#### 详细变更

查看 [changelogs/v0.1.0.md](changelogs/v0.1.0.md) 了解完整变更记录。

## 即将发布

查看 [changelogs/unreleased.md](changelogs/unreleased.md) 了解当前开发中的变更。

## 相关链接

- [变更日志总览](changelogs/README.md)
- [迁移指南](GETTING_STARTED.md)
- [框架总览](docs/LEE-Overview.md)
