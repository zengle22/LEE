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
specs/common/agents/
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
| Agent ID | agent.{domain}.{name} (snake_case) | `agent.research.fact_collector` |
| 版本目录 | `v` + 数字 | `v1`, `v2`, `v3` |
| 规范文件名 | 固定为 `agent.yaml` | `agent.yaml` |
| 说明文档 | 固定为 `README.md` | `README.md` |

---

## Agent YAML 模板详解

### 完整模板结构

```yaml
# ============================================
# 文件头
# ============================================
kind: agent
version: 1.0

# ============================================
# 基础标识 (必填)
# ============================================
id: agent.{domain}.{name}           # Agent 唯一标识符
name: Agent Display Name            # 显示名称
description: >
  Agent 的详细描述，说明其核心职责和用途
owner: team-name                    # 负责团队
tags: [tag1, tag2]                  # 标签列表

# ============================================
# 契约定义 (必填)
# ============================================
contracts:
  input_schema: contracts/{name}/v1/input.schema.json
  output_schema: contracts/{name}/v1/output.schema.json

# ============================================
# 角色定义 (必填)
# ============================================
persona:
  role: "角色描述"
  style: "工作风格描述"
  tone: professional  # professional/neutral/firm/creative

# ============================================
# 策略定义 (必填)
# ============================================
policy:
  decision_rules:
    - if: "condition_description"
      then: "action_to_take"

  quality_bar:
    must_have:
      - "必须满足的质量要求"

  refusal:
    conditions:
      - "拒绝执行的条件"

# ============================================
# 技能引用 (必填)
# ============================================
skills:
  - ref: skill.{domain}.{name}

# ============================================
# 提示工程 (必填)
# ============================================
prompting:
  system: |
    System prompt content here.
    Define the agent's core behavior.

  instructions:
    - "具体指令1"
    - "具体指令2"

  output_format: json  # json/markdown/yaml

  grounding:
    citations_required: true/false

# ============================================
# 可观测性 (推荐)
# ============================================
observability:
  log_level: info  # debug/info/warn/error
  emit:
    - event_name_1
    - event_name_2

# ============================================
# 测试钩子 (推荐)
# ============================================
tests:
  smoke:
    - name: test_case_name
      input:
        field: value
      assert:
        - path: "$.result_field"
          op: "=="  # ==, !=, >=, <=, >, <
          value: expected_value

# ============================================
# 职责边界 (推荐)
# ============================================
responsibility:
  summary: "一句话概括 Agent 核心职责"
  out_of_scope:
    - "不属于该 Agent 职责的事项1"
    - "不属于该 Agent 职责的事项2"

# ============================================
# 禁止行为 (推荐)
# ============================================
forbidden_behaviors:
  - id: behavior_id
    name: 禁止行为名称
    description: "详细说明"
    violation_example: "违规示例"

# ============================================
# 输出要求 (推荐)
# ============================================
output_requirements:
  path_pattern: "output/{type}/{YYYY-MM-DD}_{name}.json"
```

---

## 字段详解

### 1. 基础标识（必填）

| 字段 | 类型 | 说明 | 示例 |
|------|------|------|------|
| `kind` | string | 固定为 "agent" | `agent` |
| `version` | string | 规范版本 | `1.0` |
| `id` | string | 唯一标识符 | `agent.research.fact_collector` |
| `name` | string | 显示名称 | `Fact Collector` |
| `description` | string | 详细描述 | 多行文本 |
| `owner` | string | 负责团队 | `product-ai` |
| `tags` | array | 标签列表 | `[research, collection]` |

**ID 格式规范**: `agent.{domain}.{name}`

常见 domain:
- `research` - 研究调研类
- `analysis` - 分析类
- `product` - 产品类
- `dev` - 开发类
- `design` - 设计类
- `governance` - 治理类
- `orchestration` - 编排类

### 2. 契约定义（必填）

```yaml
contracts:
  input_schema: contracts/fact-collection-input/v1/schema.json
  output_schema: contracts/fact-collection-contract/v1/schema.json
```

契约路径格式: `contracts/{contract-name}/v{version}/schema.json`

### 3. 角色定义（必填）

```yaml
persona:
  role: "数据采集员"
  style: "机械式采集、不做判断、原样记录"
  tone: neutral
```

**tone 选项**:
- `professional` - 专业严谨
- `neutral` - 中立客观
- `firm` - 坚定严格
- `creative` - 创意灵活

### 4. 策略定义（必填）

```yaml
policy:
  decision_rules:
    - if: "user_provides_industry_only"
      then: "expand_to_seed_keywords"
    - if: "page_load_timeout"
      then: "mark_failed_continue_next"

  quality_bar:
    must_have:
      - "每个关键词独立记录，不合并"
      - "输出符合契约格式"

  refusal:
    conditions:
      - "requests_subjective_analysis"
      - "asks_for_recommendations"
```

### 5. 技能引用（必填）

```yaml
skills:
  - ref: skill.search.web_search
  - ref: skill.browser.navigate
  - ref: skill.io.file_write
```

### 6. 提示工程（必填）

```yaml
prompting:
  system: |
    You are a data collector. Your ONLY job is to collect search signals.

    STRICT RULES:
    - DO NOT judge user personas
    - DO NOT analyze business value

  instructions:
    - "原样记录每个关键词，不合并不修改"
    - "采集过程不停下来问用户"

  output_format: json

  grounding:
    citations_required: true
```

**output_format 选项**:
- `json` - 结构化数据
- `markdown` - 报告文档
- `yaml` - 配置文件

---

## 版本管理规则

### 何时需要新版本

| 变更类型 | 处理方式 | 示例 |
|----------|----------|------|
| 修复错误 | 直接修改当前版本 | 修正拼写错误 |
| 小幅优化 | 直接修改当前版本 | 优化 system prompt |
| 新增可选字段 | 直接修改当前版本 | 添加 examples |
| **破坏性变更** | 创建新版本 (v2) | 修改必填字段结构 |
| **职责范围变更** | 创建新版本 (v2) | 增加/减少核心职责 |
| **契约变更** | 创建新版本 (v2) | 更换 input/output schema |

### 版本升级流程

1. 创建新版本目录：`specs/agents/<name>/v2/`
2. 复制当前版本文件到新目录
3. 修改 `version` 字段
4. 进行必要的变更
5. 更新 README.md 说明变更内容
6. 保留旧版本目录不动

---

## 验证检查清单

### 创建新 Agent 时

**命名规范**
- [ ] 目录名使用 kebab-case
- [ ] ID 使用 agent.{domain}.{name} 格式
- [ ] 名称具有描述性，能体现 Agent 职责

**格式验证**
- [ ] YAML 语法正确
- [ ] 缩进统一（2 空格）
- [ ] 中文字符串使用双引号包裹

**必填字段完整性**
- [ ] kind - 填写为 agent
- [ ] version - 填写且格式正确
- [ ] id - 填写且符合命名规范
- [ ] name - 填写
- [ ] description - 填写且清晰
- [ ] owner - 填写
- [ ] tags - 至少一个
- [ ] contracts - input_schema 和 output_schema
- [ ] persona - role, style, tone
- [ ] policy - decision_rules, quality_bar
- [ ] skills - 至少一个引用
- [ ] prompting - system, instructions, output_format

**契约引用有效性**
- [ ] schema_ref 路径格式正确
- [ ] 契约版本匹配

**职责清晰度**
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
  summary: "从搜索引擎采集市场搜索信号，只做事实采集，不做任何分析"
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
    - "判断用户画像"
    - "分析商业价值"
```

### 错误 3: ID 格式错误

❌ 错误：`googleKeywordSearcher` 或 `google-keyword-searcher`

✅ 正确：`agent.research.google_keyword_searcher`

### 错误 4: 权限声明不完整

❌ 错误示例：
```yaml
skills: []
```

✅ 正确示例：
```yaml
skills:
  - ref: skill.search.web_search
  - ref: skill.io.file_write
```

---

## 使用方式

### 创建新 Agent

1. 确定 Agent 名称（kebab-case）
2. 创建目录：`specs/common/agents/<agent-name>/v1/`
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
