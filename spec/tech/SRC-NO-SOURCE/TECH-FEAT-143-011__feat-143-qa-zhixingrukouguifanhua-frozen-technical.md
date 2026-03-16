---
id: TECH-FEAT-143-011
ssot_type: tech
title: FEAT-143 QA 执行入口规范化 - Frozen Technical Architecture
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
  contract_id: FTA-20260313-001
  status: FROZEN
  is_frozen: true
  frozen_at: '2026-03-13T00:00:00+08:00'
workflow_instance_id: wf-tech-feat-143-011__feat-143-qa-zhixingrukouguifanhua-frozen-technical-20260316
  feature_id: FEAT-143
  title: FEAT-143 QA 执行入口规范化 - Frozen Technical Architecture
  owner: architect
  source_refs:
  - FEAT-143
  - ADR-001
  - ADR-007
  - TECH-FEAT-143-009
architecture_decisions:
  tech_stack:
  - layer: data_model
    technology: Python dataclass + Pydantic v2
    reasoning: 利用 Python 原生 dataclass 定义 ExecutionRequest/Response 模型，确保类型安全和 IDE
      支持，Pydantic 用于外部参数验证
  - layer: persistence
    technology: SQLite + aiosqlite (WAL mode)
    reasoning: 审计日志需要支持并发写入和快速查询，SQLite 零配置、单文件，WAL 模式提供并发能力，aiosqlite 提供异步支持
  - layer: ssot_integration
    technology: ArtifactManager + SSOTService
    reasoning: 复用现有 SSOT 基础设施，通过 ArtifactManager 读取 front matter 文件，SSOTService 提供校验和查询服务
  - layer: caching
    technology: LRU Cache (60s TTL)
    reasoning: 减少重复 SSOT 对象查询，60 秒 TTL 平衡一致性与性能，惰性更新避免主动刷新开销
  - layer: cli_framework
    technology: Click
    reasoning: 项目现有 CLI 框架，提供命令注册、参数解析、错误处理能力
  - layer: async_runtime
    technology: asyncio
    reasoning: 支持并发 SSOT 查询、异步审计写入、非阻塞 CLI 响应
  core_components:
  - name: EntryRouter
    responsibilities: 执行入口路由的核心接口，接收 ExecutionRequest，协调 BypassBlocker 和 ChainValidator
      进行校验，路由到合法执行路径或返回错误
    dependencies:
    - BypassBlocker
    - ChainValidator
    - AuditLogger
    - ArtifactManager
    interface:
      methods:
      - 'async route(request: ExecutionRequest) -> ExecutionResult'
      - 'async validate_entry(task_ref: str) -> ValidationResult'
      - 'async resolve_task(task_ref: str) -> Optional[TASK]'
      input_schema: ExecutionRequest (dataclass)
      output_schema: ExecutionResult (dataclass)
  - name: BypassBlocker
    responsibilities: 检测和阻断旁路执行请求，识别无 task_ref 的直接调用、task 不归属 TESTPLAN、TESTPLAN 不归属
      RELEASE 等旁路场景
    dependencies:
    - ArtifactManager
    - SSOTService
    - AuditLogger
    bypass_detection_rules:
    - 'BYPASS-001: 无 task_ref 的直接调用'
    - 'BYPASS-002: task 不归属 TESTPLAN (task.parent_id 不是 TESTPLAN 类型)'
    - 'BYPASS-003: TESTPLAN 不归属 RELEASE (testplan.parent_id 不是 RELEASE 类型)'
    error_codes:
    - 'ERR-BYPASS-001: 旁路执行请求被阻断'
  - name: ChainValidator
    responsibilities: 验证 RELEASE->TESTPLAN->TASK 执行路径的完整性，按渐进式顺序 (task->plan->release)
      逐级校验并提供清晰错误定位
    dependencies:
    - ArtifactManager
    - SSOTService
    - LRU Cache
    validation_rules:
    - 'CHAIN-001: TASK 存在且 parent_id 指向有效 TESTPLAN'
    - 'CHAIN-002: TESTPLAN 存在且 parent_id 指向有效 RELEASE'
    - 'CHAIN-003: RELEASE 状态有效 (scope_frozen/in_dev/in_test)'
    error_codes:
    - 'ERR-CHAIN-001: TASK 不归属有效 TESTPLAN'
    - 'ERR-CHAIN-002: TESTPLAN 不归属有效 RELEASE'
    - 'ERR-CHAIN-003: RELEASE 状态无效'
    cache_strategy:
      ttl_seconds: 60
      update_policy: lazy
      max_size: 1000
  - name: AuditLogger
    responsibilities: 记录每次执行请求的审计日志，包含 SSOT 三轴绑定信息 (业务轴/交付轴/执行轴)，支持双写机制 (内存队列 + 磁盘
      WAL) 确保审计不丢失
    dependencies:
    - aiosqlite
    - asyncio.Queue
    log_schema:
      fields:
      - 'run_id: str (执行实例 ID)'
      - 'task_id: str'
      - 'testplan_id: str'
      - 'release_id: str'
      - 'feat_id: str'
      - 'feat_version: str'
      - 'entry_source: str (cli/workflow/api)'
      - 'path_chain: List[str] (TASK/TESTPLAN/RELEASE ID 链)'
      - 'executed_at: datetime'
      - 'executor: str'
      - 'exit_code: int (可选)'
      - 'error_code: str (可选)'
      storage: SQLite + WAL mode
      write_policy: async_dual_write
    dual_write_mechanism:
      memory_queue: asyncio.Queue(maxsize=1000)
      background_writer: async task with exponential backoff
      retry_policy:
        max_retries: 3
        initial_backoff: 100ms
        backoff_factor: 2
        max_backoff: 1s
      fallback: sync write + warning
  - name: CLI Executor (lee qa execute)
    responsibilities: 实现 lee qa execute 命令，集成 EntryRouter/BypassBlocker/ChainValidator/AuditLogger，提供
      5 阶段反馈模型
    dependencies:
    - Click
    - EntryRouter
    - AuditLogger
    command: lee qa execute [OPTIONS]
    options:
    - --task-ref TEXT (必需)
    - --plan-ref TEXT (可选)
    - --release-ref TEXT (可选)
    - --validate-only (仅校验)
    - --json (JSON 输出)
    - --verbose (详细输出)
    feedback_model:
    - '[1/5] 入口校验'
    - '[2/5] 旁路检测'
    - '[3/5] 链路校验'
    - '[4/5] 执行准备'
    - '[5/5] 执行启动'
    exit_codes:
    - '0: 成功'
    - '1: 入口校验失败'
    - '2: 链路校验失败'
    - '3: 旁路阻断'
    - '4: 执行失败'
    - '5: 内部错误'
risk_management:
  high_risk_points:
  - risk_id: R-001
    description: SSOT Registry 与磁盘 front matter 不一致风险
    impact: 校验基于过期数据，导致错误判定
    probability: medium
    mitigation_plan:
    - 执行前强制 sync：检查 Registry 生成时间与文件修改时间
    - 惰性更新：检测到文件变更时自动重新读取
    - 降级策略：Registry 不可用时降级到直接读取 front matter 文件
    degradation_strategy: 若 Registry 不一致或不可用，降级为直接读取 front matter 文件进行校验，牺牲性能换取正确性
    backup_solution:
      trigger: Registry is_fresh() 返回 false 或抛出异常
      fallback: await ssot_files.read_front_matter(ssot_id)
  - risk_id: R-002
    description: 旁路检测不完备风险
    impact: 可能存在未覆盖的旁路入口，导致部分执行请求绕过 EntryRouter
    probability: low
    mitigation_plan:
    - 所有执行 API 统一通过 BypassBlocker 中间件
    - 实现 API 调用链追踪，检测直接调用底层执行接口的行为
    - 定期审计分析，识别异常执行模式
    degradation_strategy: 发现新的旁路入口时，立即更新 BypassBlocker 规则并重新审计历史请求
  - risk_id: R-003
    description: 高并发下内存队列溢出风险
    impact: 审计日志丢失
    probability: low
    mitigation_plan:
    - 限制队列大小 (maxsize=1000)
    - 后台异步写入器带指数退避重试
    - 监控队列长度，超过阈值告警
    degradation_strategy: 若队列溢出，降级为同步写入 + 告警日志，不阻塞主流程
    backup_solution:
      trigger: asyncio.QueueFull exception
      fallback: await self._write_directly(entry) + logger.warning()
  - risk_id: R-004
    description: SQLite WAL 模式在 Windows 上的兼容性风险
    impact: 审计日志写入失败
    probability: low
    mitigation_plan:
    - 充分测试 WAL 模式在 Windows 上的行为
    - 捕获 WAL 初始化异常
    - 监控 WAL 写入失败率
    degradation_strategy: 若 WAL 模式失败，降级到 DELETE 模式并记录警告
    backup_solution:
      trigger: aiosqlite.Error during PRAGMA journal_mode=WAL
      fallback: await self.conn.execute('PRAGMA journal_mode=DELETE')
  - risk_id: R-005
    description: LRU 缓存不一致风险
    impact: 校验基于过期的 SSOT 对象
    probability: medium
    mitigation_plan:
    - 60 秒 TTL 平衡一致性与性能
    - 惰性更新策略
    - 关键操作前强制刷新缓存
    degradation_strategy: 若缓存命中率持续低，增加缓存 TTL 或预加载热点对象
  - risk_id: R-006
    description: 与现有执行引擎集成风险
    impact: 集成失败导致功能不可用
    probability: low
    mitigation_plan:
    - EntryRouter 仅作为前置校验层，不替换现有执行引擎
    - 保持 ExecutionRequest/Response 与现有接口的兼容性
    - 提供 feature flag 控制入口规范化开关
    degradation_strategy: 集成出现问题时，可通过 feature flag 临时关闭入口校验，回到原有执行模式
frozen_declaration:
  frozen_at: '2026-03-13T00:00:00+08:00'
  frozen_by: architect
  review_status: pending_human_approval
  change_policy: 本架构文档已进入 FROZEN 状态，后续变更需走架构变更审批流程：1.提交变更申请 2.影响分析 3.架构评审 4.更新版本号
    5.重新冻结
  known_limitations:
  - 当前架构假设单实例部署，多实例场景下审计日志需要额外同步机制
  - 旁路检测基于请求特征分析，无法 100% 防止恶意绕过
  - SSOT Registry 一致性检查会增加单次请求处理延迟 (~50-100ms)
  - SQLite 并发写入性能有限，通过双写机制和 WAL 模式缓解
  architecture_decision_records:
  - id: D-001
    decision: 采用 SQLite + aiosqlite 作为审计存储
    reason: 轻量、无需额外服务、异步支持、WAL 模式提供并发能力
  - id: D-002
    decision: 双写机制 (内存队列 + 磁盘 WAL)
    reason: 防止审计丢失，平衡性能与可靠性
  - id: D-003
    decision: 渐进式链路校验 (task->plan->release)
    reason: 清晰的错误定位，便于调试，与 ADR-001 交付链语义一致
  - id: D-004
    decision: LRU 缓存策略 (60 秒 TTL)
    reason: 平衡一致性与性能，减少重复 SSOT 对象查询
  - id: D-005
    decision: CLI 5 阶段反馈模型
    reason: 与现有 QA Test Set Execute L3 workflow 一致，提供清晰进度反馈
  - id: D-006
    decision: SSOT 三轴绑定审计模型
    reason: 遵循 ADR-001 三轴模型，确保审计记录可追溯到业务/交付/执行全链路
