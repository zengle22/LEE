# Bug Fix L2→L3 降级 Review 报告

## 一、任务概述

**目标**: 将 Bug Fix 工作流从 L2（部门级）降级为 L3（任务级）

**原因**:
- 单个 Bug 修复是任务级操作，应该是 L3
- 批量 Bug 修复 + 发版提测才是部门级操作（L2）

**完成时间**: 2026-02-26

---

## 二、变更汇总

### 2.1 文件变更

| 操作 | 文件 | 说明 |
|------|------|------|
| 删除 | `bug-fix-l2-template.yaml` | 旧的 L2 模板 |
| 新增 | `bug-fix-l3-template.yaml` | 新的 L3 模板 |
| 修改 | `config/workflow-registry.yaml` | 更新注册表 |
| 修改 | `docs/workflow-restructure-review.md` | 更新评审报告 |

### 2.2 Git Commits

```
e8a2c8d fix(dev): downgrade bug-fix from L2 to L3 with clear contracts
```

---

## 三、架构对比

### 3.1 变更前 (L2 - 错误设计)

```yaml
kind: l2_workflow_template
phases:
  - root_cause_analysis    # Direct execution
  - fix_implementation     # Spawns L3 ❌ 过度设计
  - verification           # Spawns L3 ❌ 过度设计
  - merge_review           # Direct execution
```

**问题**:
- 单个 Bug 修复不需要编排多个 L3
- L2 应该用于批量任务，而非单个任务
- spawns_l3 增加了不必要的复杂度

### 3.2 变更后 (L3 - 正确设计)

```yaml
kind: l3_workflow_template
steps:
  - root_cause_analysis    # Agent step
  - fix_implementation     # Agent step
  - verification           # Agent step
  - code_review            # Agent step (新增)
  - merge_decision         # Agent step
```

**改进**:
- 5 个 steps 顺序执行，结构清晰
- 不再 spawns_l3，直接由 Agent 执行
- 新增 code_review 步骤，更完整

---

## 四、输入/输出契约

### 4.1 输入契约 (input_contract)

```yaml
required_fields:
  - bug_id: string          # Bug 标识 (如 BUG-1234)
  - bug_description: string # Bug 详细描述
  - project: string         # 项目名称
  - repo: string            # 仓库名称

optional_fields:
  - reproduction_steps: string  # 复现步骤
  - severity: string            # 严重程度 (critical/high/medium/low)
  - assignee: string            # 指派开发者
  - related_tests: array        # 相关测试
```

### 4.2 输出契约 (output_contract)

```yaml
artifacts:
  - root_cause_report: dev/bug-fixes/{bug_id}/root-cause.md
  - fix_diff: dev/bug-fixes/{bug_id}/fix.patch
  - test_results: dev/bug-fixes/{bug_id}/test-results.yaml
  - review_report: dev/bug-fixes/{bug_id}/review.md
  - merge_report: dev/bug-fixes/{bug_id}/merge.md

status_field: fix_status
values: [init, analyzing, fixing, verifying, reviewing, merging, completed, failed]
```

---

## 五、Workflow Registry 更新

### 5.1 更新前

```yaml
dev.bugfix:
  path: spec-global/departments/dev/workflows/templates/bug-fix-l2-template.yaml
  kind: l2_workflow_template  ❌
  description: "Bug 修复工作流 (L2)"
  required_params:
    - bug_id
    - project
```

### 5.2 更新后

```yaml
dev.bugfix:
  path: spec-global/departments/dev/workflows/templates/bug-fix-l3-template.yaml
  kind: l3_workflow_template  ✅
  description: "Bug 修复工作流 (L3) - 单个 Bug 的完整修复流程"
  required_params:
    - bug_id
    - bug_description  ✅ 新增
    - project
    - repo            ✅ 新增
  optional_params:
    - reproduction_steps  ✅ 新增
    - severity           ✅ 新增
    - assignee           ✅ 新增
```

---

## 六、清理无效条目

移除了 `qa.regression` 工作流注册项，因为文件不存在：
```diff
- qa.regression:
-   path: spec-global/departments/qa/workflows/regression/v1/workflow.yaml
-   description: "回归测试工作流"
```

---

## 七、最终模板清单

### QA 部门 (3 个模板)

| 文件 | 类型 | 用途 |
|------|------|------|
| `test-plan-l2-template.yaml` | L2 | Test Plan 执行 |
| `test-set-l3-template.yaml` | L3 | Test Set 执行 |
| `test-set-production-l3-template.yaml` | L3 | Test Set 生产 |

### Dev 部门 (6 个模板)

| 文件 | 类型 | 用途 |
|------|------|------|
| `feature-l2-template.yaml` | L2 | Feature 开发 |
| `bug-fix-l3-template.yaml` | L3 | Bug 修复 |
| `feature-contract-l3-template.yaml` | L3 | API 协议设计 |
| `feature-fe-l3-template.yaml` | L3 | 前端实现 |
| `feature-be-l3-template.yaml` | L3 | 后端实现 |
| `feature-integration-l3-template.yaml` | L3 | 连调验证 |

---

## 八、L2 vs L3 设计原则

| 维度 | L2 (部门级) | L3 (任务级) |
|------|------------|------------|
| **范围** | 批量任务编排 | 单个任务执行 |
| **Bug Fix** | 批量修复 + 发版 | 单个 Bug 修复 ✅ |
| **Test Set** | 批量 Test Set 执行 | 单个 Test Set 执行 |
| **输出** | 部门级报告 | 任务级产物 |
| **结构** | phases (可 spawns_l3) | steps (直接执行) |

---

## 九、结论

✅ **Bug Fix L2→L3 降级成功完成**

- 架构更符合 L2/L3 设计原则
- 输入/输出契约明确
- 5 步流程清晰完整
- Workflow Registry 已更新
- 无效条目已清理

**下一步**: 合并到 main 分支并 push
