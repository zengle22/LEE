---
id: TECH-FEAT-080-001
ssot_type: tech
title: FEAT-080 CLI命令层级重构技术架构
status: frozen
version: v1
parent_id: FEAT-080
derived_from_ids:
- ADR-006
source_refs:
- FEAT-080#scope
- FEAT-080#acceptance
owner: dev
tags:
- tech
- cli
- governance
- workflow-first
properties:
  contract_key: tech_spec
  identity_kind: ssot
---

# FEAT-080 CLI命令层级重构技术架构

contract_type: frozen-technical-architecture
contract_version: '1.0'
metadata:
  contract_id: FTA-20260312-080
  title: FEAT-080 CLI命令层级重构技术架构
  description: ssot create命令降级为internal/admin命令的技术实现方案
  status: FROZEN
  is_frozen: true
  frozen_at: '2026-03-12T00:00:00Z'
workflow_instance_id: wf-tech-feat-080-001__feat-080-climinglingcengjizhonggoujizhujiagou-20260316
  feat_ref: FEAT-080
  ui_ref: UI-FEAT-080-v1
  designer: Architecture Designer
  reviewer: 待人类评审
architecture_decisions:
  tech_stack:
  - layer: CLI框架
    technology: Click (Python)
    reasoning: 项目现有CLI基于Click构建，保持一致性；支持命令分组、权限flag、帮助文本定制等需求；成熟的Python CLI生态
    version_constraint: '>=8.0'
  - layer: 命令权限控制
    technology: 装饰器模式 + Flag检查
    reasoning: 通过Click的callback机制和is_eager flag实现前置权限校验；非侵入式改造现有命令
    version_constraint: N/A
  - layer: 帮助文本管理
    technology: 模板字符串 + 格式化函数
    reasoning: 支持中英文混合帮助文本；易于后期国际化扩展；结构化输出便于测试验证
    version_constraint: N/A
  - layer: 配置管理
    technology: YAML + Python Dataclass
    reasoning: 与项目现有配置体系一致；支持命令可见性、权限级别的外部化配置
    version_constraint: N/A
  core_components:
  - name: InternalCommandGuard
    responsibilities: 内部命令权限守卫；检查--internal/--admin flag；阻止未授权执行；返回友好引导信息
    dependencies:
    - Click Context
    - CommandConfig
    interface: decorator/callback mechanism
  - name: CommandVisibilityController
    responsibilities: 控制命令在帮助文本中的可见性；管理主命令列表vs内部命令分组；支持分层帮助展示
    dependencies:
    - Click Group
    - CommandMetadata
    interface: click.Group subclass
  - name: HelpTextRenderer
    responsibilities: 渲染分层帮助文本；标记Internal/Deprecated命令；生成引导提示信息；支持状态S-001至S-005的输出格式
    dependencies:
    - CommandVisibilityController
    - MessageTemplates
    interface: format_help() / get_usage()
  - name: MessageTemplates
    responsibilities: 定义所有用户-facing的文案模板；支持中英文；包含S-002阻止提示、S-004帮助警告等
    dependencies: []
    interface: get_template(template_id, lang='zh')
  - name: ssot create (modified)
    responsibilities: 保留原有SSOT创建能力；添加权限校验回调；更新帮助文本为Internal标记
    dependencies:
    - InternalCommandGuard
    - ArtifactManager
    - SSOTType
    interface: click.Command with callbacks
dependency_analysis:
  core_dependencies:
  - name: click
    type: runtime
    version: '>=8.0'
    purpose: CLI框架基础
    risk_level: low
  - name: lee.orchestrator.execution.artifacts
    type: internal
    version: current
    purpose: SSOT对象物化管理
    risk_level: low
  - name: lee.cli.main
    type: internal
    version: current
    purpose: CLI主入口
    risk_level: medium
  optional_dependencies:
  - name: rich
    type: runtime
    version: '>=13.0'
    purpose: 终端富文本渲染（可选增强）
    risk_level: low
    fallback: 使用标准Click输出
implementation_strategy:
  approach: 装饰器增强
  description: 通过Click的callback机制在不破坏原有create_ssot_object函数的情况下增加权限校验
  modification_points:
  - file: src/lee/cli/commands/ssot.py
    change: 为create_ssot_object添加callback参数检查flags
    impact: 中 - 修改核心命令
  - file: src/lee/cli/main.py
    change: 可能添加命令分组配置
    impact: 低 - 扩展配置
  - file: src/lee/cli/commands/workflow.py (如果存在)
    change: 确保workflow命令高亮显示
    impact: 低 - 已有workflow命令
risk_management:
  high_risk_points:
  - risk_id: R-001
    description: 向后兼容性风险：现有脚本或用户依赖lee ssot create行为改变可能导致破坏
    probability: 高
    impact: 中
    mitigation_plan: 1) 保留--internal/--admin flag作为显式绕过方式；2) 在阻止时提供清晰的替代方案；3) 提供迁移文档；4)
      考虑过渡期警告而非完全阻止
    degradation_strategy: 如严重影响现有工作流，可临时添加--force flag作为紧急绕过，但记录日志
  - risk_id: R-002
    description: 权限校验逻辑复杂度：flag检查可能与现有参数解析产生冲突
    probability: 中
    impact: 低
    mitigation_plan: 1) 使用Click的is_eager flag确保权限检查优先；2) 编写充分的单元测试覆盖各种参数组合；3) 使用callback机制隔离权限逻辑
    degradation_strategy: 如参数解析冲突，可将权限检查移到命令体内部，减少优雅但增加稳定性
  - risk_id: R-003
    description: 帮助文本分层展示：Click默认不支持复杂帮助分组逻辑
    probability: 中
    impact: 低
    mitigation_plan: 1) 继承click.Group自定义format_help方法；2) 通过配置驱动帮助分组；3) 优先级：核心功能正确
      > 帮助文本美观
    degradation_strategy: 如自定义帮助复杂度过高，可先采用简单标记方式（[Internal]）而非完全隐藏
  technical_uncertainties:
  - uncertainty_id: U-001
    description: Click callback与现有create_ssot_object的集成方式
    current_assumption: 通过click.callback装饰器在命令执行前检查flags
    backup_plan: 如callback机制不兼容，直接在命令函数开头添加权限检查逻辑
    validation_method: 实现原型验证callback执行顺序
  - uncertainty_id: U-002
    description: 子命令help显示控制：ssot子命令帮助中create的标记方式
    current_assumption: 通过自定义Group.format_commands方法控制输出
    backup_plan: 如自定义Group复杂，直接在命令help文本中标记⚠ Internal
    validation_method: 验证ssot --help输出格式
acceptance_mapping:
  ac_to_tech:
  - ac_id: AC-001-001
    tech_component: CommandVisibilityController
    verification: lee --help输出不包含ssot create在MAIN COMMANDS中
  - ac_id: AC-001-002
    tech_component: InternalCommandGuard
    verification: 无flag执行返回exit_code=1和引导信息
  - ac_id: AC-001-003
    tech_component: InternalCommandGuard + ssot create
    verification: --internal flag允许正常执行，exit_code=0
testing_strategy:
  unit_tests:
  - InternalCommandGuard flag检测逻辑
  - MessageTemplates 模板渲染
  - HelpTextRenderer 输出格式
  integration_tests:
  - lee ssot create (无flag) -> 阻止 + 引导信息
  - lee ssot create --internal -> 正常执行
  - lee ssot create --admin -> 正常执行
  - lee --help -> ssot create不在主列表
  - lee ssot --help -> create标记为Internal
ssot_output_contract:
  contract_version: '1.0'
  run_id: tech-arch-fe-080
  outputs:
  - key: tech_architecture
    identity_kind: ssot
    ssot_type: tech
    title: FEAT-080 Frozen Technical Architecture
    parent: FEAT-080
    implements:
    - FEAT-080
