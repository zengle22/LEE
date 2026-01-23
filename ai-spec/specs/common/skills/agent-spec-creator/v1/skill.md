---
name: agent-spec-creator
description: |
  Agent 规范创建能力。提供创建和维护 Agent Spec 的完整指南，包括：
  - agent.yaml 模板字段详解
  - 目录结构规范
  - 版本管理规则
  - 验证检查清单
  
  当需要创建新的 Agent、更新现有 Agent 规范、或理解 Agent 规范格式时使用此 Skill。
---

# Agent 规范创建指南

本 Skill 提供创建和维护 Agent Spec 的完整知识体系，确保所有 Agent 规范遵循统一标准。

## 能力概述

将用户的 Agent 需求描述转化为标准化的 Agent 规范文件。

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     Agent Spec 创建流程                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   📝 输入阶段                                                            │
│   ┌─────────────────────┐                                               │
│   │ 用户需求描述        │ → Agent 职责、能力、约束等信息                   │
│   └─────────────────────┘                                               │
│            ↓                                                            │
│   🔍 分析阶段                                                            │
│   ┌─────────────────────┐                                               │
│   │ 需求结构化分析      │ → 提取关键信息，确定 Agent 类型                  │
│   └─────────────────────┘                                               │
│            ↓                                                            │
│   📄 生成阶段                                                            │
│   ┌─────────────────────┐                                               │
│   │ 生成 agent.yaml     │ → 填充模板字段                                  │
│   ├─────────────────────┤                                               │
│   │ 生成 README.md      │ → 扩展说明文档（可选）                          │
│   └─────────────────────┘                                               │
│            ↓                                                            │
│   ✅ 验证阶段                                                            │
│   ┌─────────────────────┐                                               │
│   │ 格式与内容验证      │ → 检查完整性和规范性                             │
│   └─────────────────────┘                                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 目录结构规范

### 标准目录结构

所有 Agent 规范必须遵循以下目录结构：

```
specs/agents/
├── _template/                      # 模板目录（供参考，不可直接使用）
│   └── v1/
│       └── agent.yaml
│
├── <agent-name>/                   # Agent 目录（使用 kebab-case 命名）
│   ├── v1/                         # 版本目录
│   │   ├── agent.yaml              # Agent 规范文件（必须）
│   │   └── README.md               # 扩展说明文档（可选）
│   └── v2/                         # 新版本目录（需要时创建）
│       ├── agent.yaml
│       └── README.md
│
└── another-agent/
    └── v1/
        └── agent.yaml
```

### 命名规范

| 项目 | 规范 | 示例 |
|------|------|------|
| Agent 目录名 | kebab-case（小写字母 + 连字符） | `google-keyword-searcher` |
| Agent ID | snake_case（小写字母 + 下划线） | `google_keyword_searcher` |
| 版本目录 | `v` + 数字 | `v1`, `v2`, `v3` |
| 规范文件名 | 固定为 `agent.yaml` | `agent.yaml` |
| 说明文档 | 固定为 `README.md` | `README.md` |

---

## Agent YAML 模板详解

### 完整模板结构

```yaml
# ============================================
# 基础标识 (必填)
# ============================================
id: <agent_name>                    # Agent 唯一标识符，使用 snake_case
version: v1                         # 规范版本，格式: v1, v2, ...
type: llm_agent                     # Agent 类型

# ============================================
# 职责定义 (必填)
# ============================================
responsibility:
  summary: ""                       # 一句话描述 Agent 核心职责
  out_of_scope:                     # 明确列出不属于该 Agent 职责的事项
    - ""

# ============================================
# 模型配置 (可选)
# ============================================
model:
  default: inherit                  # 默认模型
  temperature: 0.2                  # 温度参数

# ============================================
# 输入规范 (必填)
# ============================================
inputs:
  schema_ref: null                  # 输入契约引用
  examples:                         # 输入示例 (建议填写)
    - description: ""
      value: ""

# ============================================
# 输出规范 (必填)
# ============================================
outputs:
  format: markdown                  # 输出格式
  schema_ref: null                  # 输出契约引用
  required_fields:                  # 必须包含的字段列表
    - []
  path_pattern: ""                  # 输出文件路径模式

# ============================================
# 权限声明 (必填)
# ============================================
permissions:
  tools:                            # 可使用的工具列表
    - []
  data_access:                      # 数据访问范围
    - []

# ============================================
# 工作流程 (可选，建议填写)
# ============================================
workflow:
  steps:
    - step: 1
      name: ""
      actions:
        - ""

# ============================================
# 禁止行为 (可选，建议填写)
# ============================================
forbidden_behaviors:
  - id: ""
    name: ""
    description: ""
    violation_example: ""

# ============================================
# 下游 Agent (可选)
# ============================================
downstream:
  - agent_id: ""
    handoff_fields:
      - ""
```

---

## 字段详解

### 1. 基础标识（必填）

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `id` | string | Agent 的唯一标识符，使用 snake_case | `google_keyword_searcher` |
| `version` | string | 规范版本号，格式为 `v` + 数字 | `v1` |
| `type` | enum | Agent 类型 | `llm_agent` / `tool_agent` / `orchestrator` |

**Agent 类型说明：**

| 类型 | 说明 | 使用场景 |
|------|------|----------|
| `llm_agent` | 由 LLM 驱动的智能 Agent | 需要理解、分析、生成内容的场景 |
| `tool_agent` | 工具类 Agent，执行特定操作 | 数据转换、API 调用等确定性任务 |
| `orchestrator` | 编排类 Agent，协调多个 Agent | 复杂工作流的协调和调度 |

### 2. 职责定义（必填）

```yaml
responsibility:
  summary: "通过搜索引擎发现热门关键词和长尾词"
  out_of_scope:
    - "分析用户意图"
    - "商业机会评估"
    - "趋势解读"
```

**填写指南：**
- `summary`: 一句话概括 Agent 的核心职责，清晰明确
- `out_of_scope`: 明确列出**不属于**该 Agent 职责的事项，避免职责边界模糊

### 3. 模型配置（可选）

```yaml
model:
  default: inherit                  # inherit 表示继承父级配置
  temperature: 0.2                  # 0.0-1.0，越低越确定性
  # max_tokens: 4096                # 可选，最大输出 token 数
```

**temperature 推荐值：**

| 值 | 适用场景 |
|-----|----------|
| 0.0 - 0.3 | 事实性分析、数据提取、格式化输出 |
| 0.3 - 0.6 | 结构化写作、代码生成 |
| 0.6 - 1.0 | 创意写作、头脑风暴 |

### 4. 输入规范（必填）

```yaml
inputs:
  schema_ref: contracts/user-signal-input-contract/v1/schema.json
  examples:
    - description: "搜索电商相关热词"
      value: "帮我找一些电商购物相关的热门关键词"
```

**填写指南：**
- `schema_ref`: 如果输入有严格结构，引用对应的契约；用户直接输入则设为 `null`
- `examples`: 提供典型输入示例，帮助理解使用方式

### 5. 输出规范（必填）

```yaml
outputs:
  format: markdown                  # json / markdown / yaml
  schema_ref: contracts/google-keyword-contract/v1/schema.json
  required_fields:
    - keywords
    - longtails
  path_pattern: "output/keywords/{YYYY-MM-DD}_{topic}_关键词.md"
```

**format 选项：**

| 格式 | 使用场景 |
|------|----------|
| `json` | 结构化数据，需要被程序解析 |
| `markdown` | 报告、文档类输出，供人阅读 |
| `yaml` | 配置文件、规范定义 |

### 6. 权限声明（必填）

```yaml
permissions:
  tools:
    - web_search
    - browser_navigate
    - file_write
  data_access:
    - public_internet
    - local_files
```

**常见工具列表：**
- `web_search` - 网络搜索
- `browser_navigate` / `browser_click` / `browser_type` - 浏览器操作
- `file_read` / `file_write` - 文件读写
- `code_execute` - 代码执行

**数据访问范围：**
- `public_internet` - 公开网络资源
- `local_files` - 本地文件系统
- `database` - 数据库访问

### 7. 工作流程（可选，建议填写）

```yaml
workflow:
  steps:
    - step: 1
      name: "收集关键词"
      actions:
        - "使用搜索引擎获取相关建议"
        - "记录热门搜索词"
    - step: 2
      name: "扩展长尾词"
      actions:
        - "基于核心词扩展变体"
        - "分类整理结果"
```

### 8. 禁止行为（可选，建议填写）

```yaml
forbidden_behaviors:
  - id: "skip_validation"
    name: "跳过验证"
    description: "不得跳过数据验证步骤，即使用户要求"
    violation_example: "用户说'不用检查直接输出'，Agent 仍需验证"
```

### 9. 下游 Agent（可选）

```yaml
downstream:
  - agent_id: "user_signal_analyzer"
    handoff_fields:
      - keywords
      - longtails
```

---

## 版本管理规则

### 何时需要新版本

| 变更类型 | 处理方式 | 示例 |
|----------|----------|------|
| 修复错误 | 直接修改当前版本 | 修正拼写错误 |
| 小幅优化 | 直接修改当前版本 | 优化工具列表 |
| 新增可选字段 | 直接修改当前版本 | 添加 examples |
| **破坏性变更** | 创建新版本 (v2) | 修改必填字段结构 |
| **职责范围变更** | 创建新版本 (v2) | 增加/减少核心职责 |
| **输入输出契约变更** | 创建新版本 (v2) | 更换 schema_ref |

### 版本升级流程

1. 创建新版本目录：`specs/agents/<name>/v2/`
2. 复制当前版本文件到新目录
3. 修改 `version` 字段为 `v2`
4. 进行必要的变更
5. 更新 README.md 说明变更内容
6. 保留旧版本目录不动

---

## README.md 编写指南

README.md 用于提供 agent.yaml 无法表达的扩展信息：

```markdown
# <Agent 名称>

## 概述
简要描述 Agent 的用途和价值。

## 使用场景
- 场景1: 描述
- 场景2: 描述

## 详细工作流程
（如果 workflow 字段无法详细表达，在此展开说明）

## 配置说明
（特殊配置项的详细解释）

## 示例
### 输入示例
```
<input_example>
```

### 输出示例
```
<output_example>
```

## 注意事项
- 注意事项1
- 注意事项2

## 变更历史
| 版本 | 日期 | 变更内容 |
|------|------|----------|
| v1 | YYYY-MM-DD | 初始版本 |
```

---

## 验证检查清单

### 创建新 Agent 时：

- [ ] **命名规范**
  - [ ] 目录名使用 kebab-case
  - [ ] ID 使用 snake_case
  - [ ] 名称具有描述性，能体现 Agent 职责

- [ ] **格式验证**
  - [ ] YAML 语法正确
  - [ ] 缩进统一（2 空格）
  - [ ] 中文字符串使用双引号包裹

- [ ] **必填字段完整性**
  - [ ] id - 填写且符合命名规范
  - [ ] version - 填写且格式正确
  - [ ] type - 填写且值有效
  - [ ] responsibility.summary - 填写且清晰
  - [ ] responsibility.out_of_scope - 至少列出一项
  - [ ] inputs - 填写 schema_ref 或标注为 null
  - [ ] outputs - 填写格式和必填字段
  - [ ] permissions - 填写工具和数据访问范围

- [ ] **契约引用有效性**
  - [ ] schema_ref 指向存在的契约文件
  - [ ] 契约版本匹配

- [ ] **职责清晰度**
  - [ ] summary 一句话能理解 Agent 做什么
  - [ ] out_of_scope 明确排除了边界外的事项
  - [ ] 不与其他 Agent 职责重叠

---

## 常见错误与避免

### 错误 1: 职责定义过于宽泛

❌ 错误示例：
```yaml
responsibility:
  summary: "处理用户请求并给出回答"
```

✅ 正确示例：
```yaml
responsibility:
  summary: "通过搜索引擎发现热门关键词和长尾词"
```

### 错误 2: out_of_scope 为空

❌ 错误示例：
```yaml
responsibility:
  out_of_scope: []
```

✅ 正确示例：
```yaml
responsibility:
  out_of_scope:
    - "分析用户意图"
    - "商业机会评估"
```

### 错误 3: ID 与目录名格式不一致

❌ 错误：目录名 `google-keyword-searcher`，ID `googleKeywordSearcher`

✅ 正确：目录名 `google-keyword-searcher`，ID `google_keyword_searcher`

### 错误 4: 权限声明不完整

❌ 错误示例：
```yaml
permissions:
  tools: []
```

✅ 正确示例：
```yaml
permissions:
  tools:
    - web_search
    - file_write
  data_access:
    - public_internet
```

---

## 使用方式

### 创建新 Agent

1. 确定 Agent 名称（kebab-case）
2. 创建目录：`specs/agents/<agent-name>/v1/`
3. 复制模板：从 `_template/v1/agent.yaml` 开始
4. 填充字段：根据本指南填写各字段
5. 验证：使用检查清单验证
6. 可选：创建 README.md 补充说明

### 更新现有 Agent

1. 判断变更类型（参见版本管理规则）
2. 小变更：直接修改当前版本
3. 大变更：创建新版本目录并修改

---

*本 Skill 定义了 Agent 规范创建的完整能力，配合 agent-spec-maintainer Agent 使用*
