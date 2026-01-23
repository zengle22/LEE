# AI Spec

> AI 规范集中管理目录

本目录用于集中管理项目中所有与 AI Agent 相关的规范文件，包括合约定义、策略规则、工作流程和 CLI 工具配置。

---

## 目录结构

```
ai-spec/
├── AI-CONSTITUTION.md          # AI 宪法 - 核心治理规则
├── core.yaml                   # 核心配置规范
├── README.md                   # 本文件
├── CHANGELOG.md                # 变更日志
│
├── cli/                        # CLI 工具专属配置
│   └── claude/                 # Claude Code 插件配置
│       ├── CLAUDE.md           # Claude 行为规范
│       ├── plugin.json         # 插件配置
│       ├── agents/             # Agent 定义
│       ├── commands/           # 斜杠命令
│       ├── skills/             # 技能知识库
│       └── templates/          # 文档模板
│
├── specs/                      # 通用规范定义 (与 CLI 无关)
│   ├── agents/                 # Agent 通用规范
│   │   └── <agent_name>/v1/agent.yaml
│   │
│   ├── contracts/              # 数据合约
│   │   └── <contract_name>/v1/schema.md
│   │
│   ├── policies/               # 策略规则
│   │   ├── global/v1/policy.md
│   │   └── <domain>/v1/policy.md
│   │
│   ├── workflows/              # 工作流定义
│   │   └── <workflow_name>/v1/workflow.yaml
│   │
│   ├── templates/              # 文档模板通用规范
│   │   └── <template_name>/v1/template.md
│   │
│   ├── skills/                 # 技能知识库通用规范
│   │   └── <skill_name>/v1/skill.md
│   │
│   └── org/                    # 独立域 (打包的组织单元)
│       └── prd/                # PRD 产品设计域
│           ├── plugin.json
│           ├── agents/
│           ├── commands/
│           ├── skills/
│           └── templates/
│
├── tests/                      # 测试资源
│   ├── fixtures/               # 测试数据
│   │   └── <workflow_name>/*.json
│   └── assertions/             # 断言定义
│       └── <workflow_name>/*.yaml
│
└── tools/                      # 工具脚本
    └── spec_cli/               # 校验、编译、测试脚本
```

---

## 管理规则

### 1. 顶层文件

| 文件 | 说明 |
|------|------|
| `AI-CONSTITUTION.md` | AI 宪法，定义核心治理规则和阶段门禁 |
| `core.yaml` | 核心配置，定义角色、工作流和质量标准 |

这些文件对整个 AI 系统具有全局约束力。

### 2. CLI 目录 (`cli/`)

存放特定 CLI 工具的专属配置，按工具名称分目录：

- `cli/claude/` - Claude Code 插件配置，按照 `.claude` 目录结构组织
- 未来可扩展：`cli/cursor/`, `cli/copilot/` 等

**迁移原则**：将 CLI 专属文件按原有目录结构直接搬入对应目录。

### 3. Specs 目录 (`specs/`) - 通用规范

存放与 CLI 无关的**通用规范定义**，这些是所有 CLI 工具共享的基础规范：

| 子目录 | 内容 | 版本化规则 |
|--------|------|------------|
| `agents/` | Agent 通用规范 | `<name>/v1/agent.yaml` |
| `contracts/` | 数据合约 | `<name>/v1/schema.json` + `schema.md` |
| `policies/` | 策略规则 | `global/v1/` 或 `<domain>/v1/` |
| `workflows/` | 工作流定义 | `<name>/v1/workflow.yaml` |
| `templates/` | 文档模板通用规范 | `<name>/v1/template.md` |
| `skills/` | 技能知识库通用规范 | `<name>/v1/skill.md` |

### 3.2 Contract Schema 规范

所有 contract 必须包含 **JSON Schema** (`schema.json`) 进行结构验证：

```
contracts/<name>/v1/
├── schema.json    # JSON Schema 验证 (必须)
├── schema.md      # 人类可读文档 (可选)
└── schema.yaml    # 机器可读模板 (可选)
```

**JSON Schema 标准**：
- 使用 [JSON Schema draft-07](https://json-schema.org/specification-links.html#draft-7) 规范
- 所有 contract 必须包含 `contract_type` 和 `contract_version` 字段
- 使用 `$defs` 定义可复用的类型
- 设置 `"additionalProperties": false` 确保严格校验

**schema.json 模板**：

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "$id": "https://ai-spec.example.com/contracts/<name>/v1/schema.json",
  "title": "<Contract Name> Schema",
  "type": "object",
  "required": ["contract_type", "contract_version", "metadata"],
  "properties": {
    "contract_type": { "type": "string", "const": "<contract-type>" },
    "contract_version": { "type": "string", "pattern": "^\\d+\\.\\d+\\.\\d+$" },
    "metadata": { ... }
  },
  "additionalProperties": false,
  "$defs": {
    "ReusableType": { ... }
  }
}
```

**当前 Contract 列表**：

| Contract | 用途 | Schema |
|----------|------|--------|
| `fact-collection-contract` | 市场信号原始数据收集 | ✅ |
| `google-keyword-contract` | 关键词搜索结果 | ✅ |
| `user-signal-input-contract` | 用户信号输入 | ✅ |
| `user-signal-output-contract` | 用户信号分析输出 | ✅ |
| `supply-analysis-contract` | 供给分析结果 | ✅ |
| `business-opportunity-contract` | 商业机会分析 | ✅ |
| `opportunity-builder-contract` | 机会构建输出 | ✅ |
| `frozen-analysis-contract` | 冻结分析报告 | ✅ |
| `trend-research-contract` | 趋势研究输出 | ✅ |
| `product-goal-contract` | 产品目标定义 | ✅ |
| `plan-contract` | 研发计划合约 | ✅ |

**版本化原则**：
- 每个规范都放入 `v1/` 目录
- 重大变更时创建 `v2/` 目录，保留旧版本
- 版本号遵循语义化版本 (SemVer)

### 3.1 通用版本 vs 专用版本

```
┌─────────────────────────────────────────────────────────────────┐
│                    规范继承关系                                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   specs/ (通用规范)                                              │
│   ├── agents/fact-collector/v1/agent.yaml    ← 定义核心行为      │
│   ├── contracts/...                          ← 定义数据结构      │
│   ├── templates/...                          ← 定义模板格式      │
│   └── skills/...                             ← 定义知识库        │
│                      │                                          │
│                      │ 继承 & 扩展                               │
│                      ▼                                          │
│   cli/claude/ (Claude 专用版本)                                  │
│   ├── agents/fact-collector.md               ← 添加 Claude 配置  │
│   │   - name, description (触发条件)                             │
│   │   - tools (可用工具列表)                                     │
│   │   - model, color (运行配置)                                  │
│   ├── commands/...                           ← Claude 斜杠命令   │
│   ├── templates/...                          ← Claude 格式模板   │
│   └── skills/...                             ← Claude 技能定义   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

**核心原则**：
1. **specs/** 维护**通用版本**：定义核心行为、约束、工作流程
2. **cli/<tool>/** 维护**专用版本**：在通用版本基础上添加工具特定配置
3. 修改规范时，**先更新 specs/ 通用版本**，再同步到各 CLI 专用版本
4. 通用规范使用 **YAML 格式**（机器可解析），专用版本可使用 **Markdown 格式**（人类友好）

**通用规范内容**（在 specs/ 中定义）：
- 角色定位 (role)
- 核心职责 (responsibilities)
- 禁止行为 (forbidden_behaviors)
- 工作流程 (workflow)
- 输入输出契约引用 (contracts)
- 字段规则 (field_rules)

**专用版本扩展**（在 cli/<tool>/ 中添加）：
- 工具列表 (tools)
- 触发条件和示例 (description with examples)
- 运行配置 (model, color)
- 工具特定的提示词优化

### 4. 独立域 (`specs/org/`)

打包成独立组织单元的规范集合，每个域是一个完整的子系统：

- `specs/org/prd/` - PRD 产品设计域
- 未来可扩展：`specs/org/dev/`, `specs/org/qa/` 等

**归属规则**：
- 如果一组规范形成完整的子系统（有自己的 agents、commands、skills），放入 `org/`
- 暂时还未归属的单独规范文件放在 `specs/` 外层对应目录

### 5. 测试资源 (`tests/`)

| 子目录 | 内容 |
|--------|------|
| `fixtures/` | 测试输入数据 (JSON) |
| `assertions/` | 预期输出断言 (YAML) |

按 workflow 名称组织测试数据。

### 6. 工具脚本 (`tools/`)

存放规范相关的工具脚本：
- `spec_cli/` - 规范校验、编译、测试脚本

---

## 文件迁移对照表

| 原位置 | 新位置 |
|--------|--------|
| `ai-auto/AI-CONSTITUTION.md` | `ai-spec/AI-CONSTITUTION.md` |
| `core.yaml` | `ai-spec/core.yaml` |
| `ai-auto/CLAUDE.md` | `ai-spec/cli/claude/CLAUDE.md` |
| `ai-auto/plugin.json` | `ai-spec/cli/claude/plugin.json` |
| `ai-auto/agents/*` | `ai-spec/cli/claude/agents/*` |
| `ai-auto/commands/*` | `ai-spec/cli/claude/commands/*` |
| `ai-auto/skills/*` | `ai-spec/cli/claude/skills/*` |
| `ai-auto/templates/*` | `ai-spec/cli/claude/templates/*` |
| `ai-auto/contracts/*` | `ai-spec/specs/contracts/<name>/v1/schema.md` |
| `ai-auto/pipelines/*` | `ai-spec/specs/workflows/<name>/v1/workflow.yaml` |
| `ai-auto/prd/` | `ai-spec/specs/org/prd/` |

---

## 如何使用

### Claude Code 用户

将 `cli/claude/` 目录链接或复制到项目的 `.claude/` 目录：

```bash
# 方式1：符号链接
ln -s ai-spec/cli/claude .claude

# 方式2：复制
cp -r ai-spec/cli/claude .claude
```

### 查看合约定义

```bash
# 查看用户信号输入合约
cat ai-spec/specs/contracts/user-signal-input-contract/v1/schema.md
```

### 查看工作流

```bash
# 查看产品决策流水线
cat ai-spec/specs/workflows/product-pipeline/v1/workflow.yaml
```

---

## 贡献指南

1. **新增规范**：在对应目录创建 `<name>/v1/` 子目录
2. **修改规范**：小改动直接修改，重大变更创建新版本目录
3. **新增独立域**：在 `specs/org/` 下创建完整的子系统目录
4. **更新日志**：所有变更记录到 `CHANGELOG.md`
