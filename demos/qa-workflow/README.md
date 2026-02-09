# QA Workflow Demo

演示 QA 部门两个核心工作流的使用。

## 工作流概述

### 1. Test Set Production (生产 Test Set)

将需求文档转化为 Test Set 设计资产。

**流程：** 需求分析 → 策略设计 → Test Set 生成 → 审评

### 2. Test Plan Execution (执行 Test Plan)

执行完整的测试批次。

**流程：** Test Run 初始化 → 环境准备 → 用例生成 → 脚本翻译 → 脚本执行 → TSE 组装 → Bug 起草 → 出测评估

---

## Demo 1: 生产 Test Set

### 准备

示例需求文档已准备好：`requirements/daily-plan-prd.md`

### 执行

```bash
# 方式一：使用 lee run 命令
lee run qa.test-set-production \
  --module daily-plan \
  --requirement demos/qa-workflow/requirements/daily-plan-prd.md

# 方式二：使用 lee qa 子命令
lee qa test-set create daily-plan \
  --requirement demos/qa-workflow/requirements/daily-plan-prd.md
```

### 预期产出

```
qa/
└── test-sets/
    ├── ts-daily-plan.yaml              # Test Set 设计资产
    └── ts-daily-plan/
        ├── analysis.md                 # 需求分析报告
        └── strategy-draft.yaml         # 测试策略草稿
```

### 人工门禁点

1. **需求分析审核** - 确认模块边界和可测试特性
2. **测试策略审核** - 确认测试重点和风险区域
3. **Test Set 最终批准** - 确认 Test Set 完整可用

---

## Demo 2: 执行 Test Plan

### 准备

1. 复制示例 Test Set 到 qa 目录：

```bash
mkdir -p qa/test-sets qa/test-plans
cp demos/qa-workflow/test-sets/*.yaml qa/test-sets/
cp demos/qa-workflow/test-plans/*.yaml qa/test-plans/
```

2. 确认 Test Plan 和 Test Set 已就绪：

```bash
lee qa test-plan list
lee qa test-set list
```

### 执行

```bash
# 启动 Test Run
lee qa test-run start TP-DEMO-PHASE0 \
  --build 1.0.0 \
  --commit abc1234

# 或使用快捷命令
lee qa run TP-DEMO-PHASE0 \
  --build 1.0.0 \
  --commit abc1234
```

### 预期产出

```
qa/
├── test-runs/
│   └── TR-2026-02-09-abc1234/
│       ├── test-run.yaml           # Test Run 记录
│       ├── env-health.yaml         # 环境健康检查
│       ├── exit-evaluation.yaml    # 出测评估
│       ├── tse-smoke/
│       │   ├── cases.yaml          # 生成的用例
│       │   ├── scripts/            # 翻译的脚本
│       │   ├── results.yaml        # 执行结果
│       │   └── tse.yaml            # TSE 汇总
│       └── tse-daily-plan/
│           └── ...
└── bugs/
    └── BUG-2026-0001.yaml          # 发现的 Bug（如有）
```

### 人工门禁点

1. **用例审核** - 确认生成的用例覆盖完整
2. **Bug 确认** - 确认 Bug 草稿
3. **出测决策** - 确认出测评估结果

---

## 命令参考

### Test Set 管理

```bash
# 创建 Test Set
lee qa test-set create <module> --requirement <doc> [--tech-design <doc>]

# 列出所有 Test Set
lee qa test-set list

# 查看 Test Set 详情
lee qa test-set show <test-set-id>
```

### Test Plan 管理

```bash
# 创建 Test Plan
lee qa test-plan create <plan-id> \
  --scope <module1> --scope <module2> \
  --test-set TS-SMOKE --test-set TS-DAILY-PLAN

# 列出所有 Test Plan
lee qa test-plan list

# 查看 Test Plan 详情
lee qa test-plan show <plan-id>
```

### Test Run 管理

```bash
# 启动 Test Run
lee qa test-run start <plan-id> --build <version> --commit <hash>

# 快捷命令
lee qa run <plan-id> --build <version> --commit <hash>

# 查看状态
lee qa test-run status [run-id]

# 批准门禁
lee qa test-run approve <gate-id>
```

---

## 目录结构

```
demos/qa-workflow/
├── README.md                       # 本文件
├── requirements/
│   └── daily-plan-prd.md          # 示例需求文档
├── test-sets/
│   ├── ts-daily-plan.yaml         # 示例 Test Set
│   └── ts-smoke.yaml              # 示例 Test Set
└── test-plans/
    └── tp-demo-phase0.yaml        # 示例 Test Plan
```
