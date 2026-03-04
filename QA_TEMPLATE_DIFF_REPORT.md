# QA 模板文件差异分析报告

**日期**: 2026-03-04  
**分析范围**: spec-global/departments/qa/workflows/templates/

---

## 一、文件清单

### test-set-l3-template 文件 (3个)

| 文件名 | 版本 | 大小 | 状态 |
|--------|------|------|------|
| test-set-l3-template.yaml | 1.1 | 387行 | 主文件 |
| test-set-l3-template-v1.1.yaml | 1.1 | 387行 | 与主文件**完全相同** |
| test-set-production-l3-template.yaml | - | - | 未分析 |

### test-plan-l2-template 文件 (2个)

| 文件名 | 版本 | phases数量 | 状态 |
|--------|------|------------|------|
| test-plan-l2-template.yaml | 2.0 | 8个 | 旧版本 |
| test-plan-l2-template-v2.1.yaml | 2.1 | 9个 | 新版本 |

---

## 二、test-set-l3-template 对比

### 结论

`test-set-l3-template.yaml` 和 `test-set-l3-template-v1.1.yaml` **内容完全相同**。

### 建议

可以**删除** `test-set-l3-template-v1.1.yaml`，保留 `test-set-l3-template.yaml` 作为主文件。

```bash
# 删除重复文件
rm spec-global/departments/qa/workflows/templates/test-set-l3-template-v1.1.yaml
```

---

## 三、test-plan-l2-template 详细对比

### 3.1 基本信息对比

| 属性 | v2.0 | v2.1 | 变化 |
|------|------|------|------|
| version | "2.0" | "2.1" | 升级 |
| phases数量 | 8个 | 9个 | +1 |
| description | 8 phases | 9 phases | 更新 |

### 3.2 phases 对比

```
v2.0 phases:                    v2.1 phases:
1. test_run_init                1. test_run_init
2. env_provision                2. env_provision
3. env_check                    3. env_check
4. test_set_execution           4. test_set_execution
5. bug_summary                  5. l3_output_validation (新增)
6. test_report                  6. bug_summary
7. exit_evaluation              7. test_report
8. retrospective                8. exit_evaluation
                                9. retrospective
```

### 3.3 v2.1 新增内容详解

#### 1. 新增 phase: l3_output_validation

```yaml
- id: l3_output_validation
  name: "L3 Output Validation"
  description: |
    Validate L3 outputs for schema compliance and data integrity.
    Checks: required fields, status enumeration, evidence linkage.
  default_complexity: S
  depends_on: ["test_set_execution"]
  validation_rules:
    - id: require_expected_fields
      description: "All L3 outputs must have required fields"
      severity: error
      fail_on_violation: true
    - id: status_enum_check
      description: "Status must be one of: completed, failed, skipped, invalid_run"
      severity: error
      fail_on_violation: true
    - id: evidence_link_consistency
      description: "completed/failed status must have valid evidence linkage"
      severity: error
      fail_on_violation: true
    - id: invalid_run_reporting
      description: "Invalid runs must have invalid_run_reason"
      severity: warning
      fail_on_violation: false
  on_failure:
    action: mark_l2_invalid_run
    report_all_invalid_runs: true
    allow_partial_summary: true
```

#### 2. 新增顶级字段: execution_mode

```yaml
execution_mode:
  description: "Controls L3 behavior_compliance enforcement level"
  default: enforce
  inherit_from_env: true
  modes:
    enforce:
      description: "All L3s use enforce mode"
    warn:
      description: "All L3s use warn mode (testing only)"
  prod_enforce: true  # Production always enforces
```

#### 3. 新增顶级字段: l2_invalid_run_reasons

```yaml
l2_invalid_run_reasons:
  description: "Reasons why L2 workflow itself is marked as invalid_run"
  reasons:
    - id: l3_output_schema_error
      description: "L3 output missing required fields"
    - id: l3_output_integrity_error
      description: "L3 output evidence linkage invalid"
    - id: critical_l3_invalid_run
      description: "Critical L3 marked as invalid_run"
    - id: env_check_blocked
      description: "env_check failed and blocked all L3s"
```

#### 4. 新增顶级字段: observability

包含 metrics 和 tracing 配置：
- l2_execution_duration
- l3_instances_total
- l2_invalid_run_total
- test_set_execution_duration
- 追踪 spans: l2_execution, l3_spawning

#### 5. env_check phase 增强

v2.0:
```yaml
- id: env_check
  name: "Environment Check"
  description: "Orchestrator executes tool availability check"
  default_complexity: S
  depends_on: ["env_provision"]
```

v2.1:
```yaml
- id: env_check
  name: "Environment Check"
  description: |
    Orchestrator executes tool availability check.
    Must pass before spawning L3 instances.
  default_complexity: S
  depends_on: ["env_provision"]
  gate:
    type: auto_check
    on_pass: proceed_to_l3_spawning
    on_fail: block_l3_spawning
  outputs:
    - env_check_result  # pass | fail | degraded
```

#### 6. test_set_dependencies 增强

v2.0:
```yaml
test_set_dependencies:
  description: |
    Test Sets can have dependencies on each other based on module relationships.
    # ...
```

v2.1:
```yaml
test_set_dependencies:
  description: |
    Test Sets can have dependencies on each other based on module relationships.
    # ...
  format: dag  # Directed Acyclic Graph
  execution_mode: serial  # Serial execution by default
```

#### 7. l3_input_schema 增强

v2.1 新增字段:
- `execution_mode` (enforce | warn)

#### 8. l3_output_schema 增强

v2.1 新增字段:
- `invalid_run_reason` (Required if status == invalid_run)
- `compliance_result_path`

### 3.4 关键改进总结

| 改进项 | v2.0 | v2.1 | 重要性 |
|--------|------|------|--------|
| L3 输出验证 | ❌ | ✅ (新phase) | 高 |
| 执行模式控制 | ❌ | ✅ | 中 |
| L2 无效运行原因 | ❌ | ✅ | 中 |
| 可观测性 | ❌ | ✅ | 中 |
| 环境检查门禁 | ❌ | ✅ | 高 |
| DAG 格式支持 | ❌ | ✅ | 低 |

---

## 四、统一建议

### 方案 A: 保留 v2.1 (推荐)

**理由**: v2.1 包含重要的功能增强，特别是 L3 输出验证和门禁控制。

**操作**:
1. 删除 `test-plan-l2-template.yaml`
2. 重命名 `test-plan-l2-template-v2.1.yaml` → `test-plan-l2-template.yaml`

```bash
rm spec-global/departments/qa/workflows/templates/test-plan-l2-template.yaml
mv spec-global/departments/qa/workflows/templates/test-plan-l2-template-v2.1.yaml \
   spec-global/departments/qa/workflows/templates/test-plan-l2-template.yaml
```

### 方案 B: 保留两个版本

如果某些项目仍然依赖 v2.0，可以暂时保留两个版本，但在文件名中明确版本号。

```bash
# 重命名为清晰的版本号格式
mv test-plan-l2-template.yaml test-plan-l2-template-v2.0.yaml
mv test-plan-l2-template-v2.1.yaml test-plan-l2-template.yaml  # 默认使用最新
```

---

## 五、test-set 文件统一建议

由于两个文件内容完全相同，建议删除带版本号的文件：

```bash
rm spec-global/departments/qa/workflows/templates/test-set-l3-template-v1.1.yaml
```

或者，如果遵循版本号命名规范，可以：

```bash
# 保留带版本号的文件作为标准
mv test-set-l3-template.yaml test-set-l3-template-v1.1.yaml
```

---

## 六、最终统一后的文件结构

```
spec-global/departments/qa/workflows/templates/
├── test-plan-l2-template.yaml          # v2.1 (默认)
├── test-set-l3-template.yaml           # v1.1 (默认)
└── test-set-production-l3-template.yaml # 保持不变
```

或者 (带版本号格式):

```
spec-global/departments/qa/workflows/templates/
├── test-plan-l2-template-v2.1.yaml     # 默认使用
├── test-plan-l2-template-v2.0.yaml     # 向后兼容
├── test-set-l3-template-v1.1.yaml      # 统一使用带版本号格式
└── test-set-production-l3-template.yaml
```
