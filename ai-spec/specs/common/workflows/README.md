# Workflow Specification Standard

工作流规范标准 - 定义 AI Agent 工作流的标准化格式

## 设计原则

1. **扁平化 steps 结构** - 清晰表达执行顺序，避免深层嵌套
2. **显式版本化** - agent 和 contract 必须带版本号 (如 `@v1`)
3. **统一失败处理** - 每个 step 都有明确的失败处理策略
4. **依赖声明** - 通过 `input.source` 显式声明步骤间依赖

## 目录结构

```
workflows/
├── README.md                    # 本文档
├── _template/v1/workflow.yaml   # 工作流模板
└── {workflow-name}/v1/
    └── workflow.yaml            # 具体工作流定义
```

## 规范格式

### 顶级字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 工作流唯一标识 (snake_case) |
| `version` | string | ✅ | 版本号，如 `v1` |
| `metadata` | object | ✅ | 工作流元数据 |
| `steps` | array | ✅ | 步骤定义列表 |
| `constraints` | object | ❌ | 工作流级约束 |
| `completion` | object | ❌ | 完成条件定义 |

### Step 定义

```yaml
steps:
  - id: step_id                    # 步骤唯一标识
    agent: agent_name@v1           # Agent 引用 (必须带版本)
    contract: contract_name@v1     # Contract 引用 (必须带版本)

    metadata:
      name: Step Name
      name_zh: 步骤名称
      description: 步骤描述

    input:                         # 输入依赖
      - source: previous_step_id   # 引用其他步骤输出
        required: true
      - file: "path/to/file.md"    # 直接引用文件
        required: false

    output:
      file: "output/path.md"       # 输出文件路径
      freeze: false                # 是否需要人类审批

    on_failure:                    # 失败处理 (必填)
      retry: 2                     # 重试次数
      fallback: human_review       # 回退策略
```

### 版本化引用格式

**Agent 引用:**
```yaml
agent: product_value_agent@v1
```

**Contract 引用:**
```yaml
contract: product_value_proposal@v1
```

版本号格式: `@v{N}` (如 `@v1`, `@v2`)

### 失败处理策略 (on_failure)

每个 step **必须**定义 `on_failure`:

```yaml
on_failure:
  retry: 2                    # 重试次数 (0-5)
  fallback: human_review      # 回退策略
```

**回退策略选项:**
| 策略 | 说明 |
|------|------|
| `human_review` | 交由人类审查决定 |
| `skip` | 跳过此步骤继续执行 |
| `abort` | 终止整个工作流 |

### 人类审批配置 (human_role)

用于冻结步骤或需要人类决策的步骤:

```yaml
human_role:
  type: decision              # decision | validation | review
  actions:
    - approve: 进入下一阶段
    - request_revision: Agent 重新生成
    - reject: 终止流程
```

**角色类型:**
| 类型 | 说明 |
|------|------|
| `decision` | 人类做出关键决策 |
| `validation` | 人类验证对齐/一致性 |
| `review` | 人类审阅但不阻塞 |

## 示例

### 最小化工作流

```yaml
id: keyword_discovery

version: v1

metadata:
  name: Keyword Discovery
  name_zh: 关键词发现

steps:
  - id: search
    agent: search_agent@v1
    contract: search_result@v1
    on_failure:
      retry: 2
      fallback: human_review
```

### 带冻结点的工作流

```yaml
id: value_definition

version: v1

metadata:
  name: Value Definition Pipeline
  name_zh: 价值定义流水线

steps:
  - id: analyze_value
    agent: value_analyzer@v1
    contract: value_analysis@v1
    output:
      file: "output/value_analysis.md"
      freeze: false
    on_failure:
      retry: 2
      fallback: human_review

  - id: freeze_value
    agent: approval_reviewer@v1
    contract: frozen_value@v1
    input:
      - source: analyze_value
        required: true
    output:
      file: "output/frozen/{project}-value-freeze.md"
      freeze: true
    human_role:
      type: decision
      actions:
        - approve: 进入下一阶段
        - reject: 终止流程
    on_failure:
      retry: 1
      fallback: human_review

completion:
  required_outputs:
    - "output/frozen/{project}-value-freeze.md"
```

## 约束规则

### 冻结传递 (freeze_propagation)

冻结文件一旦生成，下游步骤必须基于冻结版本工作。如需修改上游冻结:
1. 解冻上游文件
2. 完成修改
3. 重新冻结
4. 重新执行所有下游步骤

### 禁止回溯 (no_backtracking)

Agent 不得在当前步骤试图修改上游冻结内容。如发现上游问题:
1. 在输出中标记问题
2. 请求人类审批回退
3. 等待解冻后再修改

### 边界强制 (boundary_enforcement)

每个 Agent 的 `non_goals` 是硬性约束。违反 `non_goals` 的输出将被视为无效，必须重新生成。

## 相关资源

- **Agent 规范**: `specs/agents/`
- **Contract 规范**: `specs/contracts/`
- **模板**: `_template/v1/workflow.yaml`
