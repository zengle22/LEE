# UI Component Contract v1.0

组件契约规范 - 把组件当成"前端 API"，让开发/测试/验收都有共同语言。

## 核心理念

组件是 UI 的最小可复用单元，Component Contract 定义：
- **Props**: 组件接受什么参数
- **States**: 组件有哪些状态
- **Events**: 组件触发什么事件
- **A11y**: 可访问性要求

## 字段说明

### 基础字段

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `id` | string | ✅ | 组件唯一标识，格式: `component.{name}` |
| `name` | string | | 组件显示名称 |
| `category` | enum | | 组件分类 |
| `figma` | string | | Figma 组件链接 |
| `props` | object | ✅ | 属性定义 |
| `states` | array | ✅ | 状态列表 |
| `events` | array | | 事件定义 |
| `a11y` | object | | 可访问性配置 |

### props - 属性定义

```yaml
props:
  size:
    type: string
    enum: [sm, md, lg]
    default: md
    description: 按钮尺寸

  variant:
    type: string
    enum: [primary, secondary, danger, ghost]
    default: primary

  disabled:
    type: boolean
    default: false

  loading:
    type: boolean
    default: false

  icon:
    type: string
    required: false
    description: 图标名称
```

### states - 状态列表

```yaml
states:
  - default    # 默认状态
  - hover      # 悬停状态
  - active     # 激活状态
  - focus      # 聚焦状态
  - disabled   # 禁用状态
  - loading    # 加载状态
```

### events - 事件定义

```yaml
events:
  - name: click
    when: disabled == false && loading == false
    payload:
      event: MouseEvent
    description: 点击事件

  - name: focus
    description: 获得焦点

  - name: blur
    description: 失去焦点
```

### a11y - 可访问性配置

```yaml
a11y:
  role: button
  ariaLabel: Submit form
  focusable: true
  keyboard:
    - key: Enter
      event: click
      description: 触发点击
    - key: Space
      event: click
      description: 触发点击
```

## 示例：Primary Button 组件契约

```yaml
# spec/ui/components/primary-button.component.yaml
id: component.primary_button
name: Primary Button
category: basic
figma: https://figma.com/design/xxx/button

props:
  size:
    type: string
    enum: [sm, md, lg]
    default: md
    tokenRef: button.size

  variant:
    type: string
    enum: [primary, secondary, danger, ghost]
    default: primary

  disabled:
    type: boolean
    default: false

  loading:
    type: boolean
    default: false

  fullWidth:
    type: boolean
    default: false

  icon:
    type: string
    required: false

  iconPosition:
    type: string
    enum: [left, right]
    default: left

states:
  - default
  - hover
  - active
  - focus
  - disabled
  - loading

events:
  - name: click
    when: disabled == false && loading == false
    payload:
      event: MouseEvent

slots:
  - name: default
    description: 按钮文本内容
  - name: icon
    description: 自定义图标插槽

a11y:
  role: button
  focusable: true
  keyboard:
    - key: Enter
      event: click
    - key: Space
      event: click

tokens:
  - color.primary
  - color.primary.hover
  - color.danger
  - font.size.md
  - space.3
  - radius.md

variants:
  - name: icon-only
    description: 仅图标按钮
    props:
      icon: required

  - name: loading
    description: 加载中状态
    props:
      loading: true
      disabled: true

examples:
  - name: basic
    description: 基础用法
    props:
      variant: primary
    code: |
      <Button variant="primary">Submit</Button>

  - name: with-icon
    description: 带图标
    props:
      icon: check
      iconPosition: left
    code: |
      <Button icon="check">Confirm</Button>
```

## 与测试的映射

Component Contract 可自动生成以下测试：

| Contract 字段 | 生成的测试类型 |
|--------------|---------------|
| `props` | Props 类型校验测试 |
| `states` | 组件状态快照测试 |
| `events` | 事件触发单测 |
| `a11y.keyboard` | 键盘交互测试 |
| `a11y.role` | ARIA 角色验证 |
| `variants` | 变体渲染测试 |

## Storybook 映射

Component Contract 可自动生成 Storybook stories：

```typescript
// 自动生成的 stories
export default {
  title: 'Basic/PrimaryButton',
  component: PrimaryButton,
  argTypes: {
    size: { control: 'select', options: ['sm', 'md', 'lg'] },
    variant: { control: 'select', options: ['primary', 'secondary', 'danger', 'ghost'] },
    disabled: { control: 'boolean' },
    loading: { control: 'boolean' },
  },
};

export const Default = { args: { variant: 'primary' } };
export const WithIcon = { args: { icon: 'check', iconPosition: 'left' } };
export const Loading = { args: { loading: true } };
```

## 门禁规则

Dev Gate 会检查：
- [ ] 每个 `state` 必须有对应的样式实现
- [ ] `a11y.keyboard` 定义的快捷键必须实现
- [ ] `tokens` 引用的 token 必须存在
- [ ] Storybook 必须能正常构建
