# LEE Workflow Instance 架构需求文档

> 本需求用于 LEE Framework 的 Workflow Instance 功能开发

## 项目概述

LEE Framework 当前 workflow 执行缺少统一的 Plan → Instance → Execute 流程，导致：
- 所有 workflow 直接执行静态模板
- 没有任务分析和拆分决策
- 缺乏人类审批机制
- 重试副作用不透明

本项目旨在实现标准化的 workflow 实例化机制，提升 workflow 执行的可控性和可追溯性。

## 需求背景

### 当前问题

1. **没有 Plan 阶段** - LLM 没有机会分析任务、决定是否拆分
2. **没有 Instance 文件** - workflow 直接执行静态模板
3. **执行路径不统一** - `lee run` 和 `lee qa test-set run` 走不同流程
4. **缺乏人类干预** - 所有任务强制执行，无法审批
5. **重试不透明** - 重试可能有副作用，不被记录

### 目标用户

- LEE Framework 开发者
- 使用 LEE 的项目团队
- 需要人工审批 workflow 的场景

## 功能需求

### F1: Plan Agent

LLM 分析输入的 workflow 模板和参数，生成执行计划。

#### F1.1 Plan 输入
- 渲染后的 workflow 模板（YAML）
- 用户输入参数
- 模板配置（planning.mode）

#### F1.2 Plan 输出
- **Instance YAML** - 机器执行用
- **Plan Summary (Markdown)** - 人类决策用

#### F1.3 Plan 内容
- 复杂度评估（步骤数、Agent数、Human Gates数）
- 拆分决策（是否需要 L3）
- Review Gate 建议（simple/suggest/force）
- 成功标准
- 失败标准
- 重试配置

#### F1.4 Plan 失败处理
- 换 LLM 重试
- 直到成功，不跳过

### F2: Instance Generator

根据 Plan 结果生成 Instance 文件。

#### F2.1 Instance 文件格式
```yaml
kind: workflow-instance
id: wf_xxx
template_ref: workflow.dev.xxx
template_version: "1.0"
phase_id: xxx

# Plan 信息
plan:
  mode: force  # simple/suggest/force
  complexity: high
  needs_l3_split: false
  needs_review: true
  success_criteria: [...]
  failure_criteria: [...]
  retry: {...}

# Instance 配置
instance_config:
  success_criteria:
    simple: [...]      # 简单条件（必须有）
    expressions: [...] # 表达式条件（可选）
  failure_criteria:
    simple: [...]
    expressions: [...]
  retry:
    enabled: true
    max_attempts: 3
    strategy: exponential
    base_delay: 10
    side_effects_analysis: true  # 触发重试时分析

# 步骤定义
steps:
  - id: step_1
    name: Step 1
    status: pending
    mandatory: true
    retry_count: 0

# 状态
status: pending/running/completed/failed
version: 1
created_at: timestamp
```

#### F2.2 文件命名
```
instances/
├── l2/{workflow_id}-v{version}.yaml
└── l3/{workflow_id}-v{version}.yaml
```

#### F2.3 版本管理
- 每次生成新 Instance，版本号 +1
- 执行时取最新版本

### F3: Plan Review Gate

人类审批 Plan 决策的机制。

#### F3.1 配置级别
| 级别 | 说明 | 触发条件 |
|------|------|----------|
| simple | 自动跳过 | 满足 skip_conditions |
| suggest | LLM 判断 | 满足 review_criteria |
| force | 强制审批 | 始终需要 |

#### F3.2 审批不通过
- 重新 Plan
- Instance 版本号 +1
- 重新提交审批

### F4: Orchestrator 改造

从 Instance 文件加载执行，而不是直接读模板。

#### F4.1 执行流程
1. 根据 workflow_id 找到最新版本的 Instance 文件
2. 解析 Instance YAML
3. 计算 ready steps
4. 执行每个 step
5. 更新 Instance 文件状态
6. 触发 Human Gate 时暂停

#### F4.2 状态持久化
- Instance 文件包含实时状态
- 执行完成后保留 1 个月
- 1 个月后归档到 evidence/

### F5: 重试副作用分析

当 workflow 执行触发重试时，分析可能的副作用。

#### F5.1 分析时机
- 触发重试时自动执行

#### F5.2 分析内容
- 数据重复风险
- 状态不一致风险
- 外部系统影响

#### F5.3 输出
- 记录到执行日志
- 作为最终部署决策的参考

## 非功能需求

### 性能
- Plan 生成时间 < 30 秒
- Instance 文件加载时间 < 1 秒

### 可用性
- Plan 失败时自动换 LLM 重试
- Instance 版本管理自动完成

### 可扩展性
- 支持自定义 Plan Agent
- 支持自定义成功/失败标准

## 验收标准

### AC1: Plan 生成
- [ ] 输入模板和参数，能生成 Plan 结果
- [ ] Plan 结果包含 Instance YAML 和 Plan Summary
- [ ] Plan 失败时自动换 LLM 重试

### AC2: Instance 文件
- [ ] Instance 文件格式符合规范
- [ ] 版本号正确递增
- [ ] 执行时能正确加载最新版本

### AC3: Review Gate
- [ ] simple 模式自动跳过
- [ ] suggest 模式 LLM 判断
- [ ] force 模式强制审批
- [ ] 审批不通过时版本号 +1

### AC4: Orchestrator 执行
- [ ] 能从 Instance 加载执行
- [ ] 步骤状态正确更新
- [ ] Human Gate 正确触发

### AC5: 重试副作用
- [ ] 触发重试时自动分析
- [ ] 分析结果记录到日志

## 待确定项

1. Plan Agent 的具体实现方式（独立 Agent 还是复用现有能力）
2. Instance 文件的存储路径配置
3. Plan Summary 的详细格式
4. 表达式条件的评估引擎选择

## 依赖项

- LEE Framework 现有代码库
- Jinja2 模板引擎
- SQLite 状态存储
- LLM Provider（DeepSeek/Zhipu/etc.）
