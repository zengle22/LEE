# WeChat Sandbox Runner Skill v1.0
# 微信小程序沙箱自动化技能

## 概述

微信小程序沙箱自动化技能负责在微信开发者工具中执行小程序 E2E 测试。
由于小程序自动化相对复杂，建议先从核心链路冒烟测试开始。

## 技能标识

- **ID**: skill.test.wechat_sandbox_runner
- **名称**: WeChat Sandbox Runner
- **版本**: 1.0
- **所有者**: test-governance

## 适用 Agent

- agent.test.e2e_test_executor

## 重要限制

```yaml
limitations:
  - "依赖微信开发者工具运行"
  - "需要登录态才能执行"
  - "CI 环境配置相对复杂"
  - "选择器稳定性较差"
  - "不支持所有浏览器 API"

recommendations:
  - "先跑通 Web/H5 E2E 作为基线"
  - "小程序先从冒烟级 E2E 开始 (5-10 条)"
  - "核心链路优先，非核心暂缓"
```

---

## 1. 环境准备

### 1.1 开发者工具配置

```yaml
devtools_config:
  version: "1.06.2401020"  # 推荐版本
  path:
    windows: "C:\\Program Files (x86)\\Tencent\\微信web开发者工具"
    mac: "/Applications/wechatwebdevtools.app"
    linux: "/opt/wechat_devtools"

  project:
    appid: "${WECHAT_APPID}"
    project_path: "${PROJECT_PATH}"

  cli:
    enabled: true
    port: 9420
```

### 1.2 自动化框架选择

```yaml
automation_frameworks:
  # 选项 1: 官方 miniprogram-automator
  miniprogram_automator:
    npm_package: "miniprogram-automator"
    pros:
      - "官方支持"
      - "API 相对稳定"
    cons:
      - "功能有限"
      - "调试困难"

  # 选项 2: Minium (腾讯出品)
  minium:
    npm_package: "@aspect-dev/minium"
    pros:
      - "功能更丰富"
      - "支持原生组件"
    cons:
      - "维护状态不确定"

  # 选项 3: 自定义 WebSocket 方案
  custom_ws:
    description: "通过开发者工具 WebSocket 接口控制"
    pros:
      - "灵活"
      - "可定制"
    cons:
      - "开发成本高"
      - "需要维护"

  recommended: "miniprogram_automator"
```

---

## 2. 核心能力

### 2.1 小程序启动

```yaml
launch:
  # 启动开发者工具
  start_devtools:
    project_path: "/path/to/miniprogram"
    appid: "${WECHAT_APPID}"

  # 等待编译完成
  wait_for_compile:
    timeout_ms: 60000

  # 进入指定页面
  navigate_to_page:
    path: "pages/index/index"
    query: "id=123"
```

### 2.2 页面操作

```yaml
page_actions:
  # 获取当前页面
  get_current_page:
    returns: "page_path"

  # 页面跳转
  navigate:
    path: "pages/detail/detail"
    method: "navigateTo"  # navigateTo | redirectTo | switchTab

  # 返回上一页
  navigate_back:
    delta: 1

  # 页面数据
  get_page_data:
    selector: null  # 获取整个 data
    path: "userInfo.name"  # 或指定路径
```

### 2.3 元素交互

```yaml
element_actions:
  # 元素定位 (小程序用 WXML 选择器)
  selectors:
    # 推荐: 自定义属性
    custom_attr: "//*[@data-testid='login-btn']"
    # 组件类型
    component: "button"
    # 类名
    class: ".submit-button"
    # 文本
    text: "登录"

  # 点击
  tap:
    selector: "[data-testid='login-btn']"

  # 输入
  input:
    selector: "[data-testid='phone-input']"
    value: "13800138000"

  # 滑动
  swipe:
    start: { x: 200, y: 500 }
    end: { x: 200, y: 200 }
    duration: 500

  # 长按
  long_press:
    selector: "[data-testid='item']"
    duration: 1000

  # 获取元素属性
  get_element:
    selector: "[data-testid='error-msg']"
    properties:
      - "textContent"
      - "style"
      - "data"
```

### 2.4 原生组件处理

```yaml
native_components:
  # 模态框
  modal:
    wait_for: "modal"
    action: "confirm"  # confirm | cancel

  # Toast
  toast:
    wait_for: "toast"
    get_content: true

  # ActionSheet
  action_sheet:
    wait_for: "actionSheet"
    select_index: 0

  # 选择器
  picker:
    type: "date"
    value: "2026-01-13"

  # 扫码 (mock)
  scan_code:
    mock_result:
      result: "https://example.com/qrcode/123"
      scan_type: "QR_CODE"
```

---

## 3. 登录态处理

### 3.1 Mock 登录

```yaml
mock_login:
  # 方法 1: 注入 Storage
  inject_storage:
    key: "token"
    value: "${TEST_TOKEN}"
    key: "userInfo"
    value: { "openId": "test_openid", "nickName": "测试用户" }

  # 方法 2: Mock wx.login
  mock_wx_login:
    code: "mock_code_123"
    # 后端需配合识别 mock code

  # 方法 3: 开发者工具登录态
  use_devtools_login:
    enabled: true
    # 需要在开发者工具中先登录
```

---

## 4. 证据采集

### 4.1 截图

```yaml
screenshot:
  # 页面截图
  page:
    path: "evidence/screenshots/{case_id}-{page}.png"

  # WXML 结构
  wxml_snapshot:
    path: "evidence/wxml/{case_id}-{page}.xml"
```

### 4.2 日志采集

```yaml
logs:
  # 小程序日志
  miniprogram_logs:
    path: "evidence/logs/{case_id}-mp.log"
    levels: ["error", "warn", "info"]

  # 网络请求
  network:
    path: "evidence/logs/{case_id}-network.json"
    capture:
      wx_request: true
      headers: true
      response: true
```

---

## 5. CI 集成

### 5.1 Docker 方案

```yaml
docker_ci:
  # 目前没有官方 Docker 镜像
  # 需要自建包含开发者工具的镜像
  challenges:
    - "开发者工具体积大"
    - "需要图形界面 (xvfb)"
    - "登录态管理困难"

  workaround:
    - "使用专用 CI 机器 (非 Docker)"
    - "或 Windows/Mac 构建节点"
```

### 5.2 推荐 CI 配置

```yaml
ci_config:
  # 使用专用 Windows/Mac Runner
  runner:
    type: "shell"
    os: "windows"
    tags: ["wechat-e2e"]

  # 定时运行 (避免频繁运行)
  schedule:
    cron: "0 6 * * *"  # 每天早上 6 点

  # 仅核心链路
  suite: "E2E-SUITE-WECHAT-SMOKE"
  max_cases: 10
```

---

## 6. 最佳实践

### 6.1 选择器策略

```yaml
selector_strategy:
  # 必须: 前端添加 data-testid
  required:
    - "所有可交互元素加 data-testid"
    - "列表项用 data-testid + data-index"

  # 示例
  wxml_example: |
    <button data-testid="submit-btn" bindtap="onSubmit">提交</button>
    <view wx:for="{{list}}" data-testid="item" data-index="{{index}}">
      {{item.name}}
    </view>
```

### 6.2 稳定性建议

- 冒烟用例控制在 10 条以内
- 避免复杂的多页面跳转
- Mock 掉不稳定的外部依赖
- 设置合理的等待时间

### 6.3 分阶段实施

```yaml
implementation_phases:
  phase_1:
    name: "基线"
    cases: 5
    scope: "登录 + 核心功能"

  phase_2:
    name: "扩展"
    cases: 15
    scope: "主流程覆盖"

  phase_3:
    name: "完善"
    cases: 30
    scope: "边界场景"
```

---

## 版本历史

| 版本 | 日期 | 变更说明 |
|------|------|----------|
| 1.0 | 2026-01-13 | 初始版本 |
