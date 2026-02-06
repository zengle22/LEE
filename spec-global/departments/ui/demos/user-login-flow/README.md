# Demo: 用户登录流程 - 单主路径原则演示

本目录演示 UI 部门 v1.1 规范升级后的完整工作流程。

## 文件清单

| 文件 | 说明 |
|------|------|
| `login.flow.yaml` | ✅ 用户流契约 - 定义单主路径 |
| `login-phone.page.yaml` | ✅ 手机号输入页面契约 |
| `login-verify.page.yaml` | ✅ 验证码输入页面契约 |
| `ai-walkthrough-report.json` | ✅ AI盲跑验证报告（通过） |
| `ui-gate-report.md` | ✅ UI Gate检查报告（通过） |
| `bad-example-gate-report.md` | ❌ 反面案例 - Gate失败报告 |

---

## 流程演示

### 1. 主路径定义

```
[首页]
   │
   ▼ click(login_button)
   │
[手机号页面] ── precondition: 未登录
   │
   ▼ click(get_code_button)
   │
[验证码页面] ── precondition: 已发送验证码
   │
   ▼ click(login_submit_button)
   │
[仪表盘] ── completion: 登录成功
```

### 2. 关键设计决策

| 决策点 | V1 选择 | 原因 |
|--------|---------|------|
| 登录方式 | 仅手机号+验证码 | 单主路径原则 |
| 前置条件 | 入口处redirect | 禁止点进去才失败 |
| 错误处理 | 每个错误有恢复路径 | 状态不可隐含 |
| 分支逻辑 | 无 | V1禁止分支 |

### 3. AI 盲跑验证

```
✅ AI 可仅凭 UI 顺序盲跑通过
✅ 每一步只有一个明确的下一步
✅ 所有状态可通过 UI 识别
✅ AI 友好度评分: 92/100
```

---

## 正反案例对比

### ✅ 正确设计

```yaml
# 单一路径，无分支
main_path:
  steps:
    - id: step_1_phone
      action: "输入手机号并获取验证码"
    - id: step_2_verify
      action: "输入验证码并登录"
  completion:
    state: success

# 前置条件在入口处解决
preconditions:
  - id: not_logged_in
    not_met_action: redirect  # ✅ 不满足就跳走
```

### ❌ 错误设计

```yaml
# 多路径分支
main_path:
  steps:
    - id: step_choose
      branches:  # ❌ V1禁止分支
        - phone_login
        - password_login
        - wechat_login

# 前置条件点进去才失败
preconditions:
  - id: phone_verified
    not_met_action: null  # ❌ 没有定义处理方式
```

---

## Gate 检查清单

### 必须通过（Blocker）

- [ ] `single_main_path_verified` - 只有一条主路径
- [ ] `preconditions_at_entry` - 前置条件入口处解决
- [ ] `no_hidden_state` - 无黑洞状态
- [ ] `ai_walkthrough_passed` - AI盲跑评分 >= 80

### 应该通过（Major）

- [ ] `blocked_patterns_defined` - 定义禁止模式
- [ ] `recovery_strategies_defined` - 定义恢复策略
- [ ] `ai_walkthrough_enabled` - 启用AI盲跑
- [ ] `paths_enumerable` - 路径可枚举

---

## 如何使用

### 1. 设计阶段

```bash
# 创建用户流契约
spec/ui/flows/xxx.flow.yaml

# 创建页面契约
spec/ui/pages/xxx.page.yaml
```

### 2. 验证阶段

```bash
# AI 盲跑验证
agent.ui.ai_walkthrough_validator

# UI Gate 检查
gate.ui.ui_gate@v1.1
```

### 3. 检查结果

- **通过**: 进入研发阶段
- **未通过**: 返回设计修改，直到所有 blocker = 0

---

## 核心理念

> **好的 UE 不是"什么都顺滑"，
> 而是"哪里不能顺滑，明确告诉你为什么"。**

> **如果 AI 走不通，说明设计不够清晰。**
