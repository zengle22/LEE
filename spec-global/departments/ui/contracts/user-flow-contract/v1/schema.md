# User Flow Contract v1.0

用户流契约 - 定义功能的**强制闭合主路径**，实现「单主路径原则」和「路径可枚举」。

## 核心理念

### 第一原则：单主路径原则（Single Main Path）

> **任何功能在 V1 阶段，必须且只能存在一条可执行的主路径。**

- 主路径 = 从入口到完成态，**无需猜测、不依赖隐含前置知识**
- 不存在"走一半再去干别的"
- 不存在"完成 B 后再回来继续 A"

**违反即视为设计缺陷，不进入实现阶段。**

### 第二原则：状态不可隐含（No Hidden State）

所有状态必须被处理成三种"可控形态"：

| 状态类型 | 处理方式 |
|---------|---------|
| 可执行态 | 正常展示，允许交互 |
| 不可执行态 | 明确原因 + 明确下一步 + 回到主路径的方式 |
| 中间态 | **禁止依赖其他功能的中间态** |

### 第三原则：前置条件入口处解决

- 条件不满足 → 不显示入口 或 显式引导
- **禁止**：点进去才告诉你"不行"

---

## 契约结构

```yaml
# spec/ui/flows/user-registration.flow.yaml

id: flow.user_registration
name: 用户注册
description: 新用户完成注册的完整流程
version: v1
priority: P0

# ============================================
# 入口定义
# ============================================
entry:
  page_ref: page.home
  trigger: click(register_button)

  # 前置条件 - 在入口处解决
  preconditions:
    - id: not_logged_in
      condition: "user.isLoggedIn == false"
      not_met_action: redirect
      guide_to: page.dashboard
      message_key: already_logged_in

  # 入口显隐规则
  visibility_rule:
    condition: "user.isLoggedIn == false"
    hidden_reason: "已登录用户不显示注册入口"

  # 入口禁用规则（不常用，优先用visibility_rule）
  disabled_rule:
    condition: "system.registrationOpen == false"
    message_key: registration_closed
    tooltip: true

# ============================================
# 主路径定义（核心）
# ============================================
main_path:
  max_steps: 4
  allow_back: true
  force_sequential: true  # 不允许跳步

  steps:
    - id: step_1_phone
      page_ref: page.register_phone
      action: "输入手机号并获取验证码"
      trigger: click(get_code_button)
      preconditions:
        - id: valid_phone
          condition: "form.phone.isValid"
          not_met_action: disable
          message_key: invalid_phone
      validation:
        required_fields: [phone]
        rules:
          - field: phone
            type: pattern
            value: "^1[3-9]\\d{9}$"
      on_failure:
        action: show_inline_error
        message_key: phone_send_failed
        recovery_hint_key: check_phone_retry

    - id: step_2_verify
      page_ref: page.register_verify
      action: "输入短信验证码"
      trigger: click(verify_button)
      preconditions:
        - id: code_sent
          condition: "state.codeSent == true"
          not_met_action: redirect
          guide_to: step_1_phone
          message_key: need_get_code_first
      validation:
        required_fields: [code]
      on_failure:
        action: show_inline_error
        message_key: code_verify_failed

    - id: step_3_password
      page_ref: page.register_password
      action: "设置登录密码"
      trigger: click(set_password_button)
      validation:
        required_fields: [password, confirm_password]
        rules:
          - field: password
            type: minLength
            value: 8
          - field: confirm_password
            type: match
            value: password
      on_failure:
        action: show_inline_error
        message_key: password_set_failed

    - id: step_4_profile
      page_ref: page.register_profile
      action: "完善基本资料"
      trigger: click(complete_button)
      is_optional: false  # V1 不允许可选步骤
      validation:
        required_fields: [nickname]

  # 完成态定义
  completion:
    state: success
    feedback:
      type: page
      message_key: registration_complete
      redirect_to: page.dashboard
    next_action:
      type: redirect
      target: page.dashboard

# ============================================
# 合法退出点
# ============================================
exit_points:
  - id: complete
    type: complete
    from_step: step_4_profile

  - id: cancel_early
    type: cancel
    confirmation_required: true
    confirmation_message_key: confirm_cancel_registration
    data_preservation: discard

  - id: session_timeout
    type: timeout
    data_preservation: save_draft

  - id: error_exit
    type: error
    data_preservation: save_draft

# ============================================
# 禁止的路径模式
# ============================================
blocked_patterns:
  - id: no_mid_flow_exit_to_other_feature
    pattern: "在注册流程中途跳转到其他功能（如浏览商品）"
    reason: "V1禁止中间态依赖其他功能"
    enforcement: hide_entry

  - id: no_skip_steps
    pattern: "跳过验证码直接设置密码"
    reason: "强制顺序执行"
    enforcement: block_navigation

  - id: no_parallel_registration
    pattern: "同时进行多个注册流程"
    reason: "状态冲突"
    enforcement: block_navigation

# ============================================
# 错误恢复策略
# ============================================
recovery_strategies:
  - error_type: network_error
    recovery_action: retry
    max_retries: 3
    message_key: network_error_retry

  - error_type: validation_error
    recovery_action: show_error
    message_key: fix_form_errors

  - error_type: server_error
    recovery_action: back_to_step
    target_step: step_1_phone
    message_key: server_error_restart

# ============================================
# AI 盲跑验证配置
# ============================================
ai_walkthrough:
  enabled: true
  expected_steps: 4
  hints_allowed: false  # V1 必须为 false
  success_criteria:
    - "完成所有4个步骤"
    - "到达 completion.success 状态"
    - "未触发任何 blocked_patterns"
  forbidden_actions:
    - "跳过任何步骤"
    - "在流程中访问其他功能页面"
    - "使用浏览器后退跳出流程"
```

---

## 与 Page Contract 的关系

User Flow Contract 是 Page Contract 的"上层抽象"：

```
User Flow Contract（功能路径）
    ↓ 引用
Page Contract（页面定义）
    ↓ 引用
Component Contract（组件定义）
```

### 关联方式

在 Page Contract 中通过 `flow_step` 字段关联：

```yaml
# spec/ui/pages/register-phone.page.yaml

id: page.register_phone
route: /register/phone

# 关联到用户流
flow_binding:
  flow_ref: flow.user_registration
  step_id: step_1_phone
  is_entry_page: true

# ... 其他页面定义
```

---

## 门禁规则

### single_main_path_verified 检查

UI Gate 会验证：

| 检查项 | 严重度 | 说明 |
|--------|--------|------|
| 存在且仅存在一条主路径 | blocker | `main_path.steps.length >= 1` |
| 所有步骤有明确前置条件 | blocker | `step.preconditions != null` |
| 完成态明确定义 | blocker | `main_path.completion != null` |
| 至少一个合法退出点 | blocker | `exit_points.length >= 1` |
| 禁止模式已定义 | major | `blocked_patterns.length >= 1` |
| AI盲跑配置完整 | major | `ai_walkthrough.enabled == true` |

### 与现有检查的整合

```yaml
# ui-gate 中新增检查
checks:
  - id: single_main_path_verified
    name: 单主路径验证
    description: 是否存在且仅存在一条强制闭合的用户主路径
    severity: blocker
    rule: |
      flow.main_path != null
      && flow.main_path.steps.length >= 1
      && flow.main_path.completion != null
      && flow.exit_points.length >= 1
    message: "功能未定义强制闭合的主路径"
    fix: "创建 user-flow-contract 定义完整主路径"
```

---

## AI 友好性规则

### 第九原则：AI 必须能"盲跑"主路径

> **如果一个完全不理解业务意图的 AI，仅凭 UI 顺序就能跑通主路径，那这个设计才是合格的。**

验证方式：

1. AI 从 `entry.trigger` 开始
2. 依次执行每个 `step.trigger`
3. 不依赖任何业务知识
4. 最终到达 `completion.state == success`

### 第十原则：路径必须可枚举

所有可能的路径必须是可列举的：

```yaml
# 路径枚举
paths:
  happy_path: [entry] → [step_1] → [step_2] → [step_3] → [step_4] → [complete]
  cancel_path: [entry] → [step_*] → [cancel_early]
  timeout_path: [entry] → [step_*] → [session_timeout]
  error_path: [entry] → [step_*] → [error_exit]
```

**不允许存在未被枚举的隐式路径。**

---

## 设计检查清单

在提交设计前，确认以下问题：

- [ ] 是否只有一条主路径？
- [ ] 主路径是否强制闭合（有明确完成态）？
- [ ] 每个步骤的前置条件是否在入口处解决？
- [ ] 是否定义了所有合法退出点？
- [ ] 是否明确禁止了中间态跳转？
- [ ] AI 能否仅凭 UI 顺序盲跑通过？
- [ ] 所有不可执行状态是否有明确原因和下一步？

**任何一项为否，不进入实现阶段。**

---

## 版本策略

| 版本 | 路径限制 | 可选步骤 | 分支逻辑 |
|------|---------|---------|---------|
| V1 | 仅一条主路径 | 不允许 | 不允许 |
| V2 | 可有备选路径 | 允许 | 简单条件分支 |
| V3 | 多路径 | 允许 | 复杂条件分支 |

**V1 阶段严格执行单主路径原则，后续版本可逐步放开。**
