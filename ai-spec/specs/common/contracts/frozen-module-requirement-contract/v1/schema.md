# {{product_name}} - 产品需求文档（PRD）Contract

> 📜 本文档是产品需求的交付契约，定义产品的功能需求和非功能需求。

---

## 📋 Contract 基本信息

| 项目 | 内容 |
|------|------|
| **Contract ID** | {{contract_id}} |
| **文档ID** | {{document_id}} |
| **产品名称** | {{product_name}} |
| **Contract 版本** | v{{version}} |
| **创建日期** | {{created_date}} |
| **最后更新** | {{last_modified_date}} |
| **Contract 状态** | {{status}} |

### Contract 状态说明

| 状态 | 含义 |
|------|------|
| 📝 DRAFT | 草稿 - Agent 生成，待人类 review |
| 🔍 PENDING_REVIEW | 待审阅 - 等待相关方审阅 |
| ✅ APPROVED | 已审批 - 可进入开发阶段 |
| 🔄 REVISION_REQUIRED | 需修订 - 根据反馈修改 |
| ❌ REJECTED | 已拒绝 - 终止流程 |
| 🔒 LOCKED | 已锁定 - 不可修改 |

---

### 变更历史

| 版本 | 日期 | 修改人 | 变更说明 |
|------|------|--------|----------|
{{#each change_history}}
| {{version}} | {{date}} | {{modified_by}} | {{changes}} |
{{/each}}

---

## 1. 产品概述

### 1.1 背景

{{background}}

### 1.2 目标

{{#each objectives}}
{{index}}. {{description}}
{{/each}}

### 1.3 目标用户

{{target_users_description}}

#### 用户画像

{{#each user_personas}}
**{{name}}**
- 角色: {{role}}
- 特征: {{characteristics}}
- 核心需求: {{core_needs}}
- 使用场景: {{usage_scenarios}}

{{/each}}

### 1.4 核心价值

{{core_value}}

### 1.5 成功指标

| 指标名称 | 当前基线 | 目标值 | 衡量方式 | 负责人 |
|----------|----------|--------|----------|--------|
{{#each success_metrics}}
| {{name}} | {{baseline}} | {{target}} | {{method}} | {{owner}} |
{{/each}}

---

## 2. 功能需求

### 2.1 功能架构图

```
{{architecture_diagram}}
```

### 2.2 功能模块总览

| 模块ID | 模块名称 | 优先级 | 功能数 | 描述 |
|--------|----------|--------|--------|------|
{{#each modules}}
| {{id}} | {{name}} | {{priority}} | {{feature_count}} | {{description}} |
{{/each}}

### 2.3 模块详情

{{#each modules}}

---

#### 2.3.{{index}} {{name}}

**模块ID**: `{{id}}`

**优先级**: {{priority}}

**描述**: {{description}}

{{#if dependencies}}
**依赖模块**: {{dependencies}}
{{/if}}

##### 功能列表

{{#each features}}

###### {{feature_id}}: {{name}}

**优先级**: {{priority}} | **复杂度**: {{complexity}}

**描述**: {{description}}

**用户故事**:
> {{user_story}}

**验收标准**:
{{#each acceptance_criteria}}
- [ ] {{this}}
{{/each}}

**业务规则**:
{{#each business_rules}}
- {{this}}
{{/each}}

**异常处理**:
{{#each exception_handling}}
- {{this}}
{{/each}}

{{#if ui_description}}
**界面说明**: {{ui_description}}
{{/if}}

{{#if technical_notes}}
**技术说明**: {{technical_notes}}
{{/if}}

---

{{/each}}

{{/each}}

### 2.4 用户流程

{{#each user_flows}}

#### {{name}}

**描述**: {{description}}

```mermaid
{{mermaid_code}}
```

{{/each}}

---

## 3. 非功能需求

### 3.1 性能要求

| 指标 | 要求 | 测量方式 |
|------|------|----------|
{{#each performance_requirements}}
| {{metric}} | {{requirement}} | {{measurement}} |
{{/each}}

### 3.2 安全要求

{{#each security_requirements}}
- {{this}}
{{/each}}

### 3.3 可用性要求

{{#each availability_requirements}}
- {{this}}
{{/each}}

### 3.4 兼容性要求

{{#each compatibility_requirements}}
- {{this}}
{{/each}}

### 3.5 其他要求

{{#each other_requirements}}
- {{this}}
{{/each}}

---

## 4. 实施计划

### 4.1 阶段划分

{{#each implementation_phases}}

#### Phase {{order}}: {{name}}

**描述**: {{description}}

**包含模块**:
{{#each modules}}
- {{this}}
{{/each}}

**交付物**:
{{#each deliverables}}
- {{this}}
{{/each}}

{{/each}}

### 4.2 里程碑

| 里程碑 | 描述 | 交付物 | 验收标准 |
|--------|------|--------|----------|
{{#each milestones}}
| {{name}} | {{description}} | {{deliverables}} | {{acceptance}} |
{{/each}}

### 4.3 依赖关系

{{#each dependencies}}
- {{this}}
{{/each}}

### 4.4 风险与应对

| 风险ID | 类型 | 描述 | 概率 | 影响 | 缓解措施 | 负责人 |
|--------|------|------|------|------|----------|--------|
{{#each risks}}
| {{id}} | {{type}} | {{description}} | {{probability}} | {{impact}} | {{mitigation}} | {{owner}} |
{{/each}}

---

## 5. 附录

### 5.1 术语表

| 术语 | 定义 |
|------|------|
{{#each glossary}}
| {{term}} | {{definition}} |
{{/each}}

### 5.2 参考资料

{{#each references}}
{{index}}. {{this}}
{{/each}}

### 5.3 决策记录

> 以下是需求分析过程中做出的关键决策

{{#each decision_records}}

#### 决策 {{index}}: {{title}}

- **决策ID**: `{{id}}`
- **类型**: {{type}}
- **日期**: {{date}}
- **决策人**: {{decider}}

**问题描述**: {{problem}}

**选择的方案**: {{chosen_option}}

**决策理由**: {{rationale}}

**影响**: {{impact}}

---

{{/each}}

---

## ✅ 审批区域

### 审批检查项

- [ ] 产品目标清晰可衡量
- [ ] 功能需求完整无遗漏
- [ ] 验收标准明确可测试
- [ ] 非功能需求合理可达成
- [ ] 实施计划可行
- [ ] 风险识别充分

### 审批记录

| 角色 | 姓名 | 日期 | 状态 | 意见 |
|------|------|------|------|------|
{{#each approvers}}
| {{role}} | {{name}} | {{date}} | {{status}} | {{comments}} |
{{/each}}

### 审批签字

| 角色 | 姓名 | 日期 | 签字 | 意见 |
|------|------|------|------|------|
| 产品负责人 | _______ | _______ | _______ | _______ |
| 技术负责人 | _______ | _______ | _______ | _______ |
| 项目经理 | _______ | _______ | _______ | _______ |
| 测试负责人 | _______ | _______ | _______ | _______ |

### 审批意见

```
请在此填写审批意见...
```

---

## Contract 生效信息

| 项目 | 内容 |
|------|------|
| **生效状态** | {{effective_status}} |
| **生效时间** | {{effective_at}} |
| **有效期至** | {{valid_until}} |
| **下一环节** | {{next_stage}} |
| **交付责任人** | {{owner}} |

---

*本 Contract 由需求拆解 Agent 生成*

*生成时间: {{generated_at}}*

*基于需求对齐确认文档和 {{decision_count}} 项决策记录生成*
