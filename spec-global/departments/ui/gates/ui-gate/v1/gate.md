# UI Gate v1.0

UI 门禁规范 - 进入研发阶段前的质量检查。

## 概述

UI Gate 是 UI 设计进入研发阶段前的质量门禁，确保：
- Figma 设计稿就绪
- UI Contract 完整
- 必需状态全覆盖
- 可访问性配置齐全

## 触发时机

```
设计阶段完成 → UI 评审通过 → UI Gate 检查 → 进入研发
```

## 检查清单

### Blocker 级别（必须通过）

| 检查项 | 规则 | 说明 |
|--------|------|------|
| **Figma 链接** | 每个 page/component 有 figma 字段 | 无链接不允许进入研发 |
| **页面契约** | 每个 page 有 contracts.page 引用 | 缺少契约不允许进入研发 |
| **必需状态** | 每个 page 定义 default/loading/empty/error | 状态不全不允许进入研发 |
| **P0 页面完整** | 所有 P0 页面 status=approved | P0 未完成不允许进入研发 |

### Major 级别（强烈建议修复）

| 检查项 | 规则 | 说明 |
|--------|------|------|
| **组件契约** | 每个 component 有 contract 引用 | 组件规范不全 |
| **Tokens 文件** | tokens.json 存在 | 设计 token 缺失 |
| **A11y 配置** | requireA11y=true 时有 a11y 配置 | 可访问性配置缺失 |
| **交互绑定** | 有 API 的交互绑定 contractRef | 接口契约未关联 |

### Minor 级别（建议修复）

| 检查项 | 规则 | 说明 |
|--------|------|------|
| **埋点配置** | requireTracking=true 时有 tracking 配置 | 埋点规范缺失 |

## 通过条件

```yaml
pass_criteria:
  blocker: 0    # 不允许有 blocker
  major: 0      # 不允许有 major
  minor: null   # minor 仅警告，不阻断
```

## 运行方式

### 命令行

```bash
# 运行 UI Gate 检查
npx ui-gate check --config=spec/ui/ui.map.yaml

# 输出详细报告
npx ui-gate check --config=spec/ui/ui.map.yaml --verbose --output=report.json
```

### CI 集成

```yaml
# .github/workflows/ui-gate.yml
name: UI Gate

on:
  pull_request:
    paths:
      - 'spec/ui/**'

jobs:
  ui-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Run UI Gate
        run: npx ui-gate check --config=spec/ui/ui.map.yaml

      - name: Upload Report
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: ui-gate-report
          path: output/gate-reports/
```

## 报告示例

### 通过时

```
✅ UI Gate 通过

检查结果:
- [PASS] Figma 链接: 9/9 页面有链接
- [PASS] 页面契约: 9/9 页面有契约
- [PASS] 必需状态: 36/36 状态已定义
- [PASS] P0 页面: 4/4 已审批
- [PASS] 组件契约: 8/8 组件有契约
- [PASS] Tokens 文件: 存在
- [PASS] A11y 配置: 9/9 页面已配置
- [WARN] 埋点配置: 7/9 页面已配置

总结: 0 blocker, 0 major, 2 minor
可以进入研发阶段
```

### 失败时

```
❌ UI Gate 未通过

检查结果:
- [FAIL] Figma 链接: 7/9 页面有链接
  缺失: page.settings, page.achievements
- [FAIL] 必需状态: 32/36 状态已定义
  缺失: page.ai_coach (empty, error)
- [PASS] 页面契约: 9/9 页面有契约
- [WARN] 埋点配置: 5/9 页面已配置

总结: 2 blocker, 0 major, 4 minor
请修复 blocker 问题后重新提交
```

## 修复指南

### Figma 链接缺失

```yaml
# 在 ui.map.yaml 中添加
pages:
  - id: page.settings
    figma: https://figma.com/design/xxx/settings  # 添加链接
```

### 必需状态缺失

```yaml
# 在 page.yaml 中添加状态
states:
  - name: default
    components: [...]
  - name: loading
    pattern: skeleton
  - name: empty             # 添加缺失的状态
    messageKey: xxx_empty
  - name: error             # 添加缺失的状态
    errorCodes: [...]
```

### A11y 配置缺失

```yaml
# 在 page.yaml 中添加
a11y:
  required: true
  focusOrder: [...]
  landmarks:
    - role: main
      label: 页面主要内容
```

## 与其他 Gate 的关系

```
需求冻结 → UI Gate → Dev Gate → Release Gate
              ↑
           当前位置
```

- **前置**: 需求冻结（frozen-module-requirement）
- **后续**: Dev Gate（开发门禁）
