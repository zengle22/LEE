# Dev 模块全面评审报告

**评审日期**: 2026-02-27
**评审范围**: Dev 部门所有功能模块
**评审重点**: 功能缺失、集成断层、业务流连贯性

---

## 评审结论总览

| 问题类型 | 严重程度 | 数量 | 状态 |
|----------|----------|------|------|
| Agent 引用错误 | 🔴 高 | 1 | 阻塞运行 |
| Contract Schema 缺失 | 🔴 高 | 8 | 阻塞验证 |
| ArtifactManager 未集成 | 🟡 中 | 1 | 功能缺失 |
| L3 实例生成集成 | 🟢 低 | 1 | 已实现 |

---

## 一、Agent 引用错误 (🔴 阻塞)

### 问题描述

L2 v3 工作流中引用了不存在的 Agent ID。

### 详情

**错误引用位置**: `spec-global/departments/dev/workflows/feature/v3/workflow.yaml`

```yaml
# 第 34 行和第 118、166 行
agents:
  - agent.dev.backend_engineer    # ❌ 不存在

# ...
run: agent.dev.backend_engineer   # ❌ 不存在
```

**实际存在的 Agent**: `agent.dev.go_backend_engineer`

### 影响

- 工作流无法正确加载 Agent 配置
- 后端开发阶段无法执行
- 整个 L2 工作流会失败

### 修复建议

将所有 `agent.dev.backend_engineer` 替换为 `agent.dev.go_backend_engineer`：

```yaml
agents:
  - agent.dev.go_backend_engineer   # ✅ 正确

run: agent.dev.go_backend_engineer  # ✅ 正确
```

---

## 二、Contract Schema 缺失 (🔴 阻塞)

### 缺失的 Contract Schema 列表

| Schema 路径 | 引用位置 | 用途 | 严重程度 |
|-------------|----------|------|----------|
| `contracts/code-diff/v1/schema.json` | L3 v3 步骤 3 (implement) | 验证代码补丁输出 | 🔴 高 |
| `contracts/test-report/v1/schema.json` | L3 v3 步骤 4 (run_tests) | 验证测试报告输出 | 🔴 高 |
| `contracts/code-review/v1/schema.json` | L3 v3 步骤 5 (code_review) | 验证代码评审输出 | 🔴 高 |
| `contracts/retrospective/v1/schema.json` | L3 v3 步骤 6 (retrospective) | 验证复盘输出 | 🟡 中 |
| `contracts/l2-outputs/v1/schema.json` | L2 v3 outputs | 验证 L2 输出汇总 | 🔴 高 |
| `contracts/l3-outputs/v1/schema.json` | L3 v3 outputs | 验证 L3 输出汇总 | 🔴 高 |
| `contracts/l3-phase-context/v1/schema.json` | L3 v3 inputs | 验证 L3 上下文输入 | 🔴 高 |
| `contracts/requirement-analysis/v1/schema.json` | L3 v3 步骤 1 | 验证需求分析输出 | 🟡 中 |

### 影响分析

1. **契约验证无法执行**: 8 个 schema 缺失导致工作流的输入/输出验证完全失效
2. **L3 v3 无法运行**: 6 步 TDD 流程中 5 步的验证缺失
3. **重试机制失效**: `step_output_validation.on_failure: retry` 配置无法工作

### 修复建议

需要创建以下 Contract Schema 文件：

```json
// contracts/code-diff/v1/schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Code Diff Contract",
  "type": "object",
  "required": ["files_changed", "diff_summary"],
  "properties": {
    "files_changed": {
      "type": "array",
      "items": {
        "type": "object",
        "properties": {
          "path": {"type": "string"},
          "change_type": {"type": "string", "enum": ["added", "modified", "deleted"]}
        }
      }
    },
    "diff_summary": {"type": "string"}
  }
}

// contracts/test-report/v1/schema.json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "Test Report Contract",
  "type": "object",
  "required": ["test_results", "coverage"],
  "properties": {
    "test_results": {
      "type": "object",
      "properties": {
        "total": {"type": "number"},
        "passed": {"type": "number"},
        "failed": {"type": "number"}
      }
    },
    "coverage": {
      "type": "object",
      "properties": {
        "percentage": {"type": "number", "minimum": 0, "maximum": 100}
      }
    }
  }
}

// ... 其他 6 个 schema
```

---

## 三、ArtifactManager 未集成 (🟡 中)

### 问题描述

`ArtifactManager` 和 `ManifestManager` 已实现，但 `Orchestrator` 中未集成使用。

### 详情

**已实现的模块**:
- `src/lee/orchestrator/execution/artifacts/manager.py` - ArtifactManager
- `src/lee/orchestrator/execution/artifacts/manifest.py` - ManifestManager
- 完整的测试覆盖

**集成状态**:
```python
# src/lee/orchestrator/execution/orchestrator.py
# ❌ 没有 import ArtifactManager
# ❌ 没有 self.artifact_manager
# ❌ 步骤输出没有记录到 ArtifactManager
```

### 影响

1. **产出物无法追踪**: 工作流执行过程中的产出物没有被统一管理
2. **Handover 机制缺失**: 无法实现跨部门/跨阶段的产出物移交
3. **Run 历史缺失**: 无法查询历史 run 的产出物
4. **归档功能缺失**: 无法冻结和归档完成的 run

### 修复建议

在 `Orchestrator` 中集成 `ArtifactManager`:

```python
# orchestrator.py
from .execution.artifacts import ArtifactManager, ManifestManager

class Orchestrator:
    def __init__(self, ...):
        # ...
        artifacts_root = Path(project_root) / ".artifacts"
        self.artifact_manager = ArtifactManager(artifacts_root)
        self.manifest_manager = ManifestManager(
            artifacts_root,
            registry=self.artifact_manager.registry
        )

    async def _execute_step(self, ...):
        # 执行步骤
        output = await runner.run(...)

        # 记录产出物
        if output.get("files"):
            for file_path in output["files"]:
                self.artifact_manager.adopt(
                    run_id=self.workflow_id,
                    artifact_type=ArtifactType.CODE_REF,
                    file_path=file_path,
                    category="step_output"
                )
```

---

## 四、L3 实例生成集成 (🟢 已实现)

### 状态

L3 spawning 功能已正确实现在 `Orchestrator._spawn_l3_for_point()` 中。

**实现位置**: `src/lee/orchestrator/execution/orchestrator.py:1744-1820`

**功能点**:
- ✅ 使用 L3 v3 模板 (`task-l3-v3-template.yaml`)
- ✅ 动态生成 L3 实例文件
- ✅ 发布 `L3_SPAWNED` 事件
- ✅ L3 完成等待机制

---

## 五、业务流连贯性分析

### L2 v3 工作流流程图

```
┌─────────────────────────────────────────────────────────────────┐
│  L2 v3: Feature Development                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  P1: p1_contract_design (M)                                    │
│     └─ agent: agent.dev.backend_engineer ❌                     │
│        → OUTPUT: output/api-contract.yaml                       │
│                                                                 │
│  P2: p2_parallel_development (M)                               │
│     ├─ p2_1_fe_development (M) ──────┐                         │
│     │  └─ spawn_l3: template.dev.task_l3_v3 ✅                │
│     │     → OUTPUT: output/fe-l3-output.json                   │
│     │                                                             │
│     └─ p2_2_be_development (M)       │                         │
│        └─ agent: agent.dev.backend_engineer ❌                 │
│           → OUTPUT: output/be-code-diff.patch                  │
│                                                                 │
│  P3: p3_integration (S)               │                         │
│     └─ agent: agent.dev.uniapp_frontend_engineer ✅            │
│        → INPUT: fe_output, be_output                            │
│        → OUTPUT: output/integration-test-report.json            │
│                                                                 │
│  P4: p4_smoke (S)                                              │
│     └─ agent: agent.dev.uniapp_frontend_engineer ✅            │
│        → OUTPUT: output/smoke-test-report.json                 │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 业务流断层点

1. **P1 → P2**: API Contract 传递路径存在，但验证 schema 缺失
2. **P2.1 → P3**: FE L3 输出路径已定义，但 `l3-outputs` schema 缺失
3. **P2.2 → P3**: BE 输出路径已定义，但 `code-diff` schema 缺失
4. **P3 → P4**: 集成测试报告到冒烟测试的传递未明确定义

---

## 六、优先级修复建议

### P0 (必须立即修复 - 阻塞运行)

1. **修复 Agent 引用错误**
   - 文件: `spec-global/departments/dev/workflows/feature/v3/workflow.yaml`
   - 修改: `agent.dev.backend_engineer` → `agent.dev.go_backend_engineer`

2. **创建缺失的 Contract Schema**
   - `contracts/code-diff/v1/schema.json`
   - `contracts/test-report/v1/schema.json`
   - `contracts/l2-outputs/v1/schema.json`
   - `contracts/l3-outputs/v1/schema.json`
   - `contracts/l3-phase-context/v1/schema.json`

### P1 (高优先级 - 影响功能)

3. **创建剩余的 Contract Schema**
   - `contracts/code-review/v1/schema.json`
   - `contracts/retrospective/v1/schema.json`
   - `contracts/requirement-analysis/v1/schema.json`

4. **集成 ArtifactManager 到 Orchestrator**
   - 在步骤执行时记录产出物
   - 在 run 完成时生成 manifest

### P2 (中优先级 - 改进体验)

5. **完善 L2/L3 输出传递**
   - 明确定义 P3 → P4 的数据传递
   - 添加集成测试到冒烟测试的契约验证

---

## 七、验证检查清单

使用以下命令验证修复：

```bash
# 1. 验证 Agent 引用
python scripts/spec_validate.py

# 2. 检查 Contract Schema 存在性
ls spec-global/departments/dev/contracts/*/*/schema.json

# 3. 验证工作流加载
python -c "
from lee.orchestrator.execution.spec_global_parser import WorkflowSpecParser
parser = WorkflowSpecParser()
wf = parser.parse('spec-global/departments/dev/workflows/feature/v3/workflow.yaml)
print(f'Loaded: {wf.id}')
"
```

---

## 附录

### A. 现有 Contract Schema 完整列表

```
✅ api-contract/v1/schema.json
✅ bug-fix-plan-contract/v1/schema.json
✅ bug-fix-status-contract/v1/schema.json
✅ bug-root-cause-contract/v1/schema.json
✅ bug-triage-output/v1/schema.json
✅ completion-check-input/v1/schema.json
✅ completion-check-output/v1/schema.json
✅ development-plan-contract/v1/schema.json
✅ execution-log-contract/v1/schema.json
✅ frozen-dev-package-contract/v1/schema.json
✅ frozen-technical-architecture-contract/v1/schema.json
✅ knowledge-capture-contract/v1/schema.json
✅ phase-contract/v1/schema.json
✅ requirement-analysis-contract/v1/schema.json
✅ test-code-diff-contract/v1/schema.json
✅ test-review-contract/v1/schema.json
```

### B. 现有 Agent 完整列表

```
✅ agent.dev.bug_fix_implementer
✅ agent.dev.bug_fix_planner
✅ agent.dev.bug_fix_verifier
✅ agent.dev.bug_knowledge_curator
✅ agent.dev.bug_reproducer
✅ agent.dev.bug_root_cause_analyst
✅ agent.dev.bug_technical_debt_recorder
✅ agent.dev.bug_triage
✅ agent.dev.code_completion_checker
✅ agent.dev.code_reviewer
✅ agent.dev.code_self_reviewer
✅ agent.dev.contract_designer
✅ agent.dev.freeze_orchestrator
✅ agent.dev.git_committer
✅ agent.dev.go_backend_engineer
✅ agent.dev.integration_planner
✅ agent.dev.smoke_tester
✅ agent.dev.tech_architect
✅ agent.dev.uniapp_frontend_engineer
✅ agent.dev.unit_test_runner
✅ agent.dev.unit_test_writer
```

### C. 现有 Skill 完整列表

```
✅ skill.file.read
✅ skill.git.checkout
✅ skill.lint.ruff
✅ skill.test.pytest
✅ skill.test.vitest
```

---

**报告生成**: 2026-02-27
**下次评审**: P0/P1 修复完成后
