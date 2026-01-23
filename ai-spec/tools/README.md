# ai-spec Tools

## validate - Spec 校验工具

校验 ai-spec 文件（workflow、agent、contract）的语法和引用完整性。

### 安装

```bash
pip install -r requirements.txt
```

### 使用方法

```bash
# 校验单个文件
python validate.py specs/workflows/product-pipeline/v1/workflow.yaml

# 校验整个 specs 目录
python validate.py specs/

# 仅校验特定类型
python validate.py --type agent specs/
python validate.py --type workflow specs/
python validate.py --type contract specs/

# JSON 格式输出（CI 集成）
python validate.py --format json specs/

# 仅显示失败项
python validate.py --quiet specs/
```

### 退出码

| 码 | 含义 |
|----|------|
| 0 | 全部通过 |
| 1 | 存在校验失败 |
| 2 | 内部错误（文件不存在等） |

### 校验规则

| 校验器 | 说明 |
|--------|------|
| `syntax` | YAML/JSON 语法校验 |
| `workflow_refs` | workflow 引用的 agent 是否存在 |
| `agent_refs` | agent 的 schema_ref 是否存在 |
| `downstream_refs` | downstream agent 引用是否存在 |
| `schema_strict` | contract 是否有 `additionalProperties: false` |

### 输出示例

CLI 格式：
```
[PASS] agent search_agent@v1
[PASS] contract search_result@v1
[FAIL] workflow keyword_discovery@v1
  - agent analytics_agent@v1 not found

----------------------------------------
Total: 3 | Pass: 2 | Fail: 1 | Warn: 0
```

JSON 格式：
```json
{
  "summary": {
    "total": 3,
    "passed": 2,
    "failed": 1,
    "warned": 0,
    "success": false
  },
  "results": [...]
}
```

### 扩展校验器

新增校验规则只需：

1. 在 `validate/validators/` 创建新文件
2. 继承 `BaseValidator` 并实现 `validate()` 方法
3. 使用 `@ValidatorRegistry.register` 装饰器注册
4. 在 `validate/validators/__init__.py` 中导入

示例：

```python
from ..base import BaseValidator, ValidatorRegistry
from ..models import SpecType, ValidationIssue, ValidationResult

@ValidatorRegistry.register
class MyValidator(BaseValidator):
    name = "my_validator"
    description = "My custom validation"
    applies_to = [SpecType.AGENT]  # 或 [] 表示所有类型

    def validate(self, path, spec_type, content, result):
        if some_condition_failed:
            result.add_issue(ValidationIssue(
                message="Something is wrong",
                validator=self.name,
                severity="error",  # or "warning"
            ))
```

## Pre-commit Hook

项目已配置 Git pre-commit hook，在每次 `git commit` 时自动运行校验。

### 行为

- 校验通过：允许提交
- 校验失败：阻止提交并显示错误信息

### 跳过校验

```bash
git commit --no-verify -m "your message"
```

> ⚠️ 仅在必要时使用，如紧急修复或非 spec 文件变更。
