# OpenSpec Integration Skill v1.0

> **技能类型**: 确定性能力 (工具操作)
> **无决策**: 仅执行 OpenSpec CLI 命令

## 概述

提供 OpenSpec CLI 的封装能力，用于 Phase 内的规范管理。

## 能力清单

### 1. 初始化 (Initialize)

```bash
# 在 Phase 目录下初始化 OpenSpec 工作空间
openspec init {phase_dir}/openspec
```

**输入**:
- `phase_dir`: Phase 目录路径

**输出**:
- `openspec/project.md`
- `openspec/specs/`
- `openspec/changes/`

### 2. 验证 (Validate)

```bash
# 验证变更提案
openspec validate {change-id} --strict
```

**输入**:
- `change-id`: 变更 ID

**输出**:
- 验证结果 (pass/fail)
- 错误列表 (如有)

### 3. 查看 (Show)

```bash
# 查看变更详情
openspec show {change-id} --json --deltas-only
```

**输入**:
- `change-id`: 变更 ID

**输出**:
- 变更详情 JSON

### 4. 列表 (List)

```bash
# 列出活动变更
openspec list

# 列出规范
openspec list --specs
```

**输出**:
- 变更/规范列表

### 5. 归档 (Archive)

```bash
# 归档已完成的变更
openspec archive {change-id} --yes
```

**输入**:
- `change-id`: 变更 ID

**输出**:
- 归档路径: `changes/archive/YYYY-MM-DD-{change-id}/`

## 目录结构规范

```
{phase_dir}/openspec/
├── project.md              # 项目配置
├── specs/                  # 当前真实状态
│   └── {capability}/
│       ├── spec.md
│       └── design.md
└── changes/                # 变更提案
    ├── {change-id}/
    │   ├── proposal.md
    │   ├── tasks.md
    │   ├── design.md
    │   └── specs/
    └── archive/
```

## 格式规范

### Requirement 格式
```markdown
### Requirement: {Title}
{Description using SHALL/MUST}

#### Scenario: {Scenario Name}
- **GIVEN** {precondition}
- **WHEN** {action}
- **THEN** {expected result}
```

### Delta 操作
- `## ADDED Requirements` - 新增
- `## MODIFIED Requirements` - 修改
- `## REMOVED Requirements` - 删除
- `## RENAMED Requirements` - 重命名

## 错误处理

| 错误 | 原因 | 处理 |
|------|------|------|
| "Change must have at least one delta" | 无 spec delta 文件 | 创建 specs/ 目录和 delta 文件 |
| "Requirement must have at least one scenario" | Scenario 格式错误 | 使用 `#### Scenario:` 格式 |
| "Silent scenario parsing failures" | 格式不正确 | 检查 `#### Scenario:` 精确格式 |

## 约束

- ❌ 不做决策
- ❌ 不判断内容质量
- ❌ 不修改 OpenSpec 行为
- ✅ 只执行 CLI 命令
- ✅ 只返回命令结果
