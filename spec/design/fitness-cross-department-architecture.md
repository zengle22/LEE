# 跨部门 Fitness Function 架构设计 v1.0

# Cross-Department Fitness Function Architecture

## 1. 设计目标

Fitness Function 作为**完成条件防腐层**，不应局限于单一部门，而应成为 LEE 框架的**治理层通用能力**。

### 核心设计原则

1. **部门无关性**: Fitness Executor 不预置任何部门特定规则
2. **规则驱动**: 行为完全由输入的 fitness_rule 定义决定
3. **结构化输出**: fitness_result 符合通用 schema，供 Gate 消费
4. **可组合性**: 可被多个部门的工作流引用和扩展

---

## 2. 架构分层

```
┌─────────────────────────────────────────────────────────────────┐
│                    GOVERNANCE LAYER (治理层)                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  skill.governance.fitness_executor (通用执行技能)            ││
│  │  - 输入：fitness_rule_path + target_context                 ││
│  │  - 处理：规则加载 → 评估执行 → 结果输出                      ││
│  │  - 输出：结构化的 fitness_result                            ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │  gate_template.governance.fitness_gate (通用门禁模板)        ││
│  │  - 配置参数：department, fitness_rule_path, target_type     ││
│  │  - 实例化：各部门创建具体的 Fitness Gate                     ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        ▼                     ▼                     ▼
┌───────────────────┐ ┌───────────────────┐ ┌───────────────────┐
│   PRODUCT DEPT    │ │     QA DEPT       │ │     DEV DEPT      │
├───────────────────┤ ├───────────────────┤ ├───────────────────┤
│ Fitness Rules:    │ │ Fitness Rules:    │ │ Fitness Rules:    │
│ - src_freeze      │ │ - test_set_comp   │ │ - feature_delivery│
│ - feat_freeze     │ │ - test_run_exit   │ │ - smoke_entry     │
│                   │ │                   │ │                   │
│ Gates:            │ │ Gates:            │ │ Gates:            │
│ - src_fitness     │ │ - test_set_fit    │ │ - evidence_fit    │
│ - feat_fitness    │ │ - test_run_fit    │ │ - smoke_fit       │
└───────────────────┘ └───────────────────┘ └───────────────────┘
```

---

## 3. 文件结构

```
spec-global/
├── departments/
│   ├── governance/
│   │   ├── skills/
│   │   │   └── fitness-executor/
│   │   │       └── v1/
│   │   │           └── skill.yaml              # 通用 Fitness Executor 技能
│   │   │
│   │   └── gates/
│   │       └── fitness-gate/
│   │           └── v1/
│   │               └── gate-template.yaml      # 通用 Fitness Gate 模板
│   │
│   ├── product/
│   │   ├── fitness-rules/
│   │   │   ├── src-freeze-rules.yaml           # SRC 冻结前规则
│   │   │   └── feat-freeze-rules.yaml          # FEAT 冻结前规则
│   │   │
│   │   └── gates/
│   │       └── fitness-gate/
│   │           └── v1/
│   │               └── gate.yaml               # Product Fitness Gate 实例
│   │
│   ├── qa/
│   │   ├── fitness-rules/
│   │   │   ├── test-set-completion-rules.yaml  # Test Set 完成前规则
│   │   │   └── test-run-exit-rules.yaml        # Test Run 退出前规则
│   │   │
│   │   └── gates/
│   │       └── fitness-gate/
│   │           └── v1/
│   │               └── gate.yaml               # QA Fitness Gate 实例
│   │
│   └── dev/
│       ├── fitness-rules/
│       │   ├── feature-delivery-rules.yaml     # 特性交付完成前规则
│       │   └── smoke-entry-rules.yaml          # Smoke 入口前规则
│       │
│       └── gates/
│           └── fitness-gate/
│               └── v1/
│                   └── gate.yaml               # Dev Fitness Gate 实例
│
└── spec/
    └── requirements/
        └── SRC-024/
            ├── FEAT-SRC-024-001__fitness-guize-shengming-jizhi-dingyi.md
            ├── FEAT-SRC-024-002__fitness-guize-zhihangqi-hexin-shixian.md
            ├── FEAT-SRC-024-003__hard-gate-yu-quality-signal-fenceng-jizhi.md
            ├── FEAT-SRC-024-004__fitness-result-jiegouhua-shuchu-yu-xiayou-duijie.md
            └── FEAT-SRC-024-005__cli-yu-ci-zuixiao-jierumian-shixian.md
```

---

## 4. 各部门 Fitness 集成点

### 4.1 Product 部门

```
raw_to_src workflow:
  ...
  → source_normalization
  → source_review
  → [Fitness Check: src_freeze_rules]  ← 新增
  → source_freeze (gate)
  ...

epic_to_feat workflow:
  ...
  → feat_identity_formalize
  → feat_review
  → [Fitness Check: feat_freeze_rules]  ← 新增
  → feat_freeze (gate)
  ...
```

**规则类型**:
- SRC Freeze: 问题定义完整性、来源追溯、Bridge 语义
- FEAT Freeze: 独立验收边界、结构化 acceptance_checks、可派生性

### 4.2 QA 部门

```
test_set_production workflow:
  ...
  → test_set_generation
  → test_set_review
  → [Fitness Check: test_set_completion_rules]  ← 新增
  → test_set_approval (gate)
  ...

test_plan_execution workflow:
  ...
  → test_set_execution (L3)
  → l3_output_validation
  → [Fitness Check: test_run_exit_rules]  ← 新增
  → exit_evaluation
  ...
```

**规则类型**:
- Test Set Completion: FEAT traceability、AC 覆盖、ADR 约束
- Test Run Exit: 通过率、Bug 修复率、覆盖率（Quality Signal）

### 4.3 Dev 部门

```
feature_delivery_l2 workflow:
  ...
  → integration
  → [Fitness Check: feature_delivery_rules]  ← 新增
  → evidence_pack
  → [Fitness Check: smoke_entry_rules]  ← 新增
  → smoke_gate
  ...
```

**规则类型**:
- Feature Delivery: 协议冻结、测试实现、验收验证
- Smoke Entry: Smoke 前置条件检查

---

## 5. 规则分类

### Hard Gate（阻断性）

- **定义**: 失败会阻断流程，不允许 merge/proceed
- **优先级**: blocker
- **示例**:
  - SSOT Header 完整性
  - FEAT traceability
  - 验收标准验证

### Quality Signal（建议性）

- **定义**: 失败仅记录质量指标，不阻断但需审查
- **优先级**: major/minor
- **示例**:
  - 覆盖率门槛
  - 文档完整性
  - 性能基线

---

## 6. Fitness Result Schema

```yaml
fitness_result:
  fitness_run_id: "fitness-20260317-001"
  executed_at: "2026-03-17T10:30:00Z"
  executed_by: "agent.governance.fitness_executor"
  fitness_rule_ref: "spec-global/departments/product/fitness-rules/src-freeze-rules.yaml"
  target_ref:
    object_type: src
    object_path: "spec/requirements/SRC-024/SRC-024__xxx.md"
    object_id: "SRC-024"

  rule_results:
    - rule_id: "ssot_header_complete"
      rule_type: hard_gate
      status: passed
    - rule_id: "problem_statement_complete"
      rule_type: hard_gate
      status: passed

  execution_summary:
    total_rules: 10
    passed_rules: 10
    failed_rules: 0
    hard_gate_total: 8
    hard_gate_passed: 8
    quality_signal_total: 2
    quality_signal_passed: 2
    pass_rate: 100

  result: PASSED  # PASSED | BLOCKED | WARNING | INVALID_RUN
  gate_handoff_ready: true

  gate_evaluation:
    ready_for_gate: true
    recommended_action: proceed
    blocking_rule_ids: []
```

---

## 7. Gate 消费逻辑

```python
def evaluate_fitness_gate(fitness_result):
    if fitness_result.result == "INVALID_RUN":
        return GATE_BLOCKED  # 执行错误，阻断

    if fitness_result.result == "BLOCKED":
        return GATE_BLOCKED  # hard_gate 失败，阻断

    if fitness_result.result == "PASSED":
        return GATE_AUTO_PASS  # 全部通过，自动通过

    if fitness_result.result == "WARNING":
        # quality_signal 失败，可配置
        if gate_config.auto_pass_on_warning:
            return GATE_AUTO_PASS
        else:
            return GATE_REQUIRE_REVIEW  # 需要人工审查

    return GATE_BLOCKED  # 默认阻断
```

---

## 8. CLI 集成

```bash
# 通用 CLI 入口
lee fitness run --rule-path <fitness_rule_path> --target <target_path> [--mode enforce|warn]

# Product 部门示例
lee fitness run \
  --rule-path spec-global/departments/product/fitness-rules/src-freeze-rules.yaml \
  --target spec/requirements/SRC-024/SRC-024__xxx.md \
  --mode enforce

# QA 部门示例
lee fitness run \
  --rule-path spec-global/departments/qa/fitness-rules/test-set-completion-rules.yaml \
  --target spec/qa/test-sets/ts-user-auth.yaml \
  --mode enforce

# Dev 部门示例
lee fitness run \
  --rule-path spec-global/departments/dev/fitness-rules/feature-delivery-rules.yaml \
  --target .workflow/evidence-pack-xxx/evidence_pack.json \
  --mode enforce
```

---

## 9. CI 集成

### GitHub Actions 示例

```yaml
name: Fitness Check

on:
  pull_request:
    branches: [main]

jobs:
  fitness:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup LEE
        uses: lee-framework/setup@v1

      - name: Run Fitness Check (Product)
        run: |
          lee fitness run \
            --rule-path spec-global/departments/product/fitness-rules/feat-freeze-rules.yaml \
            --target spec/requirements/SRC-024/FEAT-SRC-024-001__xxx.md \
            --mode enforce

      - name: Run Fitness Check (Dev)
        run: |
          lee fitness run \
            --rule-path spec-global/departments/dev/fitness-rules/feature-delivery-rules.yaml \
            --target .workflow/evidence-pack-xxx/evidence_pack.json \
            --mode enforce

      - name: Run Fitness Check (QA)
        run: |
          lee fitness run \
            --rule-path spec-global/departments/qa/fitness-rules/test-set-completion-rules.yaml \
            --target spec/qa/test-sets/ts-user-auth.yaml \
            --mode enforce
```

---

## 10. 与现有 FEAT 的对应关系

| FEAT ID | 标题 | 状态 | 对应产出 |
|---------|------|------|----------|
| FEAT-SRC-024-001 | Fitness Rule Schema 定义 | frozen | fitness_rule.schema.json |
| FEAT-SRC-024-002 | Fitness Executor 核心实现 | frozen | skill.governance.fitness_executor |
| FEAT-SRC-024-003 | Hard Gate 与 Quality Signal 分层 | frozen | gate_template.governance.fitness_gate |
| FEAT-SRC-024-004 | Fitness Result 结构化输出 | frozen | fitness_result schema |
| FEAT-SRC-024-005 | CLI 与 CI 集成 | frozen | lee fitness run command |

---

## 11. 下一步行动

### 11.1 待创建文件

- [ ] `spec-global/departments/product/gates/fitness-gate/v1/gate.yaml`
- [ ] `spec-global/departments/qa/gates/fitness-gate/v1/gate.yaml`
- [ ] `spec-global/departments/dev/gates/fitness-gate/v1/gate.yaml`
- [ ] `spec-global/departments/dev/fitness-rules/smoke-entry-rules.yaml`

### 11.2 Workflow 集成

- [ ] 更新 `raw-to-src` workflow 添加 Fitness Check
- [ ] 更新 `epic-to-feat` workflow 添加 Fitness Check
- [ ] 更新 `test-set-production` workflow 添加 Fitness Check
- [ ] 更新 `test-plan-l2` workflow 添加 Fitness Check
- [ ] 更新 `feature-delivery-l2` workflow 添加 Fitness Check

### 11.3 实现优先级

1. **P0 (MVP)**:
   - Dev 部门 Evidence Pack Fitness Check
   - Dev 部门 Smoke Entry Fitness Check

2. **P1**:
   - Product 部门 SRC Freeze Fitness Check
   - Product 部门 FEAT Freeze Fitness Check

3. **P2**:
   - QA 部门 Test Set Completion Fitness Check
   - QA 部门 Test Run Exit Fitness Check

---

## 12. 总结

Fitness Function 作为跨部门的通用治理能力，具有以下特点：

1. **通用性**: Fitness Executor 不绑定特定部门
2. **可配置**: 各部门定义自己的 Fitness Rules
3. **结构化**: fitness_result 符合统一 schema
4. **可集成**: CLI 和 CI 都可直接调用
5. **可追溯**: 与现有 FEAT 链完整对应

通过这种设计，Fitness Function 成为 LEE 框架的**完成条件防腐层**，确保各部门交付物满足质量标准。
