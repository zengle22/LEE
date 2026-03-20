---
id: TECH-FEAT-169-004
ssot_type: tech
title: FEAT-169 Frozen Technical Architecture - 系统配置层支持识别并透传 qwen 执行器类型标识
status: frozen
version: v1
parent_id: FEAT-169
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
  frozen_at: '2026-03-13T02:10:00+08:00'
workflow_instance_id: wf-tech-feat-169-004__feat-169-frozen-technical-architecture-xitongpeizh-20260316
---

id: FTA-FEAT-169-20260313
ssot_type: frozen_technical_architecture
title: FEAT-169 Frozen Technical Architecture - 系统配置层支持识别并透传 qwen 执行器类型标识
status: frozen
version: v1
parent_id: FEAT-169
frozen_at: '2026-03-13T00:00:00Z'
modules:
- name: 执行器类型定义模块
  path: src/lee/orchestrator/config/types.py
  purpose: 定义执行器类型枚举和核心数据结构，提供类型安全的执行器标识
  components:
  - name: ExecutorType
    type: enum
    responsibilities:
    - 定义允许的执行器类型集合 (qwen, claude_code, kimi, llm, shell, codex, langgraph)
    - 提供 from_string 静态方法进行大小写不敏感解析
    - 提供 allowed_values 类方法返回允许值列表供验证使用
    - 提供 is_valid 静态方法快速校验值合法性
    interfaces:
    - method: from_string
      signature: 'ExecutorType.from_string(value: str) -> ExecutorType'
      returns: ExecutorType 枚举值
    - method: allowed_values
      signature: ExecutorType.allowed_values() -> List[str]
      returns: 允许的字符串值列表
    - method: is_valid
      signature: 'ExecutorType.is_valid(value: str) -> bool'
      returns: 是否为合法值
  - name: ExecutorConfigResult
    type: dataclass
    responsibilities:
    - 封装执行器解析结果
    - 记录最终选定的执行器类型
    - 记录执行器来源 (cli/env/config/default)
    - 记录原始输入值用于调试
    interfaces:
    - method: __init__
      signature: '__init__(executor_type: ExecutorType, source: str, raw_value: str)'
      returns: None
  - name: ExecutorValidationError
    type: class
    responsibilities:
    - 定义执行器验证异常类型
    - 携带错误信息和可选值列表
    interfaces:
    - method: __init__
      signature: '__init__(message: str, invalid_value: str, allowed_values: List[str])'
      returns: None
- name: 执行器解析器模块
  path: src/lee/orchestrator/config/resolver.py
  purpose: 实现四层优先级解析策略 (CLI > Env > Config > Default)
  components:
  - name: ExecutorTypeResolver
    type: class
    responsibilities:
    - 实现四层优先级解析逻辑
    - 追踪执行器来源
    - 处理大小写不敏感匹配
    - 返回包含来源信息的解析结果
    interfaces:
    - method: resolve
      signature: 'resolve(cli_value: Optional[str], config_value: Optional[str]) ->
        ExecutorConfigResult'
      returns: ExecutorConfigResult
    - method: _resolve_cli
      signature: '_resolve_cli(cli_value: Optional[str]) -> Optional[str]'
      returns: CLI 指定的值或 None
    - method: _resolve_env
      signature: _resolve_env() -> Optional[str]
      returns: 环境变量指定的值或 None
    - method: _resolve_config
      signature: '_resolve_config(config_value: Optional[str]) -> Optional[str]'
      returns: 配置文件指定的值或 None
    - method: _resolve_default
      signature: _resolve_default() -> str
      returns: 默认执行器类型
- name: 执行器验证器模块
  path: src/lee/orchestrator/config/validator.py
  purpose: 验证执行器类型配置的合法性并提供清晰的错误信息
  components:
  - name: ExecutorTypeValidator
    type: class
    responsibilities:
    - 验证执行器类型值是否合法
    - 生成包含可选值列表的错误信息
    - 提供宽松模式和严格模式切换
    interfaces:
    - method: validate
      signature: 'validate(value: str, strict: bool = True) -> bool'
      returns: 是否合法
    - method: format_error_message
      signature: 'format_error_message(invalid_value: str) -> str'
      returns: 格式化的错误信息
- name: 配置错误处理模块
  path: src/lee/orchestrator/config/error_handler.py
  purpose: 统一处理配置验证错误并提供用户友好的错误提示
  components:
  - name: ConfigValidationErrorHandler
    type: class
    responsibilities:
    - 捕获验证异常
    - 生成错误提示信息
    - 决定是否阻止 workflow 启动
    - 记录错误日志用于追踪
    interfaces:
    - method: handle
      signature: 'handle(error: ExecutorValidationError) -> bool'
      returns: 是否阻止 workflow 启动
    - method: format_message
      signature: 'format_message(error: ExecutorValidationError) -> str'
      returns: 格式化的错误消息
dependencies:
  internal:
  - module: config_loader
    path: src/lee/orchestrator/config_loader.py
    purpose: 现有配置加载基座，ExecutorConfig 需要扩展支持 executor 字段
    risk_level: low
  - module: executors
    path: src/lee/orchestrator/execution/executors.py
    purpose: 执行器实现模块，新增执行器类型需要在此注册
    risk_level: low
  - module: run.py (CLI)
    path: src/lee/cli/commands/run.py
    purpose: CLI 命令入口，需要添加 --executor 参数并集成 Resolver
    risk_level: medium
  - module: workflow_runner
    path: src/lee/orchestrator/execution/workflow_runner.py
    purpose: 工作流执行引擎，需要支持 executor_override 参数透传
    risk_level: medium
  external:
  - library: click
    version: '>=8.1'
    purpose: CLI 参数解析，--executor 选项依赖
    risk_level: low
  - library: pyyaml
    version: '>=6.0'
    purpose: 配置文件 YAML 解析
    risk_level: low
  - library: dataclasses (stdlib)
    version: Python 3.7+
    purpose: 数据结构定义
    risk_level: low
  - library: enum (stdlib)
    version: Python 3.4+
    purpose: 枚举类型定义
    risk_level: low
risks:
- id: UC-001
  description: 执行器列表在不同模块间不同步 (executors.py vs ExecutorType)
  impact: medium
  probability: medium
  mitigation: 在 ExecutorType 中维护唯一的执行器类型白名单，executors.py 中的执行器类在初始化时向 ExecutorType
    注册
  fallback: 运行时验证：在 resolve 时检查执行器是否实际可用，不可用时回退到默认执行器并警告
- id: UC-002
  description: 旧配置文件或 CLI 脚本使用已废弃的执行器名称
  impact: low
  probability: low
  mitigation: 实现执行器别名映射表，支持向后兼容
  fallback: 验证失败时返回清晰的错误信息和迁移指南
- id: UC-003
  description: workflow_data 结构变更影响现有工作流
  impact: medium
  probability: low
  mitigation: 保持向后兼容：executor_config 作为可选字段添加，不影响现有 workflow_data 结构
  fallback: 在 workflow_runner 中检测字段缺失时使用默认行为
- id: UC-004
  description: 环境变量名冲突或覆盖逻辑复杂
  impact: low
  probability: low
  mitigation: 使用明确的环境变量名 LEE_EXECUTOR_TYPE，避免与其他配置混淆
  fallback: 环境变量优先级可配置，默认遵循 CLI > Env > Config > Default
decisions:
- id: D-001
  content: 使用 Python Enum 定义执行器类型，而非字符串常量
  status: frozen
  rationale: 类型安全、IDE 支持、易于扩展、防止拼写错误
- id: D-002
  content: 优先级策略：CLI > Environment Variable > Config File > Default
  status: frozen
  rationale: 符合业界标准配置管理实践，灵活性最高
- id: D-003
  content: 执行器类型值大小写不敏感
  status: frozen
  rationale: 提升用户体验，减少配置错误
- id: D-004
  content: 'workflow_data 中 executor_config 结构：{type: str, source: str, raw_value:
    str}'
  status: frozen
  rationale: 完整的配置溯源信息，便于调试和审计
- id: D-005
  content: 验证错误必须阻止 workflow 启动
  status: frozen
  rationale: 防止无效配置导致的运行时错误
- id: D-006
  content: 默认执行器为 claude_code
  status: frozen
  rationale: 与现有行为保持一致，避免破坏性变更
- id: D-007
  content: 新增模块统一放在 src/lee/orchestrator/config/ 目录下
  status: frozen
  rationale: 职责清晰，便于维护和测试
