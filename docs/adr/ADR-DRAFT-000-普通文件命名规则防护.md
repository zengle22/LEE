# ADR-DRAFT-000: 普通文件命名规则防护机制

**日期**: 2026-03-17
**状态**: Draft (Backlog)
**优先级**: P2 (中低)
**标签**: security, file-system, agent-constraints, naming-convention

---

## 背景

LEE Framework 通过 `code_executor_scope.py` 实现了目录级别的写入防护，防止 agent 将文件写入未授权目录。然而，对于**授权目录内的文件命名**，当前实现缺乏强制性的规则约束。

## 问题描述

### 当前防护机制

| 防护层 | 机制 | 防护粒度 |
|--------|------|---------|
| `output_path_guard.py` | 禁止写入 `spec-global/workflows/templates/` | 目录级 |
| `code_executor_scope.py` | write_scope 作用域限制 | 目录级 |
| `project_config.py` | `validate_output_path()` 路径验证 | 目录级 |
| `ArtifactManager.create_ssot()` | SSOT 文件强制命名 | **文件级（仅 SSOT）** |

### 未防护的场景

当前实现**无法约束**以下文件命名行为：

1. **代码文件命名随意**
   ```
   ✅ 允许：src/lee/agents/foo.py
   ✅ 允许：src/lee/agents/random_name.py  # 无约束
   ```

2. **测试文件命名不规范**
   ```
   ✅ 允许：src/lee/agents/tests/test_deliverables_producer.py
   ✅ 允许：src/lee/agents/tests/my_test.py  # 应该是 test_*.py
   ✅ 允许：src/lee/agents/tests/tests_example.py  # 应该是 test_*.py
   ```

3. **文档文件命名随意**
   ```
   ✅ 允许：docs/api/usage-guide.md
   ✅ 允许：docs/api/random.md  # 无约束
   ```

4. **配置文件命名不规范**
   ```
   ✅ 允许：config/settings.yaml
   ✅ 允许：config/my-config.yaml  # 无约束
   ```

### 对比：SSOT 文件的强制命名

SSOT 对象通过 `ArtifactManager.create_ssot()` 创建时，强制执行统一命名规则：

```python
# manager.py:945
filename = f"{artifact_id}__{slug}.md"
# 格式：FEAT-001__user-login.md
```

这种机制确保了：
- 文件名包含正式 ID（如 `FEAT-001`）
- 文件名包含语义化 slug（如 `user-login`）
- 命名一致性，便于追溯和管理

## 解决方案选项

### 选项 A：Contract 声明 + 运行时验证

在 agent/contract 的 outputs 声明中添加文件命名模式：

```yaml
outputs:
  - key: backend_code
    type: file
    path: src/lee/agents/
    pattern: "{agent_name}.py"  # 或使用 regex
    required: true

  - key: test_code
    type: file
    path: src/lee/agents/tests/
    pattern: "test_{agent_name}.py"
    required: true
```

运行时验证：
```python
def _validate_output_naming_pattern(cls, *, step, written_files, project_root):
    for output_spec in step.outputs:
        pattern = output_spec.get("pattern")
        if not pattern:
            continue
        # 验证写入的文件是否匹配模式
```

**优点**：
- 灵活性高，每个 output 可以有不同模式
- 与现有 `declared_output_files` 验证集成

**缺点**：
- 需要修改 contract schema
- 增加配置复杂度

### 选项 B：Convention-based 隐式规则

根据目录路径自动推断命名规则：

```python
NAMING_CONVENTIONS = {
    "tests/": r"^test_.*\.py$",
    "specs/": r"^.*-spec\.md$",
    "api/": r"^.*_api\.py$",
    "config/": r"^[a-z][a-z0-9-]*\.yaml$",
}

def _check_naming_convention(file_path: str) -> bool:
    for dir_pattern, name_pattern in NAMING_CONVENTIONS.items():
        if dir_pattern in file_path:
            filename = Path(file_path).name
            return bool(re.match(name_pattern, filename))
    return True  # 无匹配的约定则放行
```

**优点**：
- 零配置，自动应用
- 易于理解和维护

**缺点**：
- 灵活性较低
- 需要维护约定映射表

### 选项 C：Verifier 后置验证

通过独立的 verifier 在 step 完成后验证：

```yaml
validators:
  - type: naming_convention
    config:
      tests_dir: "^test_.*\\.py$"
      spec_dir: "^.*-spec\\.md$"
```

**优点**：
- 不侵入核心执行逻辑
- 可配置、可扩展

**缺点**：
- 验证发生在写入后
- 需要额外配置

## 优先级评估

### 影响分析

| 风险场景 | 发生概率 | 影响程度 | 当前缓解措施 |
|---------|---------|---------|-------------|
| 测试文件命名不规范 | 高 | 低 | pytest 自动发现可能失败 |
| 代码文件命名混乱 | 中 | 低 | 代码审查可发现 |
| 配置文件命名冲突 | 低 | 中 | 版本控制可追溯 |
| 文档文件难以查找 | 中 | 低 | 目录结构辅助定位 |

### 优先级判定

**优先级：P2（中低）**

理由：
1. 目录级防护已解决主要安全问题
2. 文件命名更多是代码风格/可维护性问题
3. 现有代码审查、CI lint 可部分缓解
4. SSOT 强制命名已覆盖关键 artifact

### 建议实施时机

1. **Phase 1（当前）**：完成目录级防护（已完成 ✅）
2. **Phase 2（未来）**：当出现以下信号时考虑实施：
   - 多次因命名不规范导致的问题
   - 团队规模扩大，需要更强约束
   - 自动化测试/文档生成依赖命名规则

## 临时缓解措施

在正式实现之前，可通过以下方式缓解：

1. **Pre-commit hooks**：在 git 提交时检查命名规则
2. **CI lint 检查**：在 PR 检查中添加命名规则验证
3. **Agent prompting**：在 agent system prompt 中强调命名约定
4. **Code review checklist**：将命名规范纳入审查清单

## 决策

**暂不实施**，保持观察。

当出现明确的业务需求或团队反馈时，再评估采用哪种方案。

## 后续行动

- [ ] 将本文档标记为 draft，纳入 ADR backlog
- [ ] 在团队会议中讨论命名规则需求
- [ ] 收集实际项目中的命名问题案例

## 参考

- [output_path_guard.py](../../src/lee/orchestrator/execution/output_path_guard.py)
- [code_executor_scope.py](../../src/lee/orchestrator/execution/runners/code_executor_scope.py)
- [manager.py - create_ssot](../../src/lee/orchestrator/execution/artifacts/manager.py)
- BUG-2026-003: Unauthorized write error fix
