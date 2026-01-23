# UI Page Contract v1.0

页面契约规范 - 把"页面应该长什么样、有哪些状态、有哪些交互、哪些校验"变成可机器读的规则。

## 核心理念

**Contract 是裁判**：验收以 contract 为准，Figma 是参考，不再陷入"像不像"争论。

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
