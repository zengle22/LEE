# Testing Workflow v2.0 使用指南
# Dual-Flow Multi-Round Testing Pipeline

> **版本:** v2.0
> **创建日期:** 2026-01-15
> **适用范围:** 所有需要系统化测试的项目

---

## 📋 目录

1. [概述](#概述)
2. [双流程架构](#双流程架构)
3. [快速开始](#快速开始)
4. [主流程详解](#主流程详解)
5. [Bug子流程详解](#bug子流程详解)
6. [门禁标准](#门禁标准)
7. [最佳实践](#最佳实践)
8. [常见问题](#常见问题)

---

## 概述

### 什么是Testing Workflow v2.0？

Testing Workflow v2.0 是一个**工程化的多轮循环测试流程**，支持：

✅ **多轮迭代** - 不强制一轮修完所有Bug，支持渐进式质量收敛
✅ **事件驱动** - Bug子流程独立运行，不阻塞主测试流程
✅ **风险回归** - 智能选择回归范围，避免重复劳动
✅ **角色权限** - 严格的读写权限，防止自证闭环
✅ **人类介入** - 关键决策点强制人类审批

### 与v1.0的区别

| 特性 | v1.0 (单轮) | v2.0 (多轮) |
|------|------------|------------|
| 测试轮次 | 单次通过 | 最多10轮循环 |
| Bug处理 | 阻塞式（等待修复） | 并行式（事件驱动） |
| 回归策略 | 全量回归 | 风险回归 |
| 出测标准 | 修完所有Bug | P0=0, P1≤3, 风险可接受 |
| 状态管理 | 简单状态机 | 双流程独立状态机 |

---

## 双流程架构

```
┌─────────────────────────────────────────────────────────────┐
│  Test Main Pipeline (主流程)                                 │
│  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐  ┌──────┐           │
│  │ ENV  │→│SMOKE │→│ E2E  │→│TRIAGE│→│ROUND │           │
│  │READY │  │      │  │      │  │ SYNC │  │SIGNOFF│          │
│  └──────┘  └──────┘  └──────┘  └──────┘  └──────┘           │
│                         │                                     │
│                         │ test_failure event                  │
│                         ↓                                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │ Bug Sub-workflow (并行子流程)                        │    │
│  │  NEW → TRIAGED → ROUTED → DEBUGGED → FIXING →       │    │
│  │  FIXED → VERIFYING → VERIFIED → CLOSED               │    │
│  │                                                       │    │
│  │  特殊分支: BLOCKED_HUMAN, BLOCKED_PM, BLOCKED_ENV    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**关键概念：**

1. **主流程** - 管理测试轮次、环境、门禁判定
2. **Bug子流程** - 每个Bug独立生命周期，并行推进
3. **事件通知** - Bug状态变化通知主流程更新清单
4. **同步点** - 主流程在TRIAGE_SYNC和ROUND_SIGNOFF读取Bug状态

---

## 快速开始

### 前置条件

```bash
# 1. 准备提测包
project/
├── release-manifest.yaml       # 研发提测清单
└── testing/
    ├── .workflow/              # Orchestrator工作目录
    ├── test-rounds/            # 测试轮次记录
    └── bugs/                   # Bug契约文件
```

### 第一轮测试

```bash
# Step 1: 初始化测试流程
cd project/testing
python -m orchestrator init . --workflow ai-spec/specs/org/testing/workflows/test-main-pipeline/v2/workflow.yaml

# Step 2: 检查状态
python -m orchestrator status .

# Step 3: 开始提交审核
python -m orchestrator start . s1_precheck

# Step 4: 完成步骤并验证
python -m orchestrator complete . s1_precheck --outputs release-manifest.yaml
python -m orchestrator validate . s1_precheck

# Step 5: 继续下一步（自动推进，直到遇到人类门禁）
python -m orchestrator status .
# 如果 action=continue && human_gate=false，继续执行
python -m orchestrator start . <next_step_id>
```

### 处理测试失败

```bash
# 测试失败时，自动触发Bug子流程
# 主流程无需等待，继续执行其他测试

# 查看Bug清单
ls bugs/

# 手动触发Bug分流（如需要）
python -m orchestrator start bugs/BUG-2026-0001.yaml triage
```

---

## 主流程详解

### 状态机

```
INIT → PRECHECK_MANIFEST → ENV_READY → SMOKE →
IN_TEST_EXECUTION → TRIAGE_SYNC → FIX_VERIFY_LOOP →
ROUND_SIGNOFF → [RELEASE_CANDIDATE | NEXT_ROUND] → RELEASED
```

### 关键阶段

#### Stage 1: 提交审核 (PRECHECK_MANIFEST)

**目的:** 确保提测包完整性

**检查项:**
- ✅ release-manifest.yaml 符合schema
- ✅ 包含版本号、Git commit hash
- ✅ 变更区域清晰标注
- ✅ 已知风险已记录

**门禁:** `submission-gate`

```yaml
# release-manifest.yaml 示例
manifest_id: MAN-2026-0001
release_version: "1.1.0"
target_env: test
git_commit: a1b2c3d4e5f6
changed_areas:
  - runner-profile
  - plan-generation
known_risks:
  - risk: "新功能未经生产验证"
    mitigation: "充分回归测试"
```

#### Stage 2: 环境准备 (ENV_READY)

**步骤:**
1. 部署测试版本到测试环境
2. 健康检查（health check）
3. 测试数据准备

**门禁:** `env-ready-gate`

#### Stage 3: 冒烟测试 (SMOKE)

**目的:** 快速验证基础功能，作为准入门禁

**门禁标准:**
- ✅ 冒烟测试100%通过
- ✅ 核心流程100%通过

**失败行为:** 直接返回BLOCKED状态，不继续测试

```bash
# 冒烟测试失败 → 立即退回研发
# 不浪费时间在环境不稳定的版本上
```

#### Stage 4: 系统测试执行 (IN_TEST_EXECUTION)

**并行执行:**
- API测试
- E2E测试（Chrome/微信）
- 性能测试
- 安全测试

**失败处理:**
- 每个失败 → 自动创建Bug契约
- 触发 `test_failure` 事件
- Bug子流程异步启动
- 主流程继续执行其他测试

#### Stage 5: 轮次同步 (TRIAGE_SYNC)

**目的:** 确保所有新Bug已分流

**检查项:**
- ✅ 所有 `status=new` 的Bug已分配owner
- ✅ P0/P1 Bug已触发Debug Agent分析
- ✅ 人类介入的Bug已上报

**同步点:** 主流程读取Bug清单，决定是否继续

#### Stage 6: 修复验证循环 (FIX_VERIFY_LOOP)

**轮内短循环:**

```
等待修复 → 验证修复 → 回归重跑 → [继续等待 | 完成]
```

**循环条件:**
- P0 Bug > 0
- 或 P1 Bug > 0 且 循环次数 < 5

**超时:** 48小时

#### Stage 7: 轮次签字 (ROUND_SIGNOFF)

**决策点:** 下一轮 or 出测？

**评估维度:**

1. **强制标准** (不可豁免)
   - P0 Bug = 0 ✅
   - 冒烟测试 = 100% ✅
   - 核心流程 = 100% ✅
   - 人类介入Bug已决策 ✅

2. **阈值标准** (可豁免)
   - P1 Bug ≤ 3
   - P2 Bug ≤ 10
   - 回归测试 ≥ 95%

3. **风险可接受** (需签字)
   - 遗留Bug有文档
   - 有规避方案
   - 回滚计划就绪

**输出:** `round-conclusion.yaml`

```yaml
conclusion:
  decision: next_round | release_candidate | blocked
  rationale: "..."
  exit_criteria_met: true/false
  blockers: [...]
  next_round_focus: "..."
```

---

## Bug子流程详解

### 状态机

```
NEW → TRIAGED → ROUTED → DEBUGGED → FIXING →
FIXED → VERIFYING → VERIFIED → CLOSED

特殊分支:
├─ BLOCKED_HUMAN (安全/财务/法律)
├─ BLOCKED_PM (需求争议)
├─ BLOCKED_ENV (环境问题)
└─ BLOCKED_DEPENDENCY (依赖其他Bug)
```

### 角色权限

| 角色 | 可写状态 | 可写字段 | 禁止写字段 |
|------|---------|---------|-----------|
| QA Agent | NEW, TRIAGED, VERIFYING, VERIFIED, CLOSED | evidence.*, verification.* | fix.*, decision.pm_resolution |
| Debug Agent | - | analysis.root_cause, analysis.fix_plan | status, fix.*, verification.* |
| Dev Agent | FIXING, FIXED | fix.* | verification.*, decision.* |
| PM Agent | BLOCKED_PM → ROUTED/CLOSED | decision.pm_resolution | fix.*, verification.* |
| Human Approver | BLOCKED_HUMAN → ROUTED/CLOSED | decision.human_decision | fix.*, verification.* |

**防自证规则:**

```yaml
validation_rule:
  no_self_certification:
    check: "verification.verified_by != routing.owner_agent"
    error: "验证者不能是Bug负责人"
```

### 人类介入触发条件

**自动触发 `BLOCKED_HUMAN` 状态：**

1. `category == security` - 安全相关
2. `category == data_loss` - 数据丢失风险
3. `category == payment` - 财务相关
4. `decision.scope_change == major` - 修复等同改需求
5. `severity == P0 AND detected_in == production` - 线上P0

**SLA:** 4小时内必须人类决策，否则升级

---

## 门禁标准

### Exit Gate v2.0 详解

#### 强制标准 (Mandatory - 0容忍)

```yaml
C001: P0 Bug清零
  rule: COUNT(bugs WHERE severity=P0 AND status != closed) == 0
  exemption: false

C002: 冒烟测试100%通过
  rule: smoke_test_pass_rate == 100
  exemption: false

C003: 核心流程100%通过
  rule: core_flow_pass_rate == 100
  exemption: false

C004: 人类介入Bug已决策
  rule: COUNT(bugs WHERE needs_human=true AND human_approver IS NULL) == 0
  exemption: false

C005: API契约无违反
  rule: api_contract_violations == 0
  exemption: false
```

#### 阈值标准 (Threshold - 可调整)

```yaml
T001: P1 Bug阈值
  default: 3
  conservative: 1
  aggressive: 5

T002: P2 Bug阈值
  default: 10
  conservative: 5
  aggressive: 20

T003: 回归测试通过率
  default: 95%
  conservative: 98%
  aggressive: 90%
```

#### 风险可接受标准 (需签字)

```yaml
R001: 已知P2/P3已记录
  required_fields: [title, impact_assessment, workaround, defer_reason]

R002: 规避方案可用
  verification: "QA验证规避方案可行"

R003: 回滚计划就绪
  required_artifacts:
    - rollback-plan.md
    - rollback-test-record.yaml

R004: 风险评估完成
  required_approvers: [qa_lead, tech_lead, pm]
```

### 回归范围验证

**必须回归:**
- ✅ 冒烟套件 (100%)
- ✅ 核心流程 (100%)
- ✅ Bug相关用例 (100%)
- ✅ 代码变更区域 (≥80%)
- ✅ 历史高发区域 (≥70%)

**可选回归:**
- 全量回归 (仅出测前最后一轮或重大版本)

---

## 最佳实践

### 1. 轮次规划

**首轮（Round 1）:** 全面探索
- 执行冒烟 + API + E2E
- 发现所有明显Bug
- 建立质量基线

**中间轮（Round 2-N）:** 增量验证
- 仅回归Bug修复影响范围
- 验证P0/P1修复
- 跟踪质量趋势

**末轮（Final Round）:** 全量确认
- 执行完整回归套件
- 确认所有遗留Bug有文档
- 人类最终签字

### 2. Bug优先级策略

**P0（立即修复）:**
- 阻塞核心流程
- 数据丢失/泄露
- 支付相关

**P1（本轮必修）:**
- 影响主要功能
- 用户体验严重受损

**P2（可延后）:**
- 影响次要功能
- 有规避方案

**P3（择机修复）:**
- 体验瑕疵
- 边缘场景

### 3. 轮次退出条件

**正常退出 → 出测:**
- P0 = 0
- P1 ≤ 3
- 所有门禁通过
- 人类签字完成

**异常退出 → 下一轮:**
- 发现新P0/P1 Bug
- 回归测试失败
- 人类决策延后

**阻塞退出 → 退回研发:**
- 冒烟测试失败
- 环境无法稳定
- 超过最大轮次(10)

### 4. 证据留存

**每轮必须归档:**
```
test-rounds/round-NNN/
├── test-round.yaml              # 轮次记录
├── smoke-report.json            # 冒烟测试报告
├── e2e-report.json              # E2E测试报告
├── api-report.json              # API测试报告
├── round-summary.md             # 轮次总结
└── evidence/                    # 测试证据
    ├── screenshots/
    ├── videos/
    └── traces/
```

**Bug契约必须包含:**
- 完整的复现步骤
- 截图/录屏证据
- trace_id/request_id
- 日志关键词

---

## 常见问题

### Q1: 什么时候进入下一轮？

**A:** 满足以下任一条件：
- 仍有P0 Bug未修复
- P1 Bug数量超过阈值(默认3个)
- 回归测试发现新问题
- 人类决策需要更多时间

### Q2: Bug子流程如何与主流程同步？

**A:** 事件驱动模型
- Bug状态变化 → 发送事件 → 主流程更新清单
- 主流程在TRIAGE_SYNC和ROUND_SIGNOFF读取Bug状态
- 不阻塞：主流程不等待单个Bug修复完成

### Q3: 如何防止自证闭环？

**A:** 严格角色权限
- Dev Agent修复Bug → 写 `fix.*` 字段
- QA Agent验证 → 写 `verification.*` 字段
- Orchestrator验证：`verified_by != owner_agent`

### Q4: 人类介入后流程如何继续？

**A:**
```bash
# 人类审批后，更新Bug状态
python -m orchestrator approve bugs/BUG-XXX.yaml human_gate --approver "张三"

# Bug状态 BLOCKED_HUMAN → ROUTED
# 主流程在下次TRIAGE_SYNC时读取更新
```

### Q5: 如何处理环境不稳定？

**A:**
- 冒烟失败 → 立即BLOCKED，退回研发
- 测试中环境问题 → 创建Bug，`category=env`
- Bug路由到Platform Agent
- Platform Agent修复后 → Bug状态 BLOCKED_ENV → ROUTED

### Q6: 最大轮次限制的意义？

**A:** 防止无限循环
- 默认10轮
- 超过限制 → 强制BLOCKED，人类介入决策
- 可能原因：质量基线太低、需求不清晰、技术债务严重

### Q7: 风险回归 vs 全量回归？

**A:**
```
风险回归（每轮默认）:
├─ 冒烟套件 (100%)
├─ 核心流程 (100%)
├─ Bug相关用例 (100%)
├─ 代码变更区域 (≥80%)
└─ 历史高发区域 (≥70%)

全量回归（仅末轮）:
└─ 所有测试用例 (100%)
```

效率优化：避免每轮都跑全量，重点关注风险区域

---

## 附录

### 相关文件

- [Test Main Pipeline Workflow](../workflows/test-main-pipeline/v2/workflow.yaml)
- [Bug Sub-workflow](../workflows/bug-sub-workflow/v1/workflow.yaml)
- [Bug Contract Schema](../contracts/bug-contract/v1/schema.yaml)
- [Test Round Schema](../contracts/test-round/v1/schema.yaml)
- [Exit Gate Rules](../gates/exit-gate/v2/gate.yaml)

### 版本历史

- v2.0 (2026-01-15) - 引入双流程、多轮循环、事件驱动
- v1.0 (2025-12-01) - 单轮流程、同步Bug处理

---

**文档维护者:** test-governance
**最后更新:** 2026-01-15
**反馈渠道:** [提交Issue](https://github.com/org/testing-specs/issues)
