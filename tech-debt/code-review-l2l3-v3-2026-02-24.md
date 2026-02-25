---
title: LEE 项目 Code Review 报告
date: 2026-02-24
version: 1.0.0
reviewers:
  - LEE Team
project: LEE Framework - L2/L3 v3 Workflow
review_scope: L2/L3 v3 工作流改造 + 实例文件位置修复
---

# LEE 项目 Code Review 报告

**审查日期**: 2026-02-24
**审查范围**: L2/L3 v3 工作流改造、实例文件位置修复、单元测试覆盖
**审查人**: LEE Team

---

## 执行摘要

本次 Code Review 涵盖了 L2/L3 v3 工作流改造的全部代码变更，以及实例文件位置修复。总体评估：

| 类别 | 评分 | 说明 |
|------|------|------|
| **代码质量** | B+ | 结构清晰，但有少量硬编码路径 |
| **测试覆盖** | C+ | P0 功能有覆盖，v3 新特性缺少测试 |
| **文档完整性** | B | 模板注释完整，demo 文档已更新 |
| **架构设计** | A- | 目录结构清晰，职责分离良好 |

---

## 1. 本次修改文件清单

### 新增文件

| 文件 | 类型 | 说明 |
|------|------|------|
| `lee/spec-global/departments/dev/workflows/feature/v3/workflow.yaml` | 模板 | L2 v3 工作流模板 |
| `lee/spec-global/departments/dev/workflows/templates/l3/task-l3-v3-template.yaml` | 模板 | L3 v3 模板（6 步 TDD） |
| `examples/l2_l3_v3_demo.py` | 演示 | v3 工作流演示脚本 |

### 修改文件

| 文件 | 修改内容 | 行数 |
|------|----------|------|
| `src/lee/orchestrator/execution/orchestrator.py` | L3 实例路径修复 | ~3 行 |
| `examples/l2_l3_v3_demo.py` | 文档更新 | ~50 行 |
| `tech-debt/tech-debt-2026-02-24.md` | 技术债记录 | ~60 行 |

---

## 2. 代码质量问题

### 🟡 MEDIUM-001: L3 v3 模板 ID 硬编码

**文件**: `orchestrator.py:1781`

**问题描述**:
```python
l3_template_id = "template.dev.task_l3_v3"
```
模板 ID 硬编码，如果模板不存在会导致 spawn 失败。

**影响**:
- 模板 ID 变化时代码需要同步修改
- 缺少 fallback 机制

**修复建议**:
```python
# 尝试使用 v3 模板，失败则 fallback 到 v2
l3_template_id = "template.dev.task_l3_v3"
template = self.template_manager.get_template(l3_template_id)
if not template:
    l3_template_id = "template.dev.task_l3"  # fallback
```

**优先级**: P2

---

### 🟡 MEDIUM-002: 模板路径查找逻辑重复

**文件**: `orchestrator.py:1762-1767`

**问题描述**:
```python
template_base = Path(self.project_root) / "lee" / "spec-global" / ...
l3_template_path = template_base / "l3" / "task-l3-v3-template.yaml"
if not l3_template_path.exists():
    l3_template_path = template_base / "task-l3-template.yaml"
```
这段路径查找逻辑与 `TemplateManager._find_template_file` 重复。

**修复建议**:
统一使用 `TemplateManager.get_template("template.dev.task_l3_v3")` 查找模板，减少路径硬编码。

**优先级**: P2

---

### 🟢 LOW-001: 目录创建缺少错误处理

**文件**: `orchestrator.py:1773` (隐式)

**问题描述**:
```python
l3_path = runtime_dir / "instances" / "l3" / f"{point.id}.yaml"
result = generator.generate_l3_instance(config, str(l3_path))
```
`generate_l3_instance` 内部创建目录，但缺少权限检查。

**修复建议**:
```python
# 在生成前检查目录可写
try:
    l3_path.parent.mkdir(parents=True, exist_ok=True)
except PermissionError as e:
    raise RuntimeError(f"Cannot write to runtime directory: {l3_path.parent}") from e
```

**优先级**: P3

---

### 🟢 LOW-002: 运行时目录路径未统一管理

**文件**: `orchestrator.py:1772`

**问题描述**:
```python
runtime_dir = Path(self.project_root) / ".workflow" if self.project_root else Path(".workflow")
```
运行时目录路径散布在多个地方，缺少统一常量。

**修复建议**:
在配置文件或常量模块中定义：
```python
# lee/orchestrator/config.py
class RuntimePaths:
    WORKFLOW_DIR = ".workflow"
    INSTANCES_DIR = ".workflow/instances"
    L2_INSTANCES = ".workflow/instances/l2"
    L3_INSTANCES = ".workflow/instances/l3"
```

**优先级**: P3

---

## 3. 测试覆盖分析

### 现有测试统计

| 指标 | 数值 |
|------|------|
| 总测试文件 | 80 个 (+1) |
| 总测试用例 | 973 个 (+12) |
| L2/L3 相关测试 | ~27 个 (+12) |
| v3 新特性测试 | 12 个 ✅ |

### ✅ 已添加的测试 (2026-02-24)

**新测试文件**: `tests/orchestrator/test_l2_l3_v3_runtime.py`

| 测试类 | 测试数量 | 覆盖功能 |
|--------|----------|----------|
| `TestRuntimeDirPath` | 3 | runtime_dir 路径逻辑 |
| `TestSpawnL3ForPoint` | 3 | `_spawn_l3_for_point` 完整流程 |
| `TestL3V3Template` | 2 | L3 v3 模板结构和依赖 |
| `TestL2V3Integration` | 2 | L2 v3 complexity 路由 |
| `TestWorkflowGeneratorL3V3` | 2 | WorkflowGenerator L3 v3 生成 |

### 测试覆盖详情

**P1 级别测试（已覆盖）**
- ✅ `runtime_dir` 路径逻辑
- ✅ L3 v3 模板加载
- ✅ `_spawn_l3_for_point` 完整流程
- ✅ 事件发布 (`L3_SPAWNED`)
- ✅ 不同 complexity 级别 spawning

**P2 级别测试（待补充）**
- ⏳ 6 步 TDD 流程端到端执行
- ⏳ L3 实例与 L2 父工作流的状态同步
- ⏳ 复杂度=L 的 PMA 拆分流程

**P3 级别测试（待补充）**
- ⏳ v3 模板不存在时的 fallback 逻辑
- ⏳ 并行 L3 执行
- ⏳ 错误处理和恢复
            "context": {"repos": [{"id": "test-repo", "type": "frontend"}]},
            "phases": [{"id": "frontend_dev", "status": "running", "complexity": "M"}]
        },
    )
    await store.create_workflow(parent)

    # Call _spawn_l3_for_point
    point = Point(
        id="test-point",
        title="Test",
        desc="Test point",
        layer="ui",
        estimated_complexity=Complexity.M,
    )

    l3_id = await orch._spawn_l3_for_point(
        parent_l2_id="l2-parent",
        parent_phase_id="frontend_dev",
        point=point,
        repo_id="test-repo",
    )

    # Verify L3 instance file was created in runtime dir
    runtime_instance_path = tmp_path / ".workflow" / "instances" / "l3" / f"{point.id}.yaml"
    framework_instance_path = tmp_path / "lee" / "spec-global" / ... / "instances" / "l3" / f"{point.id}.yaml"

    assert runtime_instance_path.exists(), "L3 instance should be in .workflow/instances/l3/"
    assert not framework_instance_path.exists(), "L3 instance should NOT be in framework directory"
```

---

## 4. 文档和注释

### ✅ 良好实践

1. **模板文件注释完整**
   - L2 v3 模板有详细的 v3 特性说明
   - L3 v3 模板标注了 6 步 TDD 流程

2. **Demo 脚本结构清晰**
   - 分 9 个章节展示 v3 特性
   - 更新了目录结构说明

### ⚠️ 需要改进

1. **内联注释不足**
   ```python
   # orchestrator.py:1771-1773
   # 缺少注释说明为什么要用 runtime_dir
   runtime_dir = Path(self.project_root) / ".workflow" if self.project_root else Path(".workflow")
   l3_path = runtime_dir / "instances" / "l3" / f"{point.id}.yaml"
   ```

   **建议**:
   ```python
   # 实例文件存放到运行时目录 (.workflow/instances/)，而非框架目录 (lee/...)
   # 这确保运行时生成的数据不会被提交到版本控制
   runtime_dir = Path(self.project_root) / ".workflow" if self.project_root else Path(".workflow")
   l3_path = runtime_dir / "instances" / "l3" / f"{point.id}.yaml"
   ```

---

## 5. 安全性检查

### ✅ 无安全问题

- 路径拼接使用 `Path` 对象，相对安全
- 实例 ID 来自 `point.id`，受控来源
- 运行时目录受 `.gitignore` 保护

---

## 6. 性能考虑

### 无明显性能问题

- 模板加载有缓存（`TemplateManager._cache`）
- L3 spawning 是异步操作

---

## 7. 兼容性

### 向后兼容性

| 组件 | v2 兼容 | 说明 |
|------|---------|------|
| L2 v2 模板 | ✅ | 保持不变 |
| L2 v3 模板 | ✅ | 新增，不影响 v2 |
| L3 v2 模板 | ✅ | fallback 机制 |
| 现有测试 | ✅ | 无影响 |

---

## 8. 审查结论

### ✅ 已完成 (2026-02-24)

| ID | 问题 | 状态 |
|----|------|------|
| TEST-001 | 添加 `runtime_dir` 路径测试 | ✅ 已完成 |
| TEST-002 | 添加 `_spawn_l3_for_point` 测试 | ✅ 已完成 |
| TEST-003 | 添加 L3 v3 模板加载测试 | ✅ 已完成 |
| CODE-GEN-001 | WorkflowGenerator 使用传入模板路径 | ✅ 已完成 |

### 建议修复 (P2)

| ID | 问题 | 预计工时 |
|----|------|----------|
| CODE-001 | L3 v3 模板 ID fallback | 2h |
| CODE-002 | 统一模板路径查找逻辑 | 4h |

### 可选优化 (P3)

| ID | 问题 | 预计工时 |
|----|------|----------|
| CODE-003 | 统一运行时路径常量 | 2h |
| CODE-004 | 添加目录创建错误处理 | 1h |
| DOC-001 | 完善 inline 注释 | 1h |

---

## 9. 后续行动建议

### ✅ 第一阶段 (已完成 - 2026-02-24)
- ✅ 添加 `runtime_dir` 路径测试 (TEST-001)
- ✅ 添加 `_spawn_l3_for_point` 完整测试 (TEST-002)
- ✅ 添加 L3 v3 模板测试 (TEST-003)
- ✅ 修复 WorkflowGenerator 模板路径逻辑

### 第二阶段 (2周内)
- 实现 L3 v3 模板 fallback 逻辑 (CODE-001)
- 添加 6 步 TDD 流程端到端测试
- 添加 L2/L3 状态同步测试

### 第三阶段 (1个月)
- 统一运行时路径管理 (CODE-003)
- 完善文档注释 (DOC-001)
- 添加并行 L3 执行测试

---

## 10. 测试文件清单

### 新增测试文件
```
tests/orchestrator/test_l2_l3_v3_runtime.py
├── TestRuntimeDirPath (3 tests)
├── TestSpawnL3ForPoint (3 tests)
├── TestL3V3Template (2 tests)
├── TestL2V3Integration (2 tests)
└── TestWorkflowGeneratorL3V3 (2 tests)
```

### 测试覆盖的功能
- ✅ L3 实例文件生成到 `.workflow/instances/l3/`
- ✅ L3 spawning 完整流程
- ✅ L3_SPAWNED 事件发布
- ✅ 不同 complexity 级别的 spawning
- ✅ L3 v3 模板结构验证
- ✅ L2 v3 complexity 路由

---

**报告生成**: 2026-02-24
**下次审查**: 2026-03-24
**版本**: 1.0.0
