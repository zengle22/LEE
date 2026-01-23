---
name: bug-flow
description: Bug 子流程 - 处理单个 Bug 的完整生命周期（创建→分流→诊断→修复→验证→关闭）
arguments:
  - name: action
    description: 操作类型：create, triage, debug, fix, verify, close, status
    required: true
  - name: bug_id
    description: Bug ID (格式: BUG-YYYY-NNNN)
    required: false
  - name: project_dir
    description: 项目目录路径
    required: false
---

# Bug 子流程命令

你正在执行 Bug 子流程，管理单个 Bug 的完整生命周期。

## 参数

**action**: $action
**bug_id**: $bug_id
**project_dir**: $project_dir (默认: 当前目录下的 testing/ 或 project/{项目名}/testing)

---

## 状态机

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           Bug 状态机                                    │
├────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│   NEW ──→ TRIAGED ──→ ROUTED ──→ DEBUGGED ──→ FIXING ──→ FIXED        │
│     │                                                                         │
│     ├────────────────→ BLOCKED_PM (需求争议)                              │
│     ├────────────────→ BLOCKED_HUMAN (安全/财务/法律)                      │
│     └────────────────→ BLOCKED_ENV (环境问题)                              │
│                                                                              │
│   FIXED ──→ VERIFYING ──→ VERIFIED ──→ CLOSED                             │
│                      │                                                      │
│                      └────────────────→ FIXING (验证失败)                │
│                                                                              │
└────────────────────────────────────────────────────────────────────────────┘
```

---

## 操作类型

### 1. create - 创建 Bug

从测试失败创建 Bug 契约。

```bash
/bug-flow create --project-dir "project/AI跑步教练/testing"
```

**自动收集信息**：
- 从 E2E 测试失败中提取证据
- 生成 Bug ID
- 创建 Bug 契约文件

**Bug 契约模板**：

```yaml
bug_id: "BUG-2026-0032"
title: "开发测试登录按钮在 H5 浏览器不可见"
severity: "P0"
category: "functional"
status: "new"

detected_in:
  round_id: "E2E-RUN-20260115-001"
  version: "v1.1.0"
  env: "test"
  test_suite: "e2e_chrome"
  test_case_id: "F-BASE-002"

evidence:
  reproduction_steps: |
    1. 打开浏览器访问 http://localhost:3002/#/pages/login/index
    2. 查找"开发测试登录"按钮
    3. 观察：按钮不可见

  screenshots:
    - "output/e2e/test-results/login-button-not-found.png"

  environment_details:
    browser: "Chromium H5"
    viewport: "375x667"
    user_agent: "Mozilla/5.0 (iPhone; CPU iPhone OS 14_0..."

routing:
  owner_team: "frontend"
  owner_agent: "frontend-developer"
```

---

### 2. triage - Bug 分流

补充复现步骤、定级、分配 owner。

```bash
/bug-flow triage BUG-2026-0032
```

**分流动作**：
1. 补充证据信息
2. 确定严重级别 (P0/P1/P2/P3)
3. 确定类别 (functional/performance/security/data/requirement/flaky/env)
4. 分配 owner

**分流规则**：

```yaml
分流决策:
  IF category == requirement:
    status = blocked_pm
    分配给 = pm_agent

  ELIF category IN [security, data_loss, payment]:
    status = blocked_human
    需要人工审批

  ELIF category IN [env, flaky]:
    status = blocked_env
    分配给 = platform_agent

  ELSE:
    status = routed
    分配给 = 对应开发团队
```

---

### 3. debug - Bug 诊断

P0/P1 Bug 自动触发 Debug Agent 分析根因。

```bash
/bug-flow debug BUG-2026-0032
```

**诊断流程**：

```yaml
debug_steps:
  - id: collect_logs
    name: "收集日志"
    收集:
      - 前端控制台日志
      - 后端 API 日志
      - 网络请求/响应

  - id: analyze_code
    name: "代码分析"
    分析:
      - 定位问题代码文件
      - 分析调用链路
      - 检查配置

  - id: root_cause
    name: "根因分析"
    输出:
      - root_cause: "..."
      - fix_plan: "..."
      - risk_area: "..."
      - confidence: "high/medium/low"
```

**诊断报告模板**：

```markdown
## Bug 诊断报告

### Bug 信息
- **Bug ID**: BUG-2026-0032
- **标题**: 开发测试登录按钮在 H5 浏览器不可见
- **严重级别**: P0

### 根本原因
\`\`\`
问题定位：git/ai-marathon-coach-front/src/pages/login/index.vue:42

原因：H5 条件编译指令 `<!-- #ifdef H5 -->` 的使用方式有问题，
     按钮被包裹在不正确的条件块中，导致在浏览器环境中被过滤掉。
\`\`\`

### 修复方案
\`\`\`diff
-  <!-- #ifdef H5 -->
-  <button v-if="isDev" @click="devLogin">开发测试登录</button>
-  <!-- #endif -->

+  <button v-if="isDev" class="dev-login-btn" @click="devLogin">
+    开发测试登录
+  </button>
\`\`\`

### 风险评估
- **影响范围**: 所有 E2E 测试
- **修复复杂度**: 低
- **回归风险**: 低
- **预估工时**: 0.5h

### 附件
- 代码定位: `git/ai-marathon-coach-front/src/pages/login/index.vue:42`
- 相关代码: `git/ai-marathon-coach-front/src/components/Login.vue`
```

---

### 4. fix - 修复 Bug

开发团队修复并提交代码。

```bash
/bug-flow fix BUG-2026-0032
```

**修复动作**：

```yaml
fix_steps:
  - id: implement_fix
    name: "实施修复"
    根据 diagnosis 的 fix_plan 修改代码

  - id: local_test
    name: "本地验证"
    - 编译通过
    - 单元测试通过

  - id: commit
    name: "提交代码"
    更新 Bug 契约:
      status: "fixed"
      fix:
        fix_commit: "abc123..."
        fix_version: "v1.1.0-hotfix"
        change_summary: "修复 H5 环境下开发测试登录按钮不显示问题"
```

---

### 5. verify - 验证修复

QA 团队验证修复效果。

```bash
/bug-flow verify BUG-2026-0032
```

**验证流程**：

```yaml
verify_steps:
  - id: get_fix_info
    name: "获取修复信息"
    从 Bug 契约读取:
      - fix_commit
      - fix_version
      - change_summary

  - id: deploy_fix
    name: "部署修复"
    部署新版本到测试环境

  - id: retest
    name: "回归测试"
    - 执行失败的测试用例
    - 执行相关回归测试

  - id: update_status
    name: "更新状态"
    IF 验证通过:
      status = "verified"
    ELSE:
      status = "fixing"  # 回退重新修复
```

**验证规则**：
- ✅ 原失败用例通过
- ✅ 无新引入的 P0/P1 问题
- ✅ 回归测试通过

---

### 6. close - 关闭 Bug

QA 关闭 Bug。

```bash
/bug-flow close BUG-2026-0032 --resolution fixed
```

**关闭条件**：

```yaml
关闭条件:
  fixed:
    验证通过，可以关闭

  by_design:
    产品确认为设计如此

  wont_fix:
    决定不修复

  duplicate:
    重复 Bug

  cannot_reproduce:
    无法复现
```

---

### 7. status - 查看状态

查看 Bug 当前状态和进度。

```bash
/bug-flow status BUG-2026-0032
```

**状态显示**：

```
┌────────────────────────────────────────────────────────────┐
│ Bug Status: BUG-2026-0032                                │
├────────────────────────────────────────────────────────────┤
│ 标题: 开发测试登录按钮在 H5 浏览器不可见              │
│ 状态: debugging                                           │
│ 严重级别: P0                                              │
│ 类别: functional                                          │
├────────────────────────────────────────────────────────────┤
│ 时间线:                                                  │
│   ✅ 2026-01-15 18:00  NEW     创建                    │
│   ✅ 2026-01-15 18:05  TRIAGED 分流                    │
│   ✅ 2026-01-15 18:10  ROUTED  分配给 frontend-developer  │
│   ⏳ 2026-01-15 18:15  DEBUGGING 诊断中...              │
├────────────────────────────────────────────────────────────┤
│ 当前处理: debug_agent                                     │
│ 负责人: frontend-developer                                │
└────────────────────────────────────────────────────────────┘
```

---

## 工作目录结构

```
testing/
├── bugs/
│   ├── BUG-2026-0032.contract.yaml    # Bug 契约
│   └── BUG-2026-0032/
│       ├── evidence/                   # 证据目录
│       ├── debug-report.md             # 诊断报告
│       ├── fix-plan.md                 # 修复计划
│       └── verification-report.md      # 验证报告
└── .workflow/
    ├── bug-state.yaml                 # Bug 状态跟踪
    └── bug-events.jsonl               # Bug 事件日志
```

---

## 使用示例

```bash
# 创建 Bug
/bug-flow create --project-dir "project/AI跑步教练/testing"

# 分流 Bug
/bug-flow triage BUG-2026-0032

# 诊断 Bug
/bug-flow debug BUG-2026-0032

# 修复 Bug
/bug-flow fix BUG-2026-0032

# 验证修复
/bug-flow verify BUG-2026-0032

# 关闭 Bug
/bug-flow close BUG-2026-0032 --resolution fixed

# 查看状态
/bug-flow status BUG-2026-0032
```

---

## 集成事件

Bug 状态变更会发出事件，可被主流程监听：

```yaml
events:
  - bug_created:
      when: "status == new"

  - bug_triaged:
      when: "status == triaged"

  - bug_routed:
      when: "status == routed"

  - bug_debugged:
      when: "status == debugged"

  - bug_fixed:
      when: "status == fixed"
      通知: "测试主流程继续"

  - bug_verified:
      when: "status == verified"

  - bug_closed:
      when: "status == closed"
```

---

## 相关资源

- Bug 契约规范: `ai-spec/specs/org/testing/contracts/bug-contract/v1/schema.yaml`
- Bug 子流程: `ai-spec/specs/org/testing/workflows/bug-sub-workflow/v1/workflow.yaml`
- Debug Agent: `ai-spec/cli/claude/agents/debug-agent.md`
