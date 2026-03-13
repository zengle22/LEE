---
id: ARCH-FEAT-143
ssot_type: tech
title: FEAT-143 QA 执行入口规范化 - 冻结技术架构
status: frozen
version: v1
parent_id: FEAT-143
derived_from_ids:
  - id: FEAT-143
    version: v1
    required: true
source_refs:
  - FEAT-143#Acceptance
  - ADR-001#12-1-p0-blocking-rules
  - ADR-007#5-mandatory-traceability-rules
  - ADR-011#6-canonical-tester-set
owner: qa
tags:
  - qa
  - ssot
  - execution-gate
  - traceability
properties:
  tech_kind: execution_gateway
  implementation_scope: execution_entry_validation
  frozen_at: '2026-03-13T00:00:00+08:00'
---

# FEAT-143 冻结技术架构

## 1. 核心设计决策

### 1.1 执行入口网关定位

FEAT-143 实现为**执行入口网关 (Execution Gateway)**，位于 QA 执行流程的最前端，负责：

- 验证执行请求是否通过合法的 TASK 入口
- 校验 RELEASE -> PLAN -> TASK 执行路径完整性
- 拒绝并记录所有旁路执行请求
- 建立执行入口与 SSOT 三轴模型的绑定关系审计

### 1.2 架构分层

```
┌─────────────────────────────────────────────────────────────┐
│                    QA 执行入口网关层                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Entry Router│  │Path Validator│  │ Audit Logger       │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    SSOT 追溯服务层                            │
│  ┌─────────────────────┐  ┌─────────────────────────────┐   │
│  │ Traceability Service│  │ Relationship Index Service  │   │
│  └─────────────────────┘  └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    现有执行器层                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ test-set-execute-l3-template (保持不变)              │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

### 1.3 不修改范围 (Non-Goals)

根据 FEAT-143#Non Goals 明确约束：

- **不修改**测试执行引擎内部逻辑 (script_execution, runner 实现)
- **不替换**现有 test-set-execute-l3-template 的 runner 实现
- **不修改**具体测试用例的内容生成逻辑
- **不影响**测试结果的判定逻辑 (result_judgment)

## 2. 技术实现方案

### 2.1 执行入口路由规则 (Entry Router)

#### 2.1.1 组件位置

```
src/lee/orchestrator/execution/gateway/
  ├── __init__.py
  ├── entry_router.py          # 执行入口路由核心
  ├── path_validator.py        # 执行路径校验器
  └── audit_logger.py          # 审计日志记录器
```

#### 2.1.2 Entry Router 接口

```python
class ExecutionEntryRouter:
    """
    QA 执行入口路由器

    职责:
    - 接收执行请求
    - 验证 task_ref 有效性
    - 验证 task 归属 testplan
    - 路由到合法执行器或拒绝请求
    """

    async def route_execution_request(
        self,
        request: ExecutionRequest
    ) -> ExecutionRoutingResult:
        """
        路由执行请求

        Args:
            request: 执行请求，包含 task_ref 或其他入口标识

        Returns:
            ExecutionRoutingResult: 路由结果

        Raises:
            InvalidEntryError: 入口不合法
            TaskNotFoundError: TASK 不存在
            TaskNotBelongToTestPlanError: TASK 不归属于 TESTPLAN
        """
```

#### 2.1.3 入口验证规则

```yaml
entry_validation_rules:
  - rule_id: ENTR-001
    name: task_ref_required
    description: "执行请求必须包含有效的 task_ref"
    check: "request.task_ref IS NOT EMPTY"
    error: "EXECUTION_ENTRY_001: task_ref is required"

  - rule_id: ENTR-002
    name: task_exists
    description: "task_ref 必须指向存在的 TASK 对象"
    check: "SSOTService.exists(request.task_ref)"
    error: "EXECUTION_ENTRY_002: task not found"

  - rule_id: ENTR-003
    name: task_parent_is_testplan
    description: "TASK 的 parent_id 必须是 TESTPLAN"
    check: "TASK.parent_id.ssot_type == 'testplan'"
    error: "EXECUTION_ENTRY_003: task must belong to testplan"

  - rule_id: ENTR-004
    name: testplan_parent_is_release
    description: "TESTPLAN 的 parent_id 必须是 RELEASE"
    check: "TESTPLAN.parent_id.ssot_type == 'release'"
    error: "EXECUTION_ENTRY_004: testplan must belong to release"

  - rule_id: ENTR-005
    name: no_bypass_allowed
    description: "禁止绕过 TESTPLAN/TASK 的直接执行"
    check: "request.has_direct_test_set_ref AND NOT request.has_task_ref => REJECT"
    error: "EXECUTION_ENTRY_005: bypass not allowed, must use task_ref"
```

### 2.2 执行路径校验器 (Path Validator)

#### 2.2.1 路径验证模型

```yaml
execution_path_model:
  canonical_path: "RELEASE -> TESTPLAN -> TASK -> EXECUTION"

  validation_segments:
    - segment: release_to_testplan
      from: RELEASE
      to: TESTPLAN
      relationship: parent_id
      validation: "TESTPLAN.parent_id == RELEASE.id"

    - segment: testplan_to_task
      from: TESTPLAN
      to: TASK
      relationship: parent_id
      validation: "TASK.parent_id == TESTPLAN.id"

    - segment: task_to_execution
      from: TASK
      to: EXECUTION
      relationship: execution_trigger
      validation: "EXECUTION.task_ref == TASK.id"
```

#### 2.2.2 路径校验算法

```python
class ExecutionPathValidator:
    """
    执行路径完整性校验器

    验证 RELEASE -> TESTPLAN -> TASK 链路完整且有效
    """

    async def validate_path_completeness(
        self,
        task_id: str
    ) -> PathValidationResult:
        """
        验证执行路径完整性

        Args:
            task_id: TASK 对象 ID

        Returns:
            PathValidationResult: 路径验证结果
        """
        # 1. 加载 TASK
        task = await self.ssot_service.load(task_id)

        # 2. 验证 TASK.parent_id -> TESTPLAN
        testplan = await self.ssot_service.load(task.parent_id)
        if testplan.ssot_type != SSOTType.TESTPLAN:
            return PathValidationResult.invalid(
                reason="TASK parent is not TESTPLAN"
            )

        # 3. 验证 TESTPLAN.parent_id -> RELEASE
        release = await self.ssot_service.load(testplan.parent_id)
        if release.ssot_type != SSOTType.RELEASE:
            return PathValidationResult.invalid(
                reason="TESTPLAN parent is not RELEASE"
            )

        # 4. 验证 derived_from_ids 追溯链
        #    TESTPLAN 必须 trace 到 FEAT/TESTSET
        #    RELEASE 必须 trace 到 FEAT@version
        trace_result = await self.traceability_service.verify_trace_chain(
            start=task_id,
            required_traces=['FEAT', 'TESTSET']
        )

        return PathValidationResult(
            is_valid=True,
            path_segments=[
                PathSegment(type='RELEASE', id=release.id),
                PathSegment(type='TESTPLAN', id=testplan.id),
                PathSegment(type='TASK', id=task.id)
            ],
            trace_chain=trace_result
        )
```

### 2.3 审计日志记录器 (Audit Logger)

#### 2.3.1 审计日志结构

```yaml
audit_log_schema:
  type: object
  required:
    - log_id
    - timestamp
    - execution_request_id
    - entry_type
    - path_snapshot
    - result
    - user_id

  properties:
    log_id:
      type: string
      format: "AUDIT-{YYYYMMDDHHmmss}-{seq}"

    timestamp:
      type: string
      format: date-time

    execution_request_id:
      type: string
      description: "执行请求唯一标识"

    entry_type:
      type: string
      enum:
        - canonical_entry      # 标准入口 (TASK 触发)
        - bypass_attempt       # 旁路尝试 (直接 TESTSET 触发)
        - invalid_task_ref     # 无效 TASK 引用
        - path_incomplete      # 路径不完整

    path_snapshot:
      type: object
      properties:
        task_id: string
        task_parent_id: string   # TESTPLAN ID
        testplan_parent_id: string  # RELEASE ID
        derived_from_ids: array  # FEAT/TESTSET trace

    result:
      type: object
      properties:
        status: enum [accepted, rejected]
        rejection_reason: string (optional)
        error_code: string (optional)

    user_id:
      type: string
      description: "发起执行请求的用户/系统标识"

    evidence_refs:
      type: array
      items: string
      description: "关联的证据对象 ID (执行后补充)"
```

#### 2.3.2 审计日志存储

```yaml
audit_storage:
  primary_location: "docs/reports/evidence/execution-audit/"
  file_format: "AUDIT-{date}.jsonl"  # JSON Lines 格式
  retention_policy:
    active_days: 90
    archive_after_days: 30

  index_structure:
    - field: execution_request_id
      type: unique_index
    - field: task_id
      type: secondary_index
    - field: result.status
      type: secondary_index
    - field: timestamp
      type: time_series_index
```

### 2.4 SSOT 追溯服务集成

#### 2.4.1 追溯服务接口

```python
class TraceabilityService:
    """
    SSOT 追溯服务

    提供跨对象类型的追溯链验证能力
    """

    async def verify_trace_chain(
        self,
        start: str,
        required_traces: List[str]
    ) -> TraceChainResult:
        """
        验证追溯链是否完整

        Args:
            start: 起始对象 ID
            required_traces: 必须追溯到的对象类型列表
                           如 ['FEAT', 'TESTSET']

        Returns:
            TraceChainResult: 追溯链验证结果
        """

    async def get_full_chain(
        self,
        object_id: str
    ) -> List[SSOTObject]:
        """
        获取完整追溯链

        Returns:
            从当前对象到根对象的完整链路
        """
```

#### 2.4.2 追溯规则配置

```yaml
traceability_rules:
  # TASK 必须能追溯到:
  task_traces:
    required:
      - TESTPLAN  # parent
      - RELEASE   # TESTPLAN.parent
    optional:
      - FEAT      # via TESTPLAN.derived_from_ids
      - TESTSET   # via TESTPLAN.derived_from_ids

  # TESTPLAN 必须能追溯到:
  testplan_traces:
    required:
      - RELEASE   # parent
      - FEAT      # derived_from_ids (at least one)
      - TESTSET   # derived_from_ids (at least one)

  # RELEASE 必须能追溯到:
  release_traces:
    required:
      - FEAT@version  # derived_from_ids with pinned versions
```

## 3. 核心依赖项

### 3.1 内部依赖

```yaml
internal_dependencies:
  - component: SSOTService
    location: src/lee/orchestrator/execution/artifacts/ssot_service.py
    usage: "加载 SSOT 对象、验证对象存在性、解析关系"
    required_methods:
      - load(object_id)
      - exists(object_id)
      - get_relationships(object_id)

  - component: SSOTType
    location: src/lee/orchestrator/execution/artifacts/types.py
    usage: "对象类型枚举与验证"
    required_features:
      - SSOTType.TASK
      - SSOTType.TESTPLAN
      - SSOTType.RELEASE
      - ObjectCategory.get_parent_requirement()

  - component: IDParser
    location: src/lee/orchestrator/utils/id_parser.py (假设存在)
    usage: "解析 SSOT ID 结构"
    required_methods:
      - parse(id_string)
      - get_type_from_id(id_string)

  - component: ArtifactManifest
    location: src/lee/orchestrator/execution/artifacts/manifest.py
    usage: "访问 artifact registry 索引"
```

### 3.2 外部依赖

```yaml
external_dependencies:
  - package: pyyaml
    version: ">=6.0"
    usage: "YAML front matter 解析"

  - package: pydantic
    version: ">=2.0"
    usage: "数据模型验证"

  - package: structlog
    version: ">=21.0"
    usage: "结构化日志记录"
```

### 3.3 数据依赖

```yaml
data_dependencies:
  - data: SSOT 对象文件
    location: spec/requirements/features/*.md
    location: spec/delivery/releases/*.md
    location: spec/delivery/testplans/*.md
    location: spec/tasks/*.md
    usage: "执行入口验证的数据源"

  - data: .artifacts/.registry.json
    usage: "加速对象查找和关系解析"
    note: "可丢弃缓存，以磁盘 front matter 为准"
```

## 4. 技术不确定性及备份方案

### 4.1 不确定性 1: SSOT 服务接口稳定性

**风险描述**:
SSOTService 的接口可能尚未完全支持高效的追溯链验证，特别是 `verify_trace_chain` 方法可能需要扩展。

**影响评估**:
- 概率：中
- 影响：高 (核心验证逻辑依赖)

**备份方案**:

```yaml
backup_plan:
  option_a:
    name: "轻量级追溯验证器"
    description: |
      在 SSOTService 外部封装一层轻量验证器，
      直接解析 front matter 进行追溯验证，
      不依赖 SSOTService 的高级方法。
    implementation:
      - 直接读取 Markdown 文件的 YAML front matter
      - 手动解析 parent_id 和 derived_from_ids
      - 构建临时追溯图进行验证
    pros:
      - 不依赖 SSOTService 升级
      - 可独立测试
    cons:
      - 代码重复
      - 需要手动处理 registry 同步

  option_b:
    name: "SSOTService 扩展优先"
    description: |
      优先扩展 SSOTService 添加追溯验证方法，
      FEAT-143 依赖于该扩展完成。
    implementation:
      - 在 ssot_service.py 中新增 verify_trace_chain()
      - 在 ssot_service.py 中新增 get_full_chain()
      - FEAT-143 直接使用扩展后的服务
    pros:
      - 复用现有服务架构
      - 统一追溯逻辑
    cons:
      - 增加 SSOTService 复杂度
      - 需要更广泛的测试覆盖

  recommended: option_b
  fallback_trigger: "若 SSOTService 扩展超过 2 天未完成，切换到 option_a"
```

### 4.2 不确定性 2: 现有执行流程兼容性

**风险描述**:
test-set-execute-l3-template 的输入参数可能不直接支持 task_ref 作为入口标识，需要调整输入契约。

**影响评估**:
- 概率：高
- 影响：中 (需要调整契约但不修改核心逻辑)

**备份方案**:

```yaml
backup_plan:
  option_a:
    name: "新增 task_ref 输入字段"
    description: |
      在 test-set-execute-l3-template 的 instance_schema 中
      新增 task_ref 作为必需输入字段。
    changes_required:
      - spec-global/departments/qa/workflows/templates/test-set-execute-l3-template.yaml
      - 在 context_fields 中添加 task_ref
      - 在 required_fields 中验证 task_ref 存在

  option_b:
    name: "包装器模式"
    description: |
      创建执行网关包装器，接收 task_ref 后解析出
      test_set_id 和其他参数，再调用现有模板。
    implementation:
      - 新增 ExecutionGatewayWrapper 类
      - wrapper 接收 task_ref
      - wrapper 解析 task 关联的 test_set_id
      - wrapper 调用现有执行流程
    pros:
      - 不修改现有模板
      - 向前兼容
    cons:
      - 增加一层间接性

  recommended: option_a
  reason: "更符合 SSOT 规范，task_ref 应成为正式输入"
```

### 4.3 不确定性 3: Registry 同步状态

**风险描述**:
根据 ADR-001，registry 是可丢弃缓存，可能与磁盘 front matter 不一致。执行入口验证需要确保使用最新数据。

**影响评估**:
- 概率：中
- 影响：中 (可能导致验证基于过期数据)

**备份方案**:

```yaml
backup_plan:
  pre_validation_sync:
    name: "验证前 registry 同步检查"
    description: |
      在执行入口验证前，先检查 registry 是否与磁盘一致。
      若检测到过期，强制执行增量同步。
    implementation:
      - 调用 lee ssot sync --check-first
      - 若检测到过期，自动执行增量 refresh
      - 若 refresh 失败，降级到直接读取磁盘 front matter

  direct_disk_read:
    name: "直接磁盘读取模式"
    description: |
      不依赖 registry，直接从磁盘读取 front matter 验证。
      性能较低但保证数据新鲜。
    implementation:
      - 使用 SSOTService 的冷加载模式
      - 或直接用 ArtifactManager 扫描磁盘
    trigger: "registry sync 失败时自动降级"

  recommended: pre_validation_sync
  fallback: direct_disk_read
```

## 5. 与现有系统集成点

### 5.1 集成架构图

```
┌────────────────────────────────────────────────────────────────┐
│                      CLI / API 入口                             │
│                    (lee qa execute)                            │
└───────────────────────┬────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────────┐
│              新增：执行入口网关 (FEAT-143)                       │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  1. Entry Router                                         │  │
│  │     - 验证 task_ref 存在                                  │  │
│  │     - 验证 task 归属 testplan                             │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  2. Path Validator                                       │  │
│  │     - 验证 RELEASE -> TESTPLAN -> TASK 链路              │  │
│  │     - 验证 derived_from_ids 追溯                         │  │
│  └──────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │  3. Audit Logger                                         │  │
│  │     - 记录入口来源                                        │  │
│  │     - 记录路径链                                          │  │
│  │     - 记录时间戳/用户                                     │  │
│  └──────────────────────────────────────────────────────────┘  │
└───────────────────────┬────────────────────────────────────────┘
                        │ (验证通过后)
                        ▼
┌────────────────────────────────────────────────────────────────┐
│              现有：test-set-execute-l3-template                 │
│  - case_generation                                             │
│  - script_translation                                          │
│  - script_execution (runner 调用，保持不变)                      │
│  - behavior_compliance (保持不变)                               │
│  - result_judgment (保持不变)                                   │
│  - tse_assembly (保持不变)                                      │
│  - bug_drafting (保持不变)                                      │
└────────────────────────────────────────────────────────────────┘
```

### 5.2 CLI 命令扩展

```yaml
cli_extensions:
  new_command:
    name: "lee qa execute"
    location: src/lee/cli/commands/qa/execute.py
    usage: |
      lee qa execute --task <TASK_ID>
      lee qa execute --task <TASK_ID> --env <environment>

    arguments:
      - name: --task
        required: true
        description: "TASK 对象 ID，执行入口标识"

      - name: --env
        required: false
        default: test
        description: "执行环境 (test/staging/prod)"

      - name: --dry-run
        required: false
        description: "仅验证入口和路径，不实际执行"

    workflow:
      - 调用 ExecutionEntryRouter.route_execution_request()
      - 调用 ExecutionPathValidator.validate_path_completeness()
      - 调用 AuditLogger.log_entry()
      - 若验证通过，调用现有执行器
      - 若验证失败，返回错误并记录审计日志
```

### 5.3 错误码定义

```yaml
error_codes:
  # 入口验证错误 (001-099)
  EXECUTION_ENTRY_001:
    message: "task_ref is required"
    http_status: 400

  EXECUTION_ENTRY_002:
    message: "task not found: {task_id}"
    http_status: 404

  EXECUTION_ENTRY_003:
    message: "task must belong to testplan, got parent type: {parent_type}"
    http_status: 400

  EXECUTION_ENTRY_004:
    message: "testplan must belong to release"
    http_status: 400

  EXECUTION_ENTRY_005:
    message: "bypass not allowed, must use task_ref instead of direct test_set_id"
    http_status: 400

  # 路径验证错误 (100-199)
  EXECUTION_PATH_101:
    message: "execution path incomplete: missing {missing_segment}"
    http_status: 400

  EXECUTION_PATH_102:
    message: "trace chain broken: cannot trace to {required_type}"
    http_status: 400

  # 审计错误 (200-299)
  EXECUTION_AUDIT_201:
    message: "failed to write audit log: {reason}"
    http_status: 500
```

## 6. 测试策略

### 6.1 单元测试范围

```yaml
unit_tests:
  - component: ExecutionEntryRouter
    test_cases:
      - name: test_route_with_valid_task_ref
        given: "有效的 TASK ID，归属于 TESTPLAN"
        expect: "路由成功，返回执行器引用"

      - name: test_route_with_missing_task_ref
        given: "请求不包含 task_ref"
        expect: "拒绝请求，返回 EXECUTION_ENTRY_001"

      - name: test_route_with_nonexistent_task
        given: "task_ref 指向不存在的对象"
        expect: "拒绝请求，返回 EXECUTION_ENTRY_002"

      - name: test_route_with_task_not_in_testplan
        given: "TASK 的 parent 不是 TESTPLAN"
        expect: "拒绝请求，返回 EXECUTION_ENTRY_003"

      - name: test_route_with_bypass_attempt
        given: "请求只包含 test_set_id，没有 task_ref"
        expect: "拒绝请求，返回 EXECUTION_ENTRY_005"

  - component: ExecutionPathValidator
    test_cases:
      - name: test_validate_complete_path
        given: "TASK -> TESTPLAN -> RELEASE 链路完整"
        expect: "验证通过，返回完整路径段"

      - name: test_validate_missing_testplan
        given: "TASK.parent 不存在或不是 TESTPLAN"
        expect: "验证失败，返回路径缺失错误"

      - name: test_validate_missing_release
        given: "TESTPLAN.parent 不是 RELEASE"
        expect: "验证失败，返回路径缺失错误"

      - name: test_validate_trace_chain
        given: "TESTPLAN 没有 derived_from_ids 到 FEAT/TESTSET"
        expect: "验证失败，返回追溯链断裂错误"

  - component: AuditLogger
    test_cases:
      - name: test_log_accepted_entry
        given: "入口验证通过的执行请求"
        expect: "写入审计日志，包含完整路径快照"

      - name: test_log_rejected_entry
        given: "入口验证失败的执行请求"
        expect: "写入审计日志，包含拒绝原因和错误码"

      - name: test_log_bypass_attempt
        given: "旁路执行尝试"
        expect: "写入审计日志，entry_type=bypass_attempt"
```

### 6.2 集成测试范围

```yaml
integration_tests:
  - name: test_full_execution_flow
    description: "从 CLI 入口到执行完成的完整流程"
    steps:
      - 创建 RELEASE / TESTPLAN / TASK / TESTSET 测试数据
      - 调用 `lee qa execute --task <TASK_ID>`
      - 验证入口网关验证通过
      - 验证审计日志已记录
      - 验证执行器被正确调用

  - name: test_bypass_blocking
    description: "验证旁路执行被正确阻断"
    steps:
      - 尝试直接用 test_set_id 触发执行
      - 验证请求被拒绝
      - 验证审计日志记录了 bypass_attempt
      - 验证执行器未被调用
```

## 7. 验收标准映射

| FEAT-143 验收标准 | 技术实现 | 验证方式 |
|------------------|----------|----------|
| AC-003-001: 执行入口唯一性 | Entry Router 验证 task_ref | 单元测试 + 集成测试 |
| AC-003-002: 执行路径完整性校验 | Path Validator 验证链路 | 单元测试 + 集成测试 |
| AC-003-003: 旁路执行入口阻断 | Entry Router 拒绝无 task_ref 请求 | 单元测试 + 集成测试 |
| AC-003-004: 执行入口审计 | Audit Logger 记录所有请求 | 单元测试 + 审计日志检查 |

## 8. 实施顺序

```yaml
implementation_phases:
  phase_1:
    name: "核心组件实现"
    duration_days: 2
    deliverables:
      - src/lee/orchestrator/execution/gateway/entry_router.py
      - src/lee/orchestrator/execution/gateway/path_validator.py
      - src/lee/orchestrator/execution/gateway/audit_logger.py

  phase_2:
    name: "SSOT 服务扩展 (若需要)"
    duration_days: 1
    deliverables:
      - src/lee/orchestrator/execution/artifacts/ssot_service.py 扩展
      - verify_trace_chain() 方法
      - get_full_chain() 方法

  phase_3:
    name: "CLI 集成"
    duration_days: 1
    deliverables:
      - src/lee/cli/commands/qa/execute.py
      - lee qa execute 命令

  phase_4:
    name: "测试与验证"
    duration_days: 2
    deliverables:
      - tests/gateway/test_entry_router.py
      - tests/gateway/test_path_validator.py
      - tests/gateway/test_audit_logger.py
      - tests/integration/test_execution_gateway.py

  phase_5:
    name: "执行模板调整"
    duration_days: 1
    deliverables:
      - test-set-execute-l3-template.yaml 输入契约扩展
      - task_ref 作为必需输入字段
```

## 9. 技术风险汇总

| 风险项 | 概率 | 影响 | 缓解措施 | 备份方案 |
|--------|------|------|----------|----------|
| SSOT 服务接口不稳定 | 中 | 高 | 优先扩展 SSOTService | 轻量级追溯验证器 |
| 执行流程兼容性 | 高 | 中 | 扩展 instance_schema | 包装器模式 |
| Registry 同步问题 | 中 | 中 | 验证前同步检查 | 直接磁盘读取 |
| 测试数据准备复杂 | 中 | 低 | 创建测试数据工厂 | 使用现有样本 |

## 10. 架构决策记录引用

本技术架构遵循以下 ADR 约束：

- **ADR-001**: SSOT 交付链硬治理设计
  - 第 12.1 节 P0 Blocking 规则 #5-7: TASK/DEVPLAN/TESTPLAN 父对象规则
  - 第 15 节：运行流程 (RELEASE -> PLAN -> TASK)

- **ADR-007**: QA 部门 SSOT 对齐
  - 第 5 节：强制性追溯规则
  - 第 6.2 节：Workflow 升级 (test-set-execute 输入迁移)

- **ADR-011**: 需求链一致性测试体系建设
  - 第 6 节：Canonical Tester Set (Schema Validator, Traceability Checker)

## 11. 配置示例

### 11.1 测试用 SSOT 对象示例

```yaml
# RELEASE 示例
---
id: REL-TEST-001
ssot_type: release
title: Test Release for FEAT-143
status: scope_frozen
version: v1
parent_id:
derived_from_ids:
  - id: FEAT-143
    version: v1
    required: true
---

# TESTPLAN 示例
---
id: TESTPLAN-REL-TEST-001
ssot_type: testplan
title: Test Plan for REL-TEST-001
status: committed
version: v1
parent_id: REL-TEST-001
derived_from_ids:
  - id: FEAT-143
    version: v1
    required: true
  - id: TESTSET-FEAT-143
    version: v1
    required: true
properties:
  slices:
    - slice_key: feat-143-entry-gate
      feat_id: FEAT-143
      feat_version: v1
      required: true
      dependencies: []
---

# TASK 示例
---
id: TASK-TESTPLAN-REL-TEST-001-001
ssot_type: task
title: Execute FEAT-143 entry gate validation
status: todo
version: v1
parent_id: TESTPLAN-REL-TEST-001
derived_from_ids:
  - id: FEAT-143
    version: v1
    required: true
properties:
  slice_key: feat-143-entry-gate
  acceptance:
    - "执行入口验证通过"
    - "路径完整性校验通过"
    - "审计日志已记录"
---
```

### 11.2 CLI 执行示例

```bash
# 标准执行 (通过)
$ lee qa execute --task TASK-TESTPLAN-REL-TEST-001-001

# 输出:
# [ENTRY] Validating task_ref: TASK-TESTPLAN-REL-TEST-001-001
# [ENTRY] Task verified: belongs to TESTPLAN-REL-TEST-001
# [PATH] Validating execution path...
# [PATH] RELEASE -> TESTPLAN -> TASK: VALID
# [PATH] Trace chain to FEAT-143: VALID
# [AUDIT] Entry logged: AUDIT-20260313-00001
# [EXEC] Starting execution...

# 旁路尝试 (被阻断)
$ lee qa execute --test-set TS-FEAT-143

# 输出:
# [ENTRY] ERROR: EXECUTION_ENTRY_005
# [ENTRY] bypass not allowed, must use task_ref instead of direct test_set_id
# [AUDIT] Bypass attempt logged: AUDIT-20260313-00002

# 无效 TASK (被阻断)
$ lee qa execute --task INVALID-TASK-001

# 输出:
# [ENTRY] ERROR: EXECUTION_ENTRY_002
# [ENTRY] task not found: INVALID-TASK-001
# [AUDIT] Invalid entry logged: AUDIT-20260313-00003
```