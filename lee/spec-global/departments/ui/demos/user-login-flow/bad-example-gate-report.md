# UI Gate 检查报告 - 反面案例

**项目**: Bad Example - 违反单主路径原则的设计
**日期**: 2026-02-06
**检查版本**: UI Gate v1.1

---

## 检查结果概要

| 指标 | 结果 |
|------|------|
| **总体状态** | ❌ **FAIL** |
| Blocker | 4 |
| Major | 2 |
| Minor | 1 |
| AI 友好度评分 | 35/100 |

---

## ❌ 阻断问题列表

### 1. single_main_path_verified [BLOCKER]

**问题**: 功能存在多条并行路径，违反单主路径原则

```yaml
# 错误设计 - 登录功能有3条并行主路径
main_path:
  steps:
    - id: step_choose_method
      action: "选择登录方式"  # ❌ V1禁止选择分支
      branches:
        - phone_login: "手机号登录"
        - password_login: "密码登录"
        - wechat_login: "微信登录"
```

**违反原则**: 第一原则 - 单主路径原则
> 任何功能在 V1 阶段，必须且只能存在一条可执行的主路径

**修复建议**:
```yaml
# 正确设计 - V1只保留一条主路径
main_path:
  steps:
    - id: step_1_phone
      action: "输入手机号"  # ✅ 只有一条路径
```

---

### 2. preconditions_at_entry [BLOCKER]

**问题**: 前置条件未在入口处解决，用户点进去才发现不能用

```yaml
# 错误设计
preconditions:
  - id: phone_verified
    condition: "user.phoneVerified == true"
    not_met_action: null  # ❌ 未定义处理方式
```

**用户体验**: 用户点击进入后看到"请先验证手机号"的错误弹窗

**违反原则**: 第三原则 - 前置条件入口处解决
> 条件不满足 → 不显示入口 或 显式引导
> 禁止：点进去才告诉你"不行"

**修复建议**:
```yaml
preconditions:
  - id: phone_verified
    condition: "user.phoneVerified == true"
    not_met_action: show_guide  # ✅ 引导用户去验证
    guide_to: page.verify_phone
    message_key: please_verify_phone_first
```

---

### 3. no_hidden_state [BLOCKER]

**问题**: 存在黑洞状态 - 用户卡在某个状态无法继续

```yaml
# 错误设计
states:
  - name: error
    errorCodes: [UNKNOWN_ERROR]
    messageKey: something_went_wrong
    # ❌ 没有定义恢复路径，用户只能刷新页面
```

**用户体验**: 用户看到"出错了"但不知道该怎么办

**违反原则**: 第二原则 - 状态不可隐含
> 不可执行态必须有：明确原因 + 明确下一步 + 回到主路径的方式

**修复建议**:
```yaml
recovery_paths:
  - error_state: UNKNOWN_ERROR
    recovery_action: retry
    message_key: unknown_error_retry
    cta_key: retry_button  # ✅ 提供明确的下一步
    max_retries: 3
```

---

### 4. ai_walkthrough_passed [BLOCKER]

**问题**: AI 盲跑验证失败，评分仅 35 分

```
AI 盲跑日志:
1. [OK] 进入首页，找到登录按钮
2. [OK] 点击登录按钮，进入登录页
3. [STUCK] 看到3个选项：手机登录、密码登录、微信登录
   → AI不知道选哪个，需要业务知识判断
   → 路径模糊，随机选择"密码登录"
4. [STUCK] 密码登录页要求输入账号
   → 但之前没有注册过，不知道账号是什么
   → 看到"忘记密码"链接，点击进入
5. [LOST] 进入忘记密码流程
   → 已经偏离登录主路径
   → AI 迷失在子流程中
```

**评分详情**:
| 维度 | 得分 | 问题 |
|------|------|------|
| 路径清晰度 | 20 | 存在分支选择，路径模糊 |
| 状态可见度 | 40 | 部分状态可识别 |
| 恢复完整度 | 30 | 多数错误无恢复路径 |
| 入口可达性 | 80 | 入口可见 |
| **总分** | **35** | **未达到80分阈值** |

**违反原则**: 第四原则 - AI 友好性
> 如果一个完全不理解业务意图的 AI，仅凭 UI 顺序就能跑通主路径，
> 那这个设计才是合格的

---

## ⚠️ 主要问题列表

### 5. blocked_patterns_defined [MAJOR]

**问题**: 未定义禁止的路径模式

```yaml
# 错误设计
blocked_patterns: []  # ❌ 空列表
```

**风险**: 用户可能在登录过程中跳转到其他功能，导致状态丢失

**修复建议**: 添加禁止模式定义

---

### 6. recovery_strategies_defined [MAJOR]

**问题**: 恢复策略不完整

```yaml
# 错误设计
recovery_strategies:
  - error_type: NETWORK_ERROR
    recovery_action: retry
# ❌ 缺少其他错误类型的恢复策略
```

**修复建议**: 为所有可能的错误定义恢复策略

---

## 问题根因分析

```
┌─────────────────────────────────────────────────────────┐
│                    设计问题根因                          │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  1. 过早引入分支逻辑                                     │
│     └── V1 阶段应该只保留最核心的一条路径                 │
│                                                         │
│  2. 假设用户理解系统                                     │
│     └── 点进去才告诉用户"不行"是糟糕的体验               │
│                                                         │
│  3. 没有考虑错误恢复                                     │
│     └── 每个错误状态都必须有明确的"下一步"               │
│                                                         │
│  4. 没有做 AI 盲跑测试                                   │
│     └── 如果 AI 走不通，说明设计不够清晰                 │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## 修复清单

| 优先级 | 问题 | 修复动作 | 负责人 |
|--------|------|----------|--------|
| P0 | 多路径分支 | 简化为单一手机号登录 | @designer |
| P0 | 前置条件 | 添加 not_met_action | @designer |
| P0 | 黑洞状态 | 添加 recovery_paths | @designer |
| P0 | AI盲跑失败 | 重新设计并验证 | @designer |
| P1 | 禁止模式 | 定义 blocked_patterns | @designer |
| P1 | 恢复策略 | 完善 recovery_strategies | @designer |

---

## 结论

| 检查项 | 状态 |
|--------|------|
| 可进入研发 | ❌ NO |
| 阻断问题 | 4 |
| 主要问题 | 2 |
| 需要修复 | **全部 blocker 必须修复** |

**最终决定**: ❌ **未通过 UI Gate，返回设计阶段修改**

---

## 设计宪法提醒

> **第一原则：单主路径原则**
> 任何功能在 V1 阶段，必须且只能存在一条可执行的主路径。
> **违反即视为设计缺陷，不进入实现阶段。**

> **好的 UE 不是"什么都顺滑"，而是"哪里不能顺滑，明确告诉你为什么"。**

---

*报告生成时间: 2026-02-06 10:40:00*
*检查器: gate.ui.ui_gate@v1.1*
