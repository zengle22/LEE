# QA 部门工作流总结

> **版本:** v2.0 (L3 级别)  
> **更新:** 2026-02-13  
> **部门:** `spec-global/departments/qa/`

---

## 一、整体架构

QA 部门有 **2 条核心工作流** + **1 个跨部门衔接**，覆盖从需求到出测的完整生命周期：

```
需求文档    ──→  ① Test Set Production  ──→  Test Set 设计资产
                      (设计阶段)                    │
                                                    ↓
构建版本    ──→  ② Test Plan Execution  ──→  Test Run + Bug + 出测报告
                      (执行阶段)                    │
                                                    ↓
测试失败    ──→  ③ Test ↔ Dev 衔接       ──→  打回研发 → 返修 → 再提测
                   (跨部门协同)
```

---

## 二、工作流 ①：Test Set Production（设计资产生产）

**ID:** `workflow.qa.test_set_production_v1`  
**用途:** 将模块需求转化为标准 Test Set YAML（测试用例设计资产）

### 流程（4 个阶段）

```
需求文档 → [S1 需求分析] → [S2 策略设计] → [S3 Test Set生成] → [S4 审评] → Test Set YAML
              ↑ 人工审核      ↑ 人工审核                          ↑ 人工最终批准
```

| 阶段 | ID | Agent/Skill | 关键产出 |
|---|---|---|---|
| S1 需求分析 | `s1_requirement_analysis` | `requirement_analyzer` + `file.read` | `analysis.md`, `testable_features.yaml` |
| S2 策略设计 | `s2_strategy_design` | `test_strategist` | `test_strategy.yaml`, `risk_areas.yaml` |
| S3 Test Set 生成 | `s3_test_set_generation` | `test_set_generator` | `ts-{module}.yaml` (契约校验) |
| S4 审评 | `s4_test_set_review` | `test_set_reviewer` | `review_result.yaml` |

### 参数

```yaml
module:          "用户登录"        # 模块名称
requirement_doc: "prd/login.md"    # 需求文档路径
tech_design:     "design/login.md" # 技术设计（可选）
```

### 使用示例

```bash
# 初始化工作流
python -m orchestrator init . \
  --workflow spec-global/departments/qa/workflows/test-set-production/v1/workflow.yaml \
  --param module="用户登录" \
  --param requirement_doc="prd/login-prd.md"

# 自动执行 → 每个阶段会暂停等人工审核
python -m orchestrator run .
```

产出目录结构：
```
qa/test-sets/
├── ts-用户登录.yaml           # Test Set 设计资产
└── ts-用户登录/
    ├── analysis.md            # 需求分析报告
    └── strategy-draft.yaml    # 测试策略草稿
```

---

## 三、工作流 ②：Test Plan Execution（测试执行）

**ID:** `workflow.qa.test_plan_execution_v1`  
**用途:** 执行完整测试批次，从 Test Run 创建到出测评估  
**版本:** v1.1（含反 Mock 宪法 + AI 行为合规检查）

### 流程（8 个阶段）

```
Test Plan + Build → [S1 初始化] → [S2 环境准备] → [S2.5 环境探测] →
                          │              │               │
                          ↓              ↓               ↓
                    Test Run YAML    env-health      env-check.json
                                                        │
→ [S3 用例生成] → [S4 脚本翻译] → [S5 执行] → [S5.5 合规检查] →
      ↑人工审核                     Runner CLI     反Mock门禁
                                        │              │
→ [S5.6 结果判定] → [S6 TSE组装] → [S7 Bug起草] → [S8 出测评估]
   判断者角色          汇总            ↑人工确认      ↑ 人工决策
                                                   (通过/有条件通过/不通过)
```

### 角色拆分（核心设计特点）

| 角色 | 负责 | 约束 |
|---|---|---|
| **执行者** (S5) | 调用 `test_runner` CLI，收集证据 | 禁止判定 pass/fail，禁止 mock |
| **判断者** (S5.6) | 读 evidence 判定结果 | 禁止调用工具，禁止修改证据 |
| **Orchestrator** (S2.5) | 环境探测（工具/网络检查）| AI 无法干预 |

### 反 Mock 宪法（v1.1 核心特性）

```yaml
principles:
  no_mock_execution:   "AI 不得模拟执行"
  evidence_required:   "所有结果必须有 evidence_bundle"
  no_fabricated_errors: "runtime_errors 只能来自 Runner/Orchestrator/人工"
  tool_check_by_orchestrator: "环境检查由 Orchestrator 执行"

violation_handling: "违规用例 → invalid_run → 本轮测试 fail"
```

### 参数

```yaml
test_plan_id:     "PLAN-2026-001"    # Test Plan ID
build_version:    "1.0.0"            # 构建版本号
build_commit:     "a1b2c3d4"         # Git commit hash
environment:      "test"             # 测试环境（默认 test）
target_test_sets: []                 # 指定 Test Sets（空=全部）
```

### 使用示例

```bash
# 初始化测试执行
python -m orchestrator init . \
  --workflow spec-global/departments/qa/workflows/test-plan-execution/v1/workflow.yaml \
  --param test_plan_id="PLAN-2026-001" \
  --param build_version="1.0.0" \
  --param build_commit="a1b2c3d4" \
  --param environment="test"

# 执行 (各阶段有门禁暂停)
python -m orchestrator run .

# 只跑部分 Test Sets
python -m orchestrator init . \
  --workflow ... \
  --param test_plan_id="PLAN-2026-001" \
  --param build_version="1.0.0" \
  --param build_commit="a1b2c3d4" \
  --param target_test_sets='["ts-login", "ts-payment"]'
```

产出目录结构：
```
qa/
├── test-runs/{test_run_id}/
│   ├── test-run.yaml                    # Test Run 记录
│   ├── env-health.yaml                  # 环境健康检查
│   ├── env-check.json                   # Orchestrator 环境探测
│   ├── exit-evaluation.yaml             # 出测评估
│   ├── behavior-violations.yaml         # AI 违规记录（如有）
│   └── tse-{test_set_id}/
│       ├── cases.yaml                   # 生成的用例
│       ├── scripts/                     # 翻译的脚本
│       ├── runner-output.json           # Runner CLI 原始输出
│       ├── behavior-compliance.yaml     # AI 行为合规检查
│       ├── results.yaml                 # 执行结果
│       ├── evidence/                    # 证据（日志、截图）
│       └── tse.yaml                     # TSE 汇总
└── bugs/
    └── BUG-2026-NNNN.yaml              # Bug 文件
```

---

## 四、跨部门衔接：测试 ↔ 开发返修

**ID:** `workflow.integration.test_dev_retest`

```
测试失败 → 自动生成 rejection-notice.yaml → 打回研发返修流程
   │                                              │
   │  ← 返修完成，提交 retest-release-manifest.yaml ←
   ↓
新轮次测试（根据修复内容选择回归范围）
```

**防死循环：** 最多 3 轮 test↔dev 循环，超过自动上报 tech-lead / PM / QA-lead。

---

## 五、QA 资产清单

### 13 个 Agent

| Agent | 用途 |
|---|---|
| `requirement-analyzer` | 分析需求，提取可测试特性 |
| `test-strategist` | 设计测试策略和风险区域 |
| `test-set-generator` | 生成 Test Set YAML |
| `test-set-reviewer` | 审评 Test Set 完整性 |
| `test-run-initializer` | 创建 Test Run |
| `env-provisioner` | 部署测试环境 |
| `case-generator` | 动态生成测试用例 |
| `script-translator` | 翻译用例为可执行脚本 |
| `result-judge` | 判定 pass/fail（判断者角色）|
| `tse-assembler` | 组装 Test Set Execution |
| `bug-drafter` | 起草 Bug |
| `test-run-updater` | 更新 Test Run 汇总 |
| `exit-evaluator` | 评估出测条件 |

### 关键契约

| 契约 | 用途 |
|---|---|
| `test-plan-v2` | 测试计划定义 |
| `test-set` | 设计资产 |
| `test-case` | 单个用例 |
| `test-run` | Test Run 记录 |
| `test-set-execution` | TSE 汇总 |
| `bug-v2` | Bug 生命周期 |
| `e2e-script-contract` | 可执行脚本 |
| `e2e-runner-report` | Runner 输出 |

### 3 个 Skill

| Skill | 用途 |
|---|---|
| `env-check-tools` | Orchestrator 执行环境探测 |
| `test-e2e-runner` | 统一 E2E 测试执行器 |
| `behavior-compliance-checker` | AI 行为合规检查 |

---

## 六、出测标准 (Exit Gate v2.0)

### 强制标准（0 容忍）

| 编号 | 标准 | 要求 |
|---|---|---|
| C001 | P0 Bug | = 0 |
| C002 | 冒烟通过率 | = 100% |
| C003 | 核心流程通过率 | = 100% |
| C004 | 人类介入已决策 | 全部有 approver |
| C005 | API 契约违反 | = 0 |

### 阈值标准（可豁免）

| 编号 | 标准 | 默认 |
|---|---|---|
| T001 | P1 Bug | ≤ 3 |
| T002 | P2 Bug | ≤ 10 |
| T003 | 回归通过率 | ≥ 95% |
| T004 | E2E 通过率 | ≥ 90% |

---

## 七、完整使用示例

### 场景：为「用户登录」模块执行完整 QA 流程

```bash
# ── Step 1: 生产 Test Set 设计资产 ──
cd /path/to/project
python -m orchestrator init . \
  --workflow spec-global/departments/qa/workflows/test-set-production/v1/workflow.yaml \
  --param module="用户登录" \
  --param requirement_doc="prd/login-prd.md" \
  --param tech_design="design/login-tech.md"
python -m orchestrator run .
# → 产出: qa/test-sets/ts-用户登录.yaml

# ── Step 2: 编写 Test Plan（手动） ──
cat > qa/test-plans/PLAN-2026-LOGIN.yaml << 'EOF'
plan_id: PLAN-2026-LOGIN
name: "用户登录模块测试计划"
version: "1.0"
test_sets:
  - test_set_id: ts-用户登录
    priority: P0
    execution_order: 1
exit_criteria:
  mandatory:
    p0_bugs: 0
    smoke_pass_rate: 100
  threshold:
    p1_bugs: 3
    e2e_pass_rate: 90
EOF

# ── Step 3: 开发完成，执行测试 ──
python -m orchestrator init . \
  --workflow spec-global/departments/qa/workflows/test-plan-execution/v1/workflow.yaml \
  --param test_plan_id="PLAN-2026-LOGIN" \
  --param build_version="1.0.0" \
  --param build_commit="abc123" \
  --param environment="test"
python -m orchestrator run .

# ── Step 4: 查看结果 ──
cat qa/test-runs/TR-*/test-run.yaml           # Test Run 总览
cat qa/test-runs/TR-*/exit-evaluation.yaml     # 出测评估
ls  qa/bugs/                                   # Bug 列表

# ── Step 5: 如果测试失败，触发返修衔接 ──
# 自动产出 rejection-notice.yaml → 推送到开发返修流程
# 开发修复后提交 retest-release-manifest.yaml → 触发新测试轮次
```

### 主流程多轮循环（README 描述的完整流程）

```
Round 1:  提测包预检 → 环境准备 → 冒烟测试 → 系统测试 → 分流Bug → 修复验证 → 出测评估
             ↓ 不通过
Round 2:  风险回归测试 → 验证修复 → 出测评估
             ↓ 通过
最终签字:  QA Lead + PM + Tech Lead
             ↓
发布
```

最多 **10 轮**，Bug 并行处理不阻塞主流程。
