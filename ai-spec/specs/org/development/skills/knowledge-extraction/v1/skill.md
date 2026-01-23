# Knowledge Extraction Skill v1.0

> **技能类型**: 确定性能力 (格式转换)
> **无决策**: 将复盘内容转换为结构化知识格式

## 概述

将 Phase 复盘产出转换为可复用的结构化知识条目。

## 知识类型

### 1. Pattern (最佳实践)

```yaml
---
id: pattern-{uuid}
type: pattern
category: {coding|testing|process|tooling}
tags: [{tags}]
source_phase: {phase_id}
created_at: {timestamp}
---

# {Pattern Name}

## When to Use
{描述适用场景}

## How to Apply
{具体步骤}
1. ...
2. ...
3. ...

## Expected Benefit
{预期收益}

## Example
{代码或流程示例}

## References
- {相关文档链接}
```

### 2. Anti-Pattern (反模式)

```yaml
---
id: antipattern-{uuid}
type: anti-pattern
category: {coding|testing|process|tooling}
severity: {high|medium|low}
tags: [{tags}]
source_phase: {phase_id}
created_at: {timestamp}
---

# {Anti-Pattern Name}

## Symptoms
{问题表现}
- ...
- ...

## Root Cause
{根本原因}

## Why It's Problematic
{为什么是问题}

## Better Approach
{正确做法}

## Prevention
{预防措施}

## Detection Checklist
- [ ] {检测项1}
- [ ] {检测项2}
```

### 3. Checklist (检查清单)

```yaml
---
id: checklist-{uuid}
type: checklist
category: {code-review|deployment|testing|design}
trigger: {何时使用}
tags: [{tags}]
source_phase: {phase_id}
created_at: {timestamp}
---

# {Checklist Name}

## Purpose
{目的说明}

## Checklist Items

### Category 1
- [ ] {检查项1}
- [ ] {检查项2}

### Category 2
- [ ] {检查项3}
- [ ] {检查项4}

## Failure Handling
{未通过时的处理}
```

### 4. Guideline (指南)

```yaml
---
id: guideline-{uuid}
type: guideline
scope: {project|team|org}
tags: [{tags}]
source_phase: {phase_id}
created_at: {timestamp}
---

# {Guideline Title}

## Scope
{适用范围}

## Principles
1. {原则1}
2. {原则2}

## Do's
- {推荐做法1}
- {推荐做法2}

## Don'ts
- {禁止做法1}
- {禁止做法2}

## Exceptions
{例外情况说明}
```

## 转换规则

### 从复盘 → Pattern

```
输入: "我们发现提前写测试契约大大减少了返工"
输出: Pattern "Test Contract First"
```

### 从复盘 → Anti-Pattern

```
输入: "直接开始编码导致后期大量重构"
输出: Anti-Pattern "Code Before Contract"
```

### 从复盘 → Checklist

```
输入: "每次 Review 都发现同样的安全问题"
输出: Checklist "Security Review Checklist"
```

## 目录结构

```
07-knowledge/
├── patterns/
│   ├── coding/
│   ├── testing/
│   └── process/
├── anti-patterns/
│   ├── coding/
│   ├── testing/
│   └── process/
├── checklists/
│   ├── code-review/
│   ├── deployment/
│   └── testing/
└── guidelines/
    └── ...
```

## 约束

- ❌ 不判断知识价值
- ❌ 不决定分类优先级
- ❌ 不筛选内容
- ✅ 只做格式转换
- ✅ 只生成结构化输出
