# UX Review Agent

> UX 审查 Agent - 基于 ui-ux-pro-max-skill 的可用性审查

## 触发条件

当任务涉及以下内容时调用此 Agent：
- UI/UX 审查
- 可用性评审
- 交互一致性检查
- 信息架构分析
- 页面状态完整性验证

## Agent 引用

```
agent.design.ux_reviewer
```

## 定位

| 角色 | 说明 |
|------|------|
| ✅ 适合 | 审查 UI 设计的可用性问题 |
| ✅ 适合 | 检查信息架构合理性 |
| ✅ 适合 | 验证状态完整性 |
| ❌ 不适合 | 生成 UI 代码 |
| ❌ 不适合 | 替代专业设计师判断 |

## 输入要求

1. **审查目标** (必需)
   - 页面规范 (*.page.yaml)
   - 组件规范 (*.component.yaml)
   - UI 原型截图

2. **上下文** (必需)
   - 产品类型
   - 目标用户
   - 设计系统 (可选)

## 输出产物

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
    description: "问题描述"
    principle:
      name: "违反原则"
      source: "Nielsen Heuristics #1"
    recommendation: "修复建议"
```

## 审查维度

### 1. 可用性 (Nielsen Heuristics)
- 系统状态可见性
- 匹配真实世界
- 用户控制与自由
- 一致性与标准
- 错误预防

### 2. 信息架构
- 导航结构清晰度
- 层级关系合理性
- 内容分组逻辑

### 3. 状态完整性
- default 状态
- loading 状态
- empty 状态
- error 状态

### 4. 可访问性
- 对比度 (WCAG AA)
- 触摸目标 (>=44px)
- 替代文本

## 使用流程

### 步骤 1: 搜索相关 UX 准则

```bash
python .claude/skills/ui-ux-pro-max/scripts/search.py "{产品类型}" --domain ux
python .claude/skills/ui-ux-pro-max/scripts/search.py "accessibility" --domain ux
```

### 步骤 2: 分析审查目标

读取页面/组件规范，检查：
- 状态定义是否完整
- 交互模式是否一致
- 信息层级是否清晰

### 步骤 3: 生成审查报告

按严重级别输出问题清单：
- **Blocker**: 阻断级，必须修复
- **Major**: 严重，影响核心路径
- **Minor**: 轻微，体验问题
- **Enhancement**: 优化建议

## Gate 规则

```yaml
pass_criteria:
  blocker: 0    # Blocker 必须为 0
  major: 3      # Major 最多 3 个
```

## 使用示例

```
请使用 ux-review-agent 审查首页设计:

审查目标:
- ui/pages/home.page.yaml
- ui/components/training-card.component.yaml

上下文:
- 产品类型: AI 跑步教练
- 目标用户: 严肃跑者
- 平台: 微信小程序

重点审查:
- 用户路径顺畅性
- 状态完整性
- 可访问性
```

## Workflow 集成

**主要集成点**: `ui-design-pipeline/v1/workflow.yaml`

UX Review 作为步骤 1.2a 插入流水线：

```
1.1 契约生成 → 1.2 契约验证 → 1.2a UX 审查 → 1.3 UI Gate → ...
```

```yaml
- id: ux_review
  agent: ux_reviewer@v1
  contract: ux-review-contract@v1
  stage_id: "1.2a"
  input:
    - source: contract_validation
  output:
    file: "output/review-reports/ux-review-{timestamp}.md"
```

Phase 7/8 通过引用 ui-design-pipeline 自动获得 UX Review 能力。

## 关联规范

- 权威 Spec: `ai-spec/specs/common/agents/ux-review-agent/v1/agent.yaml`
- 输入输出契约: `ai-spec/specs/common/contracts/ux-review-contract/v1/schema.yaml`
- 集成指南: `ai-spec/specs/common/skills/ui-ux-pro-max-integration/v1/integration-guide.md`
