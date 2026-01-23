# CLAUDE.md - AI Agent 行为规范

## 最高规则：AI 宪法

> **所有 Agent 必须遵守 [AI-CONSTITUTION.md](./AI-CONSTITUTION.md) 中定义的规则。**
>
> AI 宪法具有最高优先级，任何其他指令均不得与宪法冲突。

### 宪法核心要点

1. **三阶段工作流**: 商业发现 → 产品设计 → 研发实现
2. **阶段门禁**: 没有前置冻结文件，禁止进入下一阶段
3. **冻结保护**: 任何修改冻结文件的尝试必须 Fail Fast
4. **人类在环**: 所有冻结/解冻操作必须人类确认

### 产品流水线 (Stage 2 子阶段)

> 详见 [pipelines/product-pipeline.yaml](./pipelines/product-pipeline.yaml)

```
2.1 价值定义 → 2.2 问题定义 → 2.3 方案设计 → 2.4 交付规划
     ↓              ↓              ↓
  value-freeze  requirement-freeze  solution-freeze
```

**核心原则**:
- 人类仅在冻结点参与审批
- 每个 Agent 有明确的 non_goals（禁止做什么）
- 下游必须基于上游冻结产物工作

### 违规即终止

```
if (尝试修改冻结文件) → FAIL FAST + 请求解冻审批
if (尝试跳过阶段门禁) → FAIL FAST + 拒绝执行
if (尝试绕过人类审批) → FAIL FAST + 终止操作
```

---

## 项目概述

本项目是一个 Claude Code Plugin，用于产品全生命周期管理，包括：

- 市场调研与商业机会发现
- 产品目标分析与需求对齐
- PRD 生成与原型设计

## 目录结构

```
.
├── AI-CONSTITUTION.md    # AI 宪法（最高规则）
├── CLAUDE.md             # 本文件
├── plugin.json           # 插件配置
├── pipelines/            # 流水线定义
│   └── product-pipeline.yaml  # 产品阶段流水线
├── agents/               # Agent 定义
├── commands/             # 命令定义
├── contracts/            # 数据契约
├── skills/               # 技能知识库
├── templates/            # 模板文件
└── output/               # 输出目录
    ├── discovery-frozen/ # Stage 1 冻结文件
    ├── design-frozen/    # Stage 2 冻结文件
    └── release-frozen/   # Stage 3 冻结文件
```

## 开发规范

### Agent 开发

- 所有 Agent 必须在执行前检查宪法约束
- 涉及写操作时必须检查目标文件是否已冻结
- 进入新阶段时必须检查门禁条件

### 冻结文件

- 使用 `templates/freeze-template.md` 作为模板
- 冻结文件必须包含完整的元数据头
- 冻结后提交到 Git 进行版本控制

### 人类审批

- 冻结前显示审批请求
- 等待用户输入 `确认冻结` 或 `approve freeze`
- 记录审批信息到文件中
