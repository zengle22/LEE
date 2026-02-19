---
title: STG Opportunity Discovery Demo
author: LEE Team
date: 2026-01-29
version: 1.0
last_updated: 2026-02-19
---

# STG Opportunity Discovery Demo

商业机会发现工作流演示项目

## 项目简介

这是 STG（策略）部门的核心工作流：**商业机会发现流程**。

### 核心特点

- ✅ **5 层架构**：从搜索采集到产品交付
- ✅ **可冻结、可复盘、可移交**：每个环节都有明确输入输出
- ✅ **对产品部门负责**：给出清晰的验证建议

---

## 快速开始

### 1. 运行测试

```bash
# 运行完整工作流测试
python test_workflow.py

# 或使用 shell 脚本
bash run.sh
```

### 2. 查看示例数据

```bash
# Layer 1: 搜索采集
cat spec-global/departments/stg/examples/layer1_search/output.json

# Layer 2: 分析层
cat spec-global/departments/stg/examples/layer2_analysis/*.json

# Layer 3: 冻结层
cat spec-global/departments/stg/examples/layer3_freeze/freeze.yaml

# Layer 4: 机会层
cat spec-global/departments/stg/examples/layer4_opportunity/opportunity.json

# Layer 5: 交付层
cat spec-global/departments/stg/examples/layer5_handoff/handoff.yaml
```

---

## 工作流架构

```
┌─────────────────────────────────────────────┐
│ Layer 1: Search Agent                      │
│ └─ 输出: 搜索信号数据                          │
├─────────────────────────────────────────────┤
│ Layer 2: Analysis Agents (并行)             │
│ ├─ User Signal Agent                        │
│ ├─ Industry Structure Agent                 │
│ └─ Supply/Competition Agent                 │
├─────────────────────────────────────────────┤
│ Layer 3: Market Freeze 🔒                   │
│ └─ 输出: 冻结的市场信号                        │
├─────────────────────────────────────────────┤
│ Layer 4: Business Opportunity Agent          │
│ └─ 输出: 可验证的商业机会假设                    │
├─────────────────────────────────────────────┤
│ Layer 5: Product Handoff                     │
│ └─ 输出: 标准产品交付文档                       │
└─────────────────────────────────────────────┘
```

---

## 目录结构

```
stg-opportunity-discovery-demo/
├── README.md                 # 本文档
├── workflow.yaml             # 工作流定义
├── test_workflow.py          # 测试脚本
└── run.sh                    # 运行脚本
```

相关的 Spec 文件在：
```
spec-global/departments/stg/
├── agents/                   # Agent specs
├── contracts/                # Contract schemas
├── gates/                    # Gate definitions
├── workflows/                # Workflow definitions
└── examples/                 # Example data
```

---

## 核心原则

### 1. 分析在 freeze 层收敛
- 三个分析层的结论在冻结层固化
- 后续层只能引用，不可推翻

### 2. 机会在 handoff 层对产品负责
- 明确区分"相信的"和"不知道的"
- 给出可执行的验证建议

### 3. 硬规则
任何 agent 同时产出"事实判断"+"价值判断" = 任务拆错了

### 4. 冻结规则
- ❌ 后续 agent 不允许推翻已接受的假设
- ✅ 只能引用，不可重解释
- ✅ 可以补充，但不能否定

---

## 输出产物

| 层级 | 产物 | 文件 |
|------|------|------|
| Layer 1 | 搜索信号数据 | `search_signals/v1/signals.yaml` |
| Layer 2 | 用户假设 | `user_hypothesis/v1/hypothesis.yaml` |
| Layer 2 | 行业结构 | `industry_structure/v1/structure.yaml` |
| Layer 2 | 供给空缺 | `supply_gap/v1/gap.yaml` |
| Layer 3 | 市场信号冻结 | `market_signal_freeze/v1/freeze.yaml` |
| Layer 4 | 商业机会假设 | `business_opportunity/v1/opportunity.yaml` |
| Layer 5 | 产品交付文档 | `product_handoff/v1/handoff.yaml` |

---

## 下一步

### 1. 真实数据运行
配置真实的 API keys：
- Google Trends API
- Keyword Tool API
- Ahrefs API

### 2. 执行验证实验
按照产品交付文档的建议：
- Landing page 测试
- 用户访谈
- Fake door test

### 3. 迭代优化
根据验证结果：
- 更新市场信号冻结
- 调整机会假设
- 重新设计实验

---

## 技术支持

- 架构文档: `docs/architecture.md`
- PM Agent 协议: `docs/PM_AGENT_PROTOCOL.md`
- STG 部门 README: `spec-global/departments/stg/README.md`

---

## 版本信息

- **创建日期**: 2025-01-23
- **当前版本**: v1.0
- **维护者**: Strategy Team
