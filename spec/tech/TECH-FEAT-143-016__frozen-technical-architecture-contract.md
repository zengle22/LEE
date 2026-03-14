---
id: TECH-FEAT-143-016
ssot_type: tech
title: QA 执行入口规范化技术架构
status: frozen
version: v1
parent_id: FEAT-143
derived_from_ids:
  - FEAT-143
source_refs:
  - FEAT-143#Acceptance
owner: architect
tags: []
properties:
  contract_key: tech
  identity_kind: ssot
  contract_type: frozen-technical-architecture
  contract_version: "v1.0"
  contract_id: FTA-20260313-001
  is_frozen: true
  feat_ref: FEAT-143
  frozen_by: architect
  approvers:
    - architect
frozen_at: "2026-03-13T00:00:00+08:00"
---

architecture_decisions:
  tech_stack:
    # 基础层 - 与现有 LEE 框架保持一致
    - layer: 运行时
      technology: Python 3.8+ (现有)
      reasoning: |
        与 LEE 框架现有技术栈保持一致，pyproject.toml 已定义 requires-python = ">=3.8"
        无需额外运行时依赖，所有现有模块均兼容

    - layer: 数据模型
      technology: 原生 dataclass + TypedDict (现有)
      reasoning: |
        现有代码使用 ArtifactMetadata 和 models.py 中的类型定义
        采用原生 Python 类型系统，避免引入 pydantic 造成的依赖冲突
        与现有 SSOT 对象模型 (types.py) 保持一致

    - layer: API/CLI 框架
      technology: Click (现有) + aiohttp (现有)
      reasoning: |
        pyproject.toml 已包含 click>=8.1 和 aiohttp>=3.9
        现有 CLI 入口 (lee.cli.commands.qa.test_plan) 已使用 Click
        无需引入 FastAPI，避免与现有架构风格不一致

    - layer: 日志格式
      technology: Python logging + JSON 结构化 (可选)
      reasoning: |
        现有证据收集器 (evidence_collector.py) 已定义日志收集模式
        审计日志采用 NDJSON 格式，便于后续分析处理
        与现有执行日志格式保持一致

    - layer: 存储
      technology: aiosqlite (现有) + 文件系统 (现有)
      reasoning: |
        pyproject.toml 已包含 aiosqlite>=0.19
        ArtifactManager 已使用 SQLite 作为 Registry 后端
        审计日志采用双写策略：SQLite (查询) + NDJSON 文件 (归档)

    - layer: 配置管理
      technology: PyYAML (现有) + 环境变量
      reasoning: |
        pyproject.toml 已包含 pyyaml>=6.0
        与现有配置体系 (template_engine.py, config.py) 一致
        支持环境变量覆盖，便于 CI/CD 集成

  core_components:
    # 组件 1: Entry Router (执行入口路由)
    - name: QAEntryRouter
      responsibilities: |
        接收并路由所有 QA 执行请求，强制执行 entry contract：
        1. 解析 ExecutionRequest，提取 task_ref
        2. 验证 task_ref 格式有效性 (TASK-TESTPLAN-REL-*-*)
        3. 拒绝无 task_ref 或格式无效的请求 (返回 QA-ENTRY-001/002)
        4. 将请求转发至 ChainValidator 进行链路校验
        5. 记录入口来源 (CLI/API/UI) 用于审计
      dependencies:
        - ChainValidator
        - AuditLogger
        - SSOTType (types.py)
      interface: |
        class QAEntryRouter:
            async def route(self, request: ExecutionRequest) -> ExecutionResponse
            def validate_task_ref_format(self, task_ref: str) -> bool
      placement: src/lee/orchestrator/execution/qa/entry_router.py

    # 组件 2: Chain Validator (链路校验器)
    - name: ChainValidator
      responsibilities: |
        校验 RELEASE->TESTPLAN->TASK 链路完整性：
        - RULE-001: task_ref 存在于 SSOT Registry
        - RULE-002: task.parent_id 必须为 TESTPLAN
        - RULE-003: testplan.parent_id 必须为 RELEASE
        - RULE-004: release 状态为 active/frozen
        - RULE-005: testplan 状态为 committed/in_progress
        - RULE-006: task 状态为 todo/doing (非 blocked/dropped)
        - RULE-007: derived_from_ids 包含有效的 FEAT/TESTSET 引用
      dependencies:
        - SSOTService (ssot_service.py)
        - SSOTValidator (ssot_service.py)
        - ArtifactRegistry (registry.py)
      interface: |
        class ChainValidator:
            async def validate_chain(
                self,
                task_ref: str
            ) -> ChainValidationResult
      placement: src/lee/orchestrator/execution/qa/chain_validator.py

    # 组件 3: Registry Validator (注册表校验器)
    - name: RegistryValidator
      responsibilities: |
        与 SSOT Registry 集成校验实体存在性和归属关系：
        1. 通过 ArtifactManager 验证 task 存在
        2. 验证 task.parent_id 指向有效的 TESTPLAN
        3. 验证 TESTPLAN.parent_id 指向有效的 RELEASE
        4. 验证 RELEASE.derived_from_ids 包含 task 关联的 FEAT
        5. 校验父对象状态机的合法性
      dependencies:
        - ArtifactManager (manager.py)
        - ArtifactRegistry (registry.py)
        - SSOTType (types.py)
      interface: |
        class RegistryValidator:
            def validate_task_exists(self, task_ref: str) -> bool
            def validate_task_in_testplan(self, task_ref: str) -> bool
            def validate_testplan_in_release(self, testplan_ref: str) -> bool
            def validate_release_status(self, release_ref: str) -> bool
      placement: src/lee/orchestrator/execution/qa/registry_validator.py

    # 组件 4: Audit Logger (审计日志)
    - name: AuditLogger
      responsibilities: |
        记录所有执行请求的审计信息：
        1. 入口来源 (CLI/API/UI)
        2. 完整路径链 (release_ref -> testplan_ref -> task_ref)
        3. 时间戳 (ISO 8601 UTC)
        4. 操作用户/上下文 (从 execution context 获取)
        5. 校验结果 (通过/失败 + 错误码)
        6. 请求元数据 (session_id, run_id 等)
        格式：双写策略 - SQLite + NDJSON 文件
      dependencies:
        - aiosqlite
        - evidence_collector.py
        - Python logging
      interface: |
        class AuditLogger:
            async def log_execution_request(
                self,
                entry: AuditEntry
            ) -> None
            async def query_by_task(
                self,
                task_ref: str
            ) -> List[AuditEntry]
            async def query_by_release(
                self,
                release_ref: str
            ) -> List[AuditEntry]
      placement: src/lee/orchestrator/execution/qa/audit_logger.py

    # 组件 5: Enforcement Engine (旁路阻断引擎)
    - name: EnforcementEngine
      responsibilities: |
        阻断非标准入口请求：
        1. 检测 bypass 尝试 (无 task_ref、伪造路径等)
        2. 返回标准错误响应 (QA-ENTRY-{001-999} 错误码)
        3. 强制记录阻断审计日志
        4. 支持模式：STRICT (阻断) / AUDIT (仅记录)
        5. 与现有 Gate Engine (gate_engine.py) 集成
      dependencies:
        - QAEntryRouter
        - AuditLogger
        - GateEngine (gate_engine.py)
      interface: |
        class EnforcementEngine:
            def check_bypass_attempt(
                self,
                request: ExecutionRequest
            ) -> Optional[BypassDetection]
            async def enforce(
                self,
                detection: BypassDetection
            ) -> ExecutionResponse
      placement: src/lee/orchestrator/execution/qa/enforcement_engine.py

    # 组件 6: CLI Integration (CLI 集成层)
    - name: QAExecutionCLI
      responsibilities: |
        提供 Click CLI 命令供用户触发执行：
        - lee qa execute <task_ref> - 触发执行 (带校验)
        - lee qa validate <task_ref> - 仅校验不执行
        - lee qa status <task_ref> - 查询执行状态
        - lee qa audit <task_ref> - 查询审计日志
        - lee qa release-check <release_ref> - Release Gate 检查
      dependencies:
        - Click (click>=8.1)
        - QAEntryRouter
        - ChainValidator
        - AuditLogger
      interface: |
        @click.group()
        def qa(): ...

        @qa.command()
        @click.argument('task_ref')
        def execute(task_ref): ...
      placement: src/lee/cli/commands/qa/execution.py

    # 组件 7: Execution Run (执行运行对象)
    - name: ExecutionRun
      responsibilities: |
        封装单次执行的完整上下文：
        1. run_id (UUID v4 或现有 ID 生成规则)
        2. task_ref, testplan_ref, release_ref
        3. 执行状态 (pending/validating/ready/running/completed/failed)
        4. 审计日志引用
        5. 时间戳 (created_at, started_at, completed_at)
        6. 与现有 Execution Context 集成
      dependencies:
        - models.py (ArtifactMetadata)
        - types.py (ArtifactStatus)
      interface: |
        class ExecutionRun:
            run_id: str
            task_ref: str
            status: ExecutionStatus
            created_at: datetime
      placement: src/lee/orchestrator/execution/qa/models.py

  data_models:
    - name: ExecutionRequest
      schema: |
        @dataclass
        class ExecutionRequest:
            task_ref: str                    # 必需：TASK-TESTPLAN-REL-*-*
            triggered_by: str                # 操作用户/系统标识
            entry_source: EntrySource        # CLI | API | UI
            session_id: Optional[str]        # 会话 ID
            metadata: Dict[str, Any]         # 扩展元数据

    - name: ExecutionResponse
      schema: |
        @dataclass
        class ExecutionResponse:
            success: bool
            run_id: Optional[str]
            status: str                      # ExecutionStatus 值
            error_code: Optional[str]        # QA-ENTRY-001 等
            error_message: Optional[str]
            audit_log_ref: Optional[str]     # 审计日志引用
            validation_result: Optional[ChainValidationResult]

    - name: AuditEntry
      schema: |
        @dataclass
        class AuditEntry:
            entry_id: str                    # AUDIT-* 或 UUID
            timestamp: datetime              # UTC ISO 8601
            entry_source: str                # CLI | API | UI
            task_ref: str
            testplan_ref: Optional[str]
            release_ref: Optional[str]
            triggered_by: str
            action: str                      # EXECUTE | VALIDATE | BYPASS_ATTEMPT
            result: str                      # SUCCESS | FAILURE | BLOCKED
            error_code: Optional[str]
            client_info: Dict[str, str]      # session_id, user_agent 等

    - name: ChainValidationResult
      schema: |
        @dataclass
        class ChainValidationResult:
            passed: bool
            task_exists: bool
            testplan_exists: bool
            release_exists: bool
            task_status_valid: bool
            testplan_status_valid: bool
            release_status_valid: bool
            errors: List[str]

  error_codes:
    - code: QA-ENTRY-001
      description: MISSING_TASK_REF
      message: "执行请求缺少必需的 task_ref 参数"

    - code: QA-ENTRY-002
      description: INVALID_TASK_REF_FORMAT
      message: "task_ref 格式无效，应为 TASK-TESTPLAN-REL-{semver}-*"

    - code: QA-ENTRY-003
      description: TASK_NOT_FOUND
      message: "指定的 task 在 SSOT Registry 中不存在"

    - code: QA-ENTRY-004
      description: TASK_PARENT_INVALID
      message: "task 的 parent_id 不指向有效的 TESTPLAN"

    - code: QA-ENTRY-005
      description: TESTPLAN_NOT_FOUND
      message: "TESTPLAN 在 SSOT Registry 中不存在"

    - code: QA-ENTRY-006
      description: TESTPLAN_PARENT_INVALID
      message: "testplan 的 parent_id 不指向有效的 RELEASE"

    - code: QA-ENTRY-007
      description: RELEASE_NOT_FOUND
      message: "RELEASE 在 SSOT Registry 中不存在"

    - code: QA-ENTRY-008
      description: RELEASE_STATUS_INVALID
      message: "RELEASE 状态不满足执行条件 (需 active/frozen)"

    - code: QA-ENTRY-009
      description: TESTPLAN_STATUS_INVALID
      message: "TESTPLAN 状态不满足执行条件 (需 committed/in_progress)"

    - code: QA-ENTRY-010
      description: TASK_STATUS_INVALID
      message: "TASK 状态不满足执行条件 (非 blocked/dropped)"

    - code: QA-ENTRY-011
      description: BYPASS_ATTEMPT_DETECTED
      message: "检测到旁路执行尝试，请求已阻断"

    - code: QA-ENTRY-012
      description: AUDIT_LOG_FAILURE
      message: "审计日志记录失败"

risk_management:
  high_risk_points:
    # 风险 1: 性能瓶颈
    - description: |
        ChainValidator 每次执行需读取多个 SSOT 对象进行校验，
        高并发场景下可能导致 Registry I/O 瓶颈和响应延迟。
      severity: HIGH
      probability: MEDIUM
      mitigation_plan: |
        1. 利用现有 ArtifactRegistry 的内存缓存层
        2. 使用 asyncio.gather 并行读取多个对象
        3. 关键路径校验结果缓存 (task_ref -> validation_result, TTL=60s)
        4. 添加性能指标采集 (现有 tracing/span_builder.py)
      degradation_strategy: |
        启用 DEGRADED 模式：跳过非关键校验 (RULE-006 状态检查)，
        仅校验 task 存在性和归属关系，确保核心功能可用。

    # 风险 2: 审计日志丢失
    - description: |
        审计日志写入失败 (磁盘满、权限问题、SQLite 锁) 导致执行记录缺失，
        违反 ADR-001 定义的合规要求。
      severity: CRITICAL
      probability: LOW
      mitigation_plan: |
        1. 双写策略：同时写入 SQLite 和 NDJSON 文件
        2. 写入失败时抛出异常，阻断执行 (fail-secure)
        3. 监控磁盘空间，阈值告警 (< 10% 时通知)
        4. 定期归档旧日志 (> 90 天)，复用现有 cleanup.py
      degradation_strategy: |
        紧急模式下可切换至内存缓冲区，
        待存储恢复后批量写入，但需告警通知。

    # 风险 3: SSOT Registry 不一致
    - description: |
        SSOT Registry 与磁盘上的 front matter 文件不一致 (手动修改、同步延迟)，
        导致校验结果错误。
      severity: HIGH
      probability: MEDIUM
      mitigation_plan: |
        1. 利用现有 ssot_files.py 的文件变更监听
        2. 校验前检查 registry 与文件的哈希一致性
        3. 定期一致性检查任务 (每日)
        4. Git 版本追踪，可回滚至已知良好状态
      degradation_strategy: |
        检测到不一致时切换至只读模式，
        禁止新执行直到人工确认修复。

    # 风险 4: 旁路绕过
    - description: |
        攻击者尝试绕过 QAEntryRouter 直接调用底层执行接口，
        绕过 SSOT 校验。
      severity: HIGH
      probability: LOW
      mitigation_plan: |
        1. EnforcementEngine 在多个层级部署 (CLI、API、Runner)
        2. 所有执行入口统一通过 QAEntryRouter
        3. 行为分析检测异常模式 (频率、来源 session)
        4. 定期安全审计日志
      degradation_strategy: |
        检测到攻击时切换至 LOCKDOWN 模式，
        仅允许白名单 session_id 访问。

    # 风险 5: 与现有 SSOT 类型系统集成风险
    - description: |
        新增的 QA 执行入口组件需要与现有 SSOTType/SSOTValidator/SSOTService
        深度集成，可能暴露出未预见的类型系统边界情况。
      severity: MEDIUM
      probability: HIGH
      mitigation_plan: |
        1. 复用现有 SSOTService 的 release_check / validate 方法
        2. 在 ssot_service.py 中新增 QA 专用校验方法，不修改核心逻辑
        3. 与 types.py 中的 SSOTType 枚举保持一致
        4. 在 ssot_contract.py 中增加 QA 执行上下文支持
      degradation_strategy: |
        若集成出现问题，可暂时使用简化的文件读取模式，
        直接读取 spec/ 目录下的 front matter 文件进行校验。

  backup_plans:
    - scenario: Registry 缓存失效
      primary: ArtifactRegistry 内存缓存 (现有)
      backup: 直接文件读取 (ssot_files.py)
      fallback: 简化校验 (仅检查 task 存在性)

    - scenario: SQLite 不可用
      primary: SQLite (本地，aiosqlite)
      backup: NDJSON 文件日志
      fallback: 标准 Python logging

    - scenario: CLI 集成阻塞
      primary: Click CLI (现有)
      backup: 直接调用 Python API
      fallback: 手动文件检查脚本

    - scenario: SSOT Registry 格式变更
      primary: front matter 解析 (现有)
      backup: JSON 解析 (双格式支持)
      fallback: 内存硬编码 (紧急修复模式)

dependencies:
  core:
    - name: Python
      version: ">=3.8"
      type: runtime

  existing:
    - name: aiosqlite
      version: ">=0.19"
      type: library
      usage: 审计日志 SQLite 存储

    - name: aiohttp
      version: ">=3.9"
      type: library
      usage: 异步 HTTP (可选 API 层)

    - name: PyYAML
      version: ">=6.0"
      type: library
      usage: SSOT front matter 解析

    - name: click
      version: ">=8.1"
      type: library
      usage: CLI 命令入口

    - name: jinja2
      version: ">=3.1"
      type: library
      usage: 模板渲染 (可选)

    - name: jsonschema
      version: ">=4.0"
      type: library
      usage: Schema 校验 (可选)

  new_additions: []  # 无需新增依赖

implementation_phases:
  phase_1:
    name: 核心校验层
    components:
      - RegistryValidator
      - ChainValidator
      - QAEntryRouter (基础版)
      - AuditLogger (基础版 - SQLite 单写 + NDJSON 文件双写)
    duration: "3-5 天"
    deliverables:
      - src/lee/orchestrator/execution/qa/registry_validator.py
      - src/lee/orchestrator/execution/qa/chain_validator.py
      - src/lee/orchestrator/execution/qa/entry_router.py
      - src/lee/orchestrator/execution/qa/audit_logger.py
      - src/lee/orchestrator/execution/qa/models.py

  phase_2:
    name: 集成层
    components:
      - QAExecutionCLI (Click 命令)
      - EnforcementEngine
      - 与现有 test_plan.py 集成
    duration: "2-3 天"
    deliverables:
      - src/lee/orchestrator/execution/qa/enforcement_engine.py
      - src/lee/cli/commands/qa/execution.py

  phase_3:
    name: 强化层
    components:
      - 缓存层优化
      - 监控告警集成
      - 完整测试覆盖
    duration: "2-3 天"
    deliverables:
      - tests/qa/test_entry_router.py
      - tests/qa/test_chain_validator.py
      - tests/qa/test_audit_logger.py
      - tests/qa/test_enforcement_engine.py

integration_points:
  - name: SSOTService
    type: existing
    location: src/lee/orchestrator/execution/artifacts/ssot_service.py
    description: 复用 release_check / validate / derive_plans 方法

  - name: SSOTValidator
    type: existing
    location: src/lee/orchestrator/execution/artifacts/ssot_service.py
    description: 复用 P0/P1 校验规则

  - name: ArtifactManager
    type: existing
    location: src/lee/orchestrator/execution/artifacts/manager.py
    description: SSOT 对象物化与查询

  - name: ArtifactRegistry
    type: existing
    location: src/lee/orchestrator/execution/artifacts/registry.py
    description: Registry 索引与关系查询

  - name: SSOTType
    type: existing
    location: src/lee/orchestrator/execution/artifacts/types.py
    description: SSOT 对象类型枚举

  - name: GateEngine
    type: existing
    location: src/lee/orchestrator/execution/gate_engine.py
    description: Gate 判定集成

  - name: EvidenceCollector
    type: existing
    location: src/lee/orchestrator/evidence_collector.py
    description: 审计日志与证据收集集成

  - name: CLI QA Commands
    type: existing
    location: src/lee/cli/commands/qa/test_plan.py
    description: 扩展现有 QA CLI 命令

frozen_scope:
  in_scope:
    - QAEntryRouter 契约定义与实现
    - ChainValidator 七项规则实现 (RULE-001 ~ RULE-007)
    - RegistryValidator SSOT 集成
    - AuditLogger 双写策略 (SQLite + NDJSON)
    - EnforcementEngine 旁路阻断
    - QAExecutionCLI 四项端点
    - ExecutionRun 状态管理
    - 与现有 SSOTService/SSOTValidator 集成

  out_of_scope:
    - 测试执行引擎内部逻辑修改
    - Runner 实现替换
    - 具体测试用例内容修改
    - 测试结果判定逻辑修改
    - 前端 UI 组件具体设计
    - 用户认证授权系统 (复用现有)
    - Task Brief / Context Bundle 生成 (现有 artifact 系统负责)

verification_criteria:
  - 所有组件通过单元测试 (覆盖率 > 80%)
  - 集成测试通过 (CLI 端到端)
  - 性能测试通过 (100 QPS 下响应 < 100ms)
  - 安全审查通过 (无旁路漏洞)
  - 架构评审通过 (人类核准)
  - 与 ADR-001 / ADR-007 / ADR-008 一致性验证通过

---
# Architecture Diagram
#
#  ┌─────────────────────────────────────────────────────────────────┐
#  │                        Client Layer                              │
#  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                      │
#  │  │ CLI      │  │ API      │  │ UI       │                      │
#  │  │ (Click)  │  │ (aiohttp)│  │ (Future) │                      │
#  │  └────┬─────┘  └────┬─────┘  └────┬─────┘                      │
#  └───────┼─────────────┼─────────────┼────────────────────────────┘
#          │             │             │
#          └─────────────┼─────────────┘
#                        ▼
#  ┌─────────────────────────────────────────────────────────────────┐
#  │                    QA Entry Router Layer                         │
#  │  ┌─────────────────────────────────────────────────────────┐    │
#  │  │ QAEntryRouter                                           │    │
#  │  │  - Parse ExecutionRequest                               │    │
#  │  │  - Validate task_ref format                             │    │
#  │  │  - Reject invalid requests (QA-ENTRY-001/002)           │    │
#  │  └────────────────────┬────────────────────────────────────┘    │
#  └───────────────────────┼─────────────────────────────────────────┘
#                          │
#          ┌───────────────┼───────────────┐
#          ▼               ▼               ▼
#  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
#  │ Chain        │ │ Registry     │ │ Enforcement  │
#  │ Validator    │ │ Validator    │ │ Engine       │
#  │ ───────────  │ │ ───────────  │ │ ───────────  │
#  │ RULE-001     │ │ Task exists  │ │ Bypass       │
#  │ RULE-002     │ │ Task->Plan   │ │ detection    │
#  │ RULE-003     │ │ Plan->Rel    │ │ Blocking     │
#  │ RULE-004     │ │ Rel status   │ │              │
#  │ RULE-005     │ │ Plan status  │ │              │
#  │ RULE-006     │ │ Task status  │ │              │
#  │ RULE-007     │ │ FEAT/TESTSET │ │              │
#  └──────┬───────┘ └──────┬───────┘ └──────┬───────┘
#         │                │                │
#         └────────────────┼────────────────┘
#                          │
#                          ▼
#  ┌─────────────────────────────────────────────────────────────────┐
#  │                      Audit Logger Layer                          │
#  │  ┌─────────────────────────────────────────────────────────┐    │
#  │  │ AuditLogger                                             │    │
#  │  │  - Dual write: SQLite + NDJSON                          │    │
#  │  │  - Query interface                                      │    │
#  │  │  - Evidence integration                                 │    │
#  │  └─────────────────────────────────────────────────────────┘    │
#  └─────────────────────────────────────────────────────────────────┘
#                          │
#                          ▼
#  ┌─────────────────────────────────────────────────────────────────┐
#  │                    Existing SSOT Infrastructure                  │
#  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
#  │  │ SSOTService  │ │ SSOTValidator│ │ ArtifactMgr  │            │
#  │  └──────────────┘ └──────────────┘ └──────────────┘            │
#  └─────────────────────────────────────────────────────────────────┘
#                          │
#          ┌───────────────┴───────────────┐
#          ▼                               ▼
#  ┌──────────────────────┐    ┌──────────────────────┐
#  │   SSOT Registry      │    │   Audit Storage      │
#  │   (SQLite + files)   │    │   (SQLite + NDJSON)  │
#  └──────────────────────┘    └──────────────────────┘
