---
title: 变更日志
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-03-08
---

# 变更日志

本文文件记录 LEE 框架所有重要变更。

## 版本历史

| 版本 | 日期 | 说明 |
|------|------|------|
| [v0.3.0](changelogs/v0.3.0.md) | 2026-03-08 | 🔧 统一项目初始化 (ADR-0020) |
| [v0.2.0](changelogs/v0.2.0.md) | 2026-02-26 | ✨ Workflow Instance |
| [v0.1.0](changelogs/v0.1.0.md) | 2026-01-22 | 🎉 初始版本 |

## 最新版本

### v0.3.0 - 2026-03-08

#### 新增特性

- **统一项目初始化 (ADR-0020)**
  - `lee init` 现在为所有目录生成 README 文件
  - 统一 `project_config.py` 和 CLI 的初始化逻辑
  - 新的 `initialize_project()` 统一入口函数
  - 目录结构定义统一到 `DEFAULT_DIRECTORY_SCHEMA` v2.0

- **CLI 新增选项**
  - `--no-readme`: 不生成 README 文件
  - `--no-templates`: 不复制模板文件

#### 废弃提醒

- `init_project_structure()` 已标记为废弃，将在 v3.0 移除
  - 请使用新的 `initialize_project()` 替代
  - 当前版本仍保持向后兼容，但会发出 DeprecationWarning

#### 文件变更

- `src/lee/orchestrator/core/project_config.py` (重大更新)
  - 扩展 `DirectoryConfig` 数据类（ADR-0020 新字段）
  - 新增 `initialize_project()` 统一初始化函数
  - 新增 Git 仓库发现、模板复制等辅助函数
  - 更新 `DEFAULT_DIRECTORY_SCHEMA` 到 v2.0
- `src/lee/cli/commands/init.py` (重构)
  - 简化为调用 `initialize_project()`
  - 新增 `--no-readme` 和 `--no-templates` 参数
- `docs/adr/ADR-0020-lee-init-unification.md` (新增)
  - 架构决策记录

#### 测试

- 新增 14 个测试用例（ADR-0020 相关）
  - `TestInitializeProject`: 测试新的初始化函数
  - `TestDirectoryConfigNewFields`: 测试新字段
  - `TestDeprecatedInitProjectStructure`: 测试废弃警告
  - `TestDirectoryStructureConfigV2`: 测试 v2.0 schema

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
