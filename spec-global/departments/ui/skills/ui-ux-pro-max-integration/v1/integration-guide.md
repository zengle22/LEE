# ui-ux-pro-max-skill 集成方案

> **版本**: v1.0.0
> **日期**: 2026-01-12
> **状态**: 提案

---

## 一、定位与边界

### 1.1 正确定位

| 角色 | 说明 |
|------|------|
| ✅ **辅助型 Skill** | 提供设计知识库和审查能力 |
| ✅ **审稿型 Agent** | 在 Gate 位置做 UX 审查 |
| ✅ **Prompt 增强器** | 规范化模糊的设计需求 |
| ❌ **UI 生成器** | 不能直接生成可用的 UI |
| ❌ **设计师替代品** | 不能替代专业设计判断 |

### 1.2 核心价值

```
ui-ux-pro-max-skill = 设计领域的「资深 reviewer + 方法论库」
```

**三个可控用途：**

1. **UX Review Gate** - 门禁审查
2. **UI Prompt 规范化** - 约束补全
3. **UI Spec 文档生成** - 结构化产出

---

## 二、集成架构

**主要集成点：ui-design-pipeline**

```
┌─────────────────────────────────────────────────────────────────┐
│                  UI Design Pipeline (主要集成点)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  阶段 1: 设计验证                                               │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐   ┌────────┐ │
│  │ Contract   │──▶│ Contract   │──▶│ UX Review  │──▶│ UI     │ │
│  │ Generation │   │ Validation │   │ (新增1.2a) │   │ Gate   │ │
│  │    1.1     │   │    1.2     │   │            │   │  1.3   │ │
│  └────────────┘   └────────────┘   └────────────┘   └────────┘ │
│                                           │                     │
│                                           ▼                     │
│                                  ┌─────────────────┐            │
│                                  │ ui-ux-pro-max   │            │
│                                  │     skill       │            │
│                                  └─────────────────┘            │
│                                                                 │
│  阶段 2: 研发                                                   │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐              │
│  │ Test Gen   │──▶│ Development│──▶│ Dev Gate   │              │
│  │    2.1     │   │    2.2     │   │    2.3     │              │
│  └────────────┘   └────────────┘   └────────────┘              │
│                                                                 │
│  阶段 3: 发布                                                   │
│  ┌────────────┐   ┌────────────┐   ┌────────────┐              │
│  │ Staging    │──▶│ Release    │──▶│ Production │              │
│  │    3.1     │   │ Gate 3.2   │   │    3.3     │              │
│  └────────────┘   └────────────┘   └────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘

Phase 7/8 通过引用 ui-design-pipeline 自动获得 UX Review 能力
```

---

## 三、新增组件

### 3.1 UX Review Agent

**文件位置**: `ai-spec/specs/common/agents/ux-review-agent/v1/agent.yaml`

**职责**:
- 基于 Nielsen 启发式检查可用性
- 分析信息架构合理性
- 验证交互一致性
- 审计可访问性 (WCAG AA)

**输入**: PRD / 页面规范 / UI 草图
**输出**: 结构化审查报告 (问题清单 + 严重级别 + 修复建议)

### 3.2 UI Prompt Enhancer Skill

**文件位置**: `ai-spec/specs/common/skills/ui-prompt-enhancer/v1/skill.yaml`

**职责**:
- 将模糊需求转换为结构化约束
- 搜索 ui-ux-pro-max 知识库
- 生成可验证的设计约束

**输入**: 原始需求 + 产品类型 + 平台
**输出**: 结构化约束文档 (yaml)

### 3.3 UX Review Contract

**文件位置**: `ai-spec/specs/common/contracts/ux-review-contract/v1/schema.yaml`

**职责**:
- 定义审查输入输出格式
- 确保审查结果可追踪

---

## 四、Workflow 集成点

### 4.1 ui-design-pipeline 集成 (主要集成点)

在 `ui-design-pipeline/v1/workflow.yaml` 中，UX Review 作为独立步骤 (1.2a) 插入：

```
完整流程:
1.1 契约生成 → 1.2 契约验证 → 1.2a UX 审查 (新增) → 1.3 UI Gate → ...
```

**已实现的步骤定义** (`workflow.yaml` 第 129-184 行):

```yaml
# 阶段 1.2a: UX 可用性审查 (UX Review)
- id: ux_review
  agent: ux_reviewer@v1
  contract: ux-review-contract@v1

  metadata:
    name: UX Usability Review
    name_zh: UX 可用性审查
    stage_id: "1.2a"
    description: |
      基于 ui-ux-pro-max-skill 审查 UI 契约的可用性问题。
      审查维度: Nielsen 启发式、信息架构、交互一致性、WCAG AA、状态完整性

  input:
    - source: contract_validation
      required: true
    - file: "spec/ui/pages/*.page.yaml"
    - file: "spec/ui/components/*.component.yaml"

  output:
    file: "output/review-reports/ux-review-{timestamp}.md"

  skill_integration:
    skill: ui-ux-pro-max
    search_commands:
      - "python .claude/skills/ui-ux-pro-max/scripts/search.py '{product_type}' --domain ux"

  gate_config:
    pass_criteria:
      ux_blocker: 0    # Blocker 必须为 0
      ux_major: 3      # Major 最多 3 个
```

### 4.2 UI Gate 增强

`ui_gate` 步骤已更新为依赖 `ux_review`：

```yaml
- id: ui_gate
  # ...
  input:
    - source: ux_review           # 改为依赖 UX 审查
      required: true
    - file: "output/review-reports/ux-review-*.md"
      required: true

  gate_config:
    gate_type: ui
    pass_criteria:
      blocker: 0
      major: 0
      ux_blocker: 0     # UX Blocker 必须为 0
      ux_major: 3       # UX Major 最多 3 个
```

### 4.3 Phase 7/8 自动获得 UX Review

Phase 7 (组件开发) 和 Phase 8 (页面开发) 通过引用 ui-design-pipeline 自动获得 UX Review 能力：

```yaml
# phase7/workflow.yaml 或 phase8/workflow.yaml
steps:
  - id: ui_design
    use: ui-design-pipeline@v1    # 引用整个流水线
    # 自动包含: 契约生成 → 契约验证 → UX 审查 → UI Gate → ...
```

**无需在每个 Phase 单独配置 UX Review 步骤。**

---

## 五、使用流程

### 5.1 生成 UI 前 (Prompt 规范化)

```bash
# 1. 使用 UI Prompt Enhancer 规范化需求
# 输入: 模糊需求
# 输出: 结构化约束

# 示例: 设计跑步 App 图标
python .claude/skills/ui-ux-pro-max/scripts/search.py "fitness running app" --domain product
python .claude/skills/ui-ux-pro-max/scripts/search.py "fitness running app" --domain color
python .claude/skills/ui-ux-pro-max/scripts/search.py "minimalism professional" --domain style
```

生成的约束文档：

```yaml
ui_constraints:
  style:
    primary: minimalism
    effects: ["subtle gradient", "clean silhouette"]
    avoid: ["complex gradients", "text in icon"]
  colors:
    use_design_system: true
    primary: "#FF6B00"
    secondary: "#1A73E8"
  forbidden:
    - "emoji"
    - "fine details at small size"
  verification_checklist:
    - check: "图标在 24px 下仍可识别"
    - check: "主色符合设计系统"
```

### 5.2 设计完成后 (UX 审查)

```bash
# 2. 运行 UX Review Agent
# 输入: 页面规范 / 组件规范
# 输出: 审查报告

orchestrator start ./project/AI跑步教练/dev p08_03a_ux_review --agent claude
```

审查报告示例：

```yaml
summary:
  total_issues: 3
  by_severity:
    blocker: 0
    major: 1
    minor: 2
  pass_gate: true

issues:
  - id: UX-001
    severity: major
    category: state_completeness
    description: "训练卡片缺少 error 状态"
    principle:
      name: "状态完整性"
      source: "UI Contract Standard"
    recommendation: "添加 error 状态，显示重试按钮"
```

### 5.3 Gate 检查

```bash
# 3. 通过 Gate 后进入实现
orchestrator validate ./project/AI跑步教练/dev p08_03a_ux_review

# 如果 pass_gate: true
orchestrator start ./project/AI跑步教练/dev p08_04_implementation
```

---

## 六、质量保证

### 6.1 可验证性检查清单

每次 UX 审查后验证：

| 检查项 | 自动化 | 说明 |
|--------|--------|------|
| 问题有 ID 编号 | ✅ | UX-001 格式 |
| 严重级别有定义 | ✅ | blocker/major/minor |
| 违反原则有来源 | ✅ | Nielsen/WCAG/HIG |
| 修复建议可执行 | ⚠️ | 人工判断 |
| Gate 规则明确 | ✅ | blocker=0 通过 |

### 6.2 禁止行为

```yaml
forbidden_behaviors:
  - 让 ui-ux-pro-max 直接生成最终 UI
  - 跳过 UX 审查直接实现
  - 忽略 blocker 级问题
  - 接受无依据的"这样更好"
```

---

## 七、回退机制

如果 UX 审查阻断流程：

1. **Blocker 问题** → 必须修复后重新审查
2. **Major > 3** → 可申请人工豁免
3. **审查结果争议** → 升级到人工评审

```bash
# 申请人工豁免
orchestrator request-exception ./project/AI跑步教练/dev p08_03a_ux_review \
  --reason "业务紧急，Minor 问题延后修复" \
  --approver product-manager
```

---

## 八、相关文件

| 文件 | 说明 |
|------|------|
| `workflows/ui-design-pipeline/v1/workflow.yaml` | UI 设计流水线 (主要集成点) |
| `agents/ux-review-agent/v1/agent.yaml` | UX 审查 Agent 定义 |
| `skills/ui-prompt-enhancer/v1/skill.yaml` | UI Prompt 增强 Skill |
| `contracts/ux-review-contract/v1/schema.yaml` | UX 审查契约 |
| `.claude/skills/ui-ux-pro-max/` | ui-ux-pro-max 知识库 |

---

## 九、总结

**集成原则**:

1. **不寄予生成 UI 的期待** - 只做审查和约束规范化
2. **放在 Gate 位置** - 作为质量门禁
3. **绑定硬性 Contract** - 确保输出可验证
4. **永远不让它单独交付 UI** - 必须配合人工/专业设计

**价值体现**:

- ✅ 系统化输出设计常识
- ✅ 早期发现可用性问题
- ✅ 规范化设计约束
- ✅ 减少返工成本
