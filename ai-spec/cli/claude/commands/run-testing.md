---
name: run-testing
description: 测试流水线 - 接收研发交付包执行完整测试流程，输出测试报告
arguments:
  - name: project_dir
    description: 项目测试目录路径（包含 release-manifest.yaml 的目录）
    required: false
  - name: options
    description: 可选参数：--skip-wechat, --smoke-only, --resume-from <step>
    required: false
---

# 测试流水线命令

你正在执行测试流水线，作为研发流程的下游，负责验证研发交付物的质量。

## 参数

**project_dir**: $project_dir
**options**: $options

---

## 执行流程

### 1. 如果 project_dir 为空

询问用户提供测试目录：

```
🧪 测试流水线 (Testing Pipeline)

请提供包含 release-manifest.yaml 的测试目录路径。

示例:
/run-testing project/AI跑步教练/testing
/run-testing project/MyApp/testing --skip-wechat
```

### 2. 如果 project_dir 有值

执行测试流水线：

#### Step 1: 验证提测包

**检查必需文件**:

```yaml
必需文件:
  - release-manifest.yaml      # 提测包清单
  - test-cases/smoke/          # 冒烟用例
  - test-cases/e2e/chrome/     # Chrome E2E 用例
  - test-cases/system/         # 系统测试用例
```

**验证 release-manifest.yaml 内容**:

```yaml
验证项:
  - manifest_id 存在且格式正确
  - artifacts 列表非空且 hash 有效
  - dependencies.upstream_gate.status == "passed"
  - signatures.dev_lead 存在
```

**失败处理**:

```
❌ 提测包验证失败

缺失文件:
- [列出缺失文件]

验证失败项:
- [列出失败验证项]

请补充完整后重新提交。
```

#### Step 2: 初始化 Orchestrator

```bash
# 初始化工作流
python -m orchestrator init "$PROJECT_DIR" \
  --workflow ai-spec/specs/org/testing/workflows/testing-pipeline/v1/workflow.yaml

# 检查状态
python -m orchestrator status "$PROJECT_DIR"
```

#### Step 3: 执行测试阶段

依次执行以下阶段：

| Stage | 名称 | 门禁 | 失败处理 |
|-------|------|------|----------|
| t1 | 研发转测 | submission_gate | 打回研发 |
| t2 | 测试准备 | - | 等待环境 |
| t3 | 冒烟测试 | smoke_gate (100%) | 打回研发 |
| t4 | E2E 测试 | e2e_gate (P0=100%) | 进入修复 |
| t5 | 系统测试 | - | 记录 Bug |
| t6 | 缺陷诊断 | diagnosis_review | 等待审核 |
| t7 | 修复循环 | - | 循环至通过 |
| t8 | 出测审核 | exit_gate + signoff | 循环修复 |
| t9 | 交付 | - | 归档通知 |

**自动继续规则**:

```yaml
# 检查状态后
if next_step_human_gate == false && action == "continue":
  # 立即执行下一步，不询问用户
  orchestrator start $PROJECT_DIR <next_step>
```

#### Step 4: 输出测试报告

完成后输出摘要：

```markdown
## 测试流水线完成

### 基本信息
| 项目 | 值 |
|------|-----|
| 项目 | <项目名> |
| 版本 | <版本号> |
| 提测包 | <manifest_id> |
| 测试周期 | <开始> ~ <结束> |

### 测试结果
| 阶段 | 状态 | 通过率 |
|------|------|--------|
| 冒烟测试 | PASS | 100% |
| E2E 测试 | PASS | 95% |
| 系统测试 | PASS | 92% |
| 回归测试 | PASS | 98% |

### 缺陷统计
| 级别 | 发现 | 关闭 | 遗留 |
|------|------|------|------|
| P0 | 2 | 2 | 0 |
| P1 | 5 | 4 | 1 |
| P2 | 8 | 6 | 2 |
| P3 | 3 | 1 | 2 |

### 出测判定
**结论**: PASS / CONDITIONAL_PASS / FAIL

### 输出文件
- 测试报告: output/test-report.yaml
- 门禁结果: output/exit-gate-result.yaml
- 归档目录: output/release-frozen/{version}/
```

---

## 可选参数处理

### --skip-wechat

跳过微信小程序 E2E 测试：

```bash
python -m orchestrator start $PROJECT_DIR t4_1_e2e_chrome_execution --agent e2e_test_executor
# 跳过 t4_2_e2e_wechat_execution
python -m orchestrator skip $PROJECT_DIR t4_2_e2e_wechat_execution --reason "User requested skip"
```

### --smoke-only

仅执行冒烟测试：

```bash
# 执行 t1 ~ t3
# 在 t3 完成后停止
python -m orchestrator pause $PROJECT_DIR --after t3_2_smoke_decision
```

### --resume-from <step>

从指定步骤继续：

```bash
python -m orchestrator resume $PROJECT_DIR --from <step>
```

---

## 人工介入点

### 1. 缺陷审核 (h1_bug_review)

```
📋 缺陷审核

发现 {bug_count} 个缺陷需要审核。

查看:
- bugs/*.yaml

审批命令:
  python -m orchestrator approve $PROJECT_DIR h1_bug_review --approver <name>

自动继续: 24h 后自动通过
```

### 2. 诊断审核 (h4_diagnosis_review)

```
🔍 诊断结果审核

P0/P1 缺陷诊断完成，需要人工确认。

审核内容:
- output/debug/{bug_id}/debug-report.md
- output/debug/{bug_id}/patch-draft.patch

审批命令:
  python -m orchestrator approve $PROJECT_DIR h4_diagnosis_review --approver <name>

操作选项:
- approve: 确认诊断，交接开发
- adjust: 调整诊断结论
- escalate: 升级为需求问题
```

### 3. 风险接受 (h2_risk_acceptance)

```
⚠️ 风险确认

出测门禁条件放行，需要确认风险接受。

查看:
- output/test-report.yaml
- output/exit-gate-result.yaml

风险项:
{risk_list}

审批命令:
  python -m orchestrator approve $PROJECT_DIR h2_risk_acceptance --approver <pm>
```

### 4. 最终签字 (h3_final_signoff)

```
✍️ 出测签字确认

需要以下角色签字确认:
- [ ] QA Lead
- [ ] PM
- [ ] Tech Lead

审批命令:
  python -m orchestrator approve $PROJECT_DIR h3_final_signoff --approver <name> --role <role>
```

---

## 错误处理

| 情况 | 处理 |
|------|------|
| release-manifest.yaml 缺失 | 立即终止，提示补充 |
| 冒烟测试失败 | 打回研发，不继续后续测试 |
| E2E P0 失败 | 自动创建 Bug，进入修复循环 |
| 环境不可用 | 等待重试，最长 4h |
| Bug 修复超时 (48h) | 升级 PM |
| 出测门禁失败 | 继续修复循环 |

---

## 使用示例

```bash
# 基本用法
/run-testing project/AI跑步教练/testing

# 跳过小程序测试
/run-testing project/AI跑步教练/testing --skip-wechat

# 仅冒烟测试
/run-testing project/AI跑步教练/testing --smoke-only

# 从系统测试继续
/run-testing project/AI跑步教练/testing --resume-from t5_system_test

# 查看帮助
/run-testing --help
```

---

## 相关资源

- Skill 文档: `ai-spec/cli/claude/skills/testing-pipeline.md`
- 工作流定义: `ai-spec/specs/org/testing/workflows/testing-pipeline/v1/workflow.yaml`
- Bug 契约: `ai-spec/specs/org/testing/contracts/bug-contract/v1/schema.json`
- 测试报告契约: `ai-spec/specs/org/testing/contracts/test-report/v1/schema.json`
