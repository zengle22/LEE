# 决策文档

---

## 文档信息

| 项目 | 内容 |
|------|------|
| **决策文档ID** | {{document_id}} |
| **关联需求** | {{requirement_title}} |
| **生成时间** | {{generated_at}} |
| **状态** | {{status}} |

---

## ⚠️ 重要提示

本文档包含 **{{ambiguity_count}}** 个需要人工决策的歧义点。

**工作流已暂停，等待您完成决策后继续。**

---

## 决策项总览

| 序号 | 类型 | 描述 | 状态 | 建议方案 |
|------|------|------|------|----------|
{{#each ambiguities}}
| {{index}} | {{type_display}} | {{description_short}} | {{status_display}} | {{suggested_option}} |
{{/each}}

---

## 决策详情

{{#each ambiguities}}

### 决策项 {{index}}: {{description}}

**ID**: `{{id}}`

**类型**: {{type_display}}

**发现位置**: {{discovery_context}}

#### 问题描述

{{detailed_description}}

#### 上下文信息

```
{{context}}
```

#### 影响范围

{{#each impact_scope}}
- {{this}}
{{/each}}

#### 可选方案

{{#each interpretations}}

##### 方案 {{option_letter}}: {{description}}

| 维度 | 评估 |
|------|------|
| **实施成本** | {{cost_display}} |
| **风险等级** | {{risk_display}} |
| **推荐度** | {{recommendation_stars}} |

**优点**:
{{#each pros}}
- ✅ {{this}}
{{/each}}

**缺点**:
{{#each cons}}
- ⚠️ {{this}}
{{/each}}

{{#if implementation_notes}}
**实施说明**: {{implementation_notes}}
{{/if}}

{{/each}}

{{#if suggested_decision}}
#### 💡 Agent 建议

{{suggested_decision}}
{{/if}}

---

#### 决策记录

> 请选择方案并填写决策理由

**选择的方案**:
- [ ] 方案 A
- [ ] 方案 B
{{#if has_option_c}}- [ ] 方案 C{{/if}}
{{#if has_option_d}}- [ ] 方案 D{{/if}}
- [ ] 其他方案（请说明）

**决策人**: _______________

**决策日期**: _______________

**决策理由**:

```
请在此填写选择该方案的理由...
```

**后续行动**:

```
如有需要跟进的事项，请在此说明...
```

---

{{/each}}

## 确认区域

### 决策完整性检查

- [ ] 所有决策项都已选择方案
- [ ] 每个决策都填写了理由
- [ ] 已考虑决策之间的相互影响
- [ ] 后续行动已明确

### 最终确认

**确认人**: _______________

**确认日期**: _______________

**总体意见**:

```
请在此填写对本次决策的总体意见或补充说明...
```

---

## 下一步

决策完成后，请通知需求拆解 Agent：

```
决策已完成，请继续需求拆解工作。
```

Agent 将：
1. 记录所有决策结果
2. 根据决策调整需求拆解
3. 继续生成 PRD

---

*本文档由需求拆解 Agent 自动生成*
*决策完成前，工作流将保持暂停状态*
