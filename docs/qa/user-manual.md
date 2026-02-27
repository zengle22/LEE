# LEE QA E2E Testing - User Manual

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [CLI Commands](#cli-commands)
5. [Writing Test Cases](#writing-test-cases)
6. [Running Tests](#running-tests)
7. [Understanding Results](#understanding-results)
8. [Troubleshooting](#troubleshooting)
9. [Best Practices](#best-practices)

---

## Introduction

LEE QA E2E Testing module provides end-to-end web testing capabilities using Playwright. It supports:

- **Local execution**: Run tests directly on your machine for faster development
- **Docker execution**: Run tests in isolated containers for CI/CD
- **Multi-layer validation**: 4-layer code quality validation (L1-L4)
- **Error classification**: Automatically distinguishes test code bugs from system bugs
- **Auto-fixing**: Automatically fixes common test code issues

---

## Installation

### Prerequisites

- Python 3.10+
- pip (Python package manager)

### Install Dependencies

```bash
# Install Python dependencies
pip install pytest playwright pyyaml jinja2

# Install Playwright browsers
playwright install chromium
```

### Install LEE QA Module

```bash
# Install from source
pip install -e /path/to/lee
```

### Docker Setup (Optional)

```bash
# Build Docker image
docker build -t lee-e2e-runner:latest -f Dockerfile.e2e .
```

---

## Quick Start

### 1. Create Your First Test Case

Create a YAML file `test-cases.yaml`:

```yaml
test_cases:
  - case_id: "LOGIN-001"
    title: "User Login"
    priority: "P0"
    type: "positive"
    preconditions:
      - "User is registered"
      - "Login page is accessible"
    steps:
      - step_num: 1
        action: "Navigate to login page"
        expected: "Page loads successfully"
      - step_num: 2
        action: "Enter valid credentials"
        expected: "Credentials are accepted"
      - step_num: 3
        action: "Click login button"
        expected: "User is logged in"
    expected_result: "User successfully logs in"
```

### 2. Generate Test Script

```bash
# Generate test script from test cases
lee test-runner generate \
    --test-cases test-cases.yaml \
    --output scripts/test_login.py \
    --base-url http://localhost:3000
```

### 3. Run Tests

```bash
# Run tests locally
lee test-runner run-e2e \
    --suite smoke \
    --env test \
    --test-set scripts/test_login.py \
    --out-dir ./output \
    --report-json report.json \
    --mode local
```

---

## CLI Commands

### run-e2e

Execute E2E tests and generate a report.

```bash
lee test-runner run-e2e [OPTIONS]
```

**Options:**

| Option | Description | Required |
|--------|-------------|----------|
| `--suite` | Test suite name (smoke, regression, etc.) | Yes |
| `--env` | Target environment (test, staging, prod) | Yes |
| `--test-set` | Path to test cases YAML or test script | Yes |
| `--out-dir` | Output directory for artifacts | Yes |
| `--report-json` | Path for JSON report | Yes |
| `--base-url` | Override base URL | No |
| `--mode` | Execution mode: `local` or `docker` | No (default: docker) |
| `--docker-image` | Docker image name (docker mode) | No |

**Examples:**

```bash
# Local execution
lee test-runner run-e2e \
    --suite smoke \
    --env test \
    --test-set test-cases.yaml \
    --out-dir ./output \
    --report-json report.json \
    --mode local

# Docker execution
lee test-runner run-e2e \
    --suite regression \
    --env staging \
    --test-set test-cases.yaml \
    --out-dir ./output \
    --report-json report.json \
    --mode docker \
    --docker-image lee-e2e-runner:latest

# With custom base URL
lee test-runner run-e2e \
    --suite smoke \
    --env test \
    --test-set test-cases.yaml \
    --out-dir ./output \
    --report-json report.json \
    --base-url http://staging.example.com
```

**Exit Codes:**

- `0`: Success, at least one test ran
- `1`: Tests ran, some failed
- `2`: Infrastructure error
- `3`: Invalid arguments

### validate

Validate generated test code quality.

```bash
lee test-runner validate --code scripts/test_login.py
```

**Output:**

```
✓ L1_Schema: 0 errors, 0 warnings
✓ L2_Syntax: 0 errors, 0 warnings
✓ L3_Selector: 0 errors, 1 warnings
  - WARN: selector_quality: Average selector stability score: 0.65 < 0.7
✓ L3_Timeout: 0 errors, 0 warnings
```

### classify

Classify an error message.

```bash
lee test-runner classify --error "Timeout waiting for selector"
```

**Output:**

```
Type: code_issue
Category: code_selector
Confidence: 0.85
Is False Fail: True
Suggested Action: verify_selector
Explanation: 选择器在页面中未找到，可能是选择器错误
```

---

## Writing Test Cases

### Test Case Format

```yaml
test_cases:
  - case_id: "TEST-001"          # Unique identifier
    title: "Test Title"           # Human-readable title
    priority: "P0"               # P0, P1, P2, P3
    type: "positive"             # positive, negative, boundary, performance
    preconditions:              # Optional preconditions
      - "Precondition 1"
      - "Precondition 2"
    steps:                       # Test steps
      - step_num: 1
        action: "Action description"
        expected: "Expected result"
      - step_num: 2
        action: "Another action"
        expected: "Another expectation"
    expected_result: "Overall expected outcome"
```

### Priority Levels

| Priority | Description | Example |
|----------|-------------|---------|
| P0 | Critical path, must work | Login, checkout |
| P1 | Important features | Search, profile |
| P2 | Nice to have | Settings, preferences |
| P3 | Edge cases | Pagination limits |

### Test Types

| Type | Description | Example |
|------|-------------|---------|
| positive | Normal flow scenarios | Successful login |
| negative | Error scenarios | Invalid credentials |
| boundary | Boundary conditions | Maximum input length |
| performance | Performance requirements | Page load time |

---

## Running Tests

### Local Mode

Best for development and debugging.

```bash
lee test-runner run-e2e \
    --suite smoke \
    --env test \
    --test-set test-cases.yaml \
    --out-dir ./output \
    --report-json report.json \
    --mode local
```

**Advantages:**
- Faster execution
- Easier debugging
- No Docker dependency

### Docker Mode

Best for CI/CD and consistent environments.

```bash
lee test-runner run-e2e \
    --suite smoke \
    --env test \
    --test-set test-cases.yaml \
    --out-dir ./output \
    --report-json report.json \
    --mode docker
```

**Advantages:**
- Isolated environment
- Consistent across machines
- Easy CI/CD integration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `BASE_URL` | Application base URL | http://localhost:3000 |
| `HEADLESS` | Run headless (true/false) | true |
| `TIMEOUT` | Default timeout in ms | 30000 |
| `LEE_ENV` | Environment name | local |

---

## Understanding Results

### Report Structure

```json
{
  "suite": "smoke",
  "env": "test",
  "total": 3,
  "passed": 2,
  "failed": 1,
  "skipped": 0,
  "cases": [
    {
      "id": "TEST-001",
      "status": "passed",
      "duration_ms": 5234,
      "error_message": null,
      "error_type": null,
      "screenshot": null
    },
    {
      "id": "TEST-002",
      "status": "failed",
      "duration_ms": 3102,
      "error_message": "AssertionError: Expected 'Success' but found 'Error'",
      "error_type": "system_assertion",
      "screenshot": "screenshots/TEST-002.png"
    }
  ]
}
```

### Status Values

| Status | Description |
|--------|-------------|
| `passed` | Test passed successfully |
| `failed` | Test failed (system issue) |
| `skipped` | Test was skipped |
| `invalid_run` | Test failed due to code issue |

### Error Types

**Code Issues (False Failures):**
- `code_syntax`: Syntax error in test code
- `code_import`: Missing import
- `code_api`: Wrong API usage
- `code_selector`: Selector not found
- `code_timeout`: Timeout configuration issue

**System Issues (True Failures):**
- `system_assertion`: Assertion failed
- `system_network`: Network error
- `system_server`: Server error (5xx)
- `system_data`: Data mismatch

---

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

1. Check if the selector exists in the page
2. Use `data-testid` attributes instead of class/text
3. Increase timeout in test code

### "False failures"

If tests fail due to code issues:

1. Run validation:
   ```bash
   lee test-runner validate --code your_test.py
   ```

2. Check error type:
   ```bash
   lee test-runner classify --error "your error message"
   ```

3. If `is_false_fail: True`, the test code needs fixing

### Tests pass locally but fail in Docker

- Check if BASE_URL is accessible from Docker
- Verify `--network host` is set for Docker
- Check for timing issues (increase timeouts)

---

## Best Practices

### 1. Use Stable Selectors

```python
# Good - data-testid
page.locator("[data-testid='submit']").click()

# Fair - id
page.locator("#submit").click()

# Poor - class
page.locator(".btn-primary").click()

# Poor - text
page.locator("text=Submit").click()
```

### 2. Add data-testid Attributes

Work with developers to add `data-testid` attributes:

```html
<!-- Add to production code -->
<button data-testid="submit">Submit</button>
```

### 3. Set Appropriate Timeouts

```python
# Set default timeout
page.set_default_timeout(30000)

# Set longer timeout for page loads
page.goto("http://example.com", timeout=60000)
```

### 4. Use Assertions

```python
# Good - explicit assertions
expect(page).to_have_title("Dashboard")
expect(page.locator("[data-testid='user']")).to_be_visible()

# Poor - no assertions
page.click("button")
```

### 5. Group Related Tests

```python
def test_login_success(page):
    """Test successful login."""
    # ...

def test_login_failure(page):
    """Test login with invalid credentials."""
    # ...
```

### 6. Add Docstrings

```python
def test_checkout_flow(page):
    """
    Test complete checkout flow.

    Steps:
    1. Add item to cart
    2. Proceed to checkout
    3. Fill payment info
    4. Confirm order

    Expected: Order is created successfully
    """
    # ...
```

### 7. Handle Async Operations

```python
# Wait for element to be visible
page.locator("[data-testid='loading']").wait_for(state="hidden")

# Wait for navigation
page.wait_for_url("*/dashboard")

# Wait for API response
page.wait_for_response("**/api/data")
```

---

## Appendix

### File Structure

```
lee/
├── qa/                           # QA module
│   ├── generator/               # Code generators
│   ├── runner/                  # Test runners
│   ├── validator/               # Code validators
│   ├── classifier/              # Error classifier
│   └── fixer/                   # Auto fixer
├── docs/qa/                     # Documentation
│   ├── api.md                   # API reference
│   └── user-manual.md           # This file
└── tests/qa/                    # Tests
    ├── fixtures/                # Test data
    ├── generator/               # Generator tests
    ├── validator/               # Validator tests
    ├── classifier/              # Classifier tests
    ├── runner/                  # Runner tests
    └── integration/             # Integration tests
```

### Exit Codes Reference

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | Proceed |
| 1 | Test failures | Review failed tests |
| 2 | Infrastructure error | Fix environment/Docker |
| 3 | Invalid arguments | Check command syntax |

### Support

For issues and questions:
- Check `docs/qa/api.md` for API documentation
- Run `lee test-runner --help` for command help
- Review test logs in `output/` directory
