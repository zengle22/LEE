---
description: Debug workflow end-to-end: run with inputs, force completion, validate outputs (directory/naming/structure/fields/semantics), no manual edits - only workflow re-runs via corresponding agents
---

# LEE Dev Debug Workflow

**调试指定工作流，强制跑通完整链路并校验产出物**

## 核心规则（铁律）

| 规则 | 说明 |
|------|------|
| 🚫 禁止手动修改文件 | 不允许直接编辑工作流产出的任何文件 |
| ✅ 只能跑工作流 | 所有调整必须通过 re-run workflow 实现 |
| 🤖 调用对应 agent | 工作流调整调用 `spec-global/core/agents` 或对应部门 agents |
| 🔍 完整校验 | 文件目录、命名、内容结构、字段、语义全部检查 |
| 🛡️ 代码修改必调 safe-code | 涉及代码修改时必须先调用 `/lee-safe-code` skill |
| 🚪 验收 gate 必须通过 | 修改完成后必须通过 `/gate-review` 验收才能提交 |

## 使用方法

### 方式 1: 直接运行工作流
```bash
# 调试 tech-design 工作流
lee run dev.tech-design-l3 --project-dir <repo> --spec <spec-file>
```

### 方式 2: 使用此 Skill 调试

**输入**：
- `workflow_key`: 工作流 key（如 `dev.tech-design-l3`）
- `spec_file`: 输入 spec 文件路径
- `project_dir`: 项目目录

**执行步骤**：
1. 运行工作流
2. 等待完成
3. 校验所有输出
4. 发现问题 → 调用对应 agent 修复 → 重新运行
5. 循环直到所有校验通过
6. **涉及代码修改时**：
   - 调用 `/lee-safe-code` 进行安全编码约束检查
   - 调用 `/gate-review` 进行人工验收确认
   - 验收通过后才可提交 git

## 校验清单（必须全部通过）

### 1. 目录校验
- [ ] 产出物在正确的目录下
- [ ] 目录层级符合契约定义

### 2. 命名校验
- [ ] 文件名符合命名规范（如 `TECH-{id}__tech-design.md`）
- [ ] 无命名冲突

### 3. 结构校验
- [ ] YAML front matter 完整
- [ ] 必需章节都存在
- [ ] 章节顺序正确

### 4. 字段校验
- [ ] 必需字段存在
- [ ] 字段类型正确
- [ ] 字段值符合约束

### 5. 语义校验
- [ ] 内容与输入 traceability 一致
- [ ] 无遗漏需求点
- [ ] 符合 governing ADRs 约束

## 输出报告格式

```markdown
## Workflow Debug Report

### Workflow Info
| Field | Value |
|-------|-------|
| Workflow ID | `instance.xxx` |
| Template | `template.xxx` |
| Status | completed / failed / blocked |
| Steps | N/M passed |

### Input
- formal_ssot_id: ...
- source_refs: [...]

### Validation Results

#### ✗ Failed (N issues)
| # | Type | Location | Expected | Actual |
|---|------|----------|----------|--------|
| 1 | field | path:line | ... | ... |

#### ✓ Passed
- [check list]

### Fix Actions
| # | Agent | Action | Status |
|---|-------|--------|--------|
| 1 | agent.xxx | ... | done/pending |
```

## 可用 Agent

### Core Agents
- `agent.governance.workflow_spec_maintainer`: 工作流规范
- `agent.governance.spec_reviewer`: Spec 审查

### Dev Agents
- `agent.dev.tech_architect`: 技术架构
- `agent.dev.code_self_reviewer`: 自审查
- `agent.dev.contract_designer`: 协议设计

## Bug 描述格式

发现 Bug 时，必须输出：

```markdown
**Bug**: [简短描述]
- **Type**: directory/naming/structure/field/semantic
- **Severity**: blocker/major/minor/nit
- **Location**: `path/to/file:line`
- **Expected**: [预期内容]
- **Actual**: [实际内容]
- **Violation**: [违反的契约/规范]
- **Fix Agent**: `agent.xxx`
```

## 示例

```yaml
# debug-spec.yaml
formal_ssot_id: FEAT-001
source_refs:
  - spec/requirements/shared/FEAT-001__feat-freeze.md
governing_adrs:
  - ADR-008
repo_context:
  repo_id: my-project
  type: backend
```

运行：
```bash
lee run dev.tech-design-l3 --spec debug-spec.yaml --project-dir .
```

等待完成后，逐项校验输出，发现问题则调用对应 agent 修复后重新运行。

## 代码修改场景（重要）

当调试的工作流产出物涉及**代码文件**（`.py`、`.ts`、`.js` 等）修改时：

### 1. 调用 Safe Code Skill
```bash
/lee-safe-code
```
- 检查代码复用情况
- 验证代码质量
- 确保测试覆盖率
- 避免重复代码

### 2. 调用 Gate Review 验收
```bash
/gate-review
```
- 人工验收修改内容
- 确认符合契约要求
- 批准后方可提交 git

### 3. 提交 Git
验收通过后，执行：
```bash
git add <modified_files>
git commit -m "<conventional_commit_message>"
```
