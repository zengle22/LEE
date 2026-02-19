---
title: STG Workflow 审核指南
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# STG Workflow 审核指南

## 📁 输出文档位置

### 实际输出文件（当前格式）
```
.workflow/workspace/
├── search_signals/response.txt           # 搜索信号数据
├── analyze_user_signals/response.txt     # 用户信号分析
├── analyze_industry_structure/response.txt # 行业结构分析
└── analyze_supply_competition/response.txt # 供给竞争分析
```

### 标准输出路径（workflow 定义）
```
contracts/
├── search_signals/v1/signals.yaml
├── user_hypothesis/v1/hypothesis.yaml
├── industry_structure/v1/structure.yaml
├── supply_gap/v1/gap.yaml
├── market_signal_freeze/v1/freeze.yaml
├── business_opportunity/v1/opportunity.yaml
└── product_handoff/v1/handoff.yaml
```

---

## 📋 后续步骤

### 当前状态
- ✅ Step 1-4: 分析层已完成
- ⏸️ Step 5: freeze_market_signals (HUMAN GATE) - **当前步骤**
- ⏳ Step 6: build_business_opportunity
- ⏳ Step 7: product_handoff

### Step 5 详细说明：市场信号冻结 (HUMAN GATE)

**目的**: 这是系统稳定性的根！冻结分析层的所有结论。

**需要审核**:
1. 分析一致性 - 三个分析层输出是否一致？
2. 置信度达标 - 综合置信度是否 ≥ 50？
3. 可验证性 - 核心假设是否可验证？

**审核标准**:
```yaml
gate_rules:
  reviewers:
    - role: stg_lead
      description: "策略部门负责人"

  approval_criteria:
    - label: "分析一致性"
      criteria: "三个分析层输出无明显矛盾"
      required: true

    - label: "置信度达标"
      criteria: "综合置信度 ≥ 50"
      required: true

    - label: "可验证性"
      criteria: "核心假设可以通过后续验证"
      required: true

  rejection_criteria:
    - "分析层输出存在重大矛盾"
    - "置信度过低（<30）"
    - "假设过于宽泛，无法验证"
```

---

## 🔍 在另一个 Claude Code CLI 上审核

### 方式 1：使用 PM Agent API（推荐）

在新的 Claude Code CLI 会话中：

```python
# 1. 查看当前状态
from flowcore.api import api_get_state

state = api_get_state('.')
print(state['workflow_name'])
print(f"已完成: {state['completed_steps']}")
print(f"待审批: {state['human_gates']}")

# 2. 查看 gate 详情
from flowcore.api import api_gate_show

gate = api_gate_show('.', 'freeze_market_signals')
print(f"Gate ID: {gate['gate_id']}")
print(f"状态: {gate['status']}")
print(f"检查清单: {gate['checklist']}")

# 3. 读取上游分析结果
import yaml
from pathlib import Path

# 读取用户信号分析
user_signals = Path('.workflow/workspace/analyze_user_signals/response.txt').read_text()
print("用户信号分析:", user_signals[:500])

# 读取行业结构分析
industry = Path('.workflow/workspace/analyze_industry_structure/response.txt').read_text()
print("行业结构分析:", industry[:500])

# 读取供给竞争分析
supply = Path('.workflow/workspace/analyze_supply_competition/response.txt').read_text()
print("供给竞争分析:", supply[:500])

# 4. 提交审批决策
from flowcore.api import api_gate_decide

result = api_gate_decide(
    project_dir='.',
    gate_id='freeze_market_signals',
    option='approve',  # 'approve' | 'reject' | 'revise'
    comment='三个分析层输出一致，置信度达标（>70），假设可验证。',
    checklist=[
        {'item': '分析一致性', 'ok': True, 'note': '无矛盾'},
        {'item': '置信度达标', 'ok': True, 'note': '综合 > 70'},
        {'item': '可验证性', 'ok': True, 'note': '可通过市场数据验证'}
    ],
    decided_by='user'
)

print(f"审批结果: {result}")
```

### 方式 2：直接查看文件并手动审批

```bash
# 查看分析层输出
cat .workflow/workspace/search_signals/response.txt
cat .workflow/workspace/analyze_user_signals/response.txt
cat .workflow/workspace/analyze_industry_structure/response.txt
cat .workflow/workspace/analyze_supply_competition/response.txt

# 手动创建 gate 决策文件
mkdir -p .workflow/gates
cat > .workflow/gates/freeze_market_signals.yaml << 'EOF'
gate_id: freeze_market_signals
status: approved
decided_by: user
decided_at: 2026-01-24T00:30:00.000000
option: approve
comment: |
  三个分析层输出一致，置信度达标，假设可验证。

  分析发现：
  - 市场信号：9+ 关键词，热度分层明显
  - 用户分层：从入门到专业，有清晰转化路径
  - 竞品分析：4 类竞品，3 个市场空缺
  - 置信度：综合 > 70%
checklist:
  - item: "分析一致性"
    ok: true
    note: "三个分析层无明显矛盾"
  - item: "置信度达标"
    ok: true
    note: "综合置信度 > 70"
  - item: "可验证性"
    ok: true
    note: "假设可通过市场数据验证"
history:
  - date: "2026-01-24T00:30:00.000000"
    action: "approved"
    decided_by: "user"
    comment: "人工审批通过"
EOF
```

### 方式 3：使用 Gate Assistant 协议

按照 `docs/GATE_ASSISTANT_PROTOCOL.md` 中的 Two-Session 架构：

**PM Session** (当前会话):
- 只能查看状态
- 不能修改 gate
- 使用 `api_gate_list_pending()` 和 `api_gate_show()`

**Gate Session** (新会话):
- 只能调用 gate 工具
- 必须等待用户确认后才能审批
- 使用 `api_gate_decide()`

---

## 📊 当前分析结果摘要

### 搜索信号（search_signals）
- 9+ 个关键词
- 热度范围：5K-500万/日
- 主要地区：广东、北京、上海、江苏、浙江

### 用户信号（analyze_user_signals）
- 6 类用户画像
- 从入门（减脂起步者）到专业（营养师）
- 高价值转化：营养计划 app 用户

### 行业结构（analyze_industry_structure）
- 成熟阶段：成熟期向精准健康转型
- 技术依赖：中餐标准化、AI 识餐
- 进入壁垒：数据积累、用户习惯

### 供给竞争（analyze_supply_competition）
- 4 类竞品：综合平台、专业工具、B端工具、轻量工具
- 3 个局限：输入成本高、准确性差、商业化干扰
- 3 个空缺：疾病人群、外卖集成、AI 识餐

### 综合评估
- ✅ 分析一致性：三个分析层无明显矛盾
- ✅ 置信度：综合 > 70%（符合 ≥ 50 标准）
- ✅ 可验证性：所有假设可通过市场数据/用户调研验证

---

## 🚀 审批通过后

执行 Step 6: build_business_opportunity

```python
from flowcore.api import api_run_step_async
import asyncio

result = asyncio.run(api_run_step_async('.', 'build_business_opportunity'))
print(result)
```

这将生成商业机会假设，包含：
- 一句话机会定义
- 目标用户和场景
- Why Now 理由
- 差异化假设
- Reasons NOT to Do
- 产品验证建议
