# UI Map Contract v1.0

UI 全局索引契约 - 页面/路由/权限/埋点总索引，用于门禁验证。

## 核心理念

**UI Map 是质量门禁的核心数据源**：
- 记录所有页面和组件的契约位置
- 定义质量要求（a11y、tracking、tokens）
- 追踪覆盖率和实现状态

## 完整示例

```yaml
# spec/ui/ui.map.yaml
$schema: ui-map-contract/v1
version: "1.0.0"

project:
  name: Running AI Coach
  description: 跑步AI教练应用
  figmaProject: https://figma.com/project/running-coach

pages:
  - id: page.home
    name: 首页
    route: /
    figma: https://figma.com/design/xxx/home
    contracts:
      page: spec/ui/pages/home.page.yaml
      api:
        - api.user.profile
        - api.training.recent
    requiredStates: [default, loading, empty, error]
    priority: P0
    status: approved
    owners: [designer-a, pm-b]

  - id: page.training_plan
    name: 训练计划
    route: /training/:planId
    figma: https://figma.com/design/xxx/training
    contracts:
      page: spec/ui/pages/training-plan.page.yaml
      api:
        - api.training.plan
        - api.training.sessions
    requiredStates: [default, loading, empty, error]
    priority: P0
    status: review

  - id: page.run_record
    name: 跑步记录
    route: /run/:recordId
    figma: https://figma.com/design/xxx/run-record
    contracts:
      page: spec/ui/pages/run-record.page.yaml
    priority: P1
    status: draft

components:
  - id: component.primary_button
    name: 主按钮
    figma: https://figma.com/design/xxx/button
    contract: spec/ui/components/primary-button.component.yaml
    category: basic
    status: implemented

  - id: component.training_card
    name: 训练卡片
    figma: https://figma.com/design/xxx/training-card
    contract: spec/ui/components/training-card.component.yaml
    category: business
    status: review

  - id: component.pace_chart
    name: 配速图表
    figma: https://figma.com/design/xxx/pace-chart
    contract: spec/ui/components/pace-chart.component.yaml
    category: data-display
    status: draft

routes:
  - path: /
    pageId: page.home
    roles: [guest, user]
    meta:
      title: 首页
      layout: default

  - path: /training/:planId
    pageId: page.training_plan
    roles: [user]
    guards: [authGuard]
    meta:
      title: 训练计划
      requiresAuth: true

  - path: /run/:recordId
    pageId: page.run_record
    roles: [user]
    guards: [authGuard]
    meta:
      title: 跑步记录
      requiresAuth: true

quality:
  requireA11y: true
  requireTracking: true
  requireTokens: true
  requireFigma: true
  requiredStates:
    - default
    - loading
    - empty
    - error
  testCoverage:
    unit: 80
    e2e: 60

coverage:
  generatedAt: "2026-01-08T10:00:00Z"
  pages:
    total: 3
    withContract: 3
    withFigma: 3
    withTests: 1
  components:
    total: 3
    withContract: 3
    withStorybook: 1
  states:
    covered: 10
    missing:
      - page.run_record.loading
      - page.run_record.empty
```

## 门禁检查规则

### UI Gate（进入研发前）

```yaml
checks:
  - name: figma_link_exists
    rule: "每个 page 必须有 figma 链接"
    severity: blocker

  - name: page_contract_exists
    rule: "每个 page 必须有 contracts.page 引用"
    severity: blocker

  - name: required_states_defined
    rule: "每个 page 的 requiredStates 必须全覆盖"
    severity: blocker

  - name: tokens_required
    rule: "quality.requireTokens = true 时，tokens.json 必须存在"
    severity: major
```

### Dev Gate（合并前）

```yaml
checks:
  - name: component_storybook
    rule: "每个 component 必须有 Storybook story"
    severity: major

  - name: a11y_compliance
    rule: "quality.requireA11y = true 时，a11y 测试必须通过"
    severity: major
```

### Release Gate（交付前）

```yaml
checks:
  - name: e2e_coverage
    rule: "所有 P0 页面必须有 E2E 覆盖"
    severity: blocker

  - name: tracking_implementation
    rule: "quality.requireTracking = true 时，埋点必须实现"
    severity: major
```

## 覆盖率计算

```typescript
// 自动生成覆盖率报告
const coverage = {
  pages: {
    total: uiMap.pages.length,
    withContract: uiMap.pages.filter(p => p.contracts?.page).length,
    withFigma: uiMap.pages.filter(p => p.figma).length,
    withTests: await countPagesWithTests(uiMap.pages),
  },
  components: {
    total: uiMap.components.length,
    withContract: uiMap.components.filter(c => c.contract).length,
    withStorybook: await countComponentsWithStorybook(uiMap.components),
  },
  states: await calculateStateCoverage(uiMap.pages),
};
```

## 与 CI 集成

```yaml
# .github/workflows/ui-gate.yml
- name: UI Map Validation
  run: |
    npx ui-contract-lint spec/ui/ui.map.yaml
    npx ui-coverage-check --min-pages=80 --min-components=70
```
