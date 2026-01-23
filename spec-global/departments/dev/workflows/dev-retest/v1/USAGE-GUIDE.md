# Development Retest Workflow - Usage Guide
# 开发返修流程使用指南

> **版本**: v1.0
> **适用范围**: 测试打回后的 Bug 修复和再提测
> **关键原则**: 在需求冻结前提下，快速修复，严格门禁

---

## 📋 目录

1. [概述](#概述)
2. [何时使用](#何时使用)
3. [快速开始](#快速开始)
4. [详细流程](#详细流程)
5. [防滥用规则](#防滥用规则)
6. [常见问题](#常见问题)

---

## 概述

### 什么是开发返修流程？

**开发返修流程（Dev Retest Workflow）**是一个轻量级但强约束的流程，专门用于处理**测试阶段打回的 Bug 修复**。

> ✅ **这是一个"返修型流程"，不是完整研发流程**
> ❌ **禁止引入新需求或非相关改动**

### 与完整研发流程的区别

| 特性 | 完整研发流程 | 返修流程 |
|------|------------|----------|
| 触发条件 | 新需求 | 测试打回 |
| 需求定义 | 需要 | ❌ 禁止（已冻结） |
| 技术方案 | 需要 | ❌ 禁止（仅修复） |
| 开发范围 | 全功能 | **仅限 Bug 修复** |
| 自测要求 | 基本 | **强制且严格** |
| 流程时长 | 数天-数周 | **数小时-1天** |

---

## 何时使用

### ✅ 应该使用返修流程的场景

1. **测试冒烟失败**
   - 冒烟测试未通过
   - 发现 P0/P1 级别 Bug

2. **测试门禁失败**
   - E2E 测试失败
   - 系统测试失败
   - 出测门禁未通过

3. **明确的 Bug 需要修复**
   - 有 bug.contract.yaml
   - 有 rejection-notice.yaml
   - 问题清晰，范围明确

### ❌ 不应该使用返修流程的场景

1. **需求变更**
   - 产品要求增加新功能
   - 验收标准变化
   - → **应该回到完整研发流程**

2. **架构重构**
   - 需要大范围重构
   - 技术方案调整
   - → **应该回到设计阶段**

3. **不明确的问题**
   - 问题原因不清
   - 没有 Bug 契约
   - → **应该先进行问题诊断**

---

## 快速开始

### 前置条件

1. **接收测试打回通知**
   ```bash
   # 检查是否有拒绝通知
   ls testing/output/rejection-notice.yaml

   # 检查 Bug 契约
   ls testing/bugs/BUG-*.contract.yaml
   ```

2. **初始化返修流程**
   ```bash
   cd project/<项目名>/dev-retest

   # 初始化工作流
   python -m orchestrator init . \
     --workflow ai-spec/specs/org/development/workflows/dev-retest/v1/workflow.yaml \
     --inputs rejection_notice=../testing/output/rejection-notice.yaml \
               bugs=../testing/bugs/
   ```

3. **查看状态**
   ```bash
   python -m orchestrator status .
   ```

### 5 步快速流程

```bash
# Step 1: 接收拒绝通知（自动）
python -m orchestrator start . r1_1_receive_rejection

# Step 2: 制定修复计划
python -m orchestrator start . r2_1_bug_triage

# Step 3: 执行修复
python -m orchestrator start . r3_1_code_fix

# Step 4: 开发自检（必须通过）
python -m orchestrator start . r4_1_unit_tests
python -m orchestrator start . r4_2_local_smoke

# Step 5: 生成返修提测包
python -m orchestrator start . r5_1_retest_manifest
```

---

## 详细流程

### Stage 1: 返修准备

#### 1.1 接收拒绝通知

**输入**：
- `rejection-notice.yaml`
- `bugs/*.contract.yaml`
- `test-report.yaml`

**输出**：
- `output/rejection-summary.yaml`

**做什么**：
- 解析测试团队的拒绝通知
- 提取需要修复的 Bug 列表
- 识别失败轮次和原因

**示例**：
```yaml
# output/rejection-summary.yaml
rejection_id: "REJ-2026-0001"
bugs_count: 2
bugs:
  - BUG-2026-0001 (P0 - 数据持久化)
  - BUG-2026-0002 (P1 - 页面导航)
```

#### 1.2 影响范围分析

**做什么**：
- 分析 Bug 影响的代码模块
- 确定需要回归测试的范围
- 识别潜在的副作用

**输出**：
```yaml
# output/impact-analysis.yaml
affected_modules:
  - server/internal/handler/goal_handler.go
  - pages.json
regression_scope:
  - 目标管理相关功能
  - 页面导航
```

---

### Stage 2: 修复计划

#### 2.1 Bug 分诊

**做什么**：
- 为每个 Bug 分配 owner
- 制定修复方案
- 确定回归测试计划

**输出**：
```yaml
# output/dev-fix-plan.yaml
plan_id: "FIXPLAN-2026-0001"
bugs_to_fix:
  - bug_id: "BUG-2026-0001"
    owner: "backend-developer"
    approach: "修复数据库事务提交逻辑"
    estimated_effort_hours: 3

scope_constraints:
  allowed:
    - "修复 bug.contract 中的问题"
    - "补充回归测试"
  forbidden:
    - "引入新需求"
    - "修改验收标准"
```

#### 2.2 修复计划审核（门禁）

**检查项**：
- ✅ 没有引入新需求
- ✅ 修复范围仅限 Bug
- ✅ 回归测试已计划

**失败则**：拒绝计划，要求重新制定

---

### Stage 3: 修复执行

#### 3.1 代码修复

**约束**：
- ✅ 只能修改 Bug 相关的文件
- ✅ Commit message 必须引用 Bug ID
- ❌ 禁止无关的 refactor

**示例 Commit**：
```bash
git commit -m "fix(goal): ensure goals persist with proper transaction

Fixes BUG-2026-0001

- Add transaction commit after goal save
- Add error handling for database operations
"
```

#### 3.2 补充回归测试

**要求**：
- 每个 Bug 至少 1 个回归测试
- 测试覆盖失败场景
- 测试必须通过

**示例**：
```go
// goal_handler_test.go
func TestGoalPersistence(t *testing.T) {
    // Regression test for BUG-2026-0001
    // ...
}
```

---

### Stage 4: 开发自检（关键门禁）⭐

这是**返修流程中最重要的门禁**，必须 100% 通过。

#### 4.1 单元测试

**要求**：
- ✅ 通过率必须 100%
- ✅ 所有相关测试通过
- ✅ 新增回归测试通过

```bash
# 运行单元测试
go test ./... -v

# 或
npm test
```

#### 4.2 本地冒烟测试

**要求**：
- ✅ 在本地/临时环境运行冒烟测试
- ✅ 修复的 Bug 必须验证通过
- ✅ 关键路径正常工作

```bash
# 启动本地环境
docker-compose up -d

# 运行冒烟测试
npm run test:smoke:local
```

#### 4.3 自检报告

**输出**：
```yaml
# output/dev-selfcheck.yaml
selfcheck_id: "SELFCHECK-2026-0001"
unit_test:
  passed: 32
  total: 32
  pass_rate: 100.0
  status: PASSED

local_smoke:
  passed: 10
  total: 10
  status: PASSED

overall_status: PASSED
```

---

### Stage 5: 再次提测

#### 5.1 生成返修提测包

**生成**：`retest-release-manifest.yaml`

**包含**：
- 修复的 Bug 列表
- 修复提交记录
- 自检结果摘要
- 风险区域声明

**关键字段**：
```yaml
manifest_type: "retest"  # 必须是 retest
retest_round: 1
bugs_fixed:
  - BUG-2026-0001 (FIXED)
  - BUG-2026-0002 (FIXED)

scope_declaration:
  new_features_added: false  # 必须为 false
  only_bug_fixes: true       # 必须为 true
```

#### 5.2 再提测门禁

**检查**：
- ✅ 所有 P0 Bug 已修复
- ✅ 自检测试通过
- ✅ 回归测试已补充
- ✅ 返修提测包完整

#### 5.3 交接测试团队

**触发**：
- 自动触发测试流程
- 测试团队接收 `retest-release-manifest.yaml`
- 开始新的测试轮次

---

## 防滥用规则

### 严格约束

#### 1. 禁止引入新需求

```yaml
# ❌ 错误示例
bugs_fixed:
  - BUG-001: 修复登录问题
scope_declaration:
  new_features_added: true  # ❌ 违规！
  modules_changed:
    - login.go
    - new_feature.go  # ❌ 不相关改动！
```

```yaml
# ✅ 正确示例
bugs_fixed:
  - BUG-001: 修复登录问题
scope_declaration:
  new_features_added: false
  only_bug_fixes: true
  modules_changed:
    - login.go  # ✅ 仅修复相关文件
```

#### 2. 禁止修改验收标准

```yaml
# ❌ 错误
fix_description: "由于实现困难，降低性能要求从1s改为3s"
# 这是验收标准变更，应该回到完整流程

# ✅ 正确
fix_description: "优化查询逻辑，响应时间从5s降至0.8s"
# 这是真正的修复
```

#### 3. 连续失败升级

**规则**：
- 第 1 次失败：允许再次尝试
- 第 2 次失败：警告，通知 tech-lead
- **第 3 次失败：强制升级人类介入**

```yaml
loop_control:
  max_iterations: 3
  on_iteration_fail:
    - if: iteration >= 3
      then:
        action: escalate_and_pause
        require_human_approval: true
```

---

## 常见问题

### Q1: 什么时候应该用返修流程 vs 完整流程？

**用返修流程**：
- 测试打回，问题明确
- 仅需修复 Bug
- 需求已冻结

**用完整流程**：
- 需求变更
- 架构调整
- 新功能开发

### Q2: 返修提测包和普通提测包有什么区别？

| 项目 | 普通提测包 | 返修提测包 |
|------|----------|----------|
| manifest_type | "normal" | **"retest"** |
| 包含内容 | 完整功能 | **仅 Bug 修复** |
| 自测要求 | 基本 | **强制且严格** |
| 测试策略 | 全量测试 | **冒烟+回归+风险区域** |

### Q3: 如果连续 3 次返修都失败怎么办？

**自动升级流程**：
1. 暂停自动化流程
2. 通知 tech-lead、product-manager、qa-lead
3. 要求人类审查：
   - 是否是需求问题？
   - 是否需要架构调整？
   - 是否需要更多时间？

### Q4: 可以在返修时"顺便"加个小功能吗？

**❌ 绝对不可以！**

这会违反返修流程的核心原则：
- 触发 `constraint_violation`
- 工作流自动 abort
- 需要升级人类审批

如果确实需要新功能：
1. 完成当前返修
2. 重新走完整研发流程

### Q5: 返修提测后，测试团队会跑完整测试吗？

**不一定，取决于返修包的建议**：

```yaml
test_strategy:
  recommended_tests:
    - smoke_test      # 必须
    - regression_test # 建议
    - affected_module_test # 建议

  skip_full_test_rationale: "变更范围小，风险可控"
```

测试团队可以根据：
- Bug 严重程度
- 变更范围
- 自检质量

决定是否跑完整测试。

---

## 最佳实践

### 1. 充分的自检

```bash
# 不要急于提测，确保本地验证通过
✅ 运行所有单元测试
✅ 运行本地冒烟测试
✅ 手动验证修复效果
✅ 检查是否有副作用

# 然后才提交
```

### 2. 清晰的 Commit

```bash
# 好的 Commit Message
fix(auth): ensure user session persists after page refresh

Fixes BUG-2026-0031

- Add session storage for user token
- Handle token expiry properly
- Add regression test for session persistence

# 差的 Commit Message
fix bug  # ❌ 不清晰
update code  # ❌ 没有上下文
```

### 3. 完整的回归测试

```javascript
// 每个 Bug 至少 1 个回归测试
describe('BUG-2026-0001: Goal Persistence', () => {
  it('should persist goal data after app restart', async () => {
    // 复现 Bug 场景
    // 验证修复效果
  });
});
```

### 4. 准确的风险声明

```yaml
risk_areas:
  - area: "用户认证模块"
    risk_level: "MEDIUM"
    mitigation: "已添加回归测试；本地验证其他认证流程正常"
```

---

## 附录

### 相关文档

- [工作流定义](./workflow.yaml)
- [返修提测包契约](../../contracts/retest-manifest/v1/schema.json)
- [自检报告契约](../../contracts/selfcheck/v1/schema.json)
- [修复计划契约](../../contracts/fix-plan/v1/schema.json)

### 联系方式

如有问题，请联系：
- 开发流程负责人
- Orchestrator 管理员
- 测试团队负责人
