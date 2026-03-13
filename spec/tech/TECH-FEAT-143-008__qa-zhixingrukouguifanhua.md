---
id: TECH-FEAT-143-008
ssot_type: tech
title: QA 执行入口规范化
status: active
version: v1
parent_id: FEAT-143
derived_from_ids: []
source_refs: []
owner: null
tags: []
properties:
  contract_key: tech_spec
  identity_kind: ssot
---

contract_type: frozen-technical-architecture
contract_version: '1.0'
metadata:
  contract_id: FTA-20260313-001
  status: FROZEN
  is_frozen: true
  frozen_at: '2026-03-13T01:12:00+08:00'
  feature_id: FEAT-143
  feature_title: QA 执行入口规范化
  designer: Architecture Agent
  design_date: '2026-03-13'
  governing_adrs:
  - ADR-001#4-1-three-axis-model
  - ADR-001#5-3-object-duty-definitions
  - ADR-001#6-3-key-constraints
  - ADR-001#11-7-transition-authority-matrix
  - ADR-001#12-1-p0-blocking-rules
  - ADR-007#1-decision
  - ADR-007#3-3-workflow-c-test-task-execution
  - ADR-007#5-mandatory-traceability-rules
  - ADR-008#3-2-object-meaning
  - ADR-008#6-3-key-constraints
  source_refs:
  - FEAT-143
  - TECH-FEAT-143-001
  - UI-FEAT-143-003
architecture_decisions:
  design_principles:
  - 单一入口原则 - 所有测试执行必须通过 TESTPLAN 下的 TASK 触发
  - 链路完整原则 - 执行前必须验证 RELEASE→PLAN→TASK 三级引用链路
  - 显式拒绝原则 - 旁路请求必须明确拒绝并记录审计日志
  - 审计透明原则 - 每次执行的入口来源、路径链、时间戳、操作用户必须可追溯
  - 渐进校验原则 - 校验失败时按 task→plan→release 顺序逐级提示
  - 静默失败原则 - 阻断旁路入口时返回友好错误，不暴露内部实现细节
  tech_stack:
  - layer: CLI Entry Layer
    technology: Typer + Click
    reasoning: LEE CLI 已采用 Typer 框架构建命令体系；支持异步命令、参数验证和结构化输出；与现有 lee qa 命令族保持一致
  - layer: SSOT Validation Layer
    technology: Pydantic v2 + Custom Validators
    reasoning: 利用 Pydantic v2 的类型验证和自定义验证器实现 SSOT 链路校验；与现有 SSOTValidator 架构兼容
  - layer: Audit Logging Layer
    technology: SQLite + JSON append-only log
    reasoning: SQLite 用于结构化审计查询；JSON append-only log 用于不可篡改的执行事实记录；双存储策略满足审计和查询双重需求
  - layer: Execution Router
    technology: Strategy Pattern + Dependency Injection
    reasoning: 使用策略模式支持多种执行路径（标准执行/自动补全/仅校验）；依赖注入便于测试和扩展
  - layer: Error Handling
    technology: Custom Exception Hierarchy + Error Code Registry
    reasoning: 分层异常体系便于精确错误处理；错误码注册表支持统一的错误文档和 CLI 展示
  - layer: Data Model
    technology: Pydantic v2
    reasoning: 利用 Pydantic 的类型安全和验证能力定义 ExecutionRequest/Response 模型，确保入口参数的结构完整性和类型安全
  - layer: Persistence
    technology: NDJSON (Newline Delimited JSON)
    reasoning: 审计日志需要支持流式追加写入和按行读取，NDJSON 格式兼容 JSON 结构且支持增量写入，便于日志轮转和审计追溯
  - layer: Registry Integration
    technology: SSOT Registry (File-based)
    reasoning: 复用现有 SSOT Registry 系统，通过 front matter 文件作为真源，registry 作为运行时索引，确保与 ADR-001
      三轴模型一致
  - layer: Validation
    technology: Synchronous Validation Chain
    reasoning: 执行入口校验必须在请求处理前完成，采用同步链式校验器 (Chain of Responsibility) 模式，确保校验逻辑的可预测性和可调试性
  - layer: Enforcement
    technology: Middleware Pattern
    reasoning: EnforcementEngine 作为中间件层拦截所有执行请求，与业务逻辑解耦，确保旁路阻断的完备性
  core_components:
  - name: EntryValidator
    responsibilities: 解析入口参数 (task_ref, plan_ref, release_ref)；检测旁路执行尝试；执行参数有效性预校验
    dependencies:
    - SSOTRegistry
    - IDParser
    interfaces:
      input:
      - 'task_ref: str'
      - 'plan_ref: Optional[str]'
      - 'release_ref: Optional[str]'
      output:
      - EntryValidationResult
  - name: ChainValidator
    responsibilities: 验证 TASK 存在性和有效性；验证 TASK 归属的 TESTPLAN；验证 TESTPLAN 归属的 RELEASE；执行渐进式校验并生成校验报告；支持自动补全模式下推导缺失的
      plan_ref/release_ref
    dependencies:
    - SSOTService
    - SSOTRegistry
    - EntryValidator
    interfaces:
      input:
      - 'task_ref: str'
      - 'auto_complete: bool'
      output:
      - ChainValidationReport
  - name: AuditRecorder
    responsibilities: 记录执行入口审计日志；绑定 SSOT 三轴关系 (release/plan/task)；生成 execution_id
      和 audit_ref；支持审计查询接口
    dependencies:
    - SQLite Connector
    - JSON Log Writer
    - IDGenerator
    interfaces:
      input:
      - AuditEntry
      output:
      - execution_id
      - audit_ref
  - name: ExecutionRouter
    responsibilities: 根据入口类型路由到执行引擎；支持标准执行/自动补全/仅校验模式；管理执行上下文传递
    dependencies:
    - EntryValidator
    - ChainValidator
    - AuditRecorder
    - ExecutionEngine
    interfaces:
      input:
      - ValidatedExecutionRequest
      output:
      - ExecutionResult
  - name: BypassBlocker
    responsibilities: 检测绕过 TESTPLAN/TASK 的直接执行请求；阻断旁路请求并返回规范错误码；记录旁路尝试审计日志
    dependencies:
    - EntryValidator
    - AuditRecorder
    interfaces:
      input:
      - ExecutionRequest
      output:
      - BlockDecision
  - name: CLIOutputFormatter
    responsibilities: 格式化 CLI 输出（状态图标、阶段指示器）；处理错误码展示和引导信息；支持结构化输出（JSON/YAML）
    dependencies:
    - Rich Library
    - Error Code Registry
    interfaces:
      input:
      - ExecutionStatus
      - ErrorInfo
      output:
      - Formatted Output
  module_interactions:
  - sequence_id: 1
    name: 标准执行流程
    steps:
    - 1. CLI 解析 --task-ref 参数 → EntryValidator
    - 2. EntryValidator 检测旁路尝试 → BypassBlocker
    - 3. ChainValidator 逐级校验 task→plan→release
    - 4. 校验通过后 AuditRecorder 记录审计日志
    - 5. ExecutionRouter 路由到 ExecutionEngine
    - 6. CLIOutputFormatter 格式化输出结果
  - sequence_id: 2
    name: 旁路阻断流程
    steps:
    - 1. 检测到无 task_ref 的执行请求
    - 2. BypassBlocker 拦截请求
    - 3. AuditRecorder 记录旁路尝试
    - 4. CLIOutputFormatter 返回 ERR-BYPASS-001 错误
  - sequence_id: 3
    name: 自动补全流程
    steps:
    - 1. 用户仅提供 task_ref
    - 2. ChainValidator 从 TASK 推导 PLAN
    - 3. ChainValidator 从 PLAN 推导 RELEASE
    - 4. 执行完整链路校验
    - 5. 校验通过则继续执行
core_dependencies:
  internal_modules:
  - module: SSOTRegistry
    location: src/lee/orchestrator/execution/artifacts/ssot_service.py
    usage: 查询 TASK/PLAN/RELEASE 对象及其关系
  - module: SSOTValidator
    location: src/lee/orchestrator/execution/artifacts/ssot_service.py
    usage: 执行 SSOT 链路一致性校验
  - module: IDParser
    location: src/lee/orchestrator/execution/artifacts/id_parser.py
    usage: 解析和验证 SSOT 对象 ID 格式
  - module: IDGenerator
    location: src/lee/orchestrator/execution/artifacts/id_generator.py
    usage: 生成 execution_id 和 audit_ref
  - module: ErrorRegistry
    location: src/lee/orchestrator/utils/error_registry.py
    usage: 错误码注册和错误信息格式化
  external_libraries:
  - library: typer>=0.9.0
    purpose: CLI 命令框架
    constraint: 与现有 LEE CLI 版本保持一致
  - library: pydantic>=2.0.0
    purpose: 数据验证和序列化
    constraint: 需要 v2 API 支持
  - library: rich>=13.0.0
    purpose: CLI 输出美化
    constraint: 支持状态图标和表格展示
  - library: aiosqlite>=0.19.0
    purpose: 异步 SQLite 访问
    constraint: 支持异步审计写入
  - library: pyyaml>=6.0
    purpose: YAML 文件解析
    constraint: 解析 SSOT front matter
  - library: click>=8.1
    purpose: CLI 命令底层支持
    constraint: Typer 依赖
  qa_contracts:
  - contract: Test Plan v2
    location: spec-global/departments/qa/contracts/test-plan-v2/v1/schema.yaml
    usage: 校验 TESTPLAN 对象结构和 parent_id=RELEASE 约束
  - contract: Test Set Execution v1
    location: spec-global/departments/qa/contracts/test-set-execution/v1/schema.yaml
    usage: 定义执行结果对象结构
  - contract: Test Set v1
    location: spec-global/departments/qa/contracts/test-set/v1/schema.yaml
    usage: 校验 TESTSET 与 FEAT 的单一绑定关系
risk_management:
  high_risk_points:
  - risk_id: RISK-001
    description: 现有 QA 执行入口可能未完全收敛到 TASK，存在历史遗留调用路径
    impact: 旁路阻断可能影响现有自动化脚本和 CI 流程
    likelihood: 高
    mitigation_plan:
    - 1. 执行入口清单审计，识别所有现有调用点
    - 2. 提供迁移指南和兼容期（warning 模式）
    - 3. 在兼容期后切换到 enforce 模式
    fallback_strategy: 保留 EXECUTION_MODE=warn 配置，允许在过渡期继续使用旧入口但记录警告
  - risk_id: RISK-002
    description: SSOT 链路可能不完整（TASK 无 PLAN 归属或 PLAN 无 RELEASE 归属）
    impact: 链路校验失败导致无法执行
    likelihood: 中
    mitigation_plan:
    - 1. 执行前运行 SSOT 链路审计报告
    - 2. 提供自动修复工具补全缺失的归属关系
    - 3. 对无法修复的提供手动修正指南
    fallback_strategy: 提供 --force-bypass 参数（仅限管理员），允许在紧急情况下绕过校验但记录审计日志
  - risk_id: RISK-003
    description: 审计日志写入失败可能导致执行中断
    impact: 即使执行成功也无法证明合规性
    likelihood: 低
    mitigation_plan:
    - 1. 审计写入采用事务性保证
    - 2. 实现双写策略（SQLite + JSON）
    - 3. 写入失败时立即阻断执行并回滚
    fallback_strategy: 审计失败时进入只读模式，允许查询但不允许新执行
  - risk_id: RISK-004
    description: 自动补全逻辑可能与用户显式指定的 plan_ref/release_ref 冲突
    impact: 参数冲突导致校验失败
    likelihood: 中
    mitigation_plan:
    - 1. 显式参数优先于自动推导
    - 2. 检测到冲突时返回详细对比信息
    - 3. 提供 --show-chain 参数展示实际归属链路
    fallback_strategy: 冲突时阻断执行，要求用户明确指定或移除冲突参数
  - risk_id: RISK-005
    description: SSOT Registry 与文件真源不一致风险
    impact: Registry 作为运行时索引可能与 front matter 文件真源产生不一致，导致校验基于过期数据
    likelihood: 中
    mitigation_plan:
    - 1. 每次校验前执行 registry sync 检查文件修改时间
    - 2. 实现增量刷新机制，检测到文件变更时自动重建相关索引
    - 3. 在 ExecutionRequest 处理前强制校验 registry 新鲜度
    fallback_strategy: 若 registry 不一致或不可用，降级为直接读取 front matter 文件进行校验，牺牲性能换取正确性
  - risk_id: RISK-006
    description: 旁路检测不完备风险
    impact: 可能存在未覆盖的旁路入口，导致部分执行请求绕过 EntryRouter
    likelihood: 中
    mitigation_plan:
    - 1. 所有执行 API 统一通过 EnforcementEngine 中间件
    - 2. 实现 API 调用链追踪，检测直接调用底层执行接口的行为
    - 3. 定期审计分析，识别异常执行模式
    fallback_strategy: 发现新的旁路入口时，立即更新 EnforcementEngine 规则并重新审计历史请求
  - risk_id: RISK-007
    description: 与现有执行系统集成风险
    impact: EntryRouter 需要与现有 QA 执行引擎集成，可能引入兼容性问题
    likelihood: 中
    mitigation_plan:
    - 1. EntryRouter 仅作为前置校验层，不替换现有执行引擎
    - 2. 保持 ExecutionRequest/Response 与现有接口的兼容性
    - 3. 提供 feature flag 控制入口规范化开关
    fallback_strategy: 集成出现问题时，可通过 feature flag 临时关闭入口校验，回到原有执行模式
  technical_uncertainties:
  - uncertainty_id: UNC-001
    description: 现有 SSOTRegistry 是否支持高效的链路查询（TASK→PLAN→RELEASE）
    resolution_approach: 先执行 POC 验证查询性能，必要时增加专用索引或缓存层
    decision_deadline: 实现前必须确认
  - uncertainty_id: UNC-002
    description: 审计日志的存储策略（纯 SQLite vs SQLite+JSON 双写）
    resolution_approach: 评估查询需求和审计合规要求后决策
    decision_deadline: 设计评审时确认
implementation_plan:
  phase_1_foundation:
    name: 基础架构层
    tasks:
    - 1.1 扩展 SSOTRegistry 支持 TASK→PLAN→RELEASE 链路查询
    - 1.2 实现 EntryValidator 和 BypassBlocker
    - 1.3 实现 ChainValidator 渐进校验逻辑
    - 1.4 实现 AuditRecorder 双写策略
    deliverables:
    - src/lee/orchestrator/execution/entry/validator.py
    - src/lee/orchestrator/execution/entry/chain_validator.py
    - src/lee/orchestrator/execution/entry/audit_recorder.py
    - src/lee/orchestrator/execution/entry/bypass_blocker.py
  phase_2_integration:
    name: 集成与路由层
    tasks:
    - 2.1 实现 ExecutionRouter 策略模式
    - 2.2 实现 CLIOutputFormatter
    - 2.3 实现 ErrorRegistry 错误码定义
    - 2.4 集成到现有 lee qa 命令体系
    deliverables:
    - src/lee/orchestrator/execution/entry/router.py
    - src/lee/orchestrator/cli/commands/qa/execute.py
    - src/lee/orchestrator/utils/error_registry.py (扩展)
  phase_3_governance:
    name: 治理与审计层
    tasks:
    - 3.1 实现审计查询接口
    - 3.2 实现 EXECUTION_MODE 配置（enforce/warn）
    - 3.3 添加 CI 校验规则
    - 3.4 编写迁移指南和兼容性说明
    deliverables:
    - src/lee/orchestrator/cli/commands/qa/audit.py
    - config/execution-mode-config.yaml
    - docs/qa/execution-entry-migration-guide.md
acceptance_criteria_mapping:
  AC-003-001:
    description: 执行入口唯一性验证
    implementation:
    - EntryValidator 检测 task_ref 存在性
    - BypassBlocker 阻断无 task_ref 请求
    - ChainValidator 验证 task 归属 plan
    validation_method: 单元测试 + 集成测试
  AC-003-002:
    description: 执行路径完整性校验
    implementation:
    - ChainValidator 逐级校验 task→plan→release
    - 自动补全模式下推导缺失的 plan_ref/release_ref
    validation_method: 集成测试 + E2E 测试
  AC-003-003:
    description: 旁路执行入口阻断验证
    implementation:
    - BypassBlocker 检测并阻断旁路请求
    - AuditRecorder 记录旁路尝试
    - CLIOutputFormatter 返回 ERR-BYPASS-001
    validation_method: 单元测试 + 渗透测试
  AC-003-004:
    description: 执行入口审计验证
    implementation:
    - AuditRecorder 记录完整审计信息
    - 审计查询接口支持多维度查询
    validation_method: 集成测试 + 审计报表验证
output_specifications:
  error_codes:
  - code: ERR-ENTRY-001
    message: 缺少 task_ref 参数
    severity: block
    action: 阻断执行，提示使用规范命令：lee qa execute --task-ref=TASK-xxx
  - code: ERR-ENTRY-002
    message: task_ref 无效或不存在
    severity: block
    action: 阻断执行，提示检查 task_ref 是否正确
  - code: ERR-ENTRY-003
    message: task 不归属任何 testplan
    severity: block
    action: 阻断执行，提示将 task 关联到 testplan
  - code: ERR-CHAIN-001
    message: plan_ref 缺失或无效
    severity: block
    action: 链路断裂阻断，尝试自动补全或提示用户指定
  - code: ERR-CHAIN-002
    message: release_ref 缺失或无效
    severity: block
    action: 链路断裂阻断，尝试自动补全或提示用户指定
  - code: ERR-CHAIN-003
    message: 链路断裂 - task/plan/release 不匹配
    severity: block
    action: 展示实际归属链路，要求用户修正参数
  - code: ERR-BYPASS-001
    message: 检测到旁路执行尝试
    severity: block
    action: 阻断并记录审计日志，提示使用规范入口
  cli_output_standards:
    status_icons:
      success: ✓
      failure: ✗
      warning: ⚠
      processing: →
      pending: ○
    stage_indicators:
    - '[ENTRY] - 入口校验阶段'
    - '[CHAIN] - 链路校验阶段'
    - '[AUDIT] - 审计记录阶段'
    - '[EXEC] - 执行引擎阶段'
    success_output:
      format: structured
      fields:
      - execution_id
      - task_ref
      - plan_ref
      - release_ref
      - audit_ref
      - status
    error_output:
      format: structured
      fields:
      - error_code
      - message
      - severity
      - suggested_action
      - help_link
frozen_declaration:
  frozen_at: '2026-03-13T01:12:00+08:00'
  frozen_by: architect
  review_status: pending_approval
  change_policy: 本架构文档进入 FROZEN 状态后，后续变更需走架构变更审批流程：1.提交变更申请 2.影响分析 3.架构评审 4.更新版本号
    5.重新冻结
  known_limitations:
  - 当前架构假设单实例部署，多实例场景下审计日志需要额外同步机制
  - 旁路检测基于请求特征分析，无法 100% 防止恶意绕过
  - SSOT Registry 一致性检查会增加单次请求处理延迟 (~50-100ms)
  - 历史 TASK 对象可能不符合新的 parent 约束，需要兼容处理
