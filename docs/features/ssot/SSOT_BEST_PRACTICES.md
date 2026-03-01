# SSOT 真理链管理系统 - 最佳实践指南

## 1. 真理链设计原则

### 1.1 单一起源原则 (Single Source of Truth)

**原则**: 每个产出物必须有明确、唯一的来源。

```yaml
# ✅ 正确：清晰的追溯链
prd_contract: ART-001
  └── derived_from: null (根节点)

api_contract: ART-002
  └── derived_from: ART-001 (源自 PRD)

implementation: ART-003
  └── implements: [ART-002] (实现 API)

test_plan: ART-004
  └── verifies: [ART-001, ART-002] (验证需求和协议)
```

```yaml
# ❌ 错误：断链
api_contract: ART-002
  └── derived_from: null (缺少来源)
```

### 1.2 完整性原则

**原则**: 真理链必须完整，不能有断点。

```
完整链条：
PRD → API → Code → Test
  ↓           ↑
  └───────────┘
    (Test 也验证 PRD)
```

### 1.3 最小依赖原则

**原则**: 产出物应依赖最小必要的上游产物。

```python
# ✅ 推荐：明确依赖特定 API
implementation:
  implements: ["ART-002"]  # 具体 API

# ❌ 不推荐：依赖整个 run 的所有 API
implementation:
  implements: ["ART-001", "ART-002", "ART-003", ...]  # 过度依赖
```

---

## 2. 工作流程最佳实践

### 2.1 推荐工作流程

```
1. 创建 PRD Contract (需求冻结)
   ↓
2. 创建 API Contract (协议设计)
   ↓
3. 创建 Implementation (代码实现)
   ↓
4. 创建 Test Plan (测试验证)
   ↓
5. 运行 SSOT 校验
   ↓
6. Gate 审批
   ↓
7. 冻结 artifacts
```

### 2.2 代码示例

```python
from lee.orchestrator.execution.artifacts import (
    ArtifactManager, ArtifactType, GovernanceKind
)

# 1. 创建 PRD
manager = ArtifactManager()
prd = manager.create(
    artifact_type=ArtifactType.CONTRACT,
    category="prd_contract",
    content="# PRD Content...",
    run_id="RUN-001",
    governance_kind=GovernanceKind.TRANSFER,
    title="用户管理模块需求",
)

# 2. 创建 API (关联 PRD)
api = manager.create(
    artifact_type=ArtifactType.CONTRACT,
    category="api_contract",
    content="# API Spec...",
    run_id="RUN-001",
    governance_kind=GovernanceKind.TRANSFER,
    derived_from=prd.id,  # 关键：关联 PRD
    title="用户管理 API",
)

# 3. 创建代码实现 (关联 API)
code = manager.create(
    artifact_type=ArtifactType.CODE_REF,
    category="implementation",
    content="def create_user(...): ...",
    run_id="RUN-001",
    governance_kind=GovernanceKind.DELIVERABLE,
    implements=[api.id],  # 关键：实现 API
    title="用户管理实现",
)

# 4. 创建测试计划 (关联 PRD 和 API)
test = manager.create(
    artifact_type=ArtifactType.TEST,
    category="test_plan",
    content="# Test Plan...",
    run_id="RUN-001",
    governance_kind=GovernanceKind.TRANSFER,
    verifies=[prd.id, api.id],  # 关键：验证需求和协议
    title="用户管理测试计划",
)
```

### 2.3 SSOT 校验

```python
from lee.orchestrator.execution.artifacts.ssot_service import SSOTService

service = SSOTService(manager)

# 校验整个 run
valid, errors = service.validate(run_id="RUN-001")
if not valid:
    print("SSOT validation failed:")
    for err in errors:
        print(f"  - {err}")
else:
    print("✅ SSOT validation passed")

# 查看影响范围
impact = service.impact(prd.id)
print(f"Direct dependents: {impact['direct_dependents']}")
print(f"Verifiers: {impact['verifiers']}")

# 查看真理链
chain = service.show_chain(api.id)
print("Truth chain:")
for entry in chain:
    print(f"  {entry['id']} ({entry['category']})")
```

---

## 3. Task Brief 最佳实践

### 3.1 何时使用 Task Brief

| 场景 | 推荐 | 说明 |
|------|------|------|
| 新功能开发 | ✅ 推荐 | 记录任务范围和目标 |
| Bug 修复 | ✅ 推荐 | 记录 bug 现象和修复方案 |
| 事件响应 | ✅ 推荐 | 记录 incident 处理过程 |
| 重构 | ✅ 推荐 | 记录重构目标和范围 |
| 简单文档更新 | ❌ 不需要 | 直接创建文档 artifact |

### 3.2 Task Brief 编写指南

```python
from lee.orchestrator.execution.artifacts.task_brief import TaskBriefGenerator

generator = TaskBriefGenerator(manager)

# 创建一个完整的 Task Brief
brief = generator.create_manual(
    run_id="RUN-001",
    department="backend",
    title="用户管理模块 - 后端实现",
    description="""
## 背景
需要实现用户管理功能，支持用户的创建、查询、更新和删除。

## 目标
完成用户管理模块的后端实现，包括 API 接口和数据库操作。

## 范围
- 用户创建接口
- 用户查询接口
- 用户更新接口
- 用户删除接口
""",
    task_type="feature",
    related_ssot={
        "prd_contract": "ART-001",
        "api_contract": "ART-002",
    },
    scope_include=[
        "用户 CRUD 接口",
        "用户数据验证",
    ],
    scope_exclude=[
        "用户认证（由 auth 模块负责）",
        "用户界面（由前端负责）",
    ],
    acceptance=[
        "所有 API 通过单元测试",
        "API 响应时间 < 100ms",
        "代码覆盖率 > 80%",
    ],
    risks=[
        "数据库 schema 变更可能影响现有功能",
        "需要与前端协调接口格式",
    ],
)
```

### 3.3 Task Brief 状态管理

```python
# 状态流转：draft → confirmed → completed

# 1. 创建时为 draft
brief.status = "draft"

# 2. 任务开始前确认为 confirmed
brief.status = "confirmed"

# 3. 任务完成后标记为 completed
brief.status = "completed"
```

---

## 4. Context Bundle 最佳实践

### 4.1 何时使用 Context Bundle

| 场景 | 推荐 | 说明 |
|------|------|------|
| LLM 辅助编程 | ✅ 推荐 | 记录完整的 prompt 和响应 |
| 代码审查 | ✅ 推荐 | 记录审查意见和修改建议 |
| 设计讨论 | ✅ 推荐 | 记录设计决策过程 |
| 简单文件操作 | ❌ 不需要 | 直接创建文档 artifact |

### 4.2 Context Bundle 编写指南

```python
from lee.orchestrator.execution.artifacts.context import (
    ContextBuilder, PromptSnapshot, LLMConfig
)

builder = ContextBuilder(manager)

# v1.0 完整版 - 推荐
bundle = builder.record_llm_call_v1_0(
    run_id="RUN-001",
    step_id="step-1",
    prompt=PromptSnapshot(
        system="你是一个 Python 专家，擅长编写高质量代码。",
        user="请帮我实现一个用户管理类，支持 CRUD 操作。",
        history=[
            {"role": "user", "content": "什么是 CRUD?"},
            {"role": "assistant", "content": "CRUD 是 Create, Read, Update, Delete..."},
        ],
    ),
    response="好的，我来实现一个用户管理类...",
    department="backend",
    artifacts={
        "prd": ["ART-001"],
        "api_contracts": ["ART-002"],
    },
    config=LLMConfig(
        model="claude-3-5-sonnet",
        temperature=0.7,
        max_tokens=4096,
    ),
)

# 保存为 artifact
artifact = builder.save_bundle(bundle)
```

### 4.3 版本选择

| 需求 | 版本 | 说明 |
|------|------|------|
| 仅需记录 prompt 文本 | v0.9 | 简化版，向后兼容 |
| 需要记录 artifacts 关联 | v1.0 | 完整版 |
| 需要记录对话历史 | v1.0 | 支持 `history` |
| 需要配置信息 | v1.0 | 支持 `config` |

---

## 5. Gate 审批最佳实践

### 5.1 Gate 审批流程

```python
from lee.orchestrator.execution.artifacts.integration import GateArtifactHandler

handler = GateArtifactHandler()

# 推荐：使用 enforce 模式进行 Gate 审批
try:
    result = handler.approve_gate_artifacts(
        run_id="RUN-001",
        gate_id="GATE-001",
        enforce=True,  # 强制模式：SSOT 校验失败则阻断
    )
    print(f"✅ Gate 审批通过")
    print(f"   Frozen artifacts: {result['frozen_count']}")
except Exception as e:
    print(f"❌ Gate 审批失败：{e}")
    # 需要修复 SSOT 问题后重新提交
```

### 5.2 模式选择

| 模式 | 适用场景 | 行为 |
|------|---------|------|
| `enforce=True` | 生产发布、正式 Gate | SSOT 失败则阻断 |
| `enforce=False` | 开发环境、临时测试 | SSOT 失败仅警告 |

---

## 6. 常见问题与解决方案

### 6.1 断链问题

**问题**: `api_contract missing derived_from`

**解决方案**:
```python
# 1. 查找所属 PRD
# 2. 重新创建 API artifact，添加 derived_from
api = manager.create(
    artifact_type=ArtifactType.CONTRACT,
    category="api_contract",
    content=api_content,
    run_id=run_id,
    governance_kind=GovernanceKind.TRANSFER,
    derived_from=prd_id,  # 添加此字段
)
```

### 6.2 孤立产物问题

**问题**: `implementation missing implements`

**解决方案**:
```python
# 1. 确认实现的 API
# 2. 重新创建 implementation，添加 implements
code = manager.create(
    artifact_type=ArtifactType.CODE_REF,
    category="implementation",
    content=code_content,
    run_id=run_id,
    governance_kind=GovernanceKind.DELIVERABLE,
    implements=[api_id],  # 添加此字段
)
```

### 6.3 测试覆盖不全

**问题**: `test_plan missing verifies`

**解决方案**:
```python
# 1. 确认验证的 PRD 和/或 API
# 2. 重新创建 test_plan，添加 verifies
test = manager.create(
    artifact_type=ArtifactType.TEST,
    category="test_plan",
    content=test_content,
    run_id=run_id,
    governance_kind=GovernanceKind.TRANSFER,
    verifies=[prd_id, api_id],  # 添加此字段
)
```

---

## 7. 性能优化建议

### 7.1 批量操作

```python
# ❌ 不推荐：逐个创建，每次重建索引
for i in range(100):
    manager.create(...)

# ✅ 推荐：批量创建后统一重建索引
for i in range(100):
    manager.create(...)
manager.registry.rebuild()  # 统一重建
```

### 7.2 索引缓存

```bash
# 定期构建 SSOT 索引
lee ssot build-index

# 索引文件位置
# .artifacts/trace/ssot-index.yaml
```

---

## 8. 检查清单

### 8.1 提交前检查

- [ ] 所有 `api_contract` 都有 `derived_from`
- [ ] 所有 `implementation` 都有 `implements`
- [ ] 所有 `test_plan` 都有 `verifies`
- [ ] 运行 `lee ssot validate --run-id <run_id>` 通过
- [ ] Task Brief 已创建并更新状态
- [ ] Context Bundle 已保存（如适用）

### 8.2 Gate 审批前检查

- [ ] SSOT 校验通过
- [ ] 所有相关 artifacts 已冻结
- [ ] Manifest 已更新
- [ ] Gate 审批使用 `enforce=True` 模式

---

## 9. 参考文档

- [SSOT 用户指南](SSOT_USER_GUIDE.md)
- [SSOT API 参考](SSOT_API_REFERENCE.md)
- [产出物管理系统架构](../../architecture/artifact-management-system.md)
