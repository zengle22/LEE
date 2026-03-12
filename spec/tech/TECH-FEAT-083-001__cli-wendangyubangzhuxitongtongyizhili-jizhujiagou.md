---
id: TECH-FEAT-083-001
ssot_type: tech
title: CLI 文档与帮助系统统一治理 - 技术架构
status: active
version: v1
parent_id: FEAT-083
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
---

contract_type: frozen-technical-architecture
contract_version: v1
metadata:
  contract_id: FTA-20260312-083
  status: FROZEN
  is_frozen: true
  title: CLI 文档与帮助系统统一治理 - 技术架构
  feat_ref: FEAT-083
  frozen_at: '2026-03-12T00:00:00Z'
architecture_decisions:
  tech_stack:
  - layer: CLI Framework
    technology: Click (Python)
    reasoning: 现有 CLI 基于 Click 构建，具备良好的命令分组和 help 生成能力，支持通过 group 和 command 装饰器实现清晰的分层结构
  - layer: Documentation
    technology: Markdown + YAML Front Matter
    reasoning: 现有文档站点使用 Markdown 格式，配合 YAML front matter 实现元数据管理，与 SSOT 体系保持一致
  - layer: Help Text Generation
    technology: Click Native Help + Custom Formatter
    reasoning: 利用 Click 内置的 help 生成能力，通过自定义 Group 类实现命令分组展示，无需引入额外依赖
  - layer: Error Handling
    technology: Click.ClickException + Custom Error Hints
    reasoning: 复用现有错误提示框架 (src/lee/orchestrator/execution/error_hints.py)，在错误消息中注入
      workflow-first 引导
  core_components:
  - name: CLICommandRegistry
    responsibilities: 管理命令注册和分组，实现 Workflow Commands 和 Internal/Maintenance Commands
      的分组展示
    dependencies:
    - click.Group
    - lee.cli.commands.*
  - name: HelpFormatter
    responsibilities: 自定义 help 输出格式，确保命令分组清晰呈现，优先展示 Workflow Commands
    dependencies:
    - click.formatting.HelpFormatter
  - name: WorkflowFirstGuide
    responsibilities: 生成 workflow-first 引导文案，用于错误提示、help 注释和文档引用
    dependencies:
    - lee.orchestrator.execution.error_hints
  - name: DocumentationUpdater
    responsibilities: 更新文档站点的 Getting Started 章节，确保内容与新 CLI 分组一致
    dependencies:
    - docs/*.md
  - name: DemoExampleRefresher
    responsibilities: 更新 demo 示例代码，使用 lee adr/epic/feat new 等 workflow-first 命令
    dependencies:
    - lee.cli.commands.demo
risk_management:
  high_risk_points:
  - description: CLI 命令分组变更可能影响现有用户的使用习惯，导致混淆
    mitigation_plan: '1. 保持原有命令不变，仅调整 help 展示顺序和分组

      2. 在 help 底部添加迁移提示，说明分组逻辑

      3. 保留所有现有命令的别名和快捷方式'
    degradation_strategy: 如果用户反馈负面，可添加 --legacy-help 选项恢复原有展示方式
  - description: 文档站点 Getting Started 更新需要与代码变更同步
    mitigation_plan: '1. 将文档更新纳入同一 FEAT 实施

      2. 在代码 PR 中必须包含文档更新

      3. 使用预提交钩子检查文档与代码一致性'
    degradation_strategy: 如果文档更新滞后，可临时保留旧版文档并添加更新提示横幅
  - description: Demo 示例变更可能影响自动化测试和 CI/CD 流程
    mitigation_plan: '1. 更新 demo 代码后，全面运行相关测试套件

      2. 在 CI 中增加 demo 命令执行验证

      3. 保留旧 demo 脚本作为 regression 测试'
    degradation_strategy: 如果 demo 新命令有缺陷，可回退到旧 demo 实现并修复
  - description: 测试用例命名规范更新可能影响历史测试数据追溯
    mitigation_plan: '1. 仅更新命名规范文档，不强制重命名历史测试

      2. 新测试遵循新规范，旧测试保持兼容

      3. 提供命名规范对照表便于追溯'
    degradation_strategy: 如果新规范不适用，可维护双轨制命名，逐步迁移
implementation_strategy:
  approach: 渐进式更新
  phases:
  - phase: 1
    name: CLI Help 分组实现
    deliverables:
    - 修改 main.py 实现命令分组
    - 定义 Workflow Commands 组
    - 定义 Internal/Maintenance Commands 组
  - phase: 2
    name: 错误提示更新
    deliverables:
    - 更新 error_hints.py 添加 workflow-first 引导
    - 修改 ssot.py 命令的提示文案
  - phase: 3
    name: 文档更新
    deliverables:
    - 更新 Getting Started 章节
    - 更新 CLI Reference
  - phase: 4
    name: Demo 和测试更新
    deliverables:
    - 更新 demo.py 示例
    - 更新测试命名规范文档
dependencies:
  core_deps:
  - click >= 8.0
  - PyYAML >= 6.0
  internal_deps:
  - lee.cli.main
  - lee.cli.commands.ssot
  - lee.cli.commands.demo
  - lee.orchestrator.execution.error_hints
  external_deps: []
constraints:
  backward_compatibility: 必须保持所有现有 CLI 命令可用，仅调整 help 展示方式
  adr_compliance: 遵循 ADR-006 CLI 命令分层与 SSOT 物化边界的决策
  non_goals: 不修改底层 SSOT 创建逻辑，不新建 workflow 命令，仅更新文档和 help 展示
