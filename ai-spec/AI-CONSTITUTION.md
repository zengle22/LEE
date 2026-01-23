# AI 宪法 (AI Constitution)

> **版本**: 1.3.0
> **生效日期**: 2026-01-10
> **更新内容**: 强化目录职责分离规则，明确 Spec 模板与项目产出物的边界
> **适用范围**: 本插件内所有 Agent 的行为规范

---

## 第负一章：强制执行规则 (Mandatory Enforcement)

> **优先级**: 🔴 最高 - 违反即终止
> **执行者**: 所有 Agent

本章规则具有**最高优先级**，任何其他规则与本章冲突时，以本章为准。

### -1.1 Orchestrator 强制 (Orchestrator Enforcement)

**核心原则**: 所有工作流执行**必须**通过 Orchestrator 驱动，禁止手动绕过。

**强约束**:
- ✅ **必须使用 Orchestrator**: 所有 Phase 执行必须通过 `python -m orchestrator` 命令驱动
- ✅ **必须获取 Token**: 执行步骤前必须从 Orchestrator 获取执行令牌
- ✅ **必须完成验证**: 步骤输出必须通过 Orchestrator 验证
- ✅ **必须通过门禁**: 人工门禁必须通过 Orchestrator 审批流程
- ❌ **禁止手动执行**: 禁止绕过 Orchestrator 直接执行工作流步骤
- ❌ **禁止跳过步骤**: 禁止手动跳过任何步骤（包括可选步骤）
- ❌ **禁止手动修改状态**: 禁止直接编辑 `.workflow/state.yaml` 文件
- ❌ **禁止手动触发门禁**: 禁止通过编辑状态文件来绕过门禁审批

**绝对禁止的操作**:
```
❌ 直接编辑 .workflow/state.yaml
❌ 直接编辑 .workflow/events.jsonl
❌ 直接添加或修改 gates 字典
❌ 手动将步骤状态从 pending 改为 completed
❌ 跳过 orchestrator validate 直接标记完成
❌ 跳过 orchestrator approve 直接通过门禁
```

**唯一合法的状态变更方式**: 通过 `python -m orchestrator` CLI 命令

**Orchestrator 命令清单**:
```bash
# 初始化
python -m orchestrator init <project_dir> --workflow <workflow.yaml>

# 状态查看
python -m orchestrator status <project_dir>

# 执行下一步
python -m orchestrator next <project_dir>

# 完成步骤
python -m orchestrator complete <project_dir> <step_id> --outputs <files>

# 验证输出
python -m orchestrator validate <project_dir> <step_id>

# 审批门禁
python -m orchestrator approve <project_dir> <gate_id> --approver <name>

# 重置步骤（失败后重试）
python -m orchestrator reset <project_dir> <step_id> --reason <reason>
```

**自动执行原则 (Run-to-Gate)**:

工作流步骤的执行遵循 **run-to-gate** 循环模式：

```
while True:
    step = get_next_step()
    if step is None:
        break  # workflow_done

    execute_step(step)
    complete_and_validate(step)

    if step.has_human_gate:
        output_gate_info(step)
        break  # 只在此处停止

    # 无门禁：自动继续下一步，不询问
```

**核心规则**:

1. **无门禁步骤自动推进**: 工作流步骤之间，除非遇到 `human_gate` 或 `conditional_human_gate` 触发条件，Agent **必须**自动连续执行，**不得**停下来询问用户确认
2. **仅门禁处暂停**: 只有以下情况需要等待人类确认：
   - `human_gate` 标记的步骤（验证通过后触发）
   - `conditional_human_gate` 条件触发时
   - 冻结/解冻操作
3. **禁止礼貌性确认**: Agent **不得**主动询问任何确认性问题，这不是"礼貌"而是**违宪**

**违宪停顿关键词 (Unconstitutional Pause Phrases)**:

以下短语在 **非 gate_pending** 状态下输出即视为违宪，必须检测并禁止：

| 违宪短语 | 类型 | 说明 |
|---------|------|------|
| `是否继续` | 询问继续 | 无门禁时禁止询问 |
| `继续推进吗` | 询问继续 | 无门禁时禁止询问 |
| `继续吗` | 询问继续 | 无门禁时禁止询问 |
| `要继续吗` | 询问继续 | 无门禁时禁止询问 |
| `需要我继续吗` | 询问继续 | 无门禁时禁止询问 |
| `下一步` + `?` | 询问下一步 | 应直接执行而非询问 |
| `您希望我` + `?` | 委婉询问 | 应按流程执行 |
| `我先` + `停一下` | 主动停顿 | 无门禁时禁止停顿 |

**强制输出格式 (每步完成后)**:

每完成一个步骤后，**必须**输出以下结构化信息：

```yaml
step_completed: <step_id>
next_step: <next_step_id> | null
next_step_human_gate: true | false
action: continue | wait_for_approval | workflow_done
```

- 如果 `next_step_human_gate: false` 且 `action: continue`，则**必须**立即执行下一步
- 如果 `next_step_human_gate: true`，则输出审批指令并停止
- 如果 `action: workflow_done`，则报告完成

**正确 vs 错误行为对比**:

```
✅ 正确: 完成 step_A → 输出 gate_check → 自动开始 step_B → 输出 gate_check → 自动开始 step_C → 遇到 human_gate 停止等待审批
❌ 错误: 完成 step_A → 询问"继续吗?" → 用户确认 → 开始 step_B → 询问"继续吗?" → ...
❌ 错误: 完成 step_A → "我先暂停一下，您希望我继续吗？"
```

**违规响应**:
```
❌ ORCHESTRATOR VIOLATION

尝试的操作: {操作描述}
违规类型: 未通过 Orchestrator 执行

该操作违反 AI 宪法 §-1.1，必须通过 Orchestrator 驱动。

正确做法:
1. 运行 python -m orchestrator status <project_dir> 查看当前状态
2. 运行 python -m orchestrator next <project_dir> 执行下一步
3. 按照 Orchestrator 提示完成操作
```

### -1.1.1 交付物强约束 (Artifact Gate)

**核心原则**: 步骤的交付物必须严格按 workflow 合同落盘，缺文件不允许过门。

> ⚠️ **这是防止"工作遗留"的硬约束**：不靠提醒，靠自动检测和门禁拦截。

**强约束**:

- ✅ **必须按合同交付**: workflow 定义的 `required_outputs` 必须全部存在
- ✅ **必须写 manifest**: 每步完成时写产物清单 (`.workflow/manifests/{step_id}.manifest.json`)
- ✅ **缺文件即失败**: `orchestrator validate` 检测缺失时直接 BLOCKED
- ❌ **禁止替代交付**: 不允许用"类似文件"替代合同要求的精确路径
- ❌ **禁止跳过验证**: 必须通过 Artifact Gate 才能进入下一步

**Output Contract 检查流程**:

```
Agent 完成步骤
       │
       ▼
orchestrator complete <step_id> --outputs <files>
       │
       ▼
orchestrator validate <step_id>
       │
       ▼
┌──────────────────────────────────┐
│  Artifact Gate: verify_required_outputs()  │
│                                  │
│  1. 获取 workflow 定义的 required_outputs   │
│  2. 检查每个必需文件是否存在              │
│  3. 生成 manifest 记录产出                │
└───────────────┬──────────────────┘
                │
        ┌───────┴───────┐
        │               │
   缺少文件          全部存在
        │               │
        ▼               ▼
   ❌ BLOCKED        ✅ PASSED
   列出缺失清单       继续流程
   Agent 补齐后重试
```

**Manifest 格式**:

```json
{
  "step": "p08_10_acceptance",
  "verified_at": "2026-01-11T16:30:00",
  "required": ["output/acceptance-report.yaml", "output/acceptance-report.md"],
  "produced": ["output/acceptance-report.yaml", "output/acceptance-report.md"],
  "missing": [],
  "extra": ["openspec/10-acceptance/acceptance-checklist.md"],
  "status": "done"
}
```

**Agent 收尾动作规范**:

Agent 完成步骤内容后，**最后的动作不是"写报告"**，而是：

1. 核对 workflow 定义的 `required_outputs`
2. 确保每个必需文件都已写入**精确路径**
3. 运行 `orchestrator complete` 并 `validate`
4. 如 validate 失败，立即补齐缺失文件

**违规响应**:

```
❌ ARTIFACT GATE BLOCKED

步骤: {step_id}
缺失输出 ({count}):
  - {missing_path_1}
  - {missing_path_2}

必须补齐所有必需输出后才能通过验证。
Agent 应立即补齐缺失文件，然后重新运行:
  python -m orchestrator validate <project_dir> <step_id>
```

**路径精确匹配规则**:

| workflow 要求 | 实际写入 | 结果 |
|--------------|---------|------|
| `output/report.yaml` | `output/report.yaml` | ✅ 通过 |
| `output/report.yaml` | `openspec/10/report.yaml` | ❌ 失败 (路径不匹配) |
| `output/report.yaml` | `output/report.md` | ❌ 失败 (文件名不匹配) |
| `output/report.yaml` | 未创建 | ❌ 失败 (缺失) |

### -1.2 输出路径规范 (Output Path Convention)

**核心原则**: 所有输出必须遵循统一的路径约定，确保可追溯和可管理。

**路径分类**:

| 类型 | 目标路径 | 示例 |
|------|----------|------|
| 文档类 | `project/{项目名}/` | PRD, 架构文档, 设计稿, 报告 |
| 代码类 | `git/{仓库名}/` | 源代码, 测试代码, 配置文件 |
| 规范类 | `ai-spec/specs/` | Agent, Skill, Contract, Workflow |
| 冻结类 | `output/` | 冻结文件 |

**详细规范**:

#### 文档类路径 (project/)
```
project/{项目名}/
├── prd/                    # PRD 文档
├── architecture/           # 技术架构
├── prototype/              # UI 原型
├── dev/                    # 研发阶段文档
│   └── phase{N}/           # 每个 Phase 的文档
│       ├── openspec/       # OpenSpec 提案
│       ├── output/         # Phase 输出
│       │   └── knowledge/  # 知识沉淀
│       └── workflow/       # 工作流状态
│           └── .workflow/  # Orchestrator 状态
└── knowledge/              # 项目级知识库
```

#### 代码类路径 (git/)
```
git/{仓库名}/
├── cmd/                    # 入口
├── internal/               # 内部代码
│   ├── service/            # 业务服务
│   ├── repository/         # 数据访问
│   ├── model/              # 数据模型
│   ├── gateway/            # 外部网关
│   └── middleware/         # 中间件
├── pkg/                    # 公共库
└── tests/                  # 测试代码
```

**强约束**:
- ✅ **文档 → project/**: 所有非代码文档必须放入 `project/{项目名}/` 对应子目录
- ✅ **代码 → git/**: 所有源代码必须放入 `git/{仓库名}/` 对应目录
- ✅ **知识 → knowledge/**: 知识沉淀放入 Phase 级或 Project 级 knowledge 目录
- ❌ **禁止混放**: 禁止在 project/ 下放代码，禁止在 git/ 下放文档

**违规检测**:
```python
# 伪代码
def check_output_path(file_path: str, file_type: str) -> bool:
    if file_type in ["doc", "md", "yaml", "json"]:  # 文档类
        if not file_path.startswith("project/"):
            raise PathViolation("文档类文件必须放入 project/ 目录")
    elif file_type in ["go", "py", "js", "ts"]:  # 代码类
        if not file_path.startswith("git/"):
            raise PathViolation("代码类文件必须放入 git/ 目录")
    return True
```

**违规响应**:
```
❌ PATH CONVENTION VIOLATION

尝试写入: {文件路径}
文件类型: {文件类型}
违规原因: {原因}

正确路径应为:
- 文档类 → project/{项目名}/{子目录}/
- 代码类 → git/{仓库名}/{子目录}/
```

---

## 第零章：元规则 (Meta-Rules)

### 0.1 单一事实源 (Single Source of Truth)

**核心原则**: 在本系统中，**YAML 规范文档**是唯一的、权威的事实源 (Source of Truth)。

1. **YAML 优先**: 当 YAML 规范文件 (如 `agent.yaml`) 与 Markdown 实现文件 (如 `agent.md`) 发生内容冲突时，**以 YAML 文件为准**。
2. **MD 的定位**: Markdown 文件仅作为面向 AI 的执行指令补充或面向人类的阅读材料，不具备规范定义的权威性。
3. **一致性维护**: 任何对 MD 文件的修改导致与 YAML 规范不一致时，必须优先同步更新 YAML 规范。

### 0.2 全局约定 (Global Conventions)

**目的**: 防止边界塌方 (Boundary Collapse)，确保各组件职责清晰、可组合、可测试。

#### 0.2.1 Skill（技能）

**定义**: 只做"确定性能力"的原子化功能单元。

**强约束**:
- ✅ **只做确定性能力**: 输入确定 → 输出确定（如：格式转换、数据提取、计算）
- ✅ **无角色/目标**: 不包含"你是…专家"等角色定义
- ✅ **无长上下文**: 不依赖多轮对话历史
- ✅ **无决策逻辑**: 不做"下一步应该…"的判断
- ❌ **禁止**: 包含业务目标、工作流编排、角色扮演

**示例**:
```yaml
# ✅ 正确的 Skill
id: extract_keywords_from_text
input: {text: string}
output: {keywords: array<string>}

# ❌ 错误的 Skill（包含决策）
id: analyze_and_decide_next_step  # 违反：包含决策
```

#### 0.2.2 Agent（智能体）

**定义**: 含角色、目标、决策规则的自主执行单元。

**强约束**:
- ✅ **必须声明角色**: 明确"你是…"的身份定位
- ✅ **必须有目标**: 明确要达成的业务目标
- ✅ **必须有决策规则**: 定义如何选择 skills、如何判断完成
- ✅ **必须声明 I/O Contract**: 输入输出必须有明确的 schema 引用
- ✅ **可调用 Skills**: 组合多个 skills 完成复杂任务
- ❌ **禁止**: 包含工作流编排逻辑（应由 Workflow 负责）

**示例**:
```yaml
# ✅ 正确的 Agent
id: google_keyword_searcher
role: "关键词研究专家"
goal: "发现热门关键词和长尾词"
input_contract: contracts/keyword-input/v1/schema.json
output_contract: contracts/keyword-output/v1/schema.json
skills: [extract_keywords, expand_longtail]
decision_rules:
  - if: autocomplete_found
    then: extract_and_expand
```

#### 0.2.3 Workflow（工作流）

**定义**: 只编排步骤、条件、回退、人类介入点的流程控制器。

**强约束**:
- ✅ **只做编排**: 定义步骤顺序、条件分支、错误处理
- ✅ **声明人类介入点**: 明确哪些节点需要人类审批
- ✅ **声明回退策略**: 定义失败时的回滚逻辑
- ❌ **禁止**: 包含业务分析内容（应在 Agent 中）
- ❌ **禁止**: 包含具体执行逻辑（应在 Agent/Skill 中）
- ❌ **禁止**: 直接操作数据（应调用 Agent/Skill）

**示例**:
```yaml
# ✅ 正确的 Workflow
id: product_discovery_pipeline
steps:
  - agent: fact_collector
    on_failure: retry_3_times
  - agent: opportunity_analyzer
    requires_human: approval
    on_reject: rollback_to_step_1

# ❌ 错误的 Workflow（包含业务逻辑）
steps:
  - name: analyze_market
    logic: "分析市场规模，如果大于1亿则…"  # 违反：包含业务分析
```

#### 0.2.4 Contract（契约）

**定义**: 用 JSON Schema 或自定义 schema 固化输入/输出接口。

**强约束**:
- ✅ **必须使用结构化 Schema**: JSON Schema、YAML Schema 或等效格式
- ✅ **必须版本化**: 每个 contract 必须有版本号（如 `v1`）
- ✅ **必须向后兼容**: 新版本不得破坏旧版本的字段
- ❌ **禁止**: 使用自然语言描述代替 schema
- ❌ **禁止**: 在代码中硬编码 I/O 格式

**示例**:
```yaml
# ✅ 正确的 Contract 引用
output_contract: contracts/google-keyword-contract/v1/schema.json

# ❌ 错误的做法（无 schema）
output: "返回关键词列表，格式自定"  # 违反：无结构化 schema
```

#### 0.2.5 Test Hooks（测试钩子）

**定义**: 每个 spec 必须声明最小测试集，确保可验证性。

**强约束**:
- ✅ **Skill 必须有单元测试**: 至少包含 1 个 smoke test
- ✅ **Agent 必须有集成测试**: 验证 I/O contract 符合性
- ✅ **Workflow 必须有回放数据**: 声明 replay 测试数据集
- ✅ **测试数据版本化**: 测试数据与 spec 版本对应

**示例**:
```yaml
# ✅ 正确的 Test Hooks
test_hooks:
  smoke_tests:
    - input: {text: "sample"}
      expected_output: {keywords: ["sample"]}
  replay_data: tests/replay/v1/scenario_001.json
```

#### 0.2.6 边界塌方检测

当出现以下情况时，视为**边界塌方**，必须重构：

| 违规类型 | 示例 | 处理 |
|---------|------|------|
| Skill 包含决策 | `if market_size > 100M then recommend...` | 拆分为 Skill + Agent |
| Agent 包含编排 | `step1 → step2 → step3` | 提取为 Workflow |
| Workflow 包含业务逻辑 | `分析用户画像并生成报告` | 移至 Agent |
| 缺失 Contract | 输入输出无 schema | 补充 Contract 定义 |
| 缺失 Test Hooks | 无测试数据 | 补充 smoke test |

#### 0.2.7 目录职责分离 (Directory Separation)

**核心原则**: `ai-spec/specs/` 目录存放**可复用的规范模板**，`project/` 目录存放**项目特定的产出物**。

> ⚠️ **重要**: 这是强制规则，违反即 Fail Fast。

**分类标准**:

| 类型 | 定义 | 位置 | 示例 |
|------|------|------|------|
| **Spec 模板** | 可复用的标准定义 | `ai-spec/specs/` | agent.yaml, workflow.yaml, schema.json |
| **Spec 实例** | 引用模板的项目配置 | `project/{name}/` | workflow-instance.yaml |
| **项目产出物** | 具体项目的实际内容 | `project/{name}/` | proposal.md, retrospective.md, 代码 |

**Spec 模板 vs 项目产出物判断规则**:

```
┌─────────────────────────────────────────────────────────────────┐
│ 该文件可以被多个项目复用吗？                                      │
├─────────────────────────────────────────────────────────────────┤
│  YES → ai-spec/specs/ (Spec 模板)                               │
│  NO  → project/{name}/ (项目产出物或 Spec 实例)                  │
└─────────────────────────────────────────────────────────────────┘
```

**强约束**:

| 类别 | 规则 | 示例 |
|------|------|------|
| ✅ **ai-spec/specs/** | 只放可复用模板 | `agents/{name}/v1/agent.yaml` |
| ✅ **project/** | 放项目产出物和配置 | `dev/phase4/proposal.md` |
| ✅ **project/workflow.yaml** | 必须是 `kind: workflow-instance` | 引用标准模板 |
| ❌ **禁止** | project 下定义完整 workflow 步骤 | 应引用 ai-spec 模板 |
| ❌ **禁止** | project 下创建 agent.yaml | 应放 ai-spec |
| ❌ **禁止** | ai-spec 下放 HTML/CSS/代码 | 应放 project |

**目录结构规范**:

```
{repository-root}/
├── ai-spec/                      # AI 规范目录 (可复用模板)
│   ├── AI-CONSTITUTION.md        # AI 宪法
│   └── specs/                    # 规范配置（只读性质）
│       ├── common/               # 通用规范
│       │   ├── agents/           # Agent 模板 (*.yaml)
│       │   ├── skills/           # Skill 模板 (*.yaml)
│       │   ├── contracts/        # Contract Schema (*.json)
│       │   ├── workflows/        # Workflow 模板 (*.yaml)
│       │   └── gates/            # Gate 模板 (*.yaml)
│       └── org/{domain}/         # 领域专属规范
│           ├── development/      # 研发领域
│           └── product/          # 产品领域
│
├── project/                      # 项目产出物（项目特定）
│   └── {project-name}/
│       ├── dev/                  # 研发阶段
│       │   └── phase{N}/
│       │       ├── workflow.yaml     # kind: workflow-instance (引用模板)
│       │       ├── openspec/         # 项目产出物
│       │       │   ├── 00-requirements/   # 需求校准结果
│       │       │   ├── 01-test-contracts/ # 测试契约
│       │       │   ├── changes/           # 变更提案
│       │       │   ├── 04-review/         # 审查报告
│       │       │   └── 05-retrospective/  # 复盘报告
│       │       ├── output/           # Phase 输出
│       │       │   └── knowledge/    # 知识沉淀
│       │       ├── src/              # 源代码
│       │       └── .workflow/        # Orchestrator 状态
│       ├── prototype/            # UI 原型
│       └── knowledge/            # 项目级知识库
│
└── output/                       # 冻结文件存放
    ├── discovery-frozen/
    ├── design-frozen/
    └── release-frozen/
```

**Workflow 实例规范**:

project 下的 `workflow.yaml` 必须使用以下格式：

```yaml
# ✅ 正确：workflow-instance（引用标准模板）
kind: workflow-instance
version: "1.0"
id: phase4-training-data-sync
name: "Phase 4: 训练数据同步服务"
extends: ai-spec/specs/org/development/workflows/phase-openspec-flow/v1/workflow.yaml
overrides:
  validation:
    coverage_threshold: 75
metadata:
  phase_number: 4
  track: backend

# ❌ 错误：在 project 下定义完整 steps
kind: workflow
steps:
  - id: step_1
    name: ...
```

**违规检测**:

| 违规类型 | 示例 | 处理 |
|---------|------|------|
| ai-spec 下有产出物 | `ai-spec/output/*.html` | 移至 `project/{name}/` |
| project 下有 Spec 模板 | `project/foo/agents/xxx.yaml` | 移至 `ai-spec/specs/` |
| project 下完整定义 workflow steps | `project/foo/workflow.yaml` with `kind: workflow` | 改为 `kind: workflow-instance` |
| Spec 维护者 Agent 输出到 project | 创建 agent.yaml 到 project/ | 必须输出到 ai-spec/specs/ |

**Spec 维护者 Agent 输出路径**:

| Agent | 输出路径 | 禁止路径 |
|-------|---------|---------|
| agent-spec-maintainer | `ai-spec/specs/{scope}/agents/` | `project/` |
| workflow-spec-maintainer | `ai-spec/specs/{scope}/workflows/` | `project/` |
| contracts-spec-maintainer | `ai-spec/specs/{scope}/contracts/` | `project/` |
| gates-spec-maintainer | `ai-spec/specs/{scope}/gates/` | `project/` |
| skills-spec-maintainer | `ai-spec/specs/{scope}/skills/` | `project/` |

**Agent 实施清单**:
- [ ] 判断输出是 Spec 模板还是项目产出物
- [ ] Spec 模板 → `ai-spec/specs/` 目录
- [ ] 项目产出物 → `project/{项目名}/` 目录
- [ ] project 下的 workflow.yaml 必须是 `kind: workflow-instance`
- [ ] 如发现路径违规，Fail Fast 并提示正确路径

#### 0.2.8 UI 本地化规范 (UI Localization)

**核心原则**: 所有 UI 原型默认使用中文。

**强约束**:
- ✅ **默认中文**: 所有 UI 文案、按钮、标签、提示信息默认使用简体中文
- ✅ **中文优先**: 生成 UI 原型时，首先生成中文版本
- ✅ **文案规范**: 使用简洁、专业的中文表达，避免翻译腔
- ❌ **禁止**: 未经要求生成纯英文 UI

**UI 文案风格**:
- 按钮: 使用动词（如 "确认"、"取消"、"开始训练"）
- 标签: 简洁明了（如 "首页"、"我的"、"设置"）
- 提示: 友好引导（如 "还没有数据"、"加载失败，点击重试"）
- 错误: 说明原因和解决方案

**示例**:
```
✅ 正确: "开始训练"、"查看详情"、"数据加载失败"
❌ 错误: "Start Training"、"View Details"、"Loading Failed"
```

### 0.3 标准模板引用 (Template References)

**目的**: 确保所有 Spec 遵循统一的 v1.0 格式标准。

#### 0.3.1 模板位置

| 类型 | 模板路径 | 说明 |
|------|---------|------|
| Skill | `specs/skills/_template/v1/skill.yaml` | 技能规范模板 |
| Agent | `specs/agents/_template/v1/agent.yaml` | 智能体规范模板 |
| Workflow | `specs/workflows/_template/v1/workflow.yaml` | 工作流规范模板 |

#### 0.3.2 Spec Review Agent

**用途**: 自动化评审 spec 文件，确保工程质量。

- **Agent 定义**: `specs/agents/spec-review/v1/agent.yaml`
- **评审规则**: `specs/agents/spec-review/v1/review_rules.md`
- **输入契约**: `specs/contracts/spec-review-contract/v1/input.schema.json`
- **输出契约**: `specs/contracts/spec-review-contract/v1/output.schema.json`

#### 0.3.3 CI 集成

Spec Review 已集成到 CI 流水线：

```
.github/workflows/spec-review.yml
```

**规则**:
- `blocker = 0` 才能合并 PR
- `major` 问题会在 PR 评论中警告
- 所有 spec 变更自动触发评审

---

## 第一章：工作流程阶段定义

### 1.1 三大顶层 Stage

整个工作流程分为三个顶层阶段，每个阶段有明确的输入、输出和边界：

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│                 │     │                 │     │                 │
│   Stage 1       │────▶│   Stage 2       │────▶│   Stage 3       │
│   商业发现      │     │   产品设计      │     │   研发实现      │
│   Discovery     │     │   Design        │     │   Development   │
│                 │     │                 │     │                 │
└────────┬────────┘     └────────┬────────┘     └────────┬────────┘
         │                       │                       │
         ▼                       ▼                       ▼
   discovery-freeze.md     design-freeze.md      release-freeze.md
```

### 1.2 各阶段职责

#### Stage 1: 商业发现 (Discovery)

**目的**: 发现和验证商业机会

**包含活动**:
- 市场调研（关键词分析、趋势研究）
- 用户信号采集
- 行业结构分析
- 竞品供给分析
- 商业机会识别与评估

**输出产物**:
- 事实采集报告
- 三维分析报告（用户/行业/竞品）
- 商业机会分析报告

**冻结产物**: `*-discovery-freeze.md`

#### Stage 2: 产品设计 (Design)

**目的**: 将商业机会转化为可执行的产品方案

**包含活动**:
- 产品目标分析
- 需求对齐与分解
- 原型设计
- PRD 编写
- 技术方案评估

**输出产物**:
- 产品目标文档
- 需求规格说明
- 原型设计稿
- PRD 文档
- 技术方案

**冻结产物**: `*-design-freeze.md`

**前置条件**: ⚠️ **必须存在已冻结的 discovery-freeze.md**

#### Stage 3: 研发实现 (Development)

**目的**: 将产品设计转化为可交付的软件

**包含活动**:
- 技术架构设计
- 代码开发
- 测试验证
- 部署发布

**输出产物**:
- 技术架构文档
- 源代码
- 测试报告
- 部署文档

**冻结产物**: `*-release-freeze.md`

**前置条件**: ⚠️ **必须存在已冻结的 design-freeze.md**

### 1.3 Stage 2 子阶段流水线 (Product Pipeline)

Stage 2 (产品设计) 内部进一步细分为 4 个子阶段，定义在 `pipelines/product-pipeline.yaml`：

```
Stage 2: 产品设计
│
├── 2.1 价值定义 (Value Definition)
│   └── freeze: product-value-freeze.md
│
├── 2.2 问题定义 (Problem Definition)
│   └── freeze: requirement-freeze.md
│
├── 2.3 方案设计 (Solution Design)
│   └── freeze: solution-freeze.md
│
└── 2.4 交付规划 (Delivery Planning)
    └── freeze: none (输出 development_plan.md)
```

#### 流水线核心原则

1. **人类仅在冻结点参与**: 人类不介入 Agent 的日常工作，仅在冻结审批时做决策
2. **Non-goals 硬约束**: 每个 Agent 明确定义"不做什么"，违反即失败
3. **严格依赖链**: 下游 Agent 的输入必须来自上游的冻结产物

#### 人类角色类型

| 类型 | 含义 | 允许的操作 |
|------|------|-----------|
| `decision` | 决策 | approve / request_revision / reject |
| `validation` | 验证 | confirm_alignment / flag_misalignment |
| `review` | 审阅 | approve_plan / adjust_plan |

> 详细定义参见: [pipelines/product-pipeline.yaml](./pipelines/product-pipeline.yaml)

---

## 第二章：冻结机制 (Freeze Mechanism)

### 2.1 冻结文件定义

冻结文件是阶段性工作的正式输出，代表该阶段工作的完成和确认。

#### 冻结文件命名规范

```
{项目名}-{stage}-freeze.md

示例:
- 跑步App-discovery-freeze.md
- 跑步App-design-freeze.md
- 跑步App-release-freeze.md
```

#### 冻结文件必须包含的元数据

```yaml
---
freeze_id: "FREEZE-{STAGE}-{YYYYMMDD}-{SEQ}"
freeze_type: "discovery" | "design" | "release"
freeze_time: "YYYY-MM-DD HH:mm:ss"
status: "🔒 已冻结"
project: "{项目名称}"
version: "1.0"
previous_freeze: "{前置冻结文件路径，如适用}"
approved_by: "{审批人}"
approved_at: "YYYY-MM-DD HH:mm:ss"
---
```

### 2.2 冻结状态

| 状态 | 标记 | 含义 |
|------|------|------|
| 草稿 | 📝 | 正在编写，可自由修改 |
| 待审批 | ⏳ | 已完成，等待人类审批 |
| 已冻结 | 🔒 | 已审批通过，受保护 |
| 已解冻 | 🔓 | 经审批后重新开放修改 |
| 已废弃 | ❌ | 被新版本替代 |

### 2.3 冻结规则

1. **阶段完成即冻结**: 每个 Stage 完成后必须生成冻结文件
2. **人类审批前置**: 冻结操作必须经过人类确认
3. **冻结即只读**: 已冻结文件不得被任何 Agent 修改
4. **版本追溯**: 如需修改冻结内容，必须先解冻，修改后重新冻结

---

## 第三章：阶段门禁 (Stage Gate)

### 3.1 门禁规则

```
┌──────────────┐
│  检查前置    │
│  冻结文件    │
└──────┬───────┘
       │
       ▼
  ┌────┴────┐
  │ 存在？  │
  └────┬────┘
       │
   ┌───┴───┐
   │       │
  Yes      No
   │       │
   ▼       ▼
┌──────┐ ┌─────────────────┐
│ 继续 │ │ FAIL FAST       │
│ 执行 │ │ 禁止进入下一阶段│
└──────┘ └─────────────────┘
```

### 3.2 各阶段门禁条件

| 目标阶段 | 必须存在的冻结文件 | 门禁检查点 |
|----------|-------------------|------------|
| Stage 2 (产品设计) | `*-discovery-freeze.md` | 开始产品设计前 |
| Stage 3 (研发实现) | `*-design-freeze.md` | 开始编码前 |
| 发布 | `*-release-freeze.md` | 部署发布前 |

### 3.3 门禁检查实现

Agent 在执行以下操作前 **必须** 检查前置冻结文件：

```python
# 伪代码示例
def stage_gate_check(target_stage: str, project_name: str) -> bool:
    required_freeze = {
        "design": f"{project_name}-discovery-freeze.md",
        "development": f"{project_name}-design-freeze.md",
        "release": f"{project_name}-release-freeze.md"
    }

    freeze_file = required_freeze.get(target_stage)
    if not freeze_file:
        return True  # Stage 1 无前置要求

    if not file_exists(freeze_file):
        raise StageGateError(
            f"❌ 门禁检查失败: 缺少前置冻结文件 {freeze_file}\n"
            f"请先完成上一阶段并获得冻结审批。"
        )

    if not is_frozen(freeze_file):
        raise StageGateError(
            f"❌ 门禁检查失败: 前置文件 {freeze_file} 未处于冻结状态\n"
            f"请先获得人类审批确认冻结。"
        )

    return True
```

---

## 第四章：防篡改保护 (Tamper Protection)

### 4.1 核心规则

> **Any agent output that attempts to modify a frozen artifact must fail fast and request re-open approval.**

### 4.2 防篡改机制

#### 4.2.1 写入拦截

当任何 Agent 尝试写入或修改已冻结文件时：

1. **立即失败 (Fail Fast)**: 操作不得执行
2. **返回错误**: 明确说明违规原因
3. **请求解冻**: 提示需要人类审批解冻

```
❌ FROZEN FILE VIOLATION

尝试修改的文件: {文件路径}
文件状态: 🔒 已冻结
冻结时间: {冻结时间}
审批人: {审批人}

该文件受 AI 宪法保护，不允许任何修改。

如需修改，请执行以下步骤:
1. 运行 /unfreeze {文件路径}
2. 等待人类审批解冻
3. 解冻后方可修改
4. 修改完成后重新冻结
```

#### 4.2.2 受保护操作

以下操作对冻结文件 **全部禁止**：

- ✗ 内容修改 (Edit)
- ✗ 内容覆盖 (Write)
- ✗ 文件删除 (Delete)
- ✗ 文件移动 (Move)
- ✗ 文件重命名 (Rename)

以下操作 **允许**：

- ✓ 读取内容 (Read)
- ✓ 复制文件 (Copy)
- ✓ 引用链接 (Reference)

### 4.3 解冻流程

```
┌────────────────┐
│ Agent 请求解冻 │
└───────┬────────┘
        │
        ▼
┌───────────────────┐
│ 通知人类审批者    │
│ 说明解冻原因      │
└───────┬───────────┘
        │
        ▼
┌───────────────────┐
│   人类决策        │
├───────────────────┤
│ ✅ 批准解冻       │──▶ 文件状态变更为 🔓
│ ❌ 拒绝解冻       │──▶ 维持冻结状态
└───────────────────┘
```

---

## 第五章：人类审批 (Human Approval)

### 5.1 强制审批点

以下操作 **必须** 获得人类明确确认：

| 操作 | 触发时机 | 确认方式 |
|------|----------|----------|
| 冻结文件 | 阶段完成时 | 人类输入 "确认冻结" 或 "approve freeze" |
| 解冻文件 | 需要修改冻结内容时 | 人类输入 "确认解冻" 或 "approve unfreeze" |
| 阶段跳跃 | 尝试跳过阶段时 | **禁止**，无论如何不得跳过 |
| 废弃冻结 | 替换冻结版本时 | 人类输入 "确认废弃" 或 "approve deprecate" |

### 5.2 审批记录

每次审批必须记录：

```yaml
approval_record:
  action: "freeze" | "unfreeze" | "deprecate"
  file: "{文件路径}"
  requested_by: "Agent:{Agent名称}"
  requested_at: "YYYY-MM-DD HH:mm:ss"
  approved_by: "{人类审批者}"
  approved_at: "YYYY-MM-DD HH:mm:ss"
  reason: "{操作原因}"
```

### 5.3 审批交互示例

#### 冻结审批

```
🔔 冻结审批请求

文件: 跑步App-discovery-freeze.md
阶段: Stage 1 - 商业发现
内容摘要:
  - 市场规模: 中国健身App用户1.04亿
  - 竞争格局: CR3≈72%，寡头竞争
  - 推荐策略: AI跑步教练

请确认是否冻结此文件？
输入 "确认冻结" 继续，或 "拒绝" 取消。
```

#### 解冻审批

```
🔔 解冻审批请求

文件: 跑步App-discovery-freeze.md
当前状态: 🔒 已冻结
冻结时间: 2026-01-04 14:30:00
解冻原因: 需要更新市场规模数据

⚠️ 警告: 解冻后文件可被修改，可能影响下游设计决策。

请确认是否解冻此文件？
输入 "确认解冻" 继续，或 "拒绝" 取消。
```

---

## 第六章：违规处理

### 6.1 违规类型

| 违规代码 | 违规行为 | 严重程度 |
|----------|----------|----------|
| V001 | 修改冻结文件 | 🔴 严重 |
| V002 | 跳过阶段门禁 | 🔴 严重 |
| V003 | 未经审批冻结 | 🟡 中等 |
| V004 | 未经审批解冻 | 🟡 中等 |
| V005 | 冻结文件格式不规范 | 🟢 轻微 |

### 6.2 违规响应

- **🔴 严重**: 立即终止操作，向人类报告，等待指示
- **🟡 中等**: 操作回滚，请求人类确认后重试
- **🟢 轻微**: 警告并自动修正

---

## 第七章：实施指南

### 7.1 Agent 实施清单

所有 Agent 在执行操作前必须：

- [ ] 识别当前所处 Stage
- [ ] 检查是否涉及冻结文件
- [ ] 如涉及写操作，检查文件是否已冻结
- [ ] 如进入新 Stage，检查门禁条件
- [ ] 如需冻结/解冻，请求人类审批

### 7.2 冻结文件存放位置

```
output/
├── discovery-frozen/     # Stage 1 冻结文件
│   └── {项目}-discovery-freeze.md
├── design-frozen/        # Stage 2 冻结文件
│   └── {项目}-design-freeze.md
└── release-frozen/       # Stage 3 冻结文件
    └── {项目}-release-freeze.md
```

### 7.3 版本控制

冻结文件应纳入 Git 版本控制：

```bash
# 冻结后提交
git add output/*-freeze.md
git commit -m "freeze: {项目名} {Stage} 阶段冻结 - {简要描述}"
```

---

## 附录

### A. 术语表

| 术语 | 定义 |
|------|------|
| Stage | 工作流程的顶层阶段 |
| Freeze | 将文档标记为只读的操作 |
| Unfreeze | 解除冻结状态的操作 |
| Stage Gate | 阶段间的检查点 |
| Fail Fast | 发现问题立即失败，不继续执行 |

### B. 相关文件

- `templates/freeze-template.md` - 冻结文件模板
- `commands/freeze.md` - 冻结命令
- `commands/unfreeze.md` - 解冻命令
- `hooks/freeze-guard.md` - 冻结保护钩子

---

*AI 宪法 v1.0.0*
*制定日期: 2026-01-04*
*本文档本身不受冻结保护，可根据实践持续优化*
