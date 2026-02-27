# LEE QA Module API Documentation

## Overview

The LEE QA module provides end-to-end test execution capabilities with:
- Multi-layer code validation (L1-L4)
- Error classification (code_issue vs system_issue)
- Automatic code fixing
- Local and Docker execution modes

## Installation

```bash
pip install -e .
```

## Quick Start

```python
from lee.qa.generator.playwright_gen import PlaywrightGenerator
from lee.qa.generator.base import GenerationRequest
from lee.qa.runner.local import LocalRunner
from lee.qa.runner.base import TestConfig

# 1. Generate test code
generator = PlaywrightGenerator()
request = GenerationRequest(
    test_cases=[{
        "case_id": "TEST-001",
        "title": "Login Test",
        "priority": "P0",
        "steps": [
            {"step_num": 1, "action": "Go to login", "expected": "Page loads"},
            {"step_num": 2, "action": "Submit form", "expected": "Login success"},
        ],
        "expected_result": "User logged in",
    }],
    base_url="http://localhost:3000",
)
result = generator.generate(request)

# 2. Save and execute
with open("test_script.py", "w") as f:
    f.write(result.code)

config = TestConfig(
    scripts=[Path("test_script.py")],
    base_url="http://localhost:3000",
    output_dir=Path("test_output"),
)
runner = LocalRunner(config)
test_result = runner.execute()
```

## Modules

### Generator Module

#### `PlaywrightGenerator`

```python
from lee.qa.generator.playwright_gen import PlaywrightGenerator
from lee.qa.generator.base import GenerationRequest

generator = PlaywrightGenerator(llm_client=None)  # Uses default LLM client

# Generate test code
request = GenerationRequest(
    test_cases=[...],
    base_url="http://localhost:3000",
    framework="playwright",
)
result = generator.generate(request)

# Result properties:
result.code         # str: Generated Python code
result.files        # Dict[str, str]: Files to write
result.validation   # ValidationResult: Validation results
result.retries      # int: Number of retries used
```

#### `GenerationRequest`

```python
from lee.qa.generator.base import GenerationRequest

request = GenerationRequest(
    test_cases=[...],      # List[Dict]: Test case definitions
    base_url="...",       # str: Base URL for tests
    framework="playwright",  # str: Framework name
    options={...},        # Dict[str, Any]: Optional parameters
)
```

#### Test Case Format

```python
{
    "case_id": "TEST-001",
    "title": "Test Title",
    "priority": "P0",      # P0, P1, P2, P3
    "type": "positive",    # positive, negative, boundary
    "preconditions": ["User logged in"],
    "steps": [
        {
            "step_num": 1,
            "action": "Click button",
            "expected": "Dialog appears",
        }
    ],
    "expected_result": "Action completed",
}
```

### Validator Module

#### Four-Layer Validation

```python
from lee.qa.validator.schema_validator import SchemaValidator
from lee.qa.validator.syntax_validator import SyntaxValidator
from lee.qa.validator.selector_validator import SelectorValidator
from lee.qa.validator.timeout_validator import TimeoutValidator

code = "..."  # Generated code

# L1: Schema validation (structure)
schema_result = SchemaValidator.validate(code)
schema_result.is_valid      # bool
schema_result.errors        # List[Dict]
schema_result.warnings      # List[Dict]

# L2: Syntax validation (AST)
syntax_result = SyntaxValidator.validate(code)

# L3: Selector quality
selector_result = SelectorValidator.validate(code)
selector_summary = SelectorValidator.validate_selectors_in_code(code)
selector_summary["avg_score"]  # float: 0-1 stability score

# L3: Timeout configuration
timeout_result = TimeoutValidator.validate(code)
```

#### `ValidationResult`

```python
result.is_valid        # bool: Overall validity
result.errors          # List[Dict]: Blocking errors
result.warnings        # List[Dict]: Non-blocking warnings
result.info            # List[Dict]: Informational messages
result.has_blocking_errors()  # bool
result.get_summary()   # Dict: Summary counts

# Merge multiple results
merged = ValidationResult.merge(result1, result2, result3)
```

### Classifier Module

#### `ErrorClassifier`

```python
from lee.qa.classifier.error_classifier import ErrorClassifier

# Classify an error
classification = ErrorClassifier.classify(
    error_message="Timeout waiting for selector [data-testid='submit']",
    context={"selector": "[data-testid='submit']", "page_elements": {...}},
)

# Properties:
classification.type           # str: "code_issue" | "system_issue" | "uncertain"
classification.category       # str: Specific error category
classification.confidence     # float: 0-1
classification.is_false_fail  # bool | None: True if test code bug
classification.suggested_action  # str: "auto_fix" | "file_bug" | "retry"
classification.explanation    # str: Human-readable explanation

# Batch classification
classifications = [
    ErrorClassifier.classify(msg) for msg in error_messages
]
stats = ErrorClassifier.get_statistics(classifications)
# stats["code_issue"], stats["system_issue"], stats["false_fail_rate"]
```

#### Error Types

**Code Issues (False Failures)**:
- `code_syntax`: Syntax errors
- `code_import`: Missing imports
- `code_api`: API usage errors
- `code_selector`: Selector errors
- `code_timeout`: Timeout configuration issues

**System Issues (True Failures)**:
- `system_assertion`: Assertion failures
- `system_network`: Network errors
- `system_server`: Server errors (5xx)
- `system_data`: Data mismatches

#### `ContextCollector`

```python
from lee.qa.classifier.context_collector import ContextCollector

# Collect context before test
context_before = ContextCollector.collect_before_test(
    page=page,
    selector="[data-testid='submit']",
)
# {"page_url": "...", "selector_exists": true, "page_elements": {...}}

# Collect context on error
context_on_error = ContextCollector.collect_on_error(page)

# Capture screenshot
screenshot_path = ContextCollector.capture_screenshot(
    page,
    path="/path/to/screenshot.png",
)
```

### Fixer Module

#### `AutoFixer`

```python
from lee.qa.fixer.auto_fixer import AutoFixer

# Check if fixable
if AutoFixer.can_fix(classification):
    fixed_code, success = AutoFixer.apply_fix(
        code=original_code,
        classification=classification,
        context=context,
    )

# Apply multiple fixes
fixed_code, summary = AutoFixer.apply_all_fixes(
    code=original_code,
    classifications=classifications,
    context=context,
)
# summary["applied"], summary["skipped"], summary["failed"]
```

### Runner Module

#### `LocalRunner`

```python
from lee.qa.runner.local import LocalRunner
from lee.qa.runner.base import TestConfig

config = TestConfig(
    scripts=[Path("test_script.py")],
    base_url="http://localhost:3000",
    output_dir=Path("output"),
    headless=True,
    timeout=30000,
    environment="local",
)

runner = LocalRunner(config)

# Check environment
env_checks = runner.check_environment()
# {"playwright": True, "chromium": True, "pytest": True}

# Execute tests
result = runner.execute()
```

#### `DockerRunner`

```python
from lee.qa.runner.docker import DockerRunner

runner = DockerRunner(config)
env_checks = runner.check_environment()
# {"docker": True, "docker_daemon": True, "image": True}

result = runner.execute()

# Build Docker image
runner.build_image(dockerfile=Path("Dockerfile.e2e"))
```

#### `TestConfig`

```python
config = TestConfig(
    scripts=[Path("test1.py"), Path("test2.py")],
    base_url="http://localhost:3000",
    output_dir=Path("output"),
    headless=True,
    timeout=30000,
    screenshot_dir=Path("output/screenshots"),
    trace_dir=Path("output/traces"),
    video_dir=Path("output/videos"),
    environment="local",
)
```

#### `TestResult`

```python
result.exit_code     # int: 0=success, 1=test failure, 2=infra error
result.total         # int: Total cases
result.passed        # int: Passed cases
result.failed        # int: Failed cases
result.skipped       # int: Skipped cases
result.duration_ms   # int: Total duration
result.cases         # List[CaseResult]: Individual results
result.report_path   # Path: Path to report file
result.error         # str | None: Error message if failed
```

#### `CaseResult`

```python
case.case_id           # str: Test case ID
case.status            # str: "passed" | "failed" | "skipped" | "invalid_run"
case.error             # str | None: Error message
case.error_type        # str | None: "code_issue" | "system_issue"
case.is_code_issue     # bool | None: True if code problem
case.exit_code         # int: Exit code for this case
case.duration_ms       # int: Duration in milliseconds
case.screenshot_path   # str | None: Path to screenshot
```

### CLI Commands

#### `test_runner run-e2e`

```bash
lee test-runner run-e2e \
    --suite smoke \
    --env test \
    --test-set test-cases.yaml \
    --out-dir ./output \
    --report-json report.json \
    --base-url http://localhost:3000 \
    --mode local  # or docker
```

**Options**:
- `--suite`: Test suite name
- `--env`: Target environment (test/staging/prod)
- `--test-set`: Path to test cases YAML
- `--out-dir`: Output directory for artifacts
- `--report-json`: Path for JSON report
- `--base-url`: Override base URL
- `--mode`: `local` or `docker`
- `--runner-script`: Path to Docker script (docker mode)
- `--docker-image`: Docker image name (docker mode)

**Exit Codes**:
- `0`: Success, at least one test ran
- `1`: Tests ran, some failed
- `2`: Infrastructure error
- `3`: Invalid arguments

#### `test_runner validate`

```bash
lee test-runner validate --code test_script.py
```

Validates test code quality using all validation layers.

#### `test_runner classify`

```bash
lee test-runner classify --error "Timeout waiting for selector"
```

Classifies an error message and shows details.

## Extending the Module

### Custom Generator

```python
from lee.qa.generator.base import BaseGenerator

class CypressGenerator(BaseGenerator):
    @property
    def name(self) -> str:
        return "cypress"

    @property
    def framework(self) -> str:
        return "cypress"

    def generate(self, request):
        return self._validate_and_retry(request)

    def _llm_generate(self, request):
        # Implement LLM generation for Cypress
        pass
```

### Custom Validator

```python
from lee.qa.validator.base import BaseValidator

class CustomValidator(BaseValidator):
    @classmethod
    def validate(cls, code: str) -> ValidationResult:
        result = ValidationResult()
        # Custom validation logic
        return result
```

### Custom Runner

```python
from lee.qa.runner.base import BaseRunner

class CustomRunner(BaseRunner):
    @property
    def name(self) -> str:
        return "custom"

    def check_environment(self) -> Dict[str, bool]:
        return {"custom_check": True}

    def execute(self) -> TestResult:
        # Custom execution logic
        pass
```

## Configuration

### Environment Variables

- `BASE_URL`: Default base URL for tests
- `LEE_ENV`: Test environment (local/test/staging)
- `HEADLESS`: Run tests headless (true/false)
- `LLM_MODEL`: LLM model for code generation
- `LLM_API_KEY`: API key for LLM service

## Error Handling

### Validation Errors

```python
from lee.qa.validator.result import CodeGenerationError

try:
    result = generator.generate(request)
except CodeGenerationError as e:
    print(f"Generation failed: {e}")
    if e.last_validation:
        print(f"Last validation: {e.last_validation.errors}")
```

### Execution Errors

```python
result = runner.execute()

if result.exit_code == 2:
    # Infrastructure error
    print(f"Infra error: {result.error}")
elif result.failed > 0:
    # Test failures
    for case in result.cases:
        if case.status == "invalid_run":
            print(f"{case.case_id}: Code issue - {case.error}")
        elif case.status == "failed":
            print(f"{case.case_id}: System issue - {case.error}")
```

## Best Practices

1. **Use data-testid selectors** for maximum stability
2. **Set appropriate timeouts** (default: 30000ms, goto: 60000ms)
3. **Run validation** before execution to catch code issues early
4. **Use error classification** to distinguish code bugs from system bugs
5. **Check environment** before running tests
6. **Review screenshots** and traces for failed tests
7. **Use local mode** for development, Docker for CI/CD

## Troubleshooting

### "playwright module not found"
```bash
pip install playwright
playwright install chromium
```

### "Docker image not found"
```bash
docker build -t lee-e2e-runner:latest -f Dockerfile.e2e .
```

### "Selector timeout"
- Check if selector exists in page
- Use data-testid instead of class/text selectors
- Increase timeout in test code

### "False failures"
- Run `test_runner validate` to check code quality
- Use `test_runner classify` to understand errors
- Check if auto-fix can resolve the issue
