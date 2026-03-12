---
id: TECH-FEAT-169-001
ssot_type: tech
title: tech_design
status: active
version: v1
parent_id: FEAT-169
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
  contract_id: FTA-FEAT-169-20260312
  status: FROZEN
  is_frozen: true
  source_features:
  - FEAT-169
  parent_epic: EPIC-022
  governing_adrs: []
  created_at: '2026-03-12'
  description: 系统配置层支持识别并透传 qwen 执行器类型标识 - 技术架构冻结文档
architecture_decisions:
  tech_stack:
  - layer: configuration-resolution
    technology: Python dataclasses + YAML/JSON parsing
    reasoning: 复用现有 config_loader.py 架构，扩展 executor 类型识别与验证能力，保持与现有配置系统的兼容性
  - layer: validation-layer
    technology: Schema validation + Enum constraint
    reasoning: 使用 Python Enum 定义合法执行器类型，在配置加载阶段进行前置验证，避免无效配置进入运行时
  - layer: config-propagation
    technology: Context dict + Dependency injection
    reasoning: 通过 workflow_data 字典透传 executor 配置到下游组件，保持与现有 orchestrator 执行模型的兼容性
  - layer: cli-integration
    technology: Click option + Parameter override
    reasoning: 复用现有 CLI --executor 选项，确保 CLI 参数能够正确覆盖配置文件设置
  - layer: error-handling
    technology: Structured exceptions + User-friendly messages
    reasoning: 定义专门的配置验证异常类，提供包含可选值列表的明确错误信息
  core_components:
  - name: ExecutorTypeResolver
    responsibilities: 解析执行器类型配置，实现 CLI > 配置文件 > 默认设置 的优先级策略，返回最终生效的执行器类型和来源标记
    dependencies:
    - LeeConfig
    - CLI args
    - Environment variables
    interfaces:
      input: 'cli_executor: Optional[str], config: LeeConfig, env: Dict[str, str]'
      output: 'ExecutorResolutionResult {executor_type: str, source: str, is_valid:
        bool}'
  - name: ExecutorTypeValidator
    responsibilities: 验证执行器类型的合法性，维护允许的执行器类型列表，生成包含可选值的错误信息
    dependencies:
    - ExecutorTypeRegistry
    interfaces:
      input: 'executor_type: str'
      output: 'ValidationResult {valid: bool, error_message: Optional[str], allowed_values:
        List[str]}'
  - name: ExecutorConfigPropagator
    responsibilities: 将解析后的执行器配置透传到下游组件，包括 workflow_data 注入、运行时上下文传递
    dependencies:
    - ExecutorTypeResolver
    - WorkflowRunner
    interfaces:
      input: 'executor_config: ExecutorResolutionResult, target_context: Dict[str,
        Any]'
      output: 'updated_context: Dict[str, Any]'
  - name: ConfigValidationErrorHandler
    responsibilities: 处理配置验证错误，格式化用户友好的错误信息，确保在配置错误时不进入 workflow 执行阶段
    dependencies:
    - CLI error formatting
    interfaces:
      input: 'validation_error: ValidationError'
      output: 'formatted_error_message: str, exit_code: int'
executor_type_contract:
  allowed_executor_types:
  - type: claude_code
    description: Claude Code 执行器，使用 Anthropic Claude API
    is_default: true
  - type: qwen
    description: 通义千问执行器，使用阿里云 Qwen API
    is_default: false
  - type: kimi
    description: Moonshot Kimi 执行器，使用 Kimi API
    is_default: false
  - type: codex
    description: OpenAI Codex 执行器，使用 Codex API
    is_default: false
  - type: langgraph
    description: LangGraph 执行器，使用 LangGraph 框架
    is_default: false
  - type: shell
    description: Shell 命令执行器，本地执行
    is_default: false
  - type: llm
    description: 通用 LLM 执行器，可配置模型
    is_default: false
  validation_rules:
  - 执行器类型必须是 allowed_executor_types 中定义的合法类型
  - 大小写敏感，必须小写匹配
  - 空值或 None 将回退到默认值 claude_code
  error_message_template: 'Invalid executor type ''{invalid_type}''. Allowed values:
    {allowed_types}. Please check your CLI argument or configuration file.'
config_priority_rules:
  priority_order:
  - level: 1
    source: cli_override
    description: CLI --executor 参数指定
    example: lee run workflow --executor=qwen
  - level: 2
    source: config_file
    description: .lee/config.yaml 中 executor.default_type 配置
    example: "executor:\n  default_type: qwen"
  - level: 3
    source: environment_variable
    description: LEE_EXECUTOR 环境变量
    example: LEE_EXECUTOR=qwen lee run workflow
  - level: 4
    source: builtin_default
    description: 内置默认值 claude_code
    example: N/A
  source_tracing:
    field: executor_selection_source
    purpose: 记录最终执行器配置的来源，用于调试和审计
    values:
    - cli_override
    - config_file
    - env_variable
    - builtin_default
config_schema_extensions:
  executor_config_extension:
    description: ExecutorConfig 类扩展
    changes:
    - 保留现有 default_type 字段
    - '添加 executor_type_registry: List[str] 字段维护允许的执行器类型'
    - 添加 validate_executor_type() 方法进行类型验证
  lee_config_extension:
    description: LeeConfig 类扩展
    changes:
    - 添加 get_executor_resolver() 方法返回 ExecutorTypeResolver 实例
    - 保持与现有配置的向后兼容性
integration_points:
- name: CLI run command
  location: src/lee/cli/commands/run.py
  integration: 在 run() 函数中调用 ExecutorTypeResolver 解析 --executor 参数，验证后注入 workflow_data
  data_flow: CLI args -> ExecutorTypeResolver -> Validation -> workflow_data['executor_override']
- name: ConfigLoader
  location: src/lee/orchestrator/config_loader.py
  integration: 扩展 ExecutorConfig 类，添加执行器类型验证逻辑
  data_flow: YAML config -> ExecutorConfig.from_dict() -> Validation -> LeeConfig
- name: WorkflowRunner
  location: src/lee/orchestrator/execution/workflow_runner.py
  integration: 接收透传的 executor_override 配置，传递给具体执行器
  data_flow: workflow_data['executor_override'] -> Runner selection -> Executor instantiation
- name: Executor Registry
  location: src/lee/runtime/executor/registry.py
  integration: 验证执行器类型是否在注册表中存在
  data_flow: executor_type -> get_graph_builder() -> Validation result
dependencies:
  core_dependencies:
  - name: PyYAML
    version: '>=6.0'
    purpose: 配置文件解析
    alternatives:
    - ruamel.yaml
  - name: Click
    version: '>=8.0'
    purpose: CLI 参数处理
    alternatives:
    - argparse
  internal_dependencies:
  - name: config_loader
    module: lee.orchestrator.config_loader
    purpose: 现有配置加载基础设施
  - name: executor_registry
    module: lee.runtime.executor.registry
    purpose: 执行器注册表，用于验证类型合法性
  - name: workflow_runner
    module: lee.orchestrator.execution.workflow_runner
    purpose: 工作流运行器，接收透传配置
risk_management:
  high_risk_points:
  - risk_id: RISK-FEAT-169-001
    description: 现有 config_loader.py 中的 ExecutorConfig 已有 default_type 字段，扩展时可能破坏向后兼容性
    risk_level: medium
    mitigation_plan: 保持现有字段不变，仅添加验证方法和新字段；添加单元测试确保现有配置加载逻辑不受影响
    degradation_strategy: 如果验证逻辑失败，回退到原有行为（仅读取 default_type 不做验证）
  - risk_id: RISK-FEAT-169-002
    description: CLI --executor 选项的合法值列表需要与 executor_registry 中的注册类型保持一致
    risk_level: medium
    mitigation_plan: 定义统一的 ALLOWED_EXECUTORS 常量，CLI 选项和验证逻辑都引用同一常量；添加集成测试确保一致性
    degradation_strategy: CLI 选项使用固定列表，验证失败时提供明确的错误信息指导用户
  - risk_id: RISK-FEAT-169-003
    description: 配置优先级逻辑实现错误可能导致用户预期外的执行器选择
    risk_level: high
    mitigation_plan: 实现详细的 source tracing，记录每个配置来源的值和最终选择；添加 debug 日志输出配置解析过程
    degradation_strategy: 默认使用 claude_code，记录 warning 日志提示配置问题
  - risk_id: RISK-FEAT-169-004
    description: 无效执行器配置的错误信息不够明确，用户难以排查问题
    risk_level: low
    mitigation_plan: 设计结构化的错误信息模板，包含非法值、允许值列表、配置来源建议；提供配置示例
    degradation_strategy: 即使错误信息不完整也要阻止无效配置进入执行阶段
  backup_strategies:
  - scenario: 配置验证组件故障
    backup: 降级为仅做基本类型检查，依赖下游组件在实例化时报错；保留原有配置加载逻辑不受影响
  - scenario: 新执行器类型未在注册表中定义
    backup: 允许配置通过但记录 warning，依赖运行时动态加载或报错
  - scenario: 优先级逻辑复杂导致 bug
    backup: 简化优先级为 CLI > 配置文件 > 默认，移除环境变量层级以降低复杂度
implementation_phases:
- phase: 1
  title: 核心类型定义与验证
  tasks:
  - 定义 ExecutorType Enum 类，包含所有允许的执行器类型
  - 扩展 ExecutorConfig 类，添加 validate_executor_type() 方法
  - 创建 ExecutorTypeResolver 类实现优先级解析逻辑
  - 添加 ExecutorResolutionResult 数据类
  acceptance_criteria:
  - 'AC-001: 单元测试验证类型解析逻辑正确'
  - 'AC-002: 单元测试验证优先级规则 (CLI > config > env > default)'
- phase: 2
  title: CLI 集成与配置透传
  tasks:
  - 修改 cli/commands/run.py 集成 ExecutorTypeResolver
  - 在 workflow_data 中注入 executor_override 和 executor_selection_source
  - 添加配置验证错误处理，阻止无效配置进入执行
  acceptance_criteria:
  - 'AC-003: CLI 指定 --executor=qwen 时正确识别并透传'
  - 'AC-004: 无效执行器配置返回明确错误信息且不进入 workflow'
- phase: 3
  title: 配置文件支持
  tasks:
  - 验证 .lee/config.yaml 中 executor.default_type 配置读取
  - 实现配置值验证，无效配置在加载时报错
  - 添加配置文件示例和文档
  acceptance_criteria:
  - 'AC-002: 配置文件设置 executor: qwen 时正确识别'
  - 'AC-003: 优先级规则正确执行 (CLI 覆盖配置文件)'
- phase: 4
  title: 集成测试与验证
  tasks:
  - 编写集成测试覆盖完整配置解析链路
  - 验证错误信息格式符合要求
  - 确保向后兼容性
  acceptance_criteria:
  - 所有 AC 通过
  - 现有配置加载测试不受影响
frozen_at: '2026-03-12T00:00:00+08:00'
approval:
  status: PENDING_HUMAN_REVIEW
  reviewers:
  - architect_lead
  - dev_lead
  signature_required: true
