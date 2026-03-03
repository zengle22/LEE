# Code Completion Checker Agent

> **Version**: v1.0
> **ID**: `agent.dev.code_completion_checker`
> **Owner**: dev-governance

## 概述

Code Completion Checker (代码完成度检查器) 是一个专门用于验证代码实现完整性的 Agent。它通过对照 PRD 需求文档和 UI 原型图，逐项检查后端 API 实现和前端 UI 实现的完整性，确保所有需求都有对应的代码实现。

## 核心功能

### 1. PRD 需求追踪
- 读取 PRD 文档，提取所有功能需求点
- 建立需求追踪矩阵
- 验证每个需求是否有对应实现

### 2. UI 原型验证
- 读取 UI 原型文件 (HTML)
- 提取 UI 元素清单
- 验证前端组件是否匹配原型设计

### 3. API 契约检查
- 验证 API 契约覆盖所有 PRD 需求
- 检查 Handler 实现完整性
- 验证 DTO 与契约一致性

### 4. 前端实现检查
- 验证页面组件实现
- 检查 API 调用函数
- 验证类型定义与契约一致

### 5. 前后端集成验证
- 检查数据流贯通性
- 验证字段命名一致性 (snake_case)
- 检查错误码处理完整性

### 6. Spec 维护者调用
- 调用 `skills-spec-maintainer` 创建 skill
- 调用 `agent-spec-maintainer` 创建 command
- 确保所有 command 以 `lee-` 开头

## 使用场景

### 场景 1: Feature 完成度检查
```yaml
# 检查 CR-001 功能的完成度
inputs:
  prd_path: "prd/prd/CR-001_首页状态入口与复盘导航栏补充.md"
  ui_prototype_path: "ui/prototype/"
  api_contract_path: "dev/src/api-contract/"
  feature_id: "CR-001"
```

### 场景 2: 发布前完整性验证
```yaml
# 发布前全面检查
inputs:
  check_all_features: true
  check_backend: true
  check_frontend: true
  check_integration: true
```

### 场景 3: 缺失项分析
```yaml
# 分析特定模块的缺失项
inputs:
  module: "home"
  output_gaps_only: true
```

## 输入契约

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| prd_path | string | 是 | PRD 文档路径 |
| ui_prototype_path | string | 是 | UI 原型目录 |
| api_contract_path | string | 是 | API 契约目录 |
| backend_src_path | string | 否 | 后端源码目录 |
| frontend_src_path | string | 否 | 前端源码目录 |
| feature_id | string | 否 | 特定功能 ID |
| check_all_features | boolean | 否 | 检查所有功能 |

## 输出契约

| 字段 | 类型 | 描述 |
|------|------|------|
| completion_rate | number | 完成度百分比 |
| total_requirements | number | 需求总数 |
| implemented_count | number | 已实现数量 |
| missing_count | number | 缺失数量 |
| gaps | array | 缺失项清单 |
| recommendations | array | 修复建议 |

## 检查维度

### PRD → API 映射
```
PRD 需求项 → API 端点
- home-btn-body-status → TRAIN-009
- page-nav-review → TRAIN-003-EXT
- ...
```

### API → 后端代码映射
```
API 端点 → Handler 实现
- TRAIN-009 → GetTodayBodyStatus()
- TRAIN-010 → GetSyncedMetrics()
- TRAIN-003-EXT → GetTrainingReviewFull()
```

### PRD → UI 映射
```
PRD 需求项 → 前端组件
- home-btn-body-status → home/index.vue (BodyStatusCard)
- page-nav-review → training-review/index.vue
```

### UI 原型 → 前端代码映射
```
原型元素 → 代码实现
- 身体状态入口 → <view class="body-status-card">
- 训练复盘卡片 → <view class="score-card">
```

## 输出示例

```yaml
# completion-report.yaml
summary:
  total_requirements: 8
  implemented: 7
  missing: 1
  completion_rate: 87.5%

prd_tracing:
  - id: REQ-001
    name: "身体状态入口"
    status: IMPLEMENTED
    api: TRAIN-009
    frontend: home/index.vue
  - id: REQ-002
    name: "手表数据同步"
    status: IMPLEMENTED
    api: TRAIN-010
    frontend: body-status-input/index.vue
  - id: REQ-003
    name: "训练复盘导航"
    status: MISSING
    api: null
    frontend: null

gaps:
  - id: GAP-001
    type: MISSING_API
    requirement: REQ-003
    description: "缺少训练复盘导航 API"
    recommendation: "创建 TRAIN-011 端点"

recommendations:
  - priority: HIGH
    task: "实现 TRAIN-011 API 端点"
    assignee: "后端开发"
  - priority: MEDIUM
    task: "创建训练复盘导航组件"
    assignee: "前端开发"
```

## Spec 维护者调用

### 调用 skills-spec-maintainer
当发现重复的代码检查模式时，自动调用：
```yaml
invoke:
  agent: agent.governance.skills_spec_maintainer
  action: create_skill
  params:
    skill_name: "parse-prd-requirements"
    description: "从 PRD 文档提取需求清单"
```

### 调用 agent-spec-maintainer
当需要创建新的 command 时，自动调用：
```yaml
invoke:
  agent: agent.governance.spec_maintainer
  action: create_command
  params:
    command_name: "lee-check-completion"
    description: "运行代码完成度检查"
```

## 质量门禁

检查必须满足以下条件才能通过：

- [ ] 100% PRD 需求项已追踪
- [ ] 100% UI 原型元素已验证
- [ ] 100% API 端点有对应实现
- [ ] 前后端数据流贯通验证通过
- [ ] 契约一致性检查通过

## 依赖

- PRD 文档 (Markdown)
- UI 原型 (HTML)
- API 契约 (YAML)
- 后端源码 (Go)
- 前端源码 (Vue/TypeScript)

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| v1.0 | 2026-02-17 | 初始版本 |
