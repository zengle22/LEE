# SSOT 真理链管理系统 - 用户指南

## 1. 概述

SSOT (Single Source of Truth) 真理链管理系统是 LEE 产出物管理体系的核心组件，用于确保产出物之间的关联关系完整、可追溯。

### 1.1 核心概念

**真理链 (Truth Chain)**: 从需求到实现的完整追溯链：
```
PRD Contract → API Contract → Implementation → Test Plan
   (需求)    →    (协议)   →    (代码)    →   (测试)
```

**SSOT 规则 (v1.0)**:
1. 所有 `api_contract` 必须通过 `derived_from` 指向某个 `prd_contract`
2. 所有 `implementation` (CODE_REF) 必须通过 `implements` 指向至少一个 `api_contract`
3. 所有 `test_plan` 必须通过 `verifies` 指向至少一个 PRD 或 API

### 1.2 产出物类型

| 类型 | 类别 | 说明 |
|------|------|------|
| CONTRACT | `prd_contract` | PRD 契约（真理链起点） |
| CONTRACT | `api_contract` | API 契约 |
| CONTRACT | `test_plan` | 测试计划 |
| CODE_REF | `implementation` | 代码实现 |
| DOCUMENT | `task_brief` | 任务简报（压缩视图） |
| DOCUMENT | `task_context_bundle` | 上下文 Bundle（展开视图） |

---

## 2. CLI 命令

### 2.1 SSOT 校验命令

#### `lee ssot validate`

校验 SSOT 真理链完整性。

```bash
# 基本用法 - 校验所有 artifacts
lee ssot validate

# 校验指定 run
lee ssot validate --run-id <run_id>

# 校验指定 release
lee ssot validate --release <release_tag>

# enforce 模式 - 失败时退出码非零
lee ssot validate --enforce
```

**输出示例**:
```
# 通过
✅ SSOT validation passed.

# 失败
❌ SSOT validation failed:
  - api_contract ART-00002 missing derived_from
  - implementation ART-00003 missing implements
```

### 2.2 SSOT 索引命令

#### `lee ssot build-index`

构建/更新 SSOT 索引缓存。

```bash
# 构建索引（默认输出到 .artifacts/trace/ssot-index.yaml）
lee ssot build-index

# 自定义输出路径
lee ssot build-index -o /path/to/index.yaml

# 仅构建指定 release 的索引
lee ssot build-index --release v1.0
```

**输出示例**:
```
✅ SSOT index built: .artifacts/trace/ssot-index.yaml
   Nodes: 15, Edges: 12
```

### 2.3 影响分析命令

#### `lee ssot impact`

分析某个 artifact 的影响范围（依赖者）。

```bash
# 基本用法 - 表格格式
lee ssot impact <artifact_id>

# JSON 格式输出
lee ssot impact <artifact_id> --format json
```

**输出示例**:
```
# 表格格式
Impact analysis for ART-00001:

Direct Dependents:
  - ART-00002 (api_contract)

Indirect Dependents:
  - ART-00003 (implementation)

Verifiers (Tests):
  - ART-00004 (test_plan)

# JSON 格式
{
  "direct_dependents": ["ART-00002"],
  "indirect_dependents": ["ART-00003"],
  "verifiers": ["ART-00004"]
}
```

### 2.4 真理链展示命令

#### `lee ssot show-chain`

显示某个 artifact 的真理链路径（追溯到源头）。

```bash
# 基本用法 - 表格格式
lee ssot show-chain <artifact_id>

# JSON 格式输出
lee ssot show-chain <artifact_id> --format json
```

**输出示例**:
```
# 表格格式
Truth chain for ART-00002:

[0] ART-00002 (api_contract)
  [1] ART-00001 (prd_contract)

# JSON 格式
[
  {"id": "ART-00002", "type": "CONTRACT", "category": "api_contract", "relation": ""},
  {"id": "ART-00001", "type": "CONTRACT", "category": "prd_contract", "relation": "derived_from"}
]
```

---

## 3. Task Brief 管理

### 3.1 列出 Task Brief

```bash
# 列出所有 Task Brief
lee task-brief list

# 按 run ID 过滤
lee task-brief list --run-id <run_id>

# 按部门过滤
lee task-brief list --department backend

# JSON 格式输出
lee task-brief list --format json
```

### 3.2 查看 Task Brief 详情

```bash
# YAML 格式（默认）
lee task-brief show <brief_id>

# JSON 格式
lee task-brief show <brief_id> --format json

# 纯文本格式
lee task-brief show <brief_id> --format text
```

### 3.3 创建 Task Brief

```bash
lee task-brief create \
  --run-id <run_id> \
  --department <department> \
  --title "任务标题" \
  --description "任务描述" \
  --task-type feature \
  --scope-include "功能 1" \
  --scope-include "功能 2" \
  --acceptance "验收标准 1" \
  --acceptance "验收标准 2"
```

**参数说明**:
- `--task-type`: `feature`, `bugfix`, `incident`, `refactor`
- `--scope-include`: 可多次指定，包含范围
- `--scope-exclude`: 可多次指定，排除范围
- `--acceptance`: 可多次指定，验收标准
- `--risks`: 可多次指定，风险项

---

## 4. Context Bundle 管理

### 4.1 列出 Context Bundles

```bash
# 列出所有 Context Bundles
lee context list

# 按 run ID 过滤
lee context list --run-id <run_id>

# 按部门过滤
lee context list --department backend

# 按时间排序
lee context list --order-by created_at

# JSON 格式输出
lee context list --format json
```

### 4.2 查看 Context Bundle 详情

```bash
# YAML 格式（默认）
lee context show <bundle_id>

# JSON 格式
lee context show <bundle_id> --format json

# 纯文本格式
lee context show <bundle_id> --format text
```

---

## 5. 版本兼容性

### 5.1 Context Bundle 版本

| 版本 | 特性 | 格式 |
|------|------|------|
| v0.9 | 仅 `prompt_text` | 简化版 |
| v1.0 | `artifacts` + `prompt_snapshot` | 完整版 |

**v0.9 格式示例**:
```yaml
id: TCTX-001
run_id: RUN-001
step_id: step-1
llm_call_id: CALL-001
prompt_text: "完整的 prompt 内容"
created_at: "2026-03-01T10:00:00"
```

**v1.0 格式示例**:
```yaml
id: TCTX-001
run_id: RUN-001
step_id: step-1
llm_call_id: CALL-001
artifacts:
  prd: ["ART-001"]
  api_contracts: ["ART-002"]
prompt_snapshot:
  system: "You are a helpful assistant."
  user: "Help me with this task."
created_at: "2026-03-01T10:00:00"
```

### 5.2 Task Brief 状态

| 状态 | 说明 | 转换 |
|------|------|------|
| `draft` | 草稿状态，可编辑 | → `confirmed` |
| `confirmed` | 已确认，执行中 | → `completed` |
| `completed` | 已完成，归档 | - |

---

## 6. 故障排查

### 6.1 常见问题

**Q1: `lee ssot validate` 提示 "SSOT validation failed"**

检查错误信息中的具体规则违反：
```bash
# 查看详细错误
lee ssot validate

# 使用 show-chain 查看具体 artifact 的链接
lee ssot show-chain <artifact_id>
```

**Q2: CLI 命令找不到 artifacts**

确保当前工作目录包含 `.artifacts/` 目录，或 artifacts 在正确的路径下。

**Q3: Windows 上运行提示 `fcntl` 错误**

已修复，请确保代码已更新到最新版本。

### 6.2 获取帮助

```bash
# 查看主帮助
lee --help

# 查看子命令帮助
lee ssot --help
lee ssot validate --help
lee task-brief --help
lee context --help
```

---

## 7. 最佳实践

1. **每次创建 artifacts 后运行校验**: `lee ssot validate --run-id <run_id>`
2. **Gate 审批前必须通过 SSOT 校验**
3. **使用 Task Brief 记录任务上下文**
4. **使用 Context Bundle 记录 LLM 调用历史**
5. **定期构建索引**: `lee ssot build-index`

---

## 8. 参考文档

- [SSOT API 参考](SSOT_API_REFERENCE.md)
- [SSOT 最佳实践](SSOT_BEST_PRACTICES.md)
- [产出物管理系统架构](../../architecture/artifact-management-system.md)
