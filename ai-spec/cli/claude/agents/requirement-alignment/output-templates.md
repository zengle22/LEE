# 输出模板 (Output Templates)

> 标准化的输出格式，确保需求对齐结果的一致性

## 模板 1: 需求分析报告

```markdown
# 🔍 需求分析报告

**分析时间**: {{timestamp}}
**需求来源**: {{source}}
**分析状态**: 进行中 | 待确认 | 已完成

---

## 原始需求

> {{original_requirement}}

---

## 需求理解

### 我的理解
{{ai_understanding}}

### 核心目标
- {{goal_1}}
- {{goal_2}}

### 涉及范围
- **包含**: {{in_scope}}
- **不包含**: {{out_of_scope}}

---

## 发现的问题 (共 {{count}} 个)

{{#each issues}}
### 问题 {{index}}: {{title}}

| 属性 | 值 |
|------|-----|
| **类型** | {{type}} |
| **严重度** | 🔴 高 / 🟡 中 / 🟢 低 |
| **影响** | {{impact}} |

**问题描述**:
{{description}}

**选项对比**:

| 选项 | 描述 | 优点 | 缺点 | 工作量 |
|------|------|------|------|--------|
{{#each options}}
| {{letter}}{{#if recommended}} ⭐{{/if}} | {{desc}} | {{pros}} | {{cons}} | {{effort}} |
{{/each}}

**推荐理由**: {{recommendation_reason}}

**你的选择**: ◻ A  ◻ B  ◻ C  ◻ 其他: ______

---
{{/each}}

## 下一步

完成以上选择后，我将：
1. 确认你的决策
2. 生成最终需求规格
3. 定义验收标准

请在每个问题后标注你的选择，或提出其他方案。
```

---

## 模板 2: 决策确认

```markdown
# ✅ 需求决策确认

**确认时间**: {{timestamp}}

---

## 决策汇总

| # | 问题 | 你的决策 | 备注 |
|---|------|----------|------|
{{#each decisions}}
| {{index}} | {{issue}} | {{choice}} | {{note}} |
{{/each}}

---

## 确认检查

请确认以下内容准确反映了你的意图：

{{#each decisions}}
### {{index}}. {{issue}}
- **决策**: {{choice}}
- **含义**: {{meaning}}

◻ 确认  ◻ 需要修改
{{/each}}

---

## 操作

- [ ] 全部确认，生成最终规格
- [ ] 部分需要修改 (请标注具体项)
- [ ] 需要补充讨论
```

---

## 模板 3: 最终需求规格

```markdown
# 📋 需求规格文档

**版本**: v1.0
**创建时间**: {{timestamp}}
**状态**: ✅ 已对齐

---

## 1. 概述

### 1.1 需求背景
{{background}}

### 1.2 目标
{{objective}}

### 1.3 范围
- **包含**: {{in_scope}}
- **不包含**: {{out_of_scope}}

---

## 2. 功能规格

### 2.1 功能描述
{{functional_description}}

### 2.2 用户角色
| 角色 | 描述 | 权限 |
|------|------|------|
{{#each roles}}
| {{name}} | {{desc}} | {{permissions}} |
{{/each}}

### 2.3 核心流程

```
{{flow_diagram}}
```

### 2.4 输入输出

**输入**:
{{#each inputs}}
- `{{name}}`: {{type}} - {{description}} {{#if required}}(必填){{/if}}
{{/each}}

**输出**:
{{#each outputs}}
- `{{name}}`: {{type}} - {{description}}
{{/each}}

---

## 3. 边界条件

| 条件 | 处理方式 |
|------|----------|
{{#each boundaries}}
| {{condition}} | {{handling}} |
{{/each}}

---

## 4. 异常处理

| 异常场景 | 错误码 | 用户提示 | 系统行为 |
|----------|--------|----------|----------|
{{#each exceptions}}
| {{scenario}} | {{code}} | {{message}} | {{behavior}} |
{{/each}}

---

## 5. 非功能需求

### 5.1 性能
- 响应时间: {{response_time}}
- 吞吐量: {{throughput}}
- 并发数: {{concurrency}}

### 5.2 安全
{{security_requirements}}

### 5.3 可用性
{{availability_requirements}}

---

## 6. 验收标准

{{#each acceptance_criteria}}
- [ ] {{criterion}}
{{/each}}

---

## 7. 关键决策记录

| 决策点 | 决策内容 | 决策理由 |
|--------|----------|----------|
{{#each decisions}}
| {{point}} | {{decision}} | {{reason}} |
{{/each}}

---

## 8. 附录

### 8.1 术语表
{{glossary}}

### 8.2 参考资料
{{references}}

---

> ✅ **需求对齐完成**
>
> 本文档已经过需求方确认，可以进入下一个环节。
> 如有变更，请重新发起需求对齐流程。
```

---

## 模板 4: 快速对齐 (简单需求)

```markdown
# ⚡ 快速需求对齐

**需求**: {{requirement}}

## 理解确认

我理解你需要: {{understanding}}

## 快速问答

{{#each questions}}
**Q{{index}}**: {{question}}
- A) {{option_a}}
- B) {{option_b}} ⭐推荐
- C) {{option_c}}

你的选择: ______
{{/each}}

---

全部回答后，我将直接开始实现。
```

---

## 使用指南

### 选择合适的模板

| 需求复杂度 | 推荐模板 |
|------------|----------|
| 简单 (1-2 个决策点) | 模板 4: 快速对齐 |
| 中等 (3-5 个决策点) | 模板 1 + 模板 3 |
| 复杂 (5+ 个决策点) | 完整流程: 模板 1 → 2 → 3 |

### 输出原则

1. **渐进式披露**: 先概述，后细节
2. **视觉层次**: 使用标题、表格、列表区分内容
3. **可操作性**: 每个输出都应该引导用户下一步行动
4. **可追溯**: 记录决策过程，便于后续回顾
