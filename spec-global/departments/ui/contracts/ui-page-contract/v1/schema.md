# UI Page Contract v1.1

页面契约规范 - 把"页面应该长什么样、有哪些状态、有哪些交互、哪些校验"变成可机器读的规则。

**v1.1 新增**：用户流关联、前置条件、显隐规则、禁用规则、恢复路径。

## 核心理念

**Contract 是裁判**：验收以 contract 为准，Figma 是参考，不再陷入"像不像"争论。

**v1.1 设计宪法**：
- 前置条件入口处解决：条件不满足 → 隐藏入口 或 禁用+文案
- 状态不可隐含：所有错误状态必须有恢复路径
- 页面与用户流关联：每个页面知道自己在哪条路径的哪一步

## 必须覆盖的状态

每个页面必须定义以下状态，这是质量门禁的核心来源：

| 状态 | 说明 | 必须 |
|------|------|------|
| `default` | 正常展示状态 | ✅ |
| `loading` | 加载中状态 | ✅ |
| `empty` | 空数据状态 | ✅ |
| `error` | 错误状态 | ✅ |
| `success` | 成功状态 | 可选 |
| `partial` | 部分加载状态 | 可选 |

## 字段说明

### 基础字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 页面唯一标识，格式: `page.{name}` |
| `route` | string | ✅ | 路由路径，支持参数如 `/user/:id` |
| `title` | string | | 页面标题 |
| `roles` | array | | 可访问角色列表 |
| `figma` | string | | Figma 设计稿链接 |
| `states` | array | ✅ | 页面状态列表 |

### states - 状态定义

```yaml
states:
  - name: default
    components:
      - ref: component.avatar
        id: avatar
        required: true
      - ref: component.input_text
        id: nickname
        props:
          maxLength: 20

  - name: loading
    pattern: skeleton  # skeleton/spinner/placeholder

  - name: empty
    messageKey: user_profile_empty

  - name: error
    errorCodes: [USER_NOT_FOUND, PERMISSION_DENIED]
```

### interactions - 交互定义

```yaml
interactions:
  - id: save_profile
    trigger: click(save_button)
    api:
      method: POST
      endpoint: /api/user/profile
      contractRef: api.user_profile_update
    success:
      toastKey: save_success
      redirect: /profile
    failure:
      showInlineError: true
```

### validation - 校验规则

```yaml
validation:
  - field: nickname
    rules:
      - type: required
      - type: maxLength
        value: 20
        messageKey: nickname_too_long
```

### tracking - 埋点配置

```yaml
tracking:
  exposure: [page_view_user_profile]
  actions:
    - event: user_profile_save_click
      trigger: click(save_button)
      params:
        source: profile_page
```

### a11y - 可访问性配置

```yaml
a11y:
  required: true
  focusOrder: [nickname, email, save_button]
  landmarks:
    - role: main
      label: User Profile Form
```

## 示例：完整的页面契约

```yaml
# spec/ui/pages/user-profile.page.yaml
id: page.user_profile
route: /user/:id
title: 用户资料
roles: [user, admin]
figma: https://figma.com/design/xxx

states:
  - name: default
    components:
      - ref: component.avatar
        id: avatar
        required: true
      - ref: component.input_text
        id: nickname
        props:
          maxLength: 20
          required: true
      - ref: component.primary_button
        id: save
        props:
          disabledWhen:
            - form.invalid == true

  - name: loading
    pattern: skeleton

  - name: empty
    messageKey: user_profile_empty

  - name: error
    errorCodes: [USER_NOT_FOUND, PERMISSION_DENIED]

interactions:
  - id: save_profile
    trigger: click(save)
    api:
      method: POST
      endpoint: /api/user/profile
      contractRef: api.user_profile_update
    success:
      toastKey: save_success
    failure:
      showInlineError: true

validation:
  - field: nickname
    rules:
      - type: required
      - type: maxLength
        value: 20

tracking:
  exposure: [user_profile_view]
  actions:
    - event: user_profile_save_click
      trigger: click(save)

a11y:
  required: true
  focusOrder: [nickname, save]
```

## 与测试的映射

Page Contract 可自动生成以下测试：

| Contract 字段 | 生成的测试类型 |
|--------------|---------------|
| `states` | E2E 状态覆盖测试 |
| `validation.rules` | 表单校验单测 |
| `roles` | 权限/角色可见性测试 |
| `interactions` | 交互流程 E2E |
| `a11y` | 可访问性自动测试 |
| `tracking` | 埋点验证测试 |

## 门禁规则

UI Gate 会检查：
- [ ] `states` 必须包含 default/loading/empty/error
- [ ] 每个 `interaction` 必须绑定 API contract
- [ ] `figma` 链接必须存在且有效
- [ ] `a11y.required = true` 时必须定义 focusOrder
- [ ] v1.1: `preconditions` 的 `not_met_action` 必须定义
- [ ] v1.1: `error` 状态必须有对应的 `recovery_paths`
- [ ] v1.1: `flow_binding` 必须关联到有效的 User Flow Contract

---

## v1.1 新增字段

### flow_binding - 用户流关联

将页面关联到特定的用户流步骤：

```yaml
flow_binding:
  flow_ref: flow.user_registration
  step_id: step_1_phone
  is_entry_page: true
  is_completion_page: false
```

### preconditions - 前置条件

定义进入该页面的前置条件，**必须在入口处解决**：

```yaml
preconditions:
  - id: user_logged_in
    condition: "user.isLoggedIn == true"
    not_met_action: redirect  # hide | disable | redirect | show_guide
    message_key: please_login_first
    guide_to: page.login

  - id: has_permission
    condition: "user.hasPermission('edit_profile')"
    not_met_action: show_guide
    message_key: no_permission
    guide_to: page.request_permission
```

**not_met_action 说明**：
| 动作 | 说明 |
|------|------|
| `hide` | 完全隐藏入口，用户看不到 |
| `disable` | 入口可见但不可点击，显示禁用文案 |
| `redirect` | 自动跳转到 guide_to 页面 |
| `show_guide` | 显示引导提示，引导用户去满足条件 |

### visibility_rules - 显隐规则

控制页面内组件的显隐：

```yaml
visibility_rules:
  - target: admin_panel
    condition: "user.role == 'admin'"
    hidden_reason: "仅管理员可见"

  - target: premium_feature
    condition: "user.isPremium == true"
    hidden_reason: "仅付费用户可见"
```

### disabled_rules - 禁用规则

控制页面内组件的禁用状态（灰掉 + 明确文案）：

```yaml
disabled_rules:
  - target: submit_button
    condition: "form.isValid == false"
    message_key: please_fill_required_fields
    tooltip: true

  - target: send_code_button
    condition: "countdown > 0"
    message_key: wait_n_seconds
    tooltip: true
```

### recovery_paths - 恢复路径

为每个错误状态定义恢复路径（**状态不可隐含**）：

```yaml
recovery_paths:
  - error_state: NETWORK_ERROR
    recovery_action: retry  # retry | back_to_previous | redirect | show_help | contact_support
    message_key: network_error_retry
    cta_key: retry_button
    max_retries: 3

  - error_state: PERMISSION_DENIED
    recovery_action: redirect
    target: page.request_permission
    message_key: no_permission_please_apply
    cta_key: apply_now

  - error_state: SESSION_EXPIRED
    recovery_action: redirect
    target: page.login
    message_key: session_expired_relogin
    cta_key: relogin
```

---

## 完整示例（v1.1 增强版）

```yaml
# spec/ui/pages/user-profile.page.yaml

id: page.user_profile
route: /user/:id
title: 用户资料
roles: [user, admin]
figma: https://figma.com/design/xxx

# v1.1: 用户流关联
flow_binding:
  flow_ref: flow.profile_edit
  step_id: step_edit_profile
  is_entry_page: true

# v1.1: 前置条件（入口处解决）
preconditions:
  - id: must_login
    condition: "user.isLoggedIn == true"
    not_met_action: redirect
    guide_to: page.login
    message_key: please_login_first

  - id: can_edit_profile
    condition: "user.id == params.id || user.role == 'admin'"
    not_met_action: show_guide
    message_key: cannot_edit_others_profile
    guide_to: page.my_profile

# 页面状态
states:
  - name: default
    components:
      - ref: component.avatar
        id: avatar
        required: true
      - ref: component.input_text
        id: nickname
        props:
          maxLength: 20
          required: true
      - ref: component.primary_button
        id: save
        props:
          label: 保存

  - name: loading
    pattern: skeleton

  - name: empty
    messageKey: user_profile_empty

  - name: error
    errorCodes: [USER_NOT_FOUND, PERMISSION_DENIED, NETWORK_ERROR]
    messageKey: user_profile_error

# v1.1: 显隐规则
visibility_rules:
  - target: admin_actions
    condition: "user.role == 'admin'"
    hidden_reason: "仅管理员可见的操作区"

# v1.1: 禁用规则
disabled_rules:
  - target: save
    condition: "form.isValid == false || form.isDirty == false"
    message_key: nothing_to_save
    tooltip: true

# 交互定义
interactions:
  - id: save_profile
    trigger: click(save)
    api:
      method: POST
      endpoint: /api/user/profile
      contractRef: api.user_profile_update
    success:
      toastKey: save_success
    failure:
      showInlineError: true

# 校验规则
validation:
  - field: nickname
    rules:
      - type: required
      - type: maxLength
        value: 20

# v1.1: 恢复路径
recovery_paths:
  - error_state: USER_NOT_FOUND
    recovery_action: redirect
    target: page.home
    message_key: user_not_found
    cta_key: go_home

  - error_state: PERMISSION_DENIED
    recovery_action: back_to_previous
    message_key: no_permission
    cta_key: go_back

  - error_state: NETWORK_ERROR
    recovery_action: retry
    message_key: network_error
    cta_key: retry
    max_retries: 3

# 埋点
tracking:
  exposure: [user_profile_view]
  actions:
    - event: user_profile_save_click
      trigger: click(save)

# 可访问性
a11y:
  required: true
  focusOrder: [nickname, save]
```

---

## 与 User Flow Contract 的关系

Page Contract 通过 `flow_binding` 与 User Flow Contract 建立关联：

```
User Flow Contract（功能路径）
    ↓ 定义 main_path.steps[].page_ref
Page Contract（页面定义）
    ↓ 通过 flow_binding 反向关联
    ↓ 引用组件
Component Contract（组件定义）
```

**关键规则**：
1. 每个在用户流中的页面必须有 `flow_binding`
2. `flow_binding.step_id` 必须与 User Flow Contract 中的步骤 ID 匹配
3. 入口页面设置 `is_entry_page: true`
4. 完成页面设置 `is_completion_page: true`
