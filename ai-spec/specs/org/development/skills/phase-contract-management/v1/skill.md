# Phase Contract Management Skill v1.0

> **技能类型**: 确定性能力 (数据管理)
> **无决策**: 管理 Phase Contract 的读写操作

## 概述

提供 Phase Contract (phase.yaml) 的标准操作能力。

## Phase Contract 结构

```yaml
phase_id: {kebab-case-id}
phase_name: {人类可读名称}
description: {描述}
owner: {负责人}
status: planning|in_progress|review|completed|blocked
priority: P0|P1|P2|P3

inputs:
  requirement_source: {需求文件路径}
  ui_source: {UI 设计路径}
  architecture_source: {架构文件路径}
  dependencies:
    - phase_id: {依赖的 Phase}
      type: hard|soft
      interface: {接口描述}
  assumptions:
    - {假设1}
    - {假设2}

outputs:
  deliverables:
    - type: api|component|service|module|config|doc
      path: {路径}
      contract: {契约文件}
  interfaces:
    - name: {接口名}
      type: rest_api|graphql|grpc|event|sdk
      spec_path: {规范路径}
  tests:
    unit_coverage_threshold: 80
    integration_tests_required: true

quality_gates:
  requirement_calibration:
    required: true
  test_contract:
    required: true
    min_scenarios: 3
  unit_test:
    required: true
    coverage_threshold: 80
  code_review:
    required: true
    min_reviewers: 1
  retrospective:
    required: true

openspec:
  workspace_path: ./openspec
  auto_init: true
  archive_on_complete: true

schedule:
  planned_start: {date}
  planned_end: {date}
  actual_start: {date}
  actual_end: {date}

handover:
  ready_for_integration: false
  integration_notes: {说明}
  known_issues: []
  verified_by: {验证人}
  verified_at: {时间}
```

## 操作定义

### 1. 创建 Phase Contract

```yaml
# 输入
phase_id: auth
phase_name: 用户认证模块
inputs:
  requirement_source: ../02-requirements/auth-requirement.md

# 输出
# 04-phases/auth/phase.yaml
```

### 2. 更新状态

```yaml
# 操作
update_status:
  phase_id: auth
  new_status: in_progress
  timestamp: {current_time}
```

### 3. 更新交接信息

```yaml
# 操作
update_handover:
  phase_id: auth
  ready_for_integration: true
  integration_notes: "API 端点已就绪"
  known_issues:
    - "需要配置 Redis"
```

### 4. 读取 Phase Contract

```yaml
# 操作
read_contract:
  phase_id: auth

# 输出: 完整的 phase.yaml 内容
```

### 5. 验证 Phase Contract

```yaml
# 操作
validate_contract:
  phase_id: auth

# 输出
validation_result:
  valid: true|false
  errors: []
  warnings: []
```

## 状态转换规则

```
planning → in_progress  # 开始开发
in_progress → review    # 提交审查
review → completed      # 审查通过
review → in_progress    # 审查未通过，返工
* → blocked             # 被阻塞
blocked → in_progress   # 解除阻塞
```

## 目录结构

```
04-phases/
├── {phase-id}/
│   ├── phase.yaml           # Phase Contract (本 Skill 管理)
│   ├── openspec/            # OpenSpec 工作空间
│   └── output/
│       ├── handover.yaml
│       ├── artifacts.md
│       └── ...
```

## 约束

- ❌ 不决定 Phase 划分
- ❌ 不判断状态转换合理性
- ❌ 不修改依赖关系
- ✅ 只做 CRUD 操作
- ✅ 只做格式验证
- ✅ 只做状态更新
