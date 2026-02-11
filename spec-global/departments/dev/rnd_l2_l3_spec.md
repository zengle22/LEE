# LEE - 研发部 L2 + L3 执行规范 v1.0

> 本文件定义研发部（L2）内部的 L3 执行规范与闭环流程。

---

## 一、组织分层定义

| 层级 | 角色 | 职责 |
|------|------|------|
| L1 | CEO | 方向与资源 |
| L2 | 研发部 | 流程制定与治理 |
| L3 | 执行 Agent | 具体角色执行 |

---

## 二、研发主流程（Feature 开发）

### Phase 1：协议设计与冻结

- **执行者**: Contract-Agent (`agent.dev.contract_designer`)
- **产物**: `/contracts/*.yaml` + version + changelog
- **规则**:
  1. 协议是唯一事实来源（Single Source of Truth）
  2. 所有 DTO / API 必须在 contract 中定义
  3. 字段命名统一、类型清晰
  4. 冻结后不得私改
  5. 协议变更必须升级版本
- **冻结标志**: contract 文件存在 + 版本号更新 + changelog 更新

### Phase 2：前后端并行开发

- **执行者**: FE-Agent (`agent.dev.uniapp_frontend_engineer`) + BE-Agent (`agent.dev.go_backend_engineer`)
- **FE-Agent 约束**:
  - 只能从 contract 生成类型
  - 不允许手写 interface
  - 不允许假设未定义字段
- **BE-Agent 约束**:
  - 返回数据必须符合 contract schema
  - 不允许新增未定义字段
  - 不允许更改字段类型

### Phase 3：连调验证

- **执行者**: Integration-Agent (`agent.dev.integration_planner`)
- **职责**: 编写集成测试、执行主流程连调、验证数据贯通
- **规则**:
  - 连调发现结构问题 → 打回 Contract-Agent (回到 Phase 1)
  - 不允许连调阶段直接改协议

### Phase 4：主流程冒烟守门

- **执行者**: Smoke-Agent (`agent.dev.smoke_tester`)
- **必须执行**: 单测 + 集成测试 + 主流程 smoke
- **规则**:
  - 冒烟失败不允许 merge
  - 冒烟失败优先级最高

---

## 三、Bugfix 流程（闭环）

### Step 1：Bug 分析与分流

- **执行者**: Bug-Triage-Agent (`agent.dev.bug_triage`)
- **必须判断**: 是否涉及 contract 修改？

### 情况 A：实现 Bug

1. 修复方案输出
2. 修复代码
3. 单测
4. 集成测试
5. 冒烟
6. Code Review
7. Merge

### 情况 B：协议 Bug

1. 修改 contract → 升版本 → 写 changelog
2. 前后端同步更新
3. 回到开发流程 Phase 2

### Code Review 重点

- 是否违反 contract
- 是否扩大修改范围
- 是否隐式修改字段
- 是否破坏兼容性

### 经验沉淀

- Bug 根因
- 是否需补测试
- 是否需补 smoke case

---

## 四、结构原则

1. **协议优先于实现** — 实现必须服从协议
2. **协议变更必须显式** — 版本号 + changelog
3. **所有结构问题必须回到 Contract-Agent** — 不允许绕过
4. **Bugfix 不能绕过结构判断** — 必须先分流

---

## 五、落地建议（执行顺序）

> 不要一次性启用全部 Agent，建议顺序：

1. 先启用 **Contract-Agent** + 协议冻结门禁
2. 再启用 **Smoke-Agent** + 冒烟门禁
3. 再加 **Bug-Triage-Agent** 到 bug-fix 流程
4. 最后完善 **Integration-Agent** 的打回机制

---

*Created: 2026-02-11 | Version: 1.0*
