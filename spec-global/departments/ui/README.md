# UI 设计部门 (ui)

> UI Design Department

## 部门职责

负责 UI 设计、原型设计、设计系统维护和设计规范管理。

### 职责边界

| 维度 | 说明 |
|------|------|
| **输入** | PRD 冻结包（来自 PRD 部门） |
| **输出** | UI 冻结包（交付给 Dev 部门） |
| **终点** | UI Gate 通过后，流程结束 |

### 主要职责

- UI/UX 设计
- 原型设计
- 设计系统维护
- 设计规范制定
- 用户流契约定义
- AI 友好性验证

### 核心设计原则（v1.1 新增）

遵循「AI 时代产品与 UE 设计宪法」：

1. **单主路径原则** - V1 阶段每个功能只有一条强制闭合的主路径
2. **状态不可隐含** - 所有状态必须显性化，有明确恢复路径
3. **前置条件入口处解决** - 条件不满足→隐藏入口或禁用+文案
4. **AI 友好性** - AI 必须能仅凭 UI 顺序盲跑通过主路径
5. **路径可枚举** - 不允许存在未被枚举的隐式路径

## 目录结构

```
ui/
├── workflows/      # 部门工作流
├── gates/          # 部门门禁
├── agents/         # 部门专属 Agent
├── skills/         # 部门技能
├── contracts/      # 部门交付物契约
└── demos/          # 演示示例
```

## 工作流 (workflows)

| 工作流 | 版本 | 说明 | 输入 | 输出 |
|--------|------|------|------|------|
| ui-design-pipeline | v1.2 | UI 设计流水线 | PRD 冻结包 | UI 冻结包 |

### 流程概览

```
PRD冻结包 → 契约生成 → 契约验证 → 用户流生成 → AI盲跑验证 → UX审查 → UI Gate → UI冻结包
   ↑                                                                              ↓
PRD部门                                                                        Dev部门
```

## 门禁 (gates)

| 门禁 | 版本 | 触发条件 | 检查项 |
|------|------|----------|--------|
| ui-gate | v1.1 | 设计阶段完成 | 契约完整性、单主路径、AI盲跑、UX审查结果 |

### UI Gate v1.1 检查项

| 检查项 | 严重度 | 说明 |
|--------|--------|------|
| figma_links | blocker | Figma 设计稿链接 |
| page_contracts | blocker | 页面契约完整 |
| required_states | blocker | 必需状态覆盖 (default/loading/empty/error) |
| single_main_path_verified | blocker | 单主路径验证 |
| preconditions_at_entry | blocker | 前置条件入口处解决 |
| no_hidden_state | blocker | 状态不可隐含 |
| ai_walkthrough_passed | blocker | AI 盲跑验证通过 (≥80分) |
| user_flow_contracts_exist | blocker | 用户流契约存在 |
| blocked_patterns_defined | major | 禁止模式定义 |
| recovery_strategies_defined | major | 恢复策略定义 |
| paths_enumerable | major | 路径可枚举 |

## Agent 列表

| Agent | 版本 | 职责 | 说明 |
|-------|------|------|------|
| ui-designer | v1.0 | UI 设计师 | 设计交互流程和关键页面状态 |
| prototype-designer | v1.1 | 原型设计师 | 遵循单主路径原则设计原型，输出 User Flow Contract |
| ui-design-executor | v2.0 | UI 设计执行器 | Design-System-First 执行完整 UI 设计 |
| ui-contract-generator | v1.0 | UI 契约生成 | 从 Figma 生成 UI 契约 |
| ui-contract-validator | v1.0 | UI 契约验证 | 验证 UI 契约完整性和一致性 |
| icon-generator | v1.0 | 图标生成 | 生成应用图标资产 |
| ui-test-generator | v1.0 | 测试生成 | 从契约生成测试用例 |
| ux-review-agent | v1.0 | UX 审查 | Nielsen 启发式可用性审查 |
| ai-walkthrough-validator | v1.0 | AI 盲跑验证 | 验证 AI 能否盲跑通过主路径 |
| ui-gate-runner | v1.0 | Gate 执行器 | 执行 UI Gate 检查 |

## 契约 (contracts)

| 契约 | 版本 | 说明 |
|------|------|------|
| user-flow-contract | v1.0 | 用户流契约 - 定义单主路径 |
| ui-page-contract | v1.1 | 页面契约 - 含前置条件、恢复路径 |
| ui-component-contract | v1.0 | 组件契约 |
| ui-tokens-contract | v1.0 | 设计 Token 契约 |
| ui-a11y-contract | v1.0 | 可访问性契约 |
| ui-map-contract | v1.0 | UI 索引契约 |
| ux-review-contract | v1.0 | UX 审查结果契约 |
| frozen-ui-prototype-contract | v1.0 | UI 原型冻结契约 |
| icon-design-token | v1.0 | 图标设计 Token |

## 技能 (skills)

| 技能 | 说明 |
|------|------|
| design-token-generator | W3C DTCG 1.0 标准 Token 生成 |
| ui-gate-check | UI Gate 检查执行 |
| figma-parser | Figma 设计稿解析 |
| figma-component-builder | Figma 组件构建 |
| figma-design-system | Figma 设计系统管理 |
| figma-interaction-design | Figma 交互设计 |
| auto-layout-master | 自动布局 |
| variant-system | 变体系统管理 |
| ui-prompt-enhancer | UI 提示词增强 |
| markdown-to-contract | Markdown 转契约 |
| icon-svg-generator | SVG 图标生成 |
| web-prototype-renderer | Web 原型渲染 |
| figma-import-guide | Figma 导入指南 |

## 跨部门协作

### 上游（输入）

| 来源部门 | 输入物 | 说明 |
|----------|--------|------|
| PRD | PRD 冻结包 | 产品需求规格说明 |

### 下游（输出）

| 目标部门 | 输出物 | 说明 |
|----------|--------|------|
| Dev | UI 冻结包 | 包含所有 UI 契约、User Flow、Gate 报告 |

### UI 冻结包内容

```
output/ui-frozen/{project}-ui-freeze.md
├── spec/ui/ui.map.yaml           # UI 契约索引
├── spec/ui/flows/*.flow.yaml     # 用户流契约
├── spec/ui/pages/*.page.yaml     # 页面契约
├── spec/ui/components/*.yaml     # 组件契约
├── spec/ui/tokens/tokens.json    # 设计 Token
├── output/reports/ai-walkthrough-*.json  # AI 盲跑报告
├── output/review-reports/ux-review-*.md  # UX 审查报告
└── output/gate-reports/ui-gate-*.md      # UI Gate 报告
```

## 演示 (demos)

| 演示 | 说明 |
|------|------|
| user-login-flow | 用户登录流程 - 单主路径原则完整落地演示 |

---

**最后更新**：2026-02-06

**维护者**：LEE 框架团队
