# Defect Management Skill v1.0
# 缺陷管理技能规范

## 概述

缺陷管理技能定义了如何使用 Bug 契约文件进行缺陷全生命周期管理。
这是 AI-first 测试体系的核心能力，用契约文件替代传统工单系统。

## 技能标识

- **ID**: skill.test.defect_management
- **名称**: Defect Management
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.bug_manager
- agent.test.system_test_executor
- agent.test.regression_test_executor

---

## 1. Bug 契约文件规范

### 1.1 文件命名

```
bugs/
├── BUG-2026-0001.yaml
├── BUG-2026-0002.yaml
└── ...
```

命名格式: `BUG-{YYYY}-{NNNN}.yaml`

### 1.2 核心字段

```yaml
# 必填字段
bug_id: BUG-2026-0001
title: "简洁、准确的问题描述"
severity: P0 | P1 | P2 | P3
type: functional | performance | security | requirement | ui | compatibility
status: new | triaged | assigned | fixed | verified | closed | rejected | deferred

# 发现信息
detected_in:
  version: v1.0.0-rc1
  commit: abc1234
  environment: test
  test_case_id: TC-AUTH-001

# 复现信息 (必填且必须完整)
repro:
  preconditions:
    - "测试账号已创建"
    - "网络连接正常"
  steps:
    - "打开登录页面"
    - "输入用户名: test@example.com"
    - "输入密码: ******"
    - "点击登录按钮"
  expected: "成功登录并跳转首页"
  actual: "显示 500 错误"
  reproducible: always | sometimes | rarely | once

# 归属信息
ownership:
  reporter_agent: agent.test.system_test_executor
  owner_agent: null  # 待分配
  reviewer_agent: null  # 验证者
```

### 1.3 证据字段

```yaml
evidence:
  logs:
    - trace_id: "9f23a-xxx-xxx"
      service: api-gateway
      log_snippet: |
        ERROR [2026-01-12 10:30:00] AuthController - Failed to authenticate
        java.lang.NullPointerException: ...
      timestamp: "2026-01-12T10:30:00Z"

  screenshots:
    - "evidence/BUG-2026-0001/screenshot-1.png"
    - "evidence/BUG-2026-0001/screenshot-2.png"

  videos:
    - "evidence/BUG-2026-0001/recording.mp4"

  network:
    request: |
      POST /api/auth/login HTTP/1.1
      Content-Type: application/json
      {"email": "test@example.com", "password": "***"}
    response: |
      HTTP/1.1 500 Internal Server Error
      {"error": "Internal error"}
    status_code: 500
```

---

## 2. 状态机管理

### 2.1 状态定义

```yaml
states:
  new:
    description: "新创建，待分类"
    color: "#FF6B6B"

  triaged:
    description: "已分类，待分配"
    color: "#4ECDC4"

  assigned:
    description: "已分配给开发"
    color: "#45B7D1"

  fixed:
    description: "开发已修复，待验证"
    color: "#96CEB4"

  verified:
    description: "已验证通过"
    color: "#88D8B0"

  closed:
    description: "已关闭"
    color: "#CCCCCC"

  rejected:
    description: "已拒绝 (非 Bug)"
    color: "#A8A8A8"

  deferred:
    description: "已延期"
    color: "#DDA0DD"
```

### 2.2 状态转换规则

```
new ─────────┬──────────► triaged
             │
             └──────────► rejected (需要 rejection_reason)

triaged ────┬──────────► assigned (需要 owner_agent)
            │
            └──────────► deferred (需要 decision_reason)

assigned ───┬──────────► fixed (需要 fix_commit, fix_description)
            │
            ├──────────► rejected (需要 decision.resolution, decision_reason)
            │
            └──────────► deferred (需要 decision_reason)

fixed ──────┬──────────► verified (需要 verified_by, verification_result)
            │            约束: verified_by ≠ owner_agent
            │
            └──────────► assigned (验证失败，重新打开)

verified ───┬──────────► closed
            │
            └──────────► assigned (回归发现问题)

deferred ──────────────► assigned (重新激活)
```

### 2.3 转换验证

```yaml
transition_validation:
  rules:
    - name: "verified_by 不能是修复者"
      transition: "fixed → verified"
      check: "verification.verified_by != ownership.owner_agent"
      error: "修复者不能验证自己的修复"

    - name: "P0/P1 修复必须有回归用例"
      transition: "verified → closed"
      check: |
        severity not in [P0, P1] ||
        (regression.required == true && regression.regression_case_id != null)
      error: "P0/P1 Bug 关闭前必须补充回归用例"

    - name: "拒绝需要说明原因"
      transition: "* → rejected"
      check: "decision.resolution != null && decision.decision_reason != null"
      error: "拒绝 Bug 必须说明原因"
```

---

## 3. 分类与分流

### 3.1 严重级别判定规则

```yaml
severity_determination:
  P0:
    criteria:
      - "核心功能不可用"
      - "系统崩溃/无法启动"
      - "数据损坏/丢失"
      - "安全漏洞"
    scope: "core_flow"
    users_affected: "all"
    response_time: "立即处理"

  P1:
    criteria:
      - "主流程可用但有明显错误"
      - "影响大量用户"
    scope: "core_flow | secondary_flow"
    users_affected: "most | all"
    response_time: "24 小时内"

  P2:
    criteria:
      - "非主流程问题"
      - "体验瑕疵"
    scope: "secondary_flow | edge_case"
    users_affected: "some"
    response_time: "本迭代内"

  P3:
    criteria:
      - "文案/样式问题"
      - "优化建议"
    scope: "cosmetic"
    users_affected: "few"
    response_time: "后续安排"
```

### 3.2 类型分流

```yaml
type_routing:
  functional:
    owner: "对应模块开发"
    description: "功能错误"

  performance:
    owner: "性能优化团队"
    description: "性能问题"

  security:
    owner: "安全团队"
    priority: "提升一级"
    description: "安全漏洞"

  requirement:
    owner: "产品经理"
    flow: "需求澄清流程"
    description: "需求不明确/争议"

  ui:
    owner: "前端开发"
    description: "界面问题"

  compatibility:
    owner: "测试 + 前端"
    description: "兼容性问题"
```

### 3.3 需求争议处理

```yaml
requirement_dispute_flow:
  trigger:
    - "type == 'requirement'"
    - "测试与需求描述不符"
    - "验收标准不明确"

  steps:
    1: "QA 标记 type: requirement"
    2: "PM 介入判定"
    3: "PM 给出结论"

  decisions:
    by_design:
      action: "关闭 Bug，标记 decision.resolution = by_design"
      note: "更新需求文档明确此行为"

    change_required:
      action: "转为需求变更"
      note: "走变更流程"

    implementation_error:
      action: "改为 type: functional"
      note: "开发修复"

    need_human_confirmation:
      action: "升级到人工确认"
      note: "PM 无法判定时"
```

---

## 4. 验证与闭环

### 4.1 验证标准

```yaml
verification_standard:
  steps:
    1: "确认修复版本已部署"
    2: "按原复现步骤执行"
    3: "验证预期结果实现"
    4: "执行回归用例 (如有)"
    5: "记录验证结果"

  criteria:
    pass:
      - "原问题不再出现"
      - "预期结果正确"
      - "回归用例通过"
      - "无新问题引入"

    fail:
      - "原问题仍存在"
      - "部分修复"
      - "引入新问题"
```

### 4.2 回归用例要求

```yaml
regression_requirement:
  mandatory_for: [P0, P1]
  recommended_for: [P2]
  optional_for: [P3]

  regression_case:
    id: "REG-{BUG_ID}"
    type: "bug_regression"
    related_bug: "{BUG_ID}"
    steps: "复用 Bug 的 repro.steps"
    expected: "复用 Bug 的 repro.expected"
    priority: "与原 Bug 相同"
    tags: ["regression", "bug-fix"]
```

### 4.3 关闭条件

```yaml
closure_conditions:
  fixed:
    - "verification.verification_result == 'pass'"
    - "P0/P1: regression.regression_case_id 不为空"

  by_design:
    - "decision.resolution == 'by_design'"
    - "decision.pm_confirmation == 'confirmed'"
    - "需求文档已更新"

  duplicate:
    - "decision.resolution == 'duplicate'"
    - "analysis.related_bugs 包含原 Bug ID"

  cannot_reproduce:
    - "decision.resolution == 'cannot_reproduce'"
    - "至少尝试复现 3 次"
    - "decision.decision_reason 包含详细说明"

  wont_fix:
    - "decision.resolution == 'wont_fix'"
    - "decision.decided_by 包含审批者"
    - "decision.decision_reason 不为空"
```

---

## 5. 报告与统计

### 5.1 Bug 统计维度

```yaml
statistics_dimensions:
  by_severity:
    - P0: { found: 0, fixed: 0, open: 0 }
    - P1: { found: 0, fixed: 0, open: 0 }
    - P2: { found: 0, fixed: 0, open: 0 }
    - P3: { found: 0, fixed: 0, open: 0 }

  by_status:
    - new: count
    - triaged: count
    - assigned: count
    - fixed: count
    - verified: count
    - closed: count

  by_module:
    - auth: { total: 0, open: 0 }
    - order: { total: 0, open: 0 }
    - payment: { total: 0, open: 0 }

  metrics:
    - fix_rate: "closed / total"
    - reopen_rate: "reopened / closed"
    - avg_fix_time: "平均修复时长"
    - avg_verify_time: "平均验证时长"
```

### 5.2 趋势分析

```yaml
trend_analysis:
  daily:
    - new_bugs: "新发现"
    - fixed_bugs: "修复"
    - verified_bugs: "验证"
    - closed_bugs: "关闭"

  burndown:
    - total_open: "总未关闭"
    - target: "目标线"

  alerts:
    - p0_increase: "P0 增长"
    - fix_rate_decrease: "修复率下降"
    - aging_bugs: "老化 Bug (>7天)"
```

---

## 6. 最佳实践

### 6.1 Bug 描述规范

- **标题**: 简洁明了，包含模块和问题摘要
- **复现步骤**: 具体可执行，包含测试数据
- **预期/实际**: 明确对比
- **证据**: 完整，包含日志和截图

### 6.2 协作规范

- **及时响应**: P0 立即处理，P1 24小时内
- **状态同步**: 及时更新 Bug 状态
- **沟通记录**: 重要讨论记录在 history
- **交接清晰**: 分配时说明上下文

### 6.3 质量保障

- **验证独立**: 修复者不能验证自己的修复
- **回归保证**: P0/P1 必须补回归用例
- **闭环完整**: 所有 Bug 必须有最终结论
- **历史可追**: 所有变更记录在 history

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-12 | 初始版本 |
