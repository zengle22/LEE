# Test Set Execute L3 流程说明

## 一、流程概述

**流程名称**: Test Set Execute L3（Test Set 执行流程）

**版本**: v1.3

**ID**: `template.qa.test_set_execute`

**职责**: 执行单个 Test Set，从用例生成到 Bug 起草

**所有者**: `qa-governance`

**标签**: `template`, `qa`, `test-set`, `execution`, `l3`

**核心设计原则**:
1. **治理层与执行层分离** - 根节点使用 `stages`（治理层），工作由 `stages[].steps` 执行（执行层）
2. **7 步执行流程** - 用例生成 → 脚本翻译 → 脚本执行 → 合规检查 → 结果判定 → TSE 组装 → Bug 起草
3. **角色隔离** - 执行器（Executor）与裁判（Judge）职责分离
4. **反作弊门禁** - 行为合规检查作为自动门禁

**注意**: 
- 此模板用于**执行**Test Set，不负责创建 Test Set
- Test Set 创建由 `test-set-production-l3-template` 负责
- Test Set 验证在 production 模板中进行
- 此模板验证执行产物（bugs、reports、evidence 等）

---

## 二、执行模式配置

| 模式 | 描述 | 合规失败处理 | 适用环境 |
|------|------|-------------|---------|
| **enforce**（强制） | 合规检查失败 = invalid_run，终止流程 | 终止 | 生产环境 |
| **warn**（警告） | 记录警告但继续执行 | 继续 | dev/test/local |

**环境变量**: `EXECUTION_MODE`

**生产环境强制**: `prod_enforce: true`

---

## 三、7 步执行流程

```
┌─────────────────────────────────────────────────────────────────┐
│                    Execution Pipeline (Stage)                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐                                               │
│  │ 1. Case      │ 从 Test Set 策略动态生成测试用例              │
│  │    Generation│                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ 2. Script    │ 将用例翻译为可执行脚本                        │
│  │    Translation│                                              │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ 3. Script    │ 通过 test_runner CLI 执行脚本（Executor 角色） │
│  │    Execution │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ 4. Behavior  │ 反作弊合规检查（强制门禁）                    │
│  │    Compliance│                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ 5. Result    │ 基于证据判定通过/失败（Judge 角色）           │
│  │    Judgment  │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ 6. TSE       │ 组装 Test Set Execution 文件                  │
│  │    Assembly  │                                               │
│  └──────┬───────┘                                               │
│         │                                                        │
│         ▼                                                        │
│  ┌──────────────┐                                               │
│  │ 7. Bug       │ 为失败用例起草 Bug（条件执行）                │
│  │    Drafting  │                                               │
│  └──────────────┘                                               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 四、详细步骤说明

### 步骤 1：Case Generation（用例生成）

| 属性 | 值 |
|------|-----|
| **ID** | `case_generation` |
| **类型** | Agent |
| **Agent** | `agent.qa.case_generator` |
| **依赖** | 无 |
| **强制性** | 是 |

**职责**: 从 Test Set 策略动态生成测试用例

**输出**:
- `cases_path` - 生成用例文件路径
- `cases_count` - 用例数量

---

### 步骤 2：Script Translation（脚本翻译）

| 属性 | 值 |
|------|-----|
| **ID** | `script_translation` |
| **类型** | Agent |
| **Agent** | `agent.qa.script_translator` |
| **依赖** | `case_generation` |
| **强制性** | 是 |

**职责**: 将测试用例翻译为可执行脚本（如 Playwright 代码）

**输出**:
- `scripts_dir` - 脚本目录路径
- `scripts_count` - 脚本数量

---

### 步骤 3：Script Execution（脚本执行）⭐

| 属性 | 值 |
|------|-----|
| **ID** | `script_execution` |
| **类型** | Skill |
| **Skill** | `skill.runner.test_e2e` |
| **依赖** | `script_translation` |
| **强制性** | 是 |
| **失败处理** | `continue_to_compliance`（继续到合规检查） |

**职责**: 通过 `test_runner` CLI 执行测试脚本

**角色约束（EXECUTOR）**:
- ✅ **允许**: 调用 test_runner、收集证据、报告执行输出
- ❌ **禁止**: 判定通过/失败、伪造错误、伪造执行

**输出**:
- `runner_output_path` - Runner 输出文件路径
- `evidence_dir` - 证据目录
- `runtime_errors` - 运行时错误列表
- `execution_status` - 执行状态

---

### 步骤 4：Behavior Compliance（行为合规检查）⭐⭐

| 属性 | 值 |
|------|-----|
| **ID** | `behavior_compliance` |
| **类型** | Skill |
| **Skill** | `skill.qa.behavior_compliance_checker` |
| **依赖** | `script_execution` |
| **强制性** | 是 |
| **门禁类型** | `auto_check`（自动检查） |

**职责**: 反作弊合规检查，**无论执行状态如何都必须执行**

**门禁逻辑**:
- ✅ **通过** → 进入结果判定
- ❌ **失败** → 标记 `invalid_run` 并终止流程

**5 项检查**:

| 检查项 | 类别 | 描述 | 严重性 |
|--------|------|------|--------|
| `ensure_evidence_for_critical_cases` | 证据完整性 | P0/P1 用例必须有 evidence_bundle | 错误 |
| `verify_no_unauthorized_mock` | 执行完整性 | 未检测到未授权 Mock | 错误 |
| `verify_runtime_errors_origin` | 执行完整性 | runtime_errors 必须来自 runner_cli/orchestrator/human | 错误 |
| `verify_executor_did_not_judge` | 角色合规 | Executor 角色不能判定通过/失败 | 错误 |
| `verify_execution_completeness` | 执行完整性 | 检查崩溃或超时 | 错误 |

**输出**:
- `compliance_result_path` - 合规结果文件路径
- `compliance_status` - 合规状态（pass/fail）
- `violations` - 违规列表

---

### 步骤 5：Result Judgment（结果判定）⭐

| 属性 | 值 |
|------|-----|
| **ID** | `result_judgment` |
| **类型** | Agent |
| **Agent** | `agent.qa.result_judge` |
| **依赖** | `behavior_compliance` |
| **强制性** | 是 |
| **人类门禁** | `gate.qa.result_judgment_review`（人工审核） |

**职责**: 基于证据判定通过/失败

**输入**:
- `runner_output` ← 步骤 3 的 `runner_output_path`
- `evidence_dir` ← 步骤 3 的 `evidence_dir`
- `expected_results` ← 步骤 1 的 `cases_path`

**角色约束（JUDGE）**:
- ✅ **允许**: 读取证据、判定通过/失败、写入结果
- ❌ **禁止**: 调用 test_runner、修改证据、伪造证据

**输出**:
- `results_path` - 结果文件路径
- `pass_count` - 通过数量
- `fail_count` - 失败数量
- `failures` - 失败详情

**人类门禁配置**:
- **类型**: `human_review`（人工审核）
- **超时**: 24 小时
- **审批人**: `qa_lead`
- **提示**: "请审核测试执行结果判定，确认基于证据的通过/失败判定正确"

---

### 步骤 6：TSE Assembly（TSE 组装）

| 属性 | 值 |
|------|-----|
| **ID** | `tse_assembly` |
| **类型** | Agent |
| **Agent** | `agent.qa.tse_assembler` |
| **依赖** | `result_judgment` |
| **强制性** | 是 |

**职责**: 组装 Test Set Execution（TSE）文件

**输出**:
- `tse_path` - TSE 文件路径

---

### 步骤 7：Bug Drafting（Bug 起草）

| 属性 | 值 |
|------|-----|
| **ID** | `bug_drafting` |
| **类型** | Agent |
| **Agent** | `agent.qa.bug_drafter` |
| **依赖** | `tse_assembly` |
| **强制性** | 是 |
| **执行条件** | `fail_count > 0` |

**职责**: 为失败用例起草 Bug（一个 Test Set 可能起草多个 Bug）

**输出**:
- `{{ tests_dir }}/qa/bugs/{{ test_run_id }}/` - Bug 草稿目录

---

## 五、证据包（Evidence Bundle）规范

### 结构定义

| 字段 | 类型 | 必填 | 描述 |
|------|------|------|------|
| `commands` | array | 否 | 执行的命令列表 |
| `logs` | string | 是 | 日志文件路径 |
| `screenshots` | array | 否 | 截图路径列表 |
| `video` | string | 否 | 录屏路径（可选） |
| `network_trace` | string | 否 | 网络追踪路径（可选） |
| `runner_result_ref` | string | 是 | runner-output.json 中的引用 |
| `exit_code` | integer | 否 | test_runner 退出码 |
| `stderr` | string | 否 | 标准错误输出 |

### 完整性规则

| 用例等级 | 必填字段 | 可选字段 |
|---------|---------|---------|
| **P0** | logs, runner_result_ref, screenshots | video, network_trace |
| **P1** | logs, runner_result_ref | screenshots |
| **P2/P3** | runner_result_ref | logs, screenshots |

**规则**: 无 evidence_bundle = `invalid_run`

---

## 六、人类门禁配置

### Result Judgment Review（结果判定审核）

| 属性 | 值 |
|------|-----|
| **Gate ID** | `gate.qa.result_judgment_review` |
| **类型** | `human_review`（人工审核） |
| **超时** | 24 小时 |
| **审批人** | `qa_lead` |
| **提示** | "请审核测试执行结果判定，确认基于证据的通过/失败判定正确" |

**说明**:
- 这是流程中**唯一**的人类门禁
- 位于结果判定步骤之后，确保 AI 判定的通过/失败结果正确
- 其他步骤（用例生成、脚本翻译、脚本执行、合规检查、TSE 组装、Bug 起草）均为自动执行

---

## 七、invalid_run 原因枚举

| 原因 ID | 描述 | 建议 |
|--------|------|------|
| `missing_critical_evidence` | P0/P1 用例缺少 evidence_bundle | 检查 Runner 是否崩溃或环境问题 |
| `unauthorized_mock_detected` | 检测到未授权的 Mock 使用 | 检查 `case.meta.allow_mock` 标志 |
| `invalid_error_origin` | runtime_errors 来源不合规 | 检查错误来源是否符合要求 |
| `executor_role_violation` | Executor 步骤超出角色边界 | 检查角色约束执行 |
| `execution_incomplete` | Runner 崩溃或超时 | 检查环境稳定性 |
| `evidence_tampered` | 证据在生成后被修改 | 检查证据完整性 |

---

## 八、反作弊约束（Anti-Mock Constraints）

| 约束 | 规则 | 违规动作 | invalid_run 原因 |
|------|------|-----------|-----------------|
| **禁止 Mock 执行** | 除非 `case.meta.allow_mock == true`，否则 AI 不能使用 Mock | invalid_run | `unauthorized_mock_detected` |
| **证据要求** | 所有 P0/P1 用例必须有 evidence_bundle | invalid_run | `missing_critical_evidence` |
| **禁止伪造错误** | runtime_errors 只能来自 runner_cli/orchestrator/human | invalid_run | `invalid_error_origin` |
| **Executor 不能判定** | script_execution 步骤不能判定通过/失败 | invalid_run | `executor_role_violation` |
| **Judge 不能重执行** | result_judgment 步骤不能调用 test_runner | invalid_run | `executor_role_violation` |
| **执行完整性** | Runner 必须完成执行（不能崩溃/超时） | invalid_run | `execution_incomplete` |

**执行者**: `behavior_compliance_checker`

---

## 十、可观测性（Observability）

### 指标（Metrics）

| 指标名称 | 类型 | 描述 | 标签 |
|---------|------|------|------|
| `l3_execution_duration` | Histogram | L3 流程执行时长（秒） | test_set_id, status |
| `compliance_check_duration` | Histogram | 合规检查时长 | check_id, result |
| `invalid_run_total` | Counter | invalid_run 总数 | invalid_run_reason, test_set_id, execution_mode |
| `evidence_bundle_size` | Histogram | 证据包大小（字节） | case_level |

### 追踪（Tracing）

| Span 名称 | 描述 | 起始步骤 | 结束步骤 | 属性 |
|----------|------|---------|---------|------|
| `l3_execution` | 完整 L3 流程执行 | case_generation | bug_drafting | test_set_id, environment |
| `compliance_validation` | 合规检查 | behavior_compliance | result_judgment | compliance_status, violations_count |

---

## 十一、Instance Schema

### 必填字段
- `id` - 实例 ID
- `template_id` - 模板 ID
- `name` - 实例名称
- `status` - 状态
- `test_set_id` - Test Set ID
- `parent_l2_id` - 父级 L2 ID
- `parent_phase_id` - 父级 Phase ID

### 上下文字段
- `test_run_id` - Test Run ID
- `test_set_id` - Test Set ID
- `test_set_definition` - Test Set 定义
- `build_version` - 构建版本
- `build_commit` - Git Commit
- `environment` - 测试环境
- `env_check_result` - 环境检查结果
- `dependency_results` - 依赖检查结果
- `execution_mode` - 执行模式

### 输出字段
- `test_set_id` - Test Set ID
- `status` - 最终状态
- `invalid_run_reason` - invalid_run 原因（如果有）
- `tse_path` - TSE 文件路径
- `results_summary` - 结果摘要
- `bug_drafts` - Bug 草稿列表
- `skip_reason` - 跳过原因（如果有）
- `failure_reason` - 失败原因（如果有）
- `compliance_result_path` - 合规结果路径

---

## 十二、流程状态流转图

```
                    ┌─────────────┐
                    │     INIT    │
                    └──────┬──────┘
                           │
                           ▼
              ┌────────────────────────┐
              │   1. Case Generation   │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │  2. Script Translation │
              └───────────┬────────────┘
                          │
                          ▼
              ┌────────────────────────┐
              │   3. Script Execution  │──────┐
              │    (Executor Role)     │      │ 失败
              └───────────┬────────────┘      │
                          │                   │
                          ▼                   │
              ┌────────────────────────┐      │
              │ 4. Behavior Compliance │◄─────┘
              │     (Auto Check)       │
              └───────────┬────────────┘
                          │
           ┌──────────────┴──────────────┐
           │                             │
           ▼ 通过                        ▼ 失败
┌────────────────────────┐    ┌─────────────────────┐
│  5. Result Judgment    │    │  Mark invalid_run   │
│    (Judge Role)        │    │  + Abort Workflow   │
│  Gate: human_review    │    └─────────────────────┘
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│   6. TSE Assembly      │
└───────────┬────────────┘
            │
            ▼
┌────────────────────────┐
│   7. Bug Drafting      │───┐
│  (if fail_count > 0)   │   │ 无条件
└───────────┬────────────┘   │
            │                │
            └────────────────┘
            │
            ▼
┌────────────────────────┐
│ 8. Output Validation   │
│    (Auto + Human)      │
│  Gate: human_review    │
└───────────┬────────────┘
            │
     ┌──────┴──────┐
     │             │
     ▼ 通过        ▼ 失败
┌─────────────┐  ┌─────────────┐
│  COMPLETED  │  │    FAILED   │
└─────────────┘  └─────────────┘
```

---

## 十三、关键设计要点

### 1. 角色隔离（Role Separation）

**Executor（执行器）**:
- 只能调用 `test_runner` 和收集证据
- 不能判定通过/失败
- 失败后继续到合规检查（不立即终止）

**Judge（裁判）**:
- 只能读取证据并判定
- 不能调用 `test_runner` 或修改证据
- 在合规检查通过后才能执行

### 2. 强制合规门禁（Mandatory Compliance Gate）

- 无论执行成功或失败，**必须**经过合规检查
- 合规失败直接标记 `invalid_run` 并终止
- 防止 AI 伪造执行结果或跳过执行

### 3. 证据完整性（Evidence Integrity）

- 每个用例执行必须产生 evidence_bundle
- P0/P1 用例的证据要求更严格
- 无证据 = `invalid_run`

### 4. 条件执行（Conditional Execution）

- Bug Drafting 仅在 `fail_count > 0` 时执行
- 其他步骤均为强制性

---

## 十四、相关文件

- **模板位置**: `spec-global/departments/qa/workflows/templates/test-set-l3-template.yaml`
- **关联 Agent**:
  - `agent.qa.case_generator` - 用例生成
  - `agent.qa.script_translator` - 脚本翻译
  - `agent.qa.result_judge` - 结果判定
  - `agent.qa.tse_assembler` - TSE 组装
  - `agent.qa.bug_drafter` - Bug 起草
  - `agent.qa.output_validator` - 输出验证 ⭐
- **关联 Skill**:
  - `skill.runner.test_e2e` - E2E 测试执行
  - `skill.qa.behavior_compliance_checker` - 行为合规检查
- **关联 Contract**:
  - `spec-global/departments/qa/contracts/test-set/v1/schema.yaml` - Test Set Schema
- **关联人类门禁**:
  - `gate.qa.result_judgment_review` - 结果判定审核
  - `gate.qa.output_validation` - 输出验证 ⭐

---

*文档由 LEE 框架自动生成 | 最后更新：2026-03-05*
