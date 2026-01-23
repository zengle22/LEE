---
name: create-plan
description: 根据PRD文档创建研发计划，拆解任务、分析依赖、智能排期
arguments:
  - name: prd_path
    description: PRD文档路径（可选，不填则进入交互模式让用户选择）
    required: false
  - name: start_date
    description: 计划开始日期，格式YYYY-MM-DD（可选，默认为明天）
    required: false
  - name: team_size
    description: 团队规模配置，格式如 "backend:2,frontend:2"（可选）
    required: false
---

# 创建研发计划

你正在执行研发计划创建任务。

## 输入参数

- PRD文档路径: $prd_path
- 计划开始日期: $start_date
- 团队规模: $team_size

## 执行步骤

### 步骤1: 确定PRD文档

{{#if prd_path}}
读取指定的PRD文档: `$prd_path`
{{else}}
使用Glob工具搜索当前目录下的PRD文档（*.md, *.txt），列出候选文件让用户选择。

搜索模式:
- `**/PRD*.md`
- `**/prd*.md`
- `**/*需求*.md`
- `**/*requirement*.md`
{{/if}}

### 步骤2: 确定排期参数

{{#if start_date}}
使用指定的开始日期: $start_date
{{else}}
默认从明天开始排期，询问用户是否需要调整。
{{/if}}

{{#if team_size}}
使用指定的团队配置: $team_size
{{else}}
询问用户团队规模配置，使用以下默认值作为参考：
- 后端开发: 2人
- 前端开发: 2人
- 测试: 1人
- 运维: 0.5人（兼职）
{{/if}}

### 步骤3: 执行计划制定流程

调用 `plan-architect` agent 的完整工作流：

1. **PRD解析**: 提取功能模块和功能点
2. **任务拆解**: 将功能点分解为开发任务
3. **依赖分析**: 识别任务间的依赖关系
4. **工时估算**: 评估每个任务的工作量
5. **智能排期**: 生成最优排期方案

### 步骤4: 生成输出文件

在 `output/` 目录下生成：

1. `plan-[需求ID].yaml` - 供AI/系统读取的结构化数据
2. `plan-[需求ID].md` - 供人类阅读的可视化计划

### 步骤5: 计划确认

展示生成的计划摘要，包括：
- 总任务数
- 总工时
- 预计工期
- 关键里程碑
- 风险提示

询问用户是否需要调整。

## 输出要求

1. 使用TodoWrite跟踪整个流程进度
2. 关键决策点使用AskUserQuestion获取用户输入
3. 最终输出两种格式的研发计划文件
4. 提供计划概览摘要

## 错误处理

- 如果PRD文档不存在，提示用户检查路径
- 如果PRD内容不完整，列出缺失的关键信息
- 如果检测到循环依赖，报告错误并建议修正
