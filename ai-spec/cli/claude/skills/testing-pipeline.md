# Testing Pipeline Skill

> 测试流水线执行技能 - 接收研发交付包，执行完整测试流程，输出测试报告

## 概述

这个 Skill 用于执行测试流水线，作为 Development Pipeline 的下游。接收研发交付物，通过冒烟测试、E2E测试、系统测试等多阶段验证，保障产品交付质量。

## 触发命令

```
/run-testing <project_dir> [options]
```

## 核心原则

### 1. 提测包驱动

- 必须有完整的 release-manifest.yaml
- 缺失必要文件立即打回研发
- 所有测试基于提测清单执行

### 2. 门禁严格

- 冒烟测试 100% 通过才能进入后续测试
- E2E P0 用例 100% 通过
- P0 Bug 必须归零才能出测

### 3. 契约式 Bug 管理

- 所有 Bug 必须符合 Bug 契约格式
- P0/P1 Bug 自动触发 Debug Agent 诊断
- Bug 修复后必须回归验证

---

## 输入定义：研发交付包 (Release Package)

### 必需文件清单

研发团队必须提交以下文件，缺一不可：

```yaml
release-manifest.yaml           # 提测包清单 (入口文件)
```

### release-manifest.yaml 结构

```yaml
# 研发交付包清单
version: "1.0"
manifest_id: "MAN-YYYY-NNNN"

# 基本信息
metadata:
  project: <项目名>
  version: <版本号>
  build_id: <构建ID>
  release_date: <提测日期>
  submitted_by: <提交人>

# 构建产物
artifacts:
  - type: frontend
    path: <前端产物路径>
    hash: <SHA256>
  - type: backend
    path: <后端产物路径>
    hash: <SHA256>
  - type: database
    path: <数据库脚本路径>
    hash: <SHA256>

# 变更范围
changes:
  features:
    - id: FEAT-001
      description: <新功能描述>
      affected_modules: [<模块列表>]
  bugfixes:
    - id: BUG-001
      description: <修复描述>
      affected_modules: [<模块列表>]

# 依赖项
dependencies:
  upstream_gate:
    ref: gate.dev.release_gate
    status: passed
    approved_at: <审批时间>
    approved_by: <审批人>

# 测试要求
test_requirements:
  smoke_cases: "test-cases/smoke/"
  e2e_cases: "test-cases/e2e/"
  system_cases: "test-cases/system/"
  regression_cases: "test-cases/regression/"

# 环境配置
environment:
  test_env_url: <测试环境URL>
  db_connection: <数据库连接>
  external_services: [<外部服务配置>]

# 签名
signatures:
  dev_lead:
    name: <开发负责人>
    signed_at: <签名时间>
```

### 必需目录结构

```
{project}/testing/
├── release-manifest.yaml       # 入口文件 (必需)
│
├── test-cases/                 # 测试用例 (必需)
│   ├── smoke/                  # 冒烟用例
│   │   └── smoke-suite.yaml
│   ├── e2e/                    # E2E 测试用例
│   │   ├── chrome/             # Chrome 浏览器 E2E
│   │   │   ├── e2e-suite.yaml  # E2E 用例集定义
│   │   │   └── pages/          # Page Object 模型
│   │   └── wechat/             # 微信小程序 E2E (可选)
│   │       ├── e2e-suite.yaml
│   │       └── pages/
│   ├── system/                 # 系统测试用例
│   │   └── system-suite.yaml
│   └── regression/             # 回归用例
│       └── regression-suite.yaml
│
└── artifacts/                  # 构建产物 (必需)
    └── ...                     # 根据 manifest 引用
```

### 必需前置条件

| 条件 | 验证方法 | 失败处理 |
|------|---------|---------|
| release-manifest.yaml 存在 | 文件检查 | 立即打回 |
| 构建产物完整 | hash 校验 | 立即打回 |
| 冒烟用例已准备 | 目录检查 | 立即打回 |
| upstream gate 通过 | 状态检查 | 立即打回 |
| dev_lead 已签名 | 签名检查 | 立即打回 |

---

## 输出定义：测试报告 (Test Report)

### 主输出文件

```yaml
output/test-report.yaml         # 测试报告 (主输出)
```

### test-report.yaml 结构

```yaml
# 测试报告
version: "1.0"
report_id: "RPT-YYYY-NNNN"

# 基本信息
metadata:
  manifest_id: <对应的提测包ID>
  project: <项目名>
  version: <版本号>
  test_period:
    start: <测试开始时间>
    end: <测试结束时间>
  generated_at: <报告生成时间>

# 测试摘要
summary:
  verdict: PASS | CONDITIONAL_PASS | FAIL
  overall_pass_rate: <整体通过率>
  risk_level: LOW | MEDIUM | HIGH | CRITICAL

# 各阶段结果
stages:
  submission:
    status: PASS | FAIL
    reviewed_at: <审核时间>
    reviewer: <审核人>
    issues: []

  smoke_test:
    status: PASS | FAIL
    pass_rate: <通过率>
    total_cases: <用例数>
    passed: <通过数>
    failed: <失败数>
    duration_minutes: <耗时>

  e2e_test:
    platforms:
      chrome:
        status: PASS | CONDITIONAL_PASS | FAIL
        p0_pass_rate: <P0通过率>
        p1_pass_rate: <P1通过率>
        overall_pass_rate: <整体通过率>
        evidence_path: "output/e2e/evidence/chrome/"
      wechat:  # 可选
        status: PASS | SKIPPED
        ...
    aggregate_status: PASS | CONDITIONAL_PASS | FAIL

  system_test:
    status: PASS | CONDITIONAL_PASS | FAIL
    pass_rate: <通过率>
    total_cases: <用例数>
    passed: <通过数>
    failed: <失败数>
    by_module:
      - module: <模块名>
        pass_rate: <通过率>

  regression_test:
    status: PASS | FAIL
    pass_rate: <通过率>
    bug_verification:
      verified: <已验证数>
      reopened: <重开数>

# 缺陷统计
bugs:
  total: <总数>
  by_severity:
    P0: { open: 0, closed: <数量> }
    P1: { open: <数量>, closed: <数量> }
    P2: { open: <数量>, closed: <数量> }
    P3: { open: <数量>, closed: <数量> }
  diagnosis_summary:
    diagnosed_count: <诊断数>
    fix_success_rate: <修复成功率>

# 出测标准
exit_criteria:
  p0_open: { required: 0, actual: <实际值>, status: PASS|FAIL }
  p1_open_max: { required: 3, actual: <实际值>, status: PASS|FAIL }
  smoke_pass_rate: { required: 100, actual: <实际值>, status: PASS|FAIL }
  e2e_p0_pass_rate: { required: 100, actual: <实际值>, status: PASS|FAIL }
  core_path_pass_rate: { required: 100, actual: <实际值>, status: PASS|FAIL }
  regression_pass_rate: { required: 95, actual: <实际值>, status: PASS|FAIL }

# 风险项
risks:
  - id: RISK-001
    description: <风险描述>
    severity: HIGH | MEDIUM | LOW
    mitigation: <规避措施>
    accepted: true | false
    accepted_by: <接受人>

# 签名
signatures:
  qa_lead:
    name: <QA负责人>
    verdict: APPROVE | REJECT
    signed_at: <签名时间>
    comments: <备注>
  pm:
    name: <产品负责人>
    verdict: APPROVE | REJECT
    signed_at: <签名时间>
  tech_lead:
    name: <技术负责人>
    verdict: APPROVE | REJECT
    signed_at: <签名时间>
```

### 完整输出目录结构

```
{project}/testing/output/
├── submission-review.yaml      # 提测包审核结果
├── env-status.yaml             # 环境状态
├── test-readiness.yaml         # 测试就绪状态
│
├── smoke-test-result.yaml      # 冒烟测试结果
│
├── e2e/                        # E2E 测试输出
│   ├── chrome-report.json      # Chrome E2E 报告
│   ├── wechat-report.json      # 微信 E2E 报告 (可选)
│   ├── e2e-summary.yaml        # E2E 汇总
│   ├── regression-report.json  # E2E 回归报告
│   └── evidence/               # E2E 证据
│       ├── chrome/
│       │   ├── screenshots/
│       │   ├── videos/
│       │   ├── traces/
│       │   └── logs/
│       └── wechat/
│
├── system-test-result.yaml     # 系统测试结果
├── regression-result.yaml      # 回归测试结果
│
├── debug/                      # Debug Agent 输出
│   ├── triage-result.yaml      # 诊断分流
│   ├── audit/queries.log       # 审计日志
│   └── BUG-YYYY-NNNN/          # 每个 Bug 的诊断
│       ├── debug-report.json   # 机器可读报告
│       ├── debug-report.md     # 人类可读报告
│       ├── patch-draft.patch   # 修复建议
│       └── regression-checklist.md  # 回归清单
│
├── test-report.yaml            # 最终测试报告 (主输出)
├── exit-gate-result.yaml       # 出测门禁结果
│
└── release-frozen/{version}/   # 归档 (冻结)
    └── ...
```

---

## 执行流程

### Stage 1: 研发转测 (t1_submission)

**目标**: 验证提测包完整性

```bash
# 1. 检查 manifest 文件
python -m orchestrator start $TEST_DIR t1_1_manifest_review --agent release_manifest_reviewer

# 2. 验证内容
- 检查必需文件存在性
- 校验 artifact hash
- 验证 upstream gate 状态
- 检查签名完整性

# 3. 输出
output/submission-review.yaml
```

**门禁**: 任何缺失立即打回研发

### Stage 2: 测试准备 (t2_preparation)

**目标**: 准备测试环境

```bash
# 1. 部署测试环境
python -m orchestrator start $TEST_DIR t2_1_env_setup --agent test_env_deployer

# 2. 确认用例就绪
python -m orchestrator start $TEST_DIR t2_2_test_cases_ready --agent test_report_generator

# 3. 输出
output/env-status.yaml
output/test-readiness.yaml
```

### Stage 3: 冒烟测试 (t3_smoke_test)

**目标**: 快速验证核心功能可用

```bash
# 1. 执行冒烟测试
python -m orchestrator start $TEST_DIR t3_1_smoke_execution --agent smoke_test_executor

# 2. 输出
output/smoke-test-result.yaml
```

**门禁**: 100% 通过才能继续，否则打回研发

### Stage 4: E2E 端到端测试 (t4_e2e_test)

**目标**: 验证真实用户场景

```bash
# 1. Chrome E2E (并行)
python -m orchestrator start $TEST_DIR t4_1_e2e_chrome_execution --agent e2e_test_executor

# 2. 微信小程序 E2E (可选，并行)
python -m orchestrator start $TEST_DIR t4_2_e2e_wechat_execution --agent e2e_test_executor

# 3. 汇总
python -m orchestrator start $TEST_DIR t4_3_e2e_aggregate --agent test_report_generator

# 4. 输出
output/e2e/chrome-report.json
output/e2e/wechat-report.json
output/e2e/e2e-summary.yaml
output/e2e/evidence/
```

**门禁标准**:
- P0 通过率 = 100%
- P1 通过率 >= 90%
- 整体通过率 >= 80%

### Stage 5: 系统测试 (t5_system_test)

**目标**: 全面功能验证

```bash
# 1. 执行系统测试
python -m orchestrator start $TEST_DIR t5_1_system_execution --agent system_test_executor

# 2. 缺陷分类
python -m orchestrator start $TEST_DIR t5_2_bug_triage --agent bug_manager

# 3. 输出
output/system-test-result.yaml
bugs/*.yaml
```

### Stage 6: 缺陷诊断 (t6_bug_diagnosis)

**目标**: P0/P1 Bug 根因分析

**触发条件**:
- 存在 P0/P1 Bug
- Bug 无法复现
- 同类 Bug >= 3 个
- Bug 被重开

```bash
# 1. 诊断分流
python -m orchestrator start $TEST_DIR t6_1_diagnosis_triage --agent bug_manager

# 2. Debug Agent 分析
python -m orchestrator start $TEST_DIR t6_2_debug_analysis --agent debug_agent

# 3. 人工审核 (P0/P1)
python -m orchestrator approve $TEST_DIR h4_diagnosis_review --approver <name>

# 4. 交接开发
python -m orchestrator start $TEST_DIR t6_4_handoff_to_dev

# 5. 输出
output/debug/{bug_id}/debug-report.json
output/debug/{bug_id}/debug-report.md
output/debug/{bug_id}/patch-draft.patch
output/debug/{bug_id}/regression-checklist.md
```

### Stage 7: 缺陷修复循环 (t7_bug_fix_cycle)

**目标**: 验证修复效果

```bash
# 循环执行直到 Bug 归零或达到最大轮次
while open_bugs > 0 && cycle < 5:
    # 1. 等待修复版本
    # 2. 部署修复
    # 3. E2E 回归
    # 4. 系统回归
    # 5. 验证修复

# 输出
output/regression-result.yaml
```

### Stage 8: 出测审核 (t8_exit_review)

**目标**: 检查出测标准

```bash
# 1. 生成测试报告
python -m orchestrator start $TEST_DIR t8_1_generate_report --agent test_report_generator

# 2. 出测门禁
python -m orchestrator start $TEST_DIR t8_2_exit_gate --agent release_gate_reviewer

# 3. 签字确认 (人工)
python -m orchestrator approve $TEST_DIR h3_final_signoff --approver <qa_lead>
python -m orchestrator approve $TEST_DIR h3_final_signoff --approver <pm>
python -m orchestrator approve $TEST_DIR h3_final_signoff --approver <tech_lead>

# 输出
output/test-report.yaml
output/exit-gate-result.yaml
```

**出测标准**:
| 指标 | 要求 |
|------|------|
| P0 开放数 | 0 |
| P1 开放数 | <= 3 |
| 冒烟通过率 | 100% |
| E2E P0 通过率 | 100% |
| E2E P1 通过率 | >= 90% |
| 核心路径通过率 | 100% |
| 回归通过率 | >= 95% |
| 风险已记录 | true |

### Stage 9: 交付 (t9_release)

**目标**: 归档并通知

```bash
# 1. 归档测试资产
python -m orchestrator start $TEST_DIR t9_1_archive --agent test_report_generator

# 2. 通知发布
python -m orchestrator start $TEST_DIR t9_2_notify

# 输出
output/release-frozen/{version}/
```

---

## 人工门禁点

| ID | 目的 | 阻塞 | 超时 |
|----|------|------|------|
| h1_bug_review | 审核缺陷分类 | 否 | 24h (自动继续) |
| h4_diagnosis_review | 审核诊断结果 | 是 (P0/P1) | 4h (升级) |
| h2_risk_acceptance | 确认风险接受 | 是 | 48h (升级) |
| h3_final_signoff | 最终签字 | 是 | 72h (升级) |

---

## 自动继续规则

当 `orchestrator status` 显示以下条件时，**必须立即自动继续**：

```yaml
next_step_human_gate: false
action: continue
```

只有以下情况才允许停下：
- `next_step_human_gate: true`
- `action: wait_for_approval`
- 遇到技术错误

---

## 错误处理

| 场景 | 处理 |
|------|------|
| 冒烟失败 | 立即打回研发，不进入后续测试 |
| 环境不可用 | 等待重试，最长 4h |
| Bug 修复超时 | 升级 PM |
| 出测门禁失败 | 继续 Bug 修复循环 |

---

## 使用示例

### 基本用法

```bash
# 执行测试流水线
/run-testing project/AI跑步教练/testing
```

### 指定选项

```bash
# 跳过微信小程序测试
/run-testing project/AI跑步教练/testing --skip-wechat

# 仅执行冒烟测试
/run-testing project/AI跑步教练/testing --smoke-only

# 从指定阶段继续
/run-testing project/AI跑步教练/testing --resume-from t5_system_test
```

---

## 相关资源

- 工作流定义: `ai-spec/specs/org/testing/workflows/testing-pipeline/v1/workflow.yaml`
- 测试类型定义: `ai-spec/specs/org/testing/concepts/test-types/v1/concept.md`
- Bug 契约: `ai-spec/specs/org/testing/contracts/bug-contract/v1/schema.json`
- 测试报告契约: `ai-spec/specs/org/testing/contracts/test-report/v1/schema.json`
