---
title: Gate Review Skill 使用指南
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# Gate Review Skill 使用指南

## 概述

`gate-review` 是一个全局 skill，用于快速审核和审批 LEE 系统中的 human gates。

## 功能特性

- ✅ 列出所有待审批的 gates
- ✅ 显示 gate 详情（审批标准、检查清单）
- ✅ 显示上游分析摘要
- ✅ 提交审批决策
- ✅ 生成决策报告
- ✅ 支持多种决策类型

## Slash Command 使用

### 基本语法

```
/gate-review [action] [gate_id] [--option] [--comment TEXT]
```

### 使用示例

#### 1. 列出所有待审批 gates

```
/gate-review
```

或者明确指定 action：

```
/gate-review list
```

**输出示例**：
```markdown
## 🚪 Pending Gates

### 1. `freeze_market_signals`
**Status**: pending
**Description**: 这是系统稳定性的根！
**Dependencies**: analyze_user_signals, analyze_industry_structure, analyze_supply_competition

📋 Approval Criteria:
  - [分析一致性] 三个分析层输出无明显矛盾
  - [置信度达标] 综合置信度 ≥ 50
  - [可验证性] 核心假设可以通过后续验证
```

#### 2. 查看特定 gate 详情

```
/gate-review freeze_market_signals
```

或者明确指定 action：

```
/gate-review show freeze_market_signals
```

**输出示例**：
```markdown
## 🚪 Gate Details: `freeze_market_signals`

**Status**: pending
**Step**: 市场信号冻结

**Description**:
这是系统稳定性的根！冻结分析层的所有结论...

### ✅ Approval Criteria
- [分析一致性] (Required)
  - 三个分析层输出无明显矛盾
- [置信度达标] (Required)
  - 综合置信度 ≥ 50
- [可验证性] (Required)
  - 核心假设可以通过后续验证

### 📊 Upstream Analysis Summary

**analyze_user_signals**:
根据您提供的搜索信号，我对关键词背后的用户意图进行了深度分析...

**analyze_industry_structure**:
```json
{
  "industry_structure_analysis": {
    "maturity_stage": {
      "stage": "Mature (Transitioning to Precision Health)",
      ...
    }
  }
}
```

**analyze_supply_competition**:
现有解决方案分类：综合性健康管理平台、专业性饮食记录工具...
```

#### 3. 审批 gate

```
/gate-review --approve freeze_market_signals
```

或者使用更完整的形式：

```
/gate-review decide freeze_market_signals --approve --comment "通过"
```

#### 4. 拒绝 gate

```
/gate-review --reject freeze_market_signals --comment "置信度不足"
```

#### 5. 要求修订

```
/gate-review --revise freeze_market_signals --comment "需要更多用户研究数据"
```

#### 6. 生成完整报告

```
/gate-review report
```

## Python API 使用

### 基本用法

```python
from flowcore.api import gate_review_handler

# 列出待审批 gates
result = gate_review_handler(action='list', project_dir='.')
print(result['markdown'])

# 查看 gate 详情
result = gate_review_handler(
    action='show',
    gate_id='freeze_market_signals',
    project_dir='.'
)
print(result['markdown'])

# 审批 gate
result = gate_review_handler(
    action='decide',
    gate_id='freeze_market_signals',
    decision='approve',
    comment='通过',
    checklist=[
        {'item': '分析一致性', 'ok': True, 'note': '无矛盾'},
        {'item': '置信度达标', 'ok': True, 'note': '>70%'},
        {'item': '可验证性', 'ok': True, 'note': '可验证'}
    ],
    project_dir='.'
)
print(result['markdown'])

# 生成报告
result = gate_review_handler(action='report', project_dir='.')
print(result['markdown'])
```

### 在新的 Claude Code CLI 中使用

在新的 Claude Code CLI 会话中执行：

```python
# 1. 查看待审批 gates
from flowcore.api import gate_review_handler
result = gate_review_handler(action='list', project_dir='E:\\ai\\LEE')
print(result['markdown'])

# 2. 查看特定 gate
result = gate_review_handler(action='show', gate_id='freeze_market_signals', project_dir='E:\\ai\\LEE')
print(result['markdown'])

# 3. 提交审批
result = gate_review_handler(
    action='decide',
    gate_id='freeze_market_signals',
    decision='approve',
    comment='三个分析层输出一致，置信度>70%，假设可验证。',
    project_dir='E:\\ai\\LEE'
)
```

## 决策类型

| 决策 | 说明 | 用途 |
|------|------|------|
| `approve` | 通过 | Gate 满足所有审批标准 |
| `reject` | 拒绝 | Gate 不满足审批标准 |
| `revise` | 修订 | 需要更多信息或修改 |

## 检查清单格式

```python
checklist = [
    {
        'item': '检查项名称',
        'ok': True,  # True=通过, False=不通过, None=未检查
        'note': '备注说明（可选）'
    },
    {
        'item': '置信度达标',
        'ok': True,
        'note': '综合置信度 > 70%'
    }
]
```

## 文件结构

```
LEE/
├── spec-global/
│   └── cross/
│       └── skills/
│           └── gate-review/
│               └── v1/
│                   └── skill.yaml    # Skill 规范
├── .claude/
│   └── tools/
│       └── gate_review.json          # Slash Command 配置
├── flowcore/
│   └── api.py                        # Handler 实现
└── .workflow/
    ├── state.yaml                    # Workflow 状态
    └── gates/
        └── freeze_market_signals.yaml # Gate 文件
```

## Gate 文件格式

```yaml
gate_id: freeze_market_signals
status: pending  # pending | approved | rejected | revised
decided_by: null
decided_at: null
option: null
comment: ''
step_name: 市场信号冻结
description: |
  Gate 的完整描述...

depends_on:
  - analyze_user_signals
  - analyze_industry_structure
  - analyze_supply_competition

approval_criteria:
  - label: 分析一致性
    criteria: 三个分析层输出无明显矛盾
    required: true
  - label: 置信度达标
    criteria: 综合置信度 ≥ 50
    required: true
  - label: 可验证性
    criteria: 核心假设可以通过后续验证
    required: true

rejection_criteria:
  - 分析层输出存在重大矛盾
  - 置信度过低（<30）
  - 假设过于宽泛，无法验证

checklist:
  - item: 分析一致性
    ok: null
    note: ''
  - item: 置信度达标
    ok: null
    note: ''
  - item: 可验证性
    ok: null
    note: ''

history: []
```

## 常见问题

### Q: 没有待审批 gates 怎么办？

A: 检查 workflow 状态：
```python
from flowcore.api import api_get_state
state = api_get_state('.')
print(f'已完成: {state["completed_steps"]}')
print(f'当前步骤: {state["current_step"]}')
```

### Q: 上游分析摘要为空？

A: 检查分析层是否完成：
```python
from pathlib import Path
workspace = Path('.workflow/workspace')

for dep in ['analyze_user_signals', 'analyze_industry_structure', 'analyze_supply_competition']:
    file = workspace / dep / 'response.txt'
    print(f'{dep}: {file.stat().st_size} bytes')
```

### Q: 如何批量审批多个 gates？

A: 使用 Python 脚本：
```python
from flowcore.api import gate_review_handler

gates = ['gate1', 'gate2', 'gate3']
for gate_id in gates:
    result = gate_review_handler(
        action='decide',
        gate_id=gate_id,
        decision='approve',
        comment='批量审批',
        project_dir='.'
    )
    print(f'{gate_id}: {result["result"]["status"]}')
```

## 更新日志

### v1.0 (2026-01-24)
- ✅ 实现 list/show/decide/report 四个 action
- ✅ 支持上游分析摘要显示
- ✅ 支持 Markdown 格式输出
- ✅ 支持检查清单管理
- ✅ 注册全局 slash command `/gate-review`
