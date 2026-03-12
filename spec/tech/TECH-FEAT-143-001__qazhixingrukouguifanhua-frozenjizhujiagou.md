---
id: TECH-FEAT-143-001
ssot_type: tech
title: QA执行入口规范化 - Frozen技术架构
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
contract_version: v1
metadata:
  contract_id: FTA-20260312-001
  status: FROZEN
  is_frozen: true
  frozen_at: '2026-03-12T22:00:00+08:00'
  feature_id: FEAT-143
  title: QA执行入口规范化 - Frozen技术架构
  owner: architect
  source_refs:
  - FEAT-143
  - ADR-001
  - UI-FEAT-143-003
architecture_decisions:
  tech_stack:
  - layer: data_model
    technology: Pydantic v2
    reasoning: 利用 Pydantic 的类型安全和验证能力定义 ExecutionRequest/Response 模型，确保入口参数的结构完整性和类型安全
  - layer: persistence
    technology: NDJSON (Newline Delimited JSON)
    reasoning: 审计日志需要支持流式追加写入和按行读取，NDJSON 格式兼容 JSON 结构且支持增量写入，便于日志轮转和审计追溯
  - layer: registry_integration
    technology: SSOT Registry (File-based)
    reasoning: 复用现有 SSOT Registry 系统，通过 front matter 文件作为真源，registry 作为运行时索引，确保与 ADR-001
      三轴模型一致
  - layer: validation
    technology: Synchronous Validation Chain
    reasoning: 执行入口校验必须在请求处理前完成，采用同步链式校验器 (Chain of Responsibility) 模式，确保校验逻辑的可预测性和可调试性
  - layer: enforcement
    technology: Middleware Pattern
    reasoning: ' EnforcementEngine 作为中间件层拦截所有执行请求，与业务逻辑解耦，确保旁路阻断的完备性'
  - layer: error_handling
    technology: Structured Error Code System
    reasoning: 定义 QA-ENTRY-{xxx} 错误码体系，使错误类型可机读，便于自动化处理和审计分类
  core_components:
  - name: EntryRouter
    responsibilities: 执行入口路由的核心接口，接收 ExecutionRequest，协调校验链，返回 ExecutionResponse。作为系统的单一入口点，所有执行请求必须通过此组件
    dependencies:
    - ChainValidator
    - RegistryValidator
    - EnforcementEngine
    - AuditLogger
    interface:
      methods:
      - 'route_execution(request: ExecutionRequest) -> ExecutionResponse'
      input_schema: ExecutionRequest (Pydantic Model)
      output_schema: ExecutionResponse (Pydantic Model)
  - name: ExecutionRequest
    responsibilities: 标准化执行请求的数据模型，包含 task_ref、user_context、entry_source、timestamp
      等字段，作为入口校验的基础数据结构
    dependencies:
    - Pydantic BaseModel
    fields:
    - 'task_ref: str (必填，TASK ID)'
    - 'user_id: str (操作用户标识)'
    - 'entry_source: str (入口来源: web/cli/api)'
    - 'request_timestamp: datetime'
    - 'client_ip: str (可选)'
    - 'metadata: Dict (扩展字段)'
  - name: ExecutionResponse
    responsibilities: 标准化执行响应的数据模型，包含路由结果、错误信息、审计日志引用等
    dependencies:
    - Pydantic BaseModel
    fields:
    - 'success: bool'
    - 'execution_id: str (执行实例ID)'
    - 'audit_log_id: str (审计日志ID)'
    - 'error_code: str (QA-ENTRY-{xxx})'
    - 'error_message: str'
    - 'validation_chain: List[ValidationResult]'
  - name: ChainValidator
    responsibilities: 校验 RELEASE->TESTPLAN->TASK 链路的完整性和有效性。实现 CV-001 至 CV-006 校验规则，包括：release存在性、plan存在性、task归属关系、链路连通性
    dependencies:
    - SSOT Registry
    - RegistryValidator
    validation_rules:
    - 'CV-001: task_ref 对应 TASK 对象存在'
    - 'CV-002: TASK.parent_id 指向有效的 TESTPLAN'
    - 'CV-003: TESTPLAN.parent_id 指向有效的 RELEASE'
    - 'CV-004: RELEASE 状态允许执行 (非 aborted)'
    - 'CV-005: TESTPLAN 状态允许执行 (committed/in_progress)'
    - 'CV-006: TASK 状态允许执行 (todo/doing/blocked)'
  - name: RegistryValidator
    responsibilities: 与 SSOT Registry 集成，校验 task 归属 testplan 的有效性，提供 registry 查询接口的封装
    dependencies:
    - SSOT Registry
    - ArtifactManager
    interface:
      methods:
      - 'validate_task_in_testplan(task_id: str, testplan_id: str) -> bool'
      - 'get_testplan_for_task(task_id: str) -> Optional[str]'
      - 'get_release_for_testplan(testplan_id: str) -> Optional[str]'
  - name: AuditLogger
    responsibilities: 记录每次执行的入口来源、路径链、时间戳、操作用户等审计信息。支持 NDJSON 格式写入，提供审计查询接口
    dependencies:
    - NDJSON File Storage
    - ExecutionContext
    log_schema:
      fields:
      - 'audit_id: str (唯一标识)'
      - 'timestamp: datetime (ISO8601)'
      - 'task_ref: str'
      - 'user_id: str'
      - 'entry_source: str'
      - 'execution_path: List[str] (RELEASE->PLAN->TASK ID链)'
      - 'result: str (success/blocked/failed)'
      - 'error_code: str (可选)'
      - 'client_ip: str (可选)'
      - 'user_agent: str (可选)'
      format: NDJSON (每行一个JSON对象)
    interface:
      methods:
      - 'log_execution(request: ExecutionRequest, result: ExecutionResult)'
      - 'log_bypass_attempt(request: ExecutionRequest, reason: str)'
      - 'query_audit_logs(filters: AuditFilter) -> List[AuditLog]'
  - name: EnforcementEngine
    responsibilities: 阻断非标准入口请求并记录审计日志。检测旁路执行尝试，返回标准错误响应，提供标准入口引导
    dependencies:
    - AuditLogger
    - ErrorCodeRegistry
    bypass_detection_rules:
    - 缺少 task_ref 参数
    - task_ref 格式不合法
    - 直接调用底层执行API (跳过EntryRouter)
    - 请求头中缺少标准入口标识
    error_codes:
    - 'QA-ENTRY-001: 缺少 task_ref 参数'
    - 'QA-ENTRY-002: task_ref 格式无效'
    - 'QA-ENTRY-003: 未找到对应 TASK'
    - 'QA-ENTRY-004: TASK 未关联 TESTPLAN'
    - 'QA-ENTRY-005: TESTPLAN 未关联 RELEASE'
    - 'QA-ENTRY-006: 链路完整性校验失败'
    - 'QA-ENTRY-007: 旁路执行被阻断'
    - 'QA-ENTRY-008: 权限不足'
    interface:
      methods:
      - 'enforce(request: ExecutionRequest) -> EnforcementResult'
      - 'is_bypass_attempt(request: ExecutionRequest) -> bool'
      - 'block_with_response(request: ExecutionRequest, error_code: str) -> ExecutionResponse'
  - name: BypassAttemptType (Enum)
    responsibilities: 定义旁路尝试的类型枚举，用于审计分类和统计分析
    values:
    - MISSING_TASK_REF
    - INVALID_TASK_REF_FORMAT
    - DIRECT_API_CALL
    - SKIP_VALIDATION
    - FORGED_ENTRY_SOURCE
  data_flow:
    standard_execution:
    - 1. 用户通过标准入口提交 ExecutionRequest
    - 2. EnforcementEngine 检测是否为旁路尝试
    - 3. ChainValidator 校验 RELEASE->PLAN->TASK 链路
    - 4. RegistryValidator 校验 task 归属有效性
    - 5. AuditLogger 记录执行审计日志
    - 6. EntryRouter 返回 ExecutionResponse
    - 7. 允许执行请求进入下游执行引擎
    bypass_blocked:
    - 1. 用户尝试非标准入口提交请求
    - 2. EnforcementEngine 检测到旁路尝试
    - 3. AuditLogger 记录阻断审计日志 (含 BypassAttemptType)
    - 4. EntryRouter 返回带 QA-ENTRY-{xxx} 错误码的 ExecutionResponse
    - 5. 请求被阻断，返回标准入口引导信息
  integration_points:
  - component: SSOT Registry
    integration_type: 读取依赖
    description: 通过 Registry 查询 TASK/TESTPLAN/RELEASE 对象的存在性和关系
  - component: 执行引擎
    integration_type: 下游调用
    description: EntryRouter 校验通过后，将请求转发给实际执行引擎
  - component: 审计存储
    integration_type: 写入依赖
    description: '审计日志写入 NDJSON 文件，路径: docs/reports/evidence/qa-execution-audit/'
risk_management:
  high_risk_points:
  - risk_id: R-001
    description: SSOT Registry 与文件真源不一致风险：Registry 作为运行时索引可能与 front matter 文件真源产生不一致，导致校验基于过期数据
    mitigation_plan: 1. 每次校验前执行 registry sync 检查文件修改时间; 2. 实现增量刷新机制，检测到文件变更时自动重建相关索引;
      3. 在 ExecutionRequest 处理前强制校验 registry 新鲜度
    degradation_strategy: 若 registry 不一致或不可用，降级为直接读取 front matter 文件进行校验，牺牲性能换取正确性
  - risk_id: R-002
    description: 旁路检测不完备风险：可能存在未覆盖的旁路入口，导致部分执行请求绕过 EntryRouter
    mitigation_plan: 1. 所有执行API统一通过 EnforcementEngine 中间件; 2. 实现 API 调用链追踪，检测直接调用底层执行接口的行为;
      3. 定期审计分析，识别异常执行模式
    degradation_strategy: 发现新的旁路入口时，立即更新 EnforcementEngine 规则并重新审计历史请求
  - risk_id: R-003
    description: 审计日志性能瓶颈风险：高并发执行场景下，NDJSON 文件追加写入可能成为性能瓶颈
    mitigation_plan: 1. 实现异步审计日志写入 (不阻塞执行主流程); 2. 支持按日期分割日志文件，避免单文件过大; 3. 实现审计日志缓冲区，批量写入
    degradation_strategy: 若审计日志写入失败，执行流程继续，但标记审计状态为 'pending'，后台任务重试写入
  - risk_id: R-004
    description: 循环依赖风险：ChainValidator 依赖 RegistryValidator，RegistryValidator 依赖 SSOT
      Service，可能形成循环依赖
    mitigation_plan: 1. 采用依赖注入模式，接口隔离; 2. 明确组件层级：EntryRouter -> Validators -> Registry
      -> FileSystem; 3. 使用工厂模式创建组件实例
    degradation_strategy: 通过架构评审确保依赖关系单向，若发现循环依赖则重构接口
  - risk_id: R-005
    description: 与现有执行系统集成风险：EntryRouter 需要与现有 QA 执行引擎集成，可能引入兼容性问题
    mitigation_plan: 1. EntryRouter 仅作为前置校验层，不替换现有执行引擎; 2. 保持 ExecutionRequest/Response
      与现有接口的兼容性; 3. 提供 feature flag 控制入口规范化开关
    degradation_strategy: 集成出现问题时，可通过 feature flag 临时关闭入口校验，回到原有执行模式
  - risk_id: R-006
    description: TASK.parent 类型变更影响：根据 ADR-001，TASK.parent 从 FEAT 改为 DEVPLAN/TESTPLAN，可能影响历史数据
    mitigation_plan: 1. ChainValidator 同时支持新旧 parent 类型，兼容历史 TASK; 2. 对于历史 TASK，仅校验有效性不强制链路完整性;
      3. 逐步迁移历史 TASK 到新的 parent 结构
    degradation_strategy: 对于无法解析 parent 的历史 TASK，允许执行但标记为 'legacy mode'，记录在审计日志中
frozen_declaration:
  frozen_at: '2026-03-12T22:00:00+08:00'
  frozen_by: architect
  review_status: approved
  change_policy: 本架构文档已进入 FROZEN 状态，后续变更需走架构变更审批流程：1.提交变更申请 2.影响分析 3.架构评审 4.更新版本号
    5.重新冻结
  known_limitations:
  - 当前架构假设单实例部署，多实例场景下审计日志需要额外同步机制
  - 旁路检测基于请求特征分析，无法100%防止恶意绕过
  - SSOT Registry 一致性检查会增加单次请求处理延迟 (~50-100ms)
