# QA L2/L3 工作流升级 - 复盘总结报告

## 项目信息

| 项目 | 内容 |
|------|------|
| **项目名称** | QA Test Plan Execution 工作流 L2/L3 架构升级 |
| **分支** | `vk/26d3-qa-l2` |
| **时间范围** | 2026-02-24 |
| **提交数** | 6 commits |
| **变更文件** | 23 files (+5021, -37) |

---

## 一、背景与目标

### 1.1 背景

原有的 Test Plan Execution 工作流 (v1) 是单层架构，所有测试步骤在一个工作流中线性执行。随着业务复杂度增加，存在以下问题：

- **缺乏分层**: 无法区分部门级 (L2) 和任务级 (L3) 职责
- **依赖管理困难**: Test Set 间依赖关系无法有效处理
- **执行效率低**: 无法支持未来并行执行需求
- **质量控制不足**: Anti-Mock 约束难以在单层架构中有效执行

### 1.2 升级目标

将 Test Plan Execution 从 v1 (单层) 升级到 v2 (L2/L3 架构)：

1. **Phase 1-3**: L2 直接执行 (Test Run 初始化、环境准备、环境检查)
2. **Phase 4**: L3 调度 - 每个 Test Set 生成一个 L3 实例，按依赖顺序串行执行
3. **Step 4-10**: 转为 L3 工作流步骤
4. **Phase 5-8**: L2 聚合 (Bug 汇总、测试报告、退出评估、复盘)
5. **依赖处理**: 支持 Test Set 依赖，上游失败则跳过下游
6. **角色分离**: 执行者 (executor) 与 判定者 (judge) 职责分离

---

## 二、架构设计

### 2.1 L2/L3 架构概览

```
┌─────────────────────────────────────────────────────────────────┐
│                         L2 (部门级)                              │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Phase 1: test_run_init  - 初始化 Test Run                 │ │
│  │ Phase 2: env_provision   - 环境准备                        │ │
│  │ Phase 3: env_check       - 环境检查                        │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Phase 4: test_set_execution (L3 Spawning)                 │ │
│  │   ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐  ┌─────┐   │ │
│  │   │L3   │→ │L3   │→ │L3   │→ │L3   │→ │L3   │→ │L3   │   │ │
│  │   │smoke│  │auth │  │pay  │  │order│  │check│  │notif│   │ │
│  │   └─────┘  └─────┘  └─────┘  └─────┘  └─────┘  └─────┘   │ │
│  │   (按依赖顺序串行执行)                                     │ │
│  └────────────────────────────────────────────────────────────┘ │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │ Phase 5: bug_summary     - Bug 汇总与去重                  │ │
│  │ Phase 6: test_report     - 生成测试报告                    │ │
│  │ Phase 7: exit_evaluation - 退出评估                        │ │
│  │ Phase 8: retrospective   - 复盘总结                        │ │
│  └────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 L3 工作流结构 (单 Test Set)

```
┌─────────────────────────────────────────────────────────────────┐
│                       L3 (任务级)                               │
│  Step 1: case_generation     - 用例生成                         │
│  Step 2: script_translation  - 脚本翻译                         │
│  Step 3: script_execution    - 脚本执行 [EXECUTOR 角色]        │
│  Step 4: behavior_compliance - 行为合规检查                     │
│  Step 5: result_judgment     - 结果判定 [JUDGE 角色]           │
│  Step 6: tse_assembly        - TSE 组装                         │
│  Step 7: bug_drafting        - Bug 起草                         │
└─────────────────────────────────────────────────────────────────┘
```

### 2.3 角色分离机制

| 角色 | 步骤 | 允许操作 | 禁止操作 |
|------|------|----------|----------|
| **EXECUTOR** | Step 3 脚本执行 | 调用 test_runner、收集证据 | 判定通过/失败、伪造错误 |
| **JUDGE** | Step 5 结果判定 | 读取证据、判定结果 | 调用 test_runner、修改证据 |

---

## 三、交付清单

### 3.1 工作流模板 (2 个)

| 文件 | 描述 |
|------|------|
| `workflows/templates/test-plan-l2-template.yaml` | L2 模板，定义 8 个阶段 |
| `workflows/templates/test-set-l3-template.yaml` | L3 模板，定义 7 个步骤 |

### 3.2 工作流实例 (1 个)

| 文件 | 描述 |
|------|------|
| `workflows/test-plan-execution/v2/workflow.yaml` | L2 实例工作流 |

### 3.3 Contract (4 个)

| 文件 | 描述 |
|------|------|
| `contracts/bug-summary/v1/schema.yaml` | Bug 汇总合约 (L2 Phase 5 输出) |
| `contracts/test-report/v1/schema.yaml` | 测试报告合约 (L2 Phase 6 输出) |
| `contracts/retrospective/v1/schema.yaml` | 复盘合约 (L2 Phase 8 输出) |
| `contracts/test-result/v1/schema.yaml` | 测试结果合约 (L3 Step 5 输出) |

### 3.4 Agent (7 个)

| 文件 | 描述 |
|------|------|
| `agents/bug-summarizer/v1/agent.yaml` | **新增** Bug 汇总 Agent |
| `agents/report-generator/v1/agent.yaml` | **新增** 报告生成 Agent |
| `agents/retrospective-generator/v1/agent.yaml` | **新增** 复盘生成 Agent |
| `agents/result-judge/v1/agent.yaml` | **更新** 结果判定 Agent (添加角色约束) |
| `agents/bug-drafter/v1/agent.yaml` | **更新** Bug 起草 Agent (统一格式) |
| `agents/case-generator/v1/agent.yaml` | **更新** 用例生成 Agent (统一格式) |
| `agents/script-translator/v1/agent.yaml` | **更新** 脚本翻译 Agent (统一格式) |
| `agents/tse-assembler/v1/agent.yaml` | **更新** TSE 组装 Agent (统一格式) |

### 3.5 Skill (2 个)

| 文件 | 描述 |
|------|------|
| `skills/file-update/v1/skill.yaml` | **新增** 文件更新 Skill |
| `skills/file-collect/v1/skill.yaml` | **新增** 文件收集 Skill |

### 3.6 Gate (2 个)

| 文件 | 描述 |
|------|------|
| `gates/bug-review-gate/v1/gate.yaml` | **新增** Bug 审核门禁 |
| `gates/exit-decision-gate/v1/gate.yaml` | **新增** 退出决策门禁 |

### 3.7 L3 实例示例 (1 个)

| 文件 | 描述 |
|------|------|
| `workflows/instances/l3/test-set-auth-instance.yaml` | **新增** Auth Test Set L3 实例 |

### 3.8 文档 (1 个)

| 文件 | 描述 |
|------|------|
| `docs/l2-l3-integration.md` | **新增** L2/L3 集成文档 |

### 3.9 Demo (1 个)

| 文件 | 描述 |
|------|------|
| `examples/qa_l2_l3_demo.py` | **新增** 集成测试演示脚本 |

### 3.10 Schema 更新 (1 个)

| 文件 | 变更 |
|------|------|
| `contracts/test-set/v1/schema.yaml` | 添加 `execution.depends_on` 字段 |

---

## 四、技术实现要点

### 4.1 Test Set 依赖解析

使用 **Kahn 算法** 实现拓扑排序，确保 Test Set 按依赖顺序执行：

```python
# 示例依赖关系
ts_smoke     (无依赖)
ts_auth      (无依赖)
ts_payment   → depends_on: [ts_auth]
ts_checkout  → depends_on: [ts_payment]
ts_order     → depends_on: [ts_auth]
ts_notification → depends_on: [ts_order]

# 执行顺序 (拓扑排序结果)
ts_smoke → ts_auth → ts_payment/ts_order → ts_checkout → ts_notification
```

### 4.2 Orchestrator 集成

通过 `SubworkflowMixin` 实现无侵入式 L3 调用：

- L2 Phase 4 配置 `spawns_l3: true`
- 指定 `l3_template_id: template.qa.test_set_l3`
- Orchestrator 自动处理 L3 实例创建与执行
- 无需额外 Python 代码

### 4.3 Anti-Mock 宪法执行

通过 **角色约束** 强化 Anti-Mock：

1. **Step 3 (EXECUTOR)**: 只负责执行和收集证据，禁止判定结果
2. **Step 4 (行为合规检查)**: 检测 Mock 行为和证据缺失
3. **Step 5 (JUDGE)**: 只负责读取证据并判定，禁止调用 test_runner

违规后果：
- 无 `evidence_bundle` → `status: invalid_run`
- 检测到 Mock → `status: invalid_run`
- L2 标记整个 Test Run 为 **INVALID**

### 4.4 Bug 去重机制

L2 Phase 5 收集所有 L3 的 Bug 草稿，进行去重：

```yaml
# Bug 去重规则
deduplication_rules:
  - by: ["title", "module", "severity"]
  - similarity_threshold: 0.85
  - keep: "highest_severity"
```

---

## 五、Git 提交记录

| Commit | 描述 |
|--------|------|
| `d946045` | feat(qa): upgrade test plan execution workflow to L2/L3 architecture |
| `08d1f66` | feat(qa): add missing skills, gates and integration docs |
| `b858267` | feat(qa): add L3 instance example and update result-judge agent |
| `5b10915` | refactor(qa): unify Agent format and add test-result contract |
| `da5b554` | refactor(qa): update result-judge agent tools/specs format |
| `cc17eec` | feat(qa): add L2/L3 workflow integration test demo |

---

## 六、问题与解决

### 6.1 W001 警告: Legacy skills format

**问题**: Agent 的 `capabilities` 字段引用了有 spec 文件的 skill

**解决**: 将所有 Agent 从 `capabilities` 格式统一为 `tools/specs` 格式

**影响文件**: 7 个 agent.yaml

### 6.2 缺失 test-result contract

**问题**: L3 Step 5 引用了不存在的 `contract.qa.test_result`

**解决**: 创建 `contracts/test-result/v1/schema.yaml`

---

## 七、验证与测试

### 7.1 集成测试 Demo

`qa_l2_l3_demo.py` 验证了以下内容：

1. ✅ L2 模板加载 (8 phases)
2. ✅ L3 模板加载 (7 steps)
3. ✅ 依赖解析 (拓扑排序)
4. ✅ L3 实例创建
5. ✅ L3 执行流程
6. ✅ L2 聚合流程
7. ✅ Anti-Mock 宪法执行
8. ✅ CLI 使用方式

### 7.2 运行方式

```bash
# 方式 1: 使用 lee-qa-test-run skill
$ lee qa test-run \
    --test-plan TP-2026-Q1 \
    --build-version v1.2.3 \
    --build-commit a1b2c3d4 \
    --environment test

# 方式 2: 使用 lee run
$ lee run workflow.qa.test_plan_execution_v2 \
    --test-plan-id TP-2026-Q1 \
    --build-version v1.2.3

# 方式 3: 指定 Test Set
$ lee qa test-run \
    --test-plan TP-2026-Q1 \
    --target-test-sets ts_auth,ts_payment
```

---

## 八、成果总结

### 8.1 量化指标

| 指标 | 数值 |
|------|------|
| 新增文件 | 15 个 |
| 修改文件 | 8 个 |
| 新增代码行 | +5021 |
| 删除代码行 | -37 |
| 新增 Contract | 4 个 |
| 新增 Agent | 3 个 |
| 新增 Skill | 2 个 |
| 新增 Gate | 2 个 |
| 新增模板 | 2 个 |

### 8.2 架构改进

| 方面 | v1 (单层) | v2 (L2/L3) |
|------|-----------|------------|
| 层次结构 | 单层工作流 | L2 部门级 + L3 任务级 |
| 依赖处理 | 不支持 | Test Set 级别依赖解析 |
| 执行模式 | 线性执行 | 支持串行，预留并行能力 |
| 质量控制 | 无角色分离 | EXECUTOR/JUDGE 角色分离 |
| Anti-Mock | 弱约束 | 强约束 + 行为合规检查 |
| 聚合能力 | 无 | L2 级 Bug 去重与报告 |

---

## 九、后续建议

### 9.1 功能增强

1. **并行执行**: 在 Orchestrator 中实现 L3 并行调度
2. **重试机制**: L3 失败后的自动重试策略
3. **增量测试**: 基于代码变更的 Test Set 智能选择
4. **实时进度**: L3 执行进度的实时推送

### 9.2 工具完善

1. **CLI 增强**: 添加 `lee qa test-run-status` 查询命令
2. **可视化**: Test Set 依赖图可视化
3. **报告模板**: Markdown/HTML 报告样式优化

### 9.3 质量保障

1. **单元测试**: 为拓扑排序、去重逻辑添加测试
2. **E2E 测试**: 真实环境下的完整工作流测试
3. **性能基准**: L2/L3 执行时间基准测试

---

## 十、总结

本次 QA Test Plan Execution 工作流升级成功实现了从单层架构到 L2/L3 分层架构的转型。通过引入部门级 (L2) 和任务级 (L3) 的职责分离，配合 EXECUTOR/JUDGE 角色分离和 Anti-Mock 宪法执行，显著提升了测试工作流的可管理性、可扩展性和质量保障能力。

**核心成就**:
- ✅ 完整的 L2/L3 模板体系
- ✅ Test Set 依赖解析机制
- ✅ 角色分离的 Anti-Mock 执行
- ✅ L2 级 Bug 聚合与报告
- ✅ 无侵入式 Orchestrator 集成
- ✅ 完善的集成测试验证

该架构为未来并行执行、增量测试等高级特性奠定了坚实基础。
