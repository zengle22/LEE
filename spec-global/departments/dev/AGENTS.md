# Dev 部门宪法 (Development Department Constitution)

> **版本**: v1.0  
> **生效日期**: 2026-02-11  
> **适用范围**: 所有 Dev 部门 Agent 和开发人员

---

## 第一章：总则

### 第1条 目的
本文档定义 Dev 部门（开发部门）的根本法则，所有 Dev 部门的 Agent、工作流、技能和标准都必须遵守。

### 第2条 适用范围
本文档适用于：
- 所有 Dev 部门的 Agent（后端、前端、架构师、测试等）
- 所有 Dev 部门的工作流（Workflow）
- 所有 Dev 部门的技能（Skill）
- 所有 Dev 部门的标准（Standard）
- 所有参与开发的工程师

### 第3条 宪法地位
**本宪法是 Dev 部门的最高规范**，所有其他文档（Agent 定义、工作流、标准）如与本宪法冲突，以本宪法为准。

---

## 第二章：契约优先原则 (Contract-First Development)

### 第4条 核心原则
**4.1** 协议（Contract）是唯一的真相来源（Single Source of Truth）。

**4.2** 所有开发活动必须先有冻结的协议，后有代码实现。

**4.3** 代码必须严格遵循协议，不允许偏离。

### 第5条 协议冻结机制

**5.1** 协议必须通过正式的冻结流程才能生效。

**5.2** 冻结的协议位于：`dev/src/api-contract/v1/api-contract.yaml`

**5.3** 当前冻结协议：
- **Contract ID**: `API-CONTRACT-20260211-001`
- **版本**: `1.0.0`
- **冻结时间**: `2026-02-11T23:45:00+08:00`
- **状态**: 🔒 **FROZEN**

### 第6条 强制遵守规则

**6.1 后端 Agent 必须遵守：**
- ✅ 所有 API 返回数据必须符合 contract schema
- ✅ 所有字段使用 `snake_case` 命名
- ✅ 返回统一错误格式：`{code, message, request_id}`
- ✅ 不允许新增 contract 未定义的字段
- ✅ 不允许更改 contract 定义的字段类型
- ✅ 发现结构问题必须反馈给 Contract-Agent，不得私自修改

**6.2 前端 Agent 必须遵守：**
- ✅ 类型必须从 contract 生成，不允许手写 interface
- ✅ 只能使用 contract 中明确定义的字段
- ✅ 请求参数使用 `snake_case`
- ✅ 处理所有 contract 定义的错误码
- ✅ 接口不匹配必须反馈给 Contract-Agent，不得自行修改

**6.3 禁止事项：**
- ❌ 私自修改已冻结的协议
- ❌ 添加协议中未定义的字段
- ❌ 修改协议中定义的字段类型
- ❌ 使用驼峰命名或其他命名风格
- ❌ 忽略协议定义的错误码

### 第7条 协议变更流程

**7.1** 冻结后的协议变更必须通过正式流程：
```
变更申请 → 影响评估 → 审批 → 版本升级 → 重新冻结 → 同步团队
```

**7.2** 变更必须通过 L3 工作流：`feature-contract-l3/v1/workflow.yaml`

**7.3** 版本号必须遵循 SemVer：
- Major：破坏性变更
- Minor：功能添加（向后兼容）
- Patch：Bug 修复（向后兼容）

---

## 第三章：代码规范

### 第8条 命名规范

**8.1** 所有 JSON 字段、数据库列、API 参数必须使用 `snake_case`。

**8.2** 禁止使用驼峰命名（camelCase）或大写驼峰（PascalCase）作为数据字段名。

**8.3** 示例：
```yaml
# ✅ 正确
user_id: "uuid"
created_at: "2026-02-11T23:45:00+08:00"
first_name: "John"

# ❌ 错误
userId: "uuid"
createdAt: "..."
firstName: "John"
```

### 第9条 错误处理规范

**9.1** 统一错误响应格式：
```json
{
  "code": "ERROR_CODE",
  "message": "Human readable description",
  "request_id": "req_abc123xyz"
}
```

**9.2** 错误码必须来自协议定义，使用大写蛇形命名。

**9.3** HTTP 状态码与业务错误码分离。

### 第10条 日志规范

**10.1** 使用结构化 JSON 日志。

**10.2** 所有日志必须包含 `trace_id` 和 `request_id`。

**10.3** 错误日志必须使用统一错误码。

**10.4** 敏感数据必须脱敏。

---

## 第四章：知识库协议

### 第11条 强制知识库访问

**11.1** 所有 Agent 在执行任务前必须阅读知识库。

**11.2** 必须阅读的目录：
- `{phase_dir}/knowledge/pitfalls/`
- `{phase_dir}/knowledge/patterns/`
- `{project_dir}/knowledge/pitfalls/`
- `{project_dir}/knowledge/patterns/`

**11.3** 必须阅读的内容：
- **Pitfalls（踩坑记录）**：避免重复犯错
- **Patterns（技术模式）**：复用已有方案

### 第12条 知识应用规则

**12.1** 遇到 pitfall 描述的场景，必须使用其解决方案。

**12.2** 存在可复用的 pattern，优先使用而非重新设计。

**12.3** 在代码中引用知识来源：
```go
// 参考知识库: {knowledge_id}
// 问题: {problem}
// 解决方案: {solution}
```

---

## 第五章：Agent 行为准则

### 第13条 职责边界

**13.1** 每个 Agent 有明确的职责范围：
- **Contract Designer**: 协议设计，不负责实现
- **Go Backend Engineer**: Go 后端实现，不负责架构决策
- **UniApp Frontend Engineer**: 前端实现，不负责设计
- **Bug Fix Implementer**: Bug 修复，不负责根因分析

**13.2** Agent 必须拒绝超出职责范围的请求。

### 第14条 质量标准

**14.1** 代码必须通过所有检查：
- 后端：golint, go vet，测试覆盖率 > 75%
- 前端：ESLint, Prettier，TypeScript 严格模式

**14.2** 新功能必须有单元测试。

**14.3** Bug 修复必须有回归测试。

### 第15条 禁止行为

**15.1** 所有 Agent 禁止：
- 忽略错误返回值
- 使用裸 panic / console.log
- 硬编码配置和密钥
- 不处理边界情况
- 私自修改协议
- 跳过知识库阅读

---

## 第六章：工作流规范

### 第16条 工作流执行

**16.1** 所有开发必须通过工作流执行。

**16.2** 工作流阶段必须顺序执行，不得跳过。

**16.3** 必须通过门禁（Gate）才能进入下一阶段。

### 第17条 门禁机制

**17.1** 关键门禁：
- **Contract Freeze Gate**: 协议冻结前必须通过
- **Dev Gate**: 代码合并前必须通过
- **Release Gate**: 发布前必须通过

**17.2** 门禁检查失败必须整改，不得绕过。

---

## 第七章：引用与实施

### 第18条 强制引用

**18.1** 所有 Dev 部门的 Agent YAML 文件必须在头部引用本宪法：

```yaml
# ============================================
# Dev 部门宪法引用 (强制)
# ============================================
constitution:
  ref: ../../AGENTS.md
  version: "1.0"
  mandatory: true
  compliance_check: true
```

**18.2** 所有工作流 YAML 文件必须在头部引用本宪法：

```yaml
# ============================================
# Dev 部门宪法引用 (强制)
# ============================================
constitution:
  ref: ../AGENTS.md
  version: "1.0"
  mandatory: true
```

### 第19条 合规检查

**19.1** Agent 执行前必须检查宪法合规性。

**19.2** 如发现违反宪法的行为，必须立即停止并报告。

**19.3** 定期审计 Agent 行为是否符合宪法。

---

## 第八章：附则

### 第20条 修订
本宪法的修订需经 Dev 部门技术委员会审批。

### 第21条 生效
本宪法自 2026-02-11 起对所有 Dev 部门 Agent 生效。

### 第22条 违反后果
违反本宪法的 Agent 将被：
1. 暂停执行权限
2. 要求整改
3. 严重违反将被标记为不可信

---

## 附录

### A. 关键文件引用

| 文件 | 路径 | 说明 |
|------|------|------|
| 冻结协议 | `dev/src/api-contract/v1/api-contract.yaml` | API 协议定义 |
| 冻结文档 | `dev/src/api-contract/docs/API-CONTRACT-FROZEN-v1.0.0.md` | 冻结声明 |
| 开发宪法 | `dev/AGENTS.md` | 开发部门规范 |
| L3 协议工作流 | `lee/spec-global/departments/dev/workflows/feature-contract-l3/v1/workflow.yaml` | 协议设计流程 |

### B. 相关 Agent

| Agent | ID | 职责 |
|-------|-----|------|
| Contract Designer | `agent.dev.contract_designer` | 协议设计 |
| Go Backend Engineer | `agent.dev.go_backend_engineer` | Go 后端实现 |
| UniApp Frontend Engineer | `agent.dev.uniapp_frontend_engineer` | 前端实现 |
| Code Reviewer | `agent.dev.code_reviewer` | 代码审查 |

### C. 版本历史

| 版本 | 日期 | 变更 |
|------|------|------|
| 1.0 | 2026-02-11 | 初始版本，定义契约优先原则 |

---

*本宪法由 Dev 部门制定*  
*制定日期: 2026-02-11*  
*版本: v1.0*  
*所有 Dev 部门 Agent 必须遵守*
