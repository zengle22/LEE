---
id: TECH-FEAT-084-001
ssot_type: tech
title: Workflow Template 与 Runtime Instance 边界定义 - 技术架构
status: frozen
version: v1
parent_id: FEAT-084
derived_from_ids:
- ADR-009
source_refs:
- FEAT-084#scope
- FEAT-084#acceptance
owner: dev
tags:
- tech
- workflow
- template
- runtime
properties:
  contract_key: tech_spec
  identity_kind: ssot
---

# Workflow Template 与 Runtime Instance 边界定义 - 技术架构

contract_type: frozen-technical-architecture
contract_version: '1.0'
metadata:
  contract_id: FTA-20260312-084
  status: FROZEN
  is_frozen: true
  frozen_at: '2026-03-12T20:00:00Z'
workflow_instance_id: wf-tech-feat-084-001__tech-design-20260316
  source_feats:
  - FEAT-084
  parent_epic: EPIC-003
  governing_adrs: []
architecture_decisions:
  tech_stack:
  - layer: Storage - Template
    technology: YAML Filesystem (templates/ directory)
    reasoning: 模板定义为静态配置，YAML 格式便于人工阅读和版本控制。文件系统存储支持原子性更新，符合 GitOps 理念。
  - layer: Storage - Instance
    technology: SQLite + Artifact Filesystem
    reasoning: 实例运行为动态状态，SQLite 提供 ACID 保证和高效查询。Artifacts 目录存储实例运行时产生的文件，与现有 LEE 证据系统保持一致。
  - layer: CLI Framework
    technology: Python Click
    reasoning: Click 是成熟的 Python CLI 框架，支持命令分组、参数解析、帮助文档自动生成。与现有 LEE CLI 架构保持一致。
  - layer: Output Formatting
    technology: Rich (table) + PyYAML/JSON (structured)
    reasoning: Rich 库提供美观的表格输出和颜色编码，提升用户体验。PyYAML 和内置 JSON 支持结构化输出，便于脚本集成。
  - layer: Version Management
    technology: Semantic Versioning 2.0.0
    reasoning: 语义化版本规范业界通用，支持版本比较、兼容性判断和升级策略制定。
  - layer: Concurrency Control
    technology: SQLite WAL Mode + File Lock
    reasoning: SQLite WAL 模式支持读写并发，文件锁防止多进程模板文件竞争。符合 ADR-009 并发控制规范。
  core_components:
  - name: TemplateStore
    responsibilities: 管理 templates/ 目录的 YAML 文件读写，支持模板元数据解析(name, version, description,
      steps)。提供模板文件的 CRUD 操作和列表查询。
    dependencies:
    - PyYAML
    - pathlib
    - fsspec
    implements_feat:
    - FEAT-084
    implements_task:
    - TASK-FEAT-084-001
  - name: InstanceStore
    responsibilities: 实现 SQLite workflow_instances 表操作，支持实例 CRUD 和状态查询。管理实例与模板的版本关联，确保数据持久化。
    dependencies:
    - sqlite3
    - SQLAlchemy
    - alembic
    implements_feat:
    - FEAT-084
    implements_task:
    - TASK-FEAT-084-001
  - name: TemplateRegistry
    responsibilities: 模板发现、加载和缓存。支持从 templates/ 目录和内置模板加载。维护模板索引，提供快速查找和列表功能。
    dependencies:
    - TemplateStore
    - watchdog (optional)
    implements_feat:
    - FEAT-084
    implements_task:
    - TASK-FEAT-084-002
  - name: InstanceManager
    responsibilities: 运行时实例生命周期管理：创建、启动、暂停、恢复、终止。管理实例状态机，集成 concurrency_scope 控制并发执行。
    dependencies:
    - InstanceStore
    - asyncio
    - concurrency-limit
    implements_feat:
    - FEAT-084
    implements_task:
    - TASK-FEAT-084-002
  - name: VersionResolver
    responsibilities: 模板版本解析与冻结。实例创建时锁定模板版本引用，防止运行时模板升级影响。支持语义化版本比较和约束匹配。
    dependencies:
    - semantic-version
    - packaging
    implements_feat:
    - FEAT-084
    implements_task:
    - TASK-FEAT-084-002
  - name: WorkflowCliGroup
    responsibilities: lee workflow 命令组实现，包括 template list 和 instance list 子命令。处理参数解析、命令路由和退出码管理。
    dependencies:
    - Click
    - TemplateRegistry
    - InstanceManager
    implements_feat:
    - FEAT-084
    implements_task:
    - TASK-FEAT-084-003
  - name: OutputFormatter
    responsibilities: 支持 table/json/yaml 三种输出格式。实现状态颜色编码：success=绿色, running=蓝色, pending=黄色,
      error=红色。
    dependencies:
    - rich
    - PyYAML
    implements_feat:
    - FEAT-084
    implements_task:
    - TASK-FEAT-084-003
  - name: TemplateSnapshotManager
    responsibilities: 实例创建时对模板进行深拷贝快照，确保模板升级不影响运行中的实例。管理快照生命周期和清理策略。
    dependencies:
    - TemplateStore
    - InstanceStore
    implements_feat:
    - FEAT-084
    implements_task:
    - TASK-FEAT-084-002
risk_management:
  high_risk_points:
  - risk_id: RISK-084-001
    description: 模板升级时运行中实例可能受影响
    severity: High
    mitigation_plan: 实现 TemplateSnapshotManager，实例创建时对模板进行深拷贝快照。Instance 表存储 template_snapshot_path
      字段，运行时始终引用快照而非原始模板。模板升级仅影响新创建的实例。
    backup_plan: 如快照机制引入性能问题，可改用模板版本哈希引用，实例运行时通过 VersionResolver 锁定特定版本。
  - risk_id: RISK-084-002
    description: SQLite 并发写入导致数据库锁定
    severity: Medium
    mitigation_plan: 启用 SQLite WAL (Write-Ahead Logging) 模式，支持读写并发。设置 busy_timeout
      为 5000ms，自动重试锁定冲突。InstanceStore 使用连接池管理。
    backup_plan: WAL 模式仍出现锁冲突时，降级为单写多读模式，队列化写操作。
  - risk_id: RISK-084-003
    description: 模板文件系统与数据库状态不一致
    severity: Medium
    mitigation_plan: 实现两阶段提交：先写文件系统，成功后写数据库。启动时执行一致性检查，修复孤儿记录。TemplateRegistry 维护内存缓存，定期同步文件系统状态。
    backup_plan: 不一致时以文件系统为准重建数据库索引，记录警告日志供人工审查。
  - risk_id: RISK-084-004
    description: 并发实例创建超过系统资源限制
    severity: Medium
    mitigation_plan: InstanceManager 集成 concurrency_scope 控制，限制全局并发数和每模板并发数。支持队列排队和优雅降级。
    backup_plan: 达到资源上限时返回友好错误提示，引导用户等待或清理已完成实例。
  - risk_id: RISK-084-005
    description: CLI 输出格式化性能问题（大量实例）
    severity: Low
    mitigation_plan: OutputFormatter 实现分页和流式输出，限制默认显示条数（如 100 条）。支持 --limit 和 --offset
      参数，避免内存溢出。
    backup_plan: 大量数据时自动切换为纯文本输出，禁用表格格式化。
  uncertainties:
  - uncertainty_id: UNC-084-001
    description: 模板文件热重载的性能影响
    impact: 频繁模板修改可能导致 TemplateRegistry 频繁重建索引，影响性能
    resolution_plan: Phase 1 实现启动时全量加载，Phase 2 评估是否需要 watchdog 文件监控实现热重载。
    fallback: 如热重载性能不可接受，改为命令触发重载（lee workflow template refresh）。
  - uncertainty_id: UNC-084-002
    description: Instance 历史数据清理策略
    impact: 长期运行可能积累大量实例记录，影响查询性能
    resolution_plan: Phase 1 实现基础功能，Phase 2 增加归档策略：completed 实例 30 天后自动归档到历史表。
    fallback: 提供手动清理命令（lee workflow instance cleanup），由用户决定清理策略。
  - uncertainty_id: UNC-084-003
    description: 跨平台路径处理差异（Windows/Linux/macOS）
    impact: 模板路径解析可能在不同平台表现不一致
    resolution_plan: 使用 pathlib.Path 处理所有路径操作，避免硬编码路径分隔符。CI 覆盖三大平台测试。
    fallback: 发现平台兼容性问题时，针对性修复并补充测试用例。
api_contracts:
  template_list:
    command: lee workflow template list
    options:
    - name: --format
      type: choice
      choices:
      - table
      - json
      - yaml
      default: table
    - name: --filter
      type: string
      description: 按名称过滤模板
    output_schema:
      name: string
      version: string (semver)
      description: string
      updated_at: ISO8601 timestamp
      source: local | builtin
    exit_codes:
      '0': 成功
      '1': 一般错误
      '2': 配置错误
  instance_list:
    command: lee workflow instance list
    options:
    - name: --format
      type: choice
      choices:
      - table
      - json
      - yaml
      default: table
    - name: --status
      type: choice
      choices:
      - pending
      - running
      - completed
      - failed
      - all
      default: all
    - name: --template
      type: string
      description: 按模板名称过滤
    - name: --watch
      type: flag
      description: 实时刷新模式
    output_schema:
      id: string (UUID)
      template_name: string
      template_version: string
      status: pending | running | completed | failed
      started_at: ISO8601 timestamp
      duration: string (human readable)
      age: string (human readable)
    exit_codes:
      '0': 成功
      '1': 一般错误
      '4': 未找到
data_model:
  template:
    storage: YAML Files (templates/)
    filename_pattern: '{name}.v{version}.yaml'
    schema:
      name:
        type: string
        required: true
        pattern: ^[a-z0-9-]+$
      version:
        type: string
        required: true
        format: semver
      description:
        type: string
        required: false
        max_length: 200
      steps:
        type: array
        required: true
        items: step_definition
      concurrency_scope:
        type: string
        required: false
        default: global
      created_at:
        type: timestamp
        auto: true
      updated_at:
        type: timestamp
        auto: true
  workflow_instance:
    storage: SQLite (orchestrator.db)
    table: workflow_instances
    fields:
    - name: id
      type: UUID
      constraints: PRIMARY KEY
    - name: template_name
      type: VARCHAR(64)
      constraints: NOT NULL, INDEX
    - name: template_version
      type: VARCHAR(32)
      constraints: NOT NULL
    - name: template_snapshot_path
      type: VARCHAR(512)
      constraints: NOT NULL
    - name: status
      type: ENUM
      values:
      - pending
      - running
      - completed
      - failed
      - cancelled
      constraints: NOT NULL, INDEX
    - name: concurrency_scope
      type: VARCHAR(64)
      constraints: NOT NULL
    - name: context
      type: JSON
      constraints: 存储运行时参数
    - name: artifacts_path
      type: VARCHAR(512)
      constraints: NOT NULL
    - name: created_at
      type: TIMESTAMP
      constraints: DEFAULT CURRENT_TIMESTAMP, INDEX
    - name: started_at
      type: TIMESTAMP
      constraints: nullable
    - name: completed_at
      type: TIMESTAMP
      constraints: nullable
    - name: exit_code
      type: INTEGER
      constraints: nullable
    indexes:
    - idx_template_name
    - idx_status
    - idx_created_at
    - idx_status_created
delivery_plan:
  phase_1_storage:
    name: 存储层实现
    features:
    - TemplateStore
    - InstanceStore
    - 数据表结构设计
    components:
    - TemplateStore
    - InstanceStore
    estimated_effort: 3-4 days
    dependencies:
    - SQLite
    - PyYAML
    deliverable: TASK-FEAT-084-001 完成
  phase_2_runtime:
    name: 运行时管理层实现
    features:
    - TemplateRegistry
    - InstanceManager
    - VersionResolver
    - TemplateSnapshotManager
    components:
    - TemplateRegistry
    - InstanceManager
    - VersionResolver
    - TemplateSnapshotManager
    estimated_effort: 4-5 days
    dependencies:
    - Phase 1 完成
    - concurrency-limit
    deliverable: TASK-FEAT-084-002 完成
  phase_3_cli:
    name: CLI 命令层实现
    features:
    - lee workflow template list
    - lee workflow instance list
    - OutputFormatter
    components:
    - WorkflowCliGroup
    - OutputFormatter
    estimated_effort: 2-3 days
    dependencies:
    - Phase 2 完成
    - Click
    - Rich
    deliverable: TASK-FEAT-084-003 完成
core_dependencies:
  required:
  - name: Click
    version: '>=8.0.0'
    purpose: CLI框架
  - name: PyYAML
    version: '>=6.0'
    purpose: YAML解析
  - name: rich
    version: '>=13.0.0'
    purpose: 表格输出和颜色
  - name: SQLAlchemy
    version: '>=2.0.0'
    purpose: ORM
  - name: alembic
    version: '>=1.12.0'
    purpose: 数据库迁移
  - name: semantic-version
    version: '>=2.10.0'
    purpose: 语义化版本
  - name: packaging
    version: '>=23.0'
    purpose: 版本约束解析
  optional:
  - name: watchdog
    version: '>=3.0'
    purpose: 文件监控热重载
    phase: Phase 2
  infrastructure:
  - name: SQLite
    version: 3.35+
    purpose: 实例状态存储
  - name: Filesystem
    version: N/A
    purpose: 模板和Artifacts存储
