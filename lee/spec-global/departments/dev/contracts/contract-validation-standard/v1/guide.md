# 契约验证标准 (Contract Validation Standard)

**版本**: v1.1
**更新日期**: 2026-02-24
**适用范围**: LEE 框架所有工作流

---

## 概述

LEE 框架的工作流系统通过**契约验证**确保输入和输出的数据结构符合预期。本文档定义了契约验证的标准配置和处理策略。

---

## 验证层次

```
┌─────────────────────────────────────────────────────────────┐
│                    契约验证体系                              │
├─────────────────────────────────────────────────────────────┤
│  Level 1: 工作流启动前 - 输入契约验证                         │
│  Level 2: 步骤执行前 - 输入契约验证                           │
│  Level 3: 步骤执行后 - 输出契约验证（含重试机制）              │
└─────────────────────────────────────────────────────────────┘
```

---

## 验证类型

| 验证类型 | 说明 | 实现类 |
|---------|------|--------|
| **Schema 验证** | 基于 JSON Schema 验证数据结构 | `SchemaValidator` |
| **文件存在验证** | 验证引用的文件是否存在 | `file_exists` check |
| **契约完整性验证** | 检查工作流所需契约是否完整 | `ContractDiscovery.validate_workflow_inputs()` |
| **输出规则验证** | 自定义表达式验证输出数据 | `validation_rules` |

---

## 处理策略

契约验证失败有 **3 种处理策略**：

| 策略 | 行为 | 使用场景 | 默认重试次数 |
|------|------|----------|-------------|
| **`block`** | 阻塞执行，工作流无法继续 | 关键输入契约验证失败 | 0 |
| **`warn`** | 仅警告，记录后继续执行 | 非关键输出验证失败 | 0 |
| **`retry`** | 自动重试（需配置次数） | 输出验证失败（L3 步骤） | 3 |

---

## 输出验证重试机制

### 重试流程

```
Step Execution
     ↓
Output Validation ← FAILED
     ↓
  [RETRY] 判断重试次数 < max_retries?
     ↓
  YES → 等待 retry_delay_seconds → 重新执行步骤
     ↓
  NO → 标记步骤失败，终止工作流
```

### 重试配置

```yaml
# 在模板的 step_output_validation 中配置
step_output_validation:
  <step_id>:
    contract_ref: <schema_path>
    on_failure: retry        # 启用重试
    max_retries: 3           # 最多重试 3 次
    retry_delay_seconds: 5   # 重试间隔 5 秒
```

### 重试策略

| 参数 | 默认值 | 说明 |
|------|-------|------|
| `max_retries` | 3 | 最大重试次数（不包括首次尝试） |
| `retry_delay_seconds` | 5 | 基础延迟时间（秒） |
| `exponential_backoff` | true | 是否启用指数退避 |
| `jitter` | true | 是否添加随机抖动 |

### 重试日志示例

```
[OutputValidation] Step implement output validation failed: Missing required field 'files_changed'
[OutputValidation] Retry attempt 1/3 for step implement...
[OutputValidation] Retry attempt 2/3 for step implement...
[OutputValidation] Step implement output validation passed after 2 attempts
```

---

## 工作流契约验证配置

### 配置结构

```yaml
contracts:
  inputs:
    - <input_name>:
        path: <path_to_schema>
        description: <description>
        validation:
          enabled: true
          on_failure: block|warn|retry
          schema_validation:
            - field: <field_path>
              required: true
              type: string|number|boolean
              pattern: <regex>
              allowed_values: [...]
              range: [min, max]
              check: file_exists|url_exists
          required_fields: [...]
  outputs:
    - <output_name>:
        path: <path_to_schema>
        description: <description>
        validation:
          enabled: true
          on_failure: warn|block|retry
          max_retries: 3
          retry_delay_seconds: 5
          required_artifacts: [...]

# 步骤级别输出验证
step_output_validation:
  <step_id>:
    contract_ref: <schema_path>
    on_failure: retry
    max_retries: 3
    required_fields: [...]
    validation_rules:
      - name: "<rule_name>"
        expression: "<expression>"
        error_message: "<error description>"
        is_blocking: true|false
```

### L2 v3 示例

```yaml
# lee/spec-global/departments/dev/workflows/feature/v3/workflow.yaml
contracts:
  inputs:
    - frozen_dev_package:
        path: ../../contracts/frozen-dev-package-contract/v1/schema.json
        validation:
          enabled: true
          on_failure: block
          schema_validation:
            - field: contract_type
              required: true
              allowed_values: ["frozen-dev-package"]
            - field: package_content.prd_ref
              required: true
              check: file_exists
  outputs:
    - l2_outputs:
        validation:
          enabled: true
          on_failure: warn
          required_artifacts:
            - output/api-contract.yaml
```

### L3 v3 示例（含重试）

```yaml
# lee/spec-global/departments/dev/workflows/templates/l3/task-l3-v3-template.yaml
step_output_validation:
  # 步骤 3: 实现输出验证
  implement:
    contract_ref: ../../contracts/code-diff/v1/schema.json
    on_failure: retry
    max_retries: 3
    retry_delay_seconds: 5
    required_fields:
      - files_changed
      - diff_summary

  # 步骤 4: 测试输出验证
  run_tests:
    contract_ref: ../../contracts/test-report/v1/schema.json
    on_failure: retry
    max_retries: 3
    validation_rules:
      - name: "all_tests_passed"
        expression: "output.test_results.failed == 0"
        error_message: "所有测试必须通过才能继续"
        is_blocking: true
      - name: "min_coverage"
        expression: "output.coverage.percentage >= 80"
        error_message: "测试覆盖率必须达到 80%"
        is_blocking: false
```

---

## 当前覆盖情况

### L1 工作流（产品级）

| 工作流 | 输入验证 | 输出验证 | 状态 |
|--------|---------|---------|------|
| N/A | N/A | N/A | ⚠️ 暂无 L1 级别工作流 |

### L2 工作流（部门级）

| 工作流 | 输入验证 | 输出验证 | 重试支持 | 状态 |
|--------|---------|---------|---------|------|
| `workflow.dev.feature_l2_v3` | ✅ frozen_dev_package | ✅ l2_outputs | ❌ | 已配置 |

### L3 工作流（任务级）

| 模板 | 输入验证 | 输出验证 | 重试支持 | 状态 |
|------|---------|---------|---------|------|
| `template.dev.task_l3_v3` | ✅ frozen_dev_package | ✅ l3_outputs | ✅ | 已配置 |

---

## 代码实现

### 验证器基类

```python
# src/lee/orchestrator/execution/validators/base.py
class Validator(ABC):
    @abstractmethod
    def validate(self, data: Any, config: Dict) -> ValidationResult:
        """执行验证，返回 ValidationResult"""
        pass
```

### Schema 验证器

```python
# src/lee/orchestrator/execution/schema_validator.py
class SchemaValidator(Validator):
    def validate(self, data: Any, config: Dict) -> ValidationResult:
        """使用 jsonschema 验证数据结构"""
        ...
```

### 输出验证（含重试）

```python
# src/lee/orchestrator/execution/runners/base.py
async def _validate_step_output_with_retry(
    self, ctx, step, output_data, workflow_id
) -> tuple[bool, Optional[ValidationResult], int]:
    """
    验证步骤输出，支持重试机制

    Returns:
        (passed, validation_result, attempt_count)
    """
    ...
```

---

## 验证失败处理

### 1. 输入契约验证失败 (on_failure: block)

```
Workflow Start
     ↓
Input Validation ← FAILED
     ↓
  [BLOCK] 工作流无法启动
     ↓
Return Validation Error
```

### 2. 输出契约验证失败 (on_failure: warn)

```
Step Execution
     ↓
Output Validation ← FAILED
     ↓
  [WARN] 记录警告，继续执行
     ↓
Next Step / Complete
```

### 3. 输出契约验证失败 (on_failure: retry)

```
Step Execution
     ↓
Output Validation ← FAILED
     ↓
Attempt 1/3 → FAILED → Wait 5s
     ↓
Attempt 2/3 → FAILED → Wait 10s (指数退避)
     ↓
Attempt 3/3 → FAILED
     ↓
  [FAILED] 标记步骤失败，终止工作流
```

---

## 最佳实践

### 1. 关键输入使用 `block` 策略

```yaml
validation:
  on_failure: block  # 确保输入正确，避免垃圾进垃圾出
```

### 2. L3 步骤输出使用 `retry` 策略

```yaml
step_output_validation:
  implement:
    on_failure: retry  # 允许 Agent 重试生成正确的输出
    max_retries: 3
```

### 3. 非关键输出使用 `warn` 策略

```yaml
validation:
  on_failure: warn  # 输出问题不阻塞，允许人工干预
```

### 4. 提供清晰的错误消息

```yaml
schema_validation:
  - field: metadata.package_id
    required: true
    pattern: "^FPKG-\\d{8}-\\d{3}$"
    error_message: "package_id 格式应为 FPKG-YYYYMMDD-NNN"
```

### 5. 使用验证规则进行业务逻辑检查

```yaml
validation_rules:
  - name: "all_tests_passed"
    expression: "output.test_results.failed == 0"
    error_message: "所有测试必须通过才能继续"
    is_blocking: true
```

---

## 下一步工作

### 已完成 (v1.1)

- [x] L2 v3 输入/输出契约验证配置
- [x] L3 v3 输入/输出契约验证配置
- [x] 输出验证重试机制实现
- [x] 步骤级别验证规则配置

### 待补充

- [ ] 各步骤输出的契约 schema 定义
- [ ] 契约验证的单元测试覆盖
- [ ] 验证失败时的自动修复建议

### 待增强

- [ ] 支持自定义验证器插件
- [ ] 契约版本兼容性检查
- [ ] 验证报告的可视化展示
- [ ] 重试策略的可视化监控

---

**维护**: Dev Workflow Team
**联系方式**: 见 Dev 部门宪法
