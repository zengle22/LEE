---
id: TECH-FEAT-SRC-046-001
ssot_type: tech
title: 交付主链建立与 RELEASE 起点治理技术设计
status: draft
version: v1
workflow_instance_id: wf_task_fff82fe5
parent_id: FEAT-SRC-046-001
derived_from_ids:
- id: FEAT-SRC-046-001
  version: v1
  required: true
source_refs:
- ADR-001#10-id-grammar-migration
- ADR-001#11-7-transition-authority-matrix
- ADR-001#12-1-p0-blocking-rules
- ADR-001#15-4-typical-l1-workflow
- ADR-001#15-9-slice-data-model
- ADR-001#8-2-1-front-matter-minimal-templates
owner: null
tags: [delivery, architecture, ssot]
properties:
  contract_key: tech
  identity_kind: ssot
---

# 交付主链建立与 RELEASE 起点治理技术设计

## 1. 架构概述

### 1.1 设计目标

本技术设计基于 ADR-001 的三轴治理模型，建立以 RELEASE 为起点的正式交付主链。核心目标：

1. **RELEASE 作为交付轴根对象**：所有正式发布版本必须通过 RELEASE 对象管理
2. **DEVPLAN/TESTPLAN 作为执行承诺**：将需求拆解为可执行 TASK
3. **硬治理校验**：通过脚本和 CI 强制执行绑定关系和完整性规则

### 1.2 架构分层

```
┌─────────────────────────────────────────────────────────┐
│                     CLI Layer                           │
│  lee ssot: validate/build-index/release-check/plan-derive│
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Service Layer                         │
│  SSOTService / SSOTValidator / RegistryManager          │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Domain Layer                          │
│  ArtifactManager / SSOTContract / types / placement     │
└─────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                  │
│  FileSystem / Git Operations / Registry Storage         │
└─────────────────────────────────────────────────────────┘
```

---

## 2. 核心模块设计

### 2.1 类型系统模块 (types.py)

**职责**: 定义 SSOT 对象类型枚举和 parent 规则

**关键改动**:

```python
class SSOTType(str, Enum):
    # 独立型 (已有)
    SRC = "src"
    EPIC = "epic"
    FEAT = "feat"
    ADR = "adr"
    RELEASE = "release"      # 新增：交付轴根对象

    # 直接父对象一致型
    UI = "ui"
    TECH = "tech"
    DEVPLAN = "devplan"      # 新增：开发计划
    TESTPLAN = "testplan"    # 新增：测试计划
    TASK = "task"
    TESTSET = "testset"
    REPORT = "report"

    # 范围归属型
    TC = "tc"
    BUG = "bug"
    EVI = "evi"
```

**parent 规则扩展**:

| SSOT Type | Parent Requirement | Category |
|-----------|-------------------|----------|
| RELEASE | None | INDEPENDENT |
| DEVPLAN | RELEASE | DIRECT_PARENT |
| TESTPLAN | RELEASE | DIRECT_PARENT |
| TASK | DEVPLAN | TESTPLAN | DIRECT_PARENT |
| BUG | FEAT | TC | SCOPE_BOUNDED |
| REPORT | RELEASE | FEAT | TASK | SCOPE_BOUNDED |

### 2.2 ID 解析器模块 (id_parser.py)

**职责**: 解析和验证 SSOT ID 格式及 parent 一致性

**新增 grammar**:

```
REL-<semver>              # e.g., REL-1.4.0
DEVPLAN-REL-<semver>      # e.g., DEVPLAN-REL-1.4.0
TESTPLAN-REL-<semver>     # e.g., TESTPLAN-REL-1.4.0
TASK-DEVPLAN-REL-<semver>-<seq>  # e.g., TASK-DEVPLAN-REL-1.4.0-001
TASK-TESTPLAN-REL-<semver>-<seq> # e.g., TASK-TESTPLAN-REL-1.4.0-001
REPORT-REL-<semver>-<kind>-<seq> # e.g., REPORT-REL-1.4.0-TEST-001
```

**解析函数扩展**:

```python
def parse_parent(artifact_id: str) -> Optional[str]:
    """从 ID 推断 parent_id"""
    # 新增规则：
    # DEVPLAN-REL-* -> REL-*
    # TESTPLAN-REL-* -> REL-*
    # TASK-DEVPLAN-REL-* -> DEVPLAN-REL-*
    # TASK-TESTPLAN-REL-* -> TESTPLAN-REL-*

def validate_parent_consistency(
    artifact_id: str,
    parent_id: Optional[str],
    ssot_type: SSOTType
) -> Optional[str]:
    """校验 parent_id 一致性，返回错误消息或 None"""
```

### 2.3 目录放置模块 (placement.py)

**职责**: 定义 SSOT 对象文件存放目录策略

**新增 placement 规则**:

```python
SSOT_PLACEMENT = {
    SSOTType.RELEASE: "spec/delivery/releases",
    SSOTType.DEVPLAN: "spec/delivery/devplans",
    SSOTType.TESTPLAN: "spec/delivery/testplans",
    SSOTType.TASK: "spec/tasks",
    SSOTType.BUG: "tests/bugs",
    SSOTType.REPORT: "docs/reports/delivery",  # 根据 report_kind 细分
}
```

### 2.4 物化器模块 (ssot_contract.py)

**职责**: 将 agent output contract 物化为正式 SSOT 文件

**扩展支持**:

- Materialize `release/devplan/testplan/bug/report` 对象
- 处理 `derived_from_ids` 结构化版本引用
- 处理 `properties.slices[]` 切片声明
- 处理 `properties.recuts[]` recut 审计记录

### 2.5 校验器模块 (ssot_service.py)

**职责**: 提供 SSOT 完整性校验和影响分析

**新增校验规则**:

```python
class SSOTValidator:
    def validate_p0(self, artifact_id: str) -> ValidationResult:
        """P0 Blocking 校验"""
        # 交付链专用规则:
        # - RELEASE 必须声明 derived_from_ids
        # - DEVPLAN.derived_from_ids 至少包含一个 FEAT
        # - TESTPLAN.derived_from_ids 至少包含一个 FEAT 和一个 TESTSET
        # - TASK 必须有 slice_key
        # - BUG 必须有 severity 和 source_report_id
        # - REPORT 必须有 report_kind/subject_id/result/evidence_refs

    def release_check(self, release_id: str) -> Dict[str, Any]:
        """执行 release 级聚合校验"""
        # 1. 验证 derived_from_ids 可解析
        # 2. 验证 DEVPLAN coverage
        # 3. 验证 TESTPLAN coverage
        # 4. 验证报告齐备性 (release/test_execution/go_no_go)
        # 5. 验证 blocker bug 状态

    def derive_plans(self, release_id: str) -> Dict[str, str]:
        """从 RELEASE scope 派生 DEVPLAN/TESTPLAN 骨架"""
```

---

## 3. 数据模型

### 3.1 RELEASE 对象

```yaml
---
id: REL-1.4.0
ssot_type: release
title: March MVP release
status: planned  # draft|planned|scope_frozen|in_dev|in_test|go_no_go|released|aborted
version: v1
parent_id: null
derived_from_ids:
  - id: FEAT-023
    version: v5
    required: true
    slice_key: feat-023-core
source_refs:
  - FEAT-023#acceptance
owner: delivery
tags: [mvp, march]
properties:
  scope_frozen_at: 2026-03-15T00:00:00+08:00
  target_env: staging
  rollback_plan: "回滚到 REL-1.3.0"
  recuts: []
---
```

### 3.2 DEVPLAN 对象

```yaml
---
id: DEVPLAN-REL-1.4.0
ssot_type: devplan
title: Dev plan for REL-1.4.0
status: draft  # draft|committed|in_progress|blocked|completed|cancelled
version: v1
parent_id: REL-1.4.0
derived_from_ids:
  - id: FEAT-023
    version: v5
    required: true
    slice_key: feat-023-core
source_refs: []
owner: delivery
tags: []
properties:
  coverage_summary: "覆盖 3 个 FEAT"
  slices:
    - slice_key: feat-023-core
      feat_id: FEAT-023
      feat_version: v5
      required: true
      dependencies: []
---
```

### 3.3 TESTPLAN 对象

```yaml
---
id: TESTPLAN-REL-1.4.0
ssot_type: testplan
title: Test plan for REL-1.4.0
status: draft  # draft|committed|in_progress|blocked|completed|cancelled
version: v1
parent_id: REL-1.4.0
derived_from_ids:
  - id: FEAT-023
    version: v5
    required: true
    slice_key: feat-023-core
source_refs:
  - TESTSET-FEAT-023#coverage
owner: qa
tags: []
properties:
  environment_matrix: [staging, production-like]
  coverage_summary: "覆盖 3 个 FEAT 的 TESTSET"
  slices:
    - slice_key: feat-023-core
      feat_id: FEAT-023
      feat_version: v5
      required: true
      dependencies: []
---
```

### 3.4 TASK 对象

```yaml
---
id: TASK-DEVPLAN-REL-1.4.0-001
ssot_type: task
title: Implement FEAT-023 core
status: todo  # todo|doing|blocked|done|verified|dropped
version: v1
parent_id: DEVPLAN-REL-1.4.0
derived_from_ids:
  - id: FEAT-023
    version: v5
source_refs: []
owner: backend
tags: []
properties:
  slice_key: feat-023-core
  acceptance:
    - "用户可以注册账号"
    - "邮箱唯一性校验"
  estimate: 4h
---
```

### 3.5 BUG 对象

```yaml
---
id: BUG-FEAT-023-001
ssot_type: bug
title: Duplicate email check fails
status: active  # draft|active|frozen|archived
version: v1
parent_id: FEAT-023
derived_from_ids: []
source_refs: []
owner: qa
tags: []
properties:
  bug_state: open  # open|triaged|in_fix|fixed|verified|closed|waived
  severity: blocker  # blocker|critical|major|minor
  found_in_release: REL-1.4.0
  source_report_id: REPORT-REL-1.4.0-FEAT-023-TEST-001
  waiver_reason: null
  waiver_approved_by: null
---
```

### 3.6 REPORT 对象

```yaml
---
id: REPORT-REL-1.4.0-TEST-001
ssot_type: report
title: Test report for REL-1.4.0
status: active  # draft|active|frozen|archived
version: v1
parent_id: REL-1.4.0
derived_from_ids: []
source_refs: []
owner: qa
tags: []
properties:
  report_kind: test_execution  # release|test_execution|go_no_go|recut_audit|delivery|regression
  subject_id: REL-1.4.0
  result: pass  # pass|fail|warning|info|approved|rejected
  summary: "所有测试用例通过"
  evidence_refs:
    - EVI-TASK-DEVPLAN-REL-1.4.0-001-001
  slice_key: null
---
```

---

## 4. 核心依赖项

### 4.1 Python 运行时依赖

| 依赖 | 版本 | 用途 |
|------|------|------|
| Python | 3.11+ | 与现有 LEE 代码栈一致 |
| Pydantic | v2 | 数据校验和类型定义 |
| PyYAML | latest | YAML front matter 解析 |
| NetworkX | latest | 图分析和依赖遍历 |
| hashlib | stdlib | 文件哈希计算 |

### 4.2 内部模块依赖

| 模块 | 路径 | 职责 |
|------|------|------|
| types.py | `src/lee/orchestrator/execution/artifacts/` | SSOT 类型定义 |
| id_parser.py | `src/lee/orchestrator/execution/artifacts/` | ID 解析和校验 |
| id_generator.py | `src/lee/orchestrator/execution/artifacts/` | ID 生成 |
| placement.py | `src/lee/orchestrator/execution/artifacts/` | 文件放置策略 |
| manager.py | `src/lee/orchestrator/execution/artifacts/` | Artifact 物化 |
| ssot_contract.py | `src/lee/orchestrator/execution/artifacts/` | Contract 物化 |
| ssot_service.py | `src/lee/orchestrator/execution/artifacts/` | 服务层校验 |
| registry.py | `src/lee/orchestrator/execution/artifacts/` | Registry 管理 |
| schema.json | `spec-global/core/contracts/ssot-agent-output/v1/` | Agent 输出契约 |

### 4.3 CLI 命令依赖

| 命令 | 入口 | 依赖服务 |
|------|------|----------|
| `lee ssot validate` | `src/lee/cli/commands/ssot.py` | SSOTValidator |
| `lee ssot build-index` | `src/lee/cli/commands/ssot.py` | RegistryManager |
| `lee ssot release check` | `src/lee/cli/commands/ssot.py` | SSOTService.release_check() |
| `lee ssot release cut` | `src/lee/cli/commands/ssot.py` | SSOTService.derive_plans() |
| `lee ssot plan derive` | `src/lee/cli/commands/ssot.py` | SSOTService.derive_plans() |
| `lee ssot plan check` | `src/lee/cli/commands/ssot.py` | SSOTValidator |

---

## 5. 技术不确定性及备份方案

### 5.1 ID Grammar 迁移风险

**不确定性**:
- 现有 ID 解析器可能不完全支持新的 `DEVPLAN-REL-*` 等 grammar
- `parse_parent()` 和 `validate_parent_consistency()` 需要精确实现

**备份方案**:
1. **阶段 1**: 先在 `id_parser.py` 中实现 grammar 解析单元测试，验证所有 ID 模式
2. **阶段 2**: 保留旧 grammar 兼容层，标记为 `@deprecated`
3. **阶段 3**: 在新 grammar 稳定后，逐步移除兼容代码

### 5.2 Registry 同步风险

**不确定性**:
- Registry 与磁盘 front matter 文件可能不同步
- 增量 refresh 逻辑可能遗漏变更检测

**备份方案**:
1. **强制 rebuild 模式**: 提供 `lee ssot rebuild-registry --force` 命令
2. **哈希检测**: 对每个文件计算 content hash，而非仅依赖 mtime
3. **事务性写入**: 物化时先写临时文件，再原子替换

### 5.3 Schema 扩展风险

**不确定性**:
- 新增 `release/devplan/testplan` 类型可能导致旧 agent 不兼容
- `derived_from_ids` 结构化改造可能破坏现有引用

**备份方案**:
1. **版本化 schema**: 保留 v1 schema，新增 `v1.1` 支持新字段
2. **向后兼容**: 允许裸字符串 `derived_from_ids` 作为过渡
3. **迁移工具**: 提供脚本将旧格式转换为结构化格式

### 5.4 CI 集成风险

**不确定性**:
- Git Hook 在 Windows 环境可能表现不一致
- CI 超时可能导致误判

**备份方案**:
1. **本地 bypass 机制**: 提供 `LEE_BYPASS_HOOK=1` 环境变量用于调试
2. **超时重试**: CI 校验支持重试机制
3. **渐进式启用**: 先在 dev 分支启用，观察稳定后再合并到 main

---

## 6. 最小落地顺序

基于 ADR-001 第 21 节建议的实施顺序：

| 阶段 | 任务 | 验收标准 | 预计复杂度 |
|------|------|----------|------------|
| 1 | ID grammar migration | `parse_parent()` 返回正确结果 | 中 |
| 2 | 扩展 SSOTType 和 placement | 新类型可落盘到正确目录 | 低 |
| 3 | Schema 扩展 | 通过 JSON Schema 验证 | 中 |
| 4 | Registry rebuild/sync | 可重建和增量同步 | 中 |
| 5 | create_ssot() 扩展 | 可物化新对象类型 | 低 |
| 6 | SSOTValidator 扩展 | P0 规则全部实现 | 高 |
| 7 | validate/build-index 升级 | 输出包含新对象类型 | 低 |
| 8 | release check 命令 | 可执行 go/no-go 检查 | 高 |
| 9 | plan derive 命令 | 可生成计划骨架 | 中 |
| 10 | CI 集成 | Git Hook 生效 | 中 |

---

## 7. 验收检查

### 7.1 功能验收

| AC-ID | 验收场景 | 预期结果 |
|-------|----------|----------|
| AC-001 | 创建 RELEASE 对象 | 文件落盘到 `spec/delivery/releases/` |
| AC-002 | 创建 DEVPLAN 对象 | parent_id 自动设为 RELEASE ID |
| AC-003 | release check 校验 | 返回 pass/fail 和详细错误列表 |
| AC-004 | plan derive 派生 | 生成包含 slices 的 DEVPLAN/TESTPLAN |
| AC-005 | P0 规则阻断 | 非法 parent 被拒绝 |
| AC-006 | blocker bug 阻断 | 存在未关闭 blocker bug 时 release check 失败 |

### 7.2 技术验收

| TC-ID | 验收场景 | 预期结果 |
|-------|----------|----------|
| TC-001 | ID 解析单元测试 | 所有 grammar 模式通过 |
| TC-002 | Schema 验证 | 所有对象通过 JSON Schema 验证 |
| TC-003 | Registry 重建 | `rebuild-registry` 后 registry 与磁盘一致 |
| TC-004 | CI 校验 | PR 触发 `lee ssot validate --changed-only` |

---

## 8. 风险与缓解

### 8.1 技术风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| ID grammar 不兼容现有代码 | 高 | 中 | 单元测试 + 兼容层 |
| Registry 同步延迟 | 中 | 中 | 强制 rebuild 模式 |
| Schema 扩展破坏旧 agent | 高 | 低 | 版本化 schema |
| CI 超时 | 中 | 低 | 重试机制 |

### 8.2 实施风险

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 低估改造复杂度 | 高 | 中 | 分阶段实施，每阶段独立验收 |
| 团队学习曲线 | 中 | 中 | 提供迁移指南和示例 |
| 旧对象迁移工作量 | 中 | 低 | 第一阶段不强制迁移旧对象 |

---

## 9. 附录

### 9.1 相关文件

- `src/lee/orchestrator/execution/artifacts/types.py` - 类型定义
- `src/lee/orchestrator/execution/artifacts/id_parser.py` - ID 解析
- `src/lee/orchestrator/execution/artifacts/placement.py` - 文件放置
- `src/lee/orchestrator/execution/artifacts/ssot_service.py` - 服务层
- `spec-global/core/contracts/ssot-agent-output/v1/schema.json` - 契约
- `spec/adr/ADR-001` - 治理决策

### 9.2 术语表

| 术语 | 定义 |
|------|------|
| SSOT | Single Source of Truth，单一真源 |
| RELEASE | 交付轴根对象，定义版本范围 |
| DEVPLAN | 开发计划，将 FEAT 拆解为 TASK |
| TESTPLAN | 测试计划，将 TESTSET 拆解为验证任务 |
| derived_from_ids | 版本化引用，pin 住上游对象版本 |
| slice | 功能切片，支持并行开发和提测 |
| recut | RELEASE scope 变更审计 |
