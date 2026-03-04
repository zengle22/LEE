---
title: LEE Framework Documentation
author: LEE Team
date: 2026-02-19
version: 1.0
last_updated: 2026-02-19
---

# LEE Framework Documentation

欢迎来到 LEE 框架文档中心!本文档系统提供了框架的完整指南、架构说明、API参考和使用示例。

## 📚 快速开始

### 新手入门
- [快速开始指南](../QUICKSTART.md) - 5分钟快速了解 LEE 框架
- [入门指南](../GETTING_STARTED.md) - 详细的新用户入门教程
- [安装指南](guides/installation/Installation-Guide.md) - 完整的安装说明

### 核心概念
- [项目概述](../README.md) - LEE 框架的项目定位和目标
- [变更日志](../CHANGELOG.md) - 版本历史和重要变更

## 🏗️ 架构文档

### 核心架构
- [架构总览](architecture/architecture.md) - 系统架构概述
- [Orchestrator 架构](architecture/Orchestrator-Architecture.md) - 编排器详细架构
- [Orchestrator 完全指南](architecture/Orchestrator-Complete-Guide.md) - 编排器使用指南
- [Orchestrator 指南](architecture/Orchestrator-Guide.md) - 编排器快速参考

### 架构决策
- [ADR-002: 执行路径治理](architecture/ADR-002-EXECUTION-PATH-GOVERNANCE.md) - 执行路径治理架构决策
- [RFC-001: 仓库注册表](architecture/RFC-001-repository-registry.md) - 仓库注册表设计
- [资产层规范](architecture/Asset-Layer-Specification.md) - 资产层技术规范

### 迁移指南
- [架构迁移指南](architecture/ARCHITECTURE-MIGRATION-GUIDE.md) - 从旧版本迁移的指南
- [Spec-Global 迁移计划](architecture/implementation-plan-spec-global-migration.md) - 迁移到 Spec-Global 的实施计划

### 实现计划
- [L3 实现计划](architecture/LEE-L3-Implementation-Plan.md) - L3 层实现路线图
- [V2 增强设计](architecture/v2-enhancement-design.md) - V2 版本增强设计
- [改进项目计划](architecture/IMPROVEMENT_PROJECT_PLAN.md) - 框架改进计划

## 🚀 框架演进

LEE 框架的未来演进提案，作为后续宪法与实现规范的输入池。

- [演进方向索引](lee-evolution/README.md) - 演进提案总览
- [L1/L2/L3 分层宪法草案](lee-evolution/2026-02-11-l2-l3-layering-constitution-draft.md) - 责任闭环、授权拒绝、反模式清单
- [Executor 双引擎演进](lee-evolution/2026-02-13-executor-dual-engine-langgraph.md) - LangGraph 渐进式替换方案
- [LEE 2.0 风险控制模型](lee-evolution/2026-02-17-risk-control-model.md) - 风险指数、预算机制、三层干预策略

## 📖 用户指南

### 安装与设置
- [安装指南](guides/installation/Installation-Guide.md) - 完整的安装步骤
- [Conda 设置指南](guides/installation/Conda-Setup-Guide.md) - 使用 Conda 管理环境
- [Conda 环境验证](guides/installation/Conda-Environment-Verification.md) - 验证 Conda 环境
- [MetaGPT 安装验证](guides/installation/MetaGPT-Installation-Verification.md) - 验证 MetaGPT 集成
- [本地环境设置完成](guides/installation/LOCAL-ENVIRONMENT-SETUP-COMPLETE.md) - 环境设置检查清单
- [集成指南](guides/installation/Integration-Guide.md) - 与其他工具集成

### 用户指南
- [CLI 参考](guides/user/CLI.md) - 命令行工具完整参考
- [斜杠命令指南](guides/user/SLASH-COMMANDS-GUIDE.md) - Claude Code 斜杠命令使用
- [工作流使用指南](guides/user/WORKFLOW-USAGE-GUIDE.md) - 工作流系统使用指南
- [STG 工作流审查指南](guides/user/STG-WORKFLOW-REVIEW-GUIDE.md) - STG 工作流审查

### 技术指南
- [依赖管理](guides/technical/Dependency-Management.md) - 项目依赖管理
- [审计日志指南](guides/technical/AUDIT-LOGGING-GUIDE.md) - 审计日志系统
- [Claude 集成](guides/technical/CLAUDE-INTEGRATION.md) - Claude AI 集成
- [MetaGPT 集成](guides/technical/MetaGPT-Integration.md) - MetaGPT 框架集成
- [Orchestrator 引擎集成指南](guides/technical/Orchestrator-Engine-Integration-Guide.md) - 引擎集成

## ⚡ 功能特性

### Human Gates (人工门禁)
- [Human Gates 文档索引](features/human-gates/HUMAN-GATES-INDEX.md) - 人工门禁文档导航
- [规范说明](features/human-gates/HUMAN-GATE-SPEC.md) - 人工门禁技术规范
- [实现指南](features/human-gates/HUMAN-GATE-IMPLEMENTATION.md) - 实现细节
- [快速参考](features/human-gates/HUMAN-GATE-QUICK-REF.md) - 快速参考卡片
- [总结报告](features/human-gates/HUMAN-GATE-SUMMARY.md) - 功能总结
- [测试报告](features/human-gates/HUMAN-GATE-TEST-REPORT.md) - 测试结果

### PM Agent
- [PM Agent 文档索引](features/pm-agent/PM-AGENT-INDEX.md) - PM Agent 文档导航
- [协议规范](features/pm-agent/PM_AGENT_PROTOCOL.md) - PM Agent 协议规范
- [用户指南](features/pm-agent/PM-AGENT-USER-GUIDE.md) - PM Agent 使用指南
- [STG 测试报告](features/pm-agent/PM-AGENT-STG-TEST-REPORT.md) - STG 测试结果
- [QA 工作流总结](features/pm-agent/QA-WORKFLOW-SUMMARY.md) - QA 工作流总结

## 🔧 技术文档

### 技术规范
- [AI 宪法](technical/specifications/AI-CONSTITUTION.md) - AI 行为准则
- [Orchestrator PRD](technical/specifications/Orchestrator-PRD.md) - 产品需求文档
- [详细执行日志提案](technical/specifications/detailed-execution-log-proposal.md) - 执行日志设计

### 缺陷报告
- [技术债务](technical/bug-reports/technical-debt.md) - 技术债务追踪
- [文件内容传递修复](technical/bug-reports/FILE-CONTENT-PASSING-FIX.md) - Bug 修复记录
- [实现完成审查](technical/bug-reports/implementation-completion-review.md) - 实现审查报告
- [测试报告 P0-P1-P2](technical/bug-reports/test-report-p0-p1-p2.md) - 测试结果

### 技术分析
- [项目深度分析报告](technical/analysis/项目深度分析报告.md) - 深度技术分析
- [P3 优化计划](technical/analysis/p3-optimization-plan.md) - 性能优化计划

## 📂 归档文档

### 状态报告
- [项目完成状态报告](archive/status-reports/FINAL_STATUS_REPORT.md) - 最终项目状态
- [工作流修复总结](archive/status-reports/WORKFLOW_FIX_SUMMARY.md) - 工作流修复总结

### 版本历史
- [V2 版本总结](archive/version-history/V2_SUMMARY.md) - V2 版本总结
- [V3 版本总结](archive/version-history/V3_SUMMARY.md) - V3 版本总结

## 🛠️ 运维文档

- [工作空间清理使用指南](operations/WORKSPACE_CLEANUP_USAGE.md) - 工作空间维护指南

## 📋 其他资源

### 命令参考
- [Lee 布局命令](../.claude/commands/lee-layout.md) - `/lee-layout` 命令
- [Lee 格式化命令](../.claude/commands/lee-fmt.md) - `/lee-fmt` 命令
- [QA 测试集命令](../.claude/commands/lee-qa-test-set.md) - `/lee-qa-test-set` 命令
- [QA 测试运行命令](../.claude/commands/lee-qa-test-run.md) - `/lee-qa-test-run` 命令
- [Gate 审查命令](../.claude/commands/gate-review.md) - `/gate-review` 命令
- [PM 工作流命令](../.claude/commands/pm-workflow.md) - `/pm-workflow` 命令

### 示例和演示
- [示例目录](../examples/) - 完整的示例代码和演示

## 🔗 相关链接

- [Spec-Global 规范](../spec-global/README.md) - 全局规范模板
- [测试套件](../tests/README.md) - 测试文档
- [变更日志目录](../changelogs/README.md) - 详细变更日志

---

**文档版本**: 1.0
**最后更新**: 2026-02-19
**维护团队**: LEE Team

---

## 贡献指南

如果您想改进文档,请参考:
1. 遵循现有的文档结构和格式
2. 添加适当的元数据 (title, author, date, version)
3. 更新相关索引文件
4. 确保所有链接有效

## 获取帮助

如果您在使用 LEE 框架时遇到问题:
1. 查看相关的用户指南
2. 检查故障排除文档
3. 查看测试报告和已知问题
4. 提交 issue 或联系团队
