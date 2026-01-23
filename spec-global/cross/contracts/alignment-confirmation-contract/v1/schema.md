# 需求对齐确认 Contract

> 📜 本文档是需求对齐确认的交付契约，用于确认需求理解的准确性。

---

## 📋 Contract 基本信息

| 项目 | 内容 |
|------|------|
| **Contract ID** | {{contract_id}} |
| **需求ID** | {{requirement_id}} |
| **需求标题** | {{requirement_title}} |
| **Contract 版本** | v{{version}} |
| **创建时间** | {{created_at}} |
| **Contract 状态** | {{status}} |

### Contract 状态说明

| 状态 | 含义 |
|------|------|
| 📝 DRAFT | 草稿 - Agent 生成，待人类 review |
| 🔍 PENDING_CONFIRMATION | 待确认 - 等待人类确认 |
| ✅ CONFIRMED | 已确认 - 确认完成，可进入下一环节 |
| 🔄 REVISION_REQUIRED | 需修订 - 根据反馈修改 |
| ❌ REJECTED | 已拒绝 - 终止流程 |

---

## 📝 原始需求

### 需求来源

| 项目 | 内容 |
|------|------|
| **来源** | {{source}} |
| **提交人** | {{submitter}} |
| **提交日期** | {{submitted_at}} |

### 原始需求描述

{{original_requirement}}

---

## 🎯 对齐后的需求理解

### 需求概述

{{clarified_description}}

### 背景信息

{{background}}

---

## 👥 目标用户

{{#each target_users}}
### {{priority_icon}} {{name}}

| 属性 | 内容 |
|------|------|
| **描述** | {{description}} |
| **预估规模** | {{estimated_size}} |
| **核心诉求** | {{core_needs}} |
| **使用场景** | {{usage_scenarios}} |

{{/each}}

---

## 🎯 业务目标

{{#each business_goals}}
### {{index}}. {{description}}

| 属性 | 内容 |
|------|------|
| **类型** | {{type_display}} |
| **重要性** | {{importance_display}} |
| **成功标准** | {{success_criteria}} |

{{/each}}

---

## 📊 成功指标

| 指标名称 | 当前值 | 目标值 | 衡量方式 |
|----------|--------|--------|----------|
{{#each success_metrics}}
| {{name}} | {{current_value}} | {{target_value}} | {{measurement_method}} |
{{/each}}

---

## 📋 范围定义

### 本次实现（In Scope）

{{#each scope_includes}}
- ✅ {{this}}
{{/each}}

### 明确排除（Out of Scope）

{{#each scope_excludes}}
- ❌ {{this}}
{{/each}}

### 未来考虑（Future Scope）

{{#each scope_future}}
- 🔮 {{this}}
{{/each}}

---

## ⚠️ 约束条件

{{#each constraints}}
- **{{type_display}}** [{{severity_display}}]: {{description}}
{{/each}}

---

## ❓ 待确认问题

> ⚠️ 以下问题需要您的确认或补充

{{#each pending_questions}}
### 问题 {{index}}: {{question}}

**上下文**: {{context}}

**建议选项**:
{{#each options}}
- {{option_letter}}. {{description}}
{{/each}}

**您的回答**: _________________

**回答状态**: {{answer_status}}

{{/each}}

---

## ✅ 确认区域

> 请仔细核对以上内容，确认无误后签字确认。

### 确认检查项

- [ ] 需求概述准确反映了原始意图
- [ ] 目标用户定义清晰完整
- [ ] 业务目标明确且可衡量
- [ ] 成功指标可量化
- [ ] 范围边界清晰无歧义
- [ ] 约束条件已充分识别
- [ ] 待确认问题已回答

### 确认签字

**确认人**: _______________

**确认日期**: _______________

**确认意见**:

```
请在此填写确认意见或补充说明...
```

---

## 📋 下一步

确认后，需求拆解 Agent 将：
1. 开始功能模块识别
2. 细化功能点定义
3. 进行歧义检测
4. 生成最终 PRD

---

## 变更记录

| 版本 | 日期 | 变更内容 | 变更人 |
|------|------|----------|--------|
| 1.0 | {{created_at}} | 初始版本创建 | requirement-analyzer |
{{#each change_log}}
| {{version}} | {{date}} | {{changes}} | {{author}} |
{{/each}}

---

*本 Contract 由需求分析 Agent 自动生成*
*最后更新: {{updated_at}}*
