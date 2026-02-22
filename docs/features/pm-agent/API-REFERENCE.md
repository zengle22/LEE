# PM Agent API Reference

> **作者**: LEE Team
> **日期**: 2026-02-20
> **版本**: v1.0.0
> **分类**: API 文档

Complete API documentation for all PM Agent components.

## Table of Contents

1. [Decision Engine](#decision-engine)
2. [Intent Classifier](#intent-classifier)
3. [Param Mapper](#param-mapper)
4. [Permission Checker](#permission-checker)
5. [Security Manager](#security-manager)
6. [Cache Manager](#cache-manager)
7. [API Wrapper](#api-wrapper)
8. [PMAgentRuntime](#pmagentruntime)

---

## Decision Engine

### Overview

The `DecisionEngine` orchestrates the decision-making pipeline by coordinating Intent Classifier, Param Mapper, and Permission Checker.

### Class: DecisionEngine

```python
from lee.orchestrator.execution.pm_agent.decision_engine import DecisionEngine

engine = DecisionEngine(
    intent_classifier=classifier,
    param_mapper=mapper,
    permission_checker=checker,
    enable_fallback=True
)
```

#### Constructor Parameters

- `intent_classifier` (IntentClassifier): Intent classification component
- `param_mapper` (ParamMapper): Parameter mapping component
- `permission_checker` (PermissionChecker): Permission validation component
- `enable_fallback` (bool): Enable fallback strategies (default: True)

#### Methods

##### decide()

```python
async def decide(
    user_input: str,
    context: Optional[ConversationContext] = None
) -> Decision
```

Make a decision from user input.

**Parameters:**
- `user_input` (str): User's natural language input
- `context` (ConversationContext, optional): Conversation context

**Returns:** `Decision` object

**Raises:**
- `IntentClassificationError`: If intent classification fails
- `PermissionDeniedError`: If permission is denied
- `ParameterExtractionError`: If parameter extraction fails

**Example:**

```python
decision = await engine.decide("运行下一步", context)
print(f"Action: {decision.action}")
print(f"Allowed: {decision.allowed}")
print(f"Confidence: {decision.intent.confidence}")
```

##### get_metrics()

```python
def get_metrics() -> Dict[str, Any]
```

Get decision engine metrics.

**Returns:** Dictionary with metrics:
- `total_decisions` (int): Total decisions made
- `successful_decisions` (int): Successful decisions
- `failed_decisions` (int): Failed decisions
- `success_rate` (float): Success rate (0-1)
- `fallback_count` (int): Fallback activations
- `fallback_rate` (float): Fallback rate (0-1)

---

## Intent Classifier

### Overview

The `IntentClassifier` identifies user intent using rule-based pattern matching and LLM fallback.

### Class: IntentClassifier

```python
from lee.orchestrator.execution.pm_agent.intent_classifier import IntentClassifier

classifier = IntentClassifier(
    config=config,
    llm_executor=llm_executor,
    default_department=None
)
```

#### Methods

##### classify()

```python
async def classify(
    user_input: str,
    context: Optional[ConversationContext] = None
) -> Intent
```

Classify user intent.

**Parameters:**
- `user_input` (str): User's natural language input
- `context` (ConversationContext, optional): Conversation context

**Returns:** `Intent` object

**Example:**

```python
intent = await classifier.classify("当前状态")
print(f"Type: {intent.type}")
print(f"Confidence: {intent.confidence}")
```

---

## Param Mapper

### Overview

The `ParamMapper` extracts workflow parameters from natural language using LLM.

### Class: ParamMapper

```python
from lee.orchestrator.execution.pm_agent.param_mapper import ParamMapper

mapper = ParamMapper(
    llm_executor=llm_executor,
    template_manager=template_manager,
    max_retries=2
)
```

#### Methods

##### map_params()

```python
async def map_params(
    user_input: str,
    intent: Intent,
    context: Optional[ConversationContext] = None
) -> WorkflowParams
```

Extract workflow parameters.

**Parameters:**
- `user_input` (str): User's natural language input
- `intent` (Intent): Classified intent
- `context` (ConversationContext, optional): Conversation context

**Returns:** `WorkflowParams` object

---

## Permission Checker

### Overview

The `PermissionChecker` validates intents against allowed tools and constitution rules.

### Class: PermissionChecker

```python
from lee.orchestrator.execution.pm_agent.permission_checker import PermissionChecker

checker = PermissionChecker(
    config=config,
    default_department=None
)
```

#### Methods

##### check()

```python
def check(
    intent: Intent,
    context: Optional[ConversationContext] = None
) -> bool
```

Check if intent is allowed.

**Parameters:**
- `intent` (Intent): Intent to check
- `context` (ConversationContext, optional): Conversation context

**Returns:** `True` if allowed

**Raises:** `PermissionDeniedError` if not allowed

---

## Security Manager

### Overview

The `SecurityManager` provides input sanitization, prompt injection detection, rate limiting, and audit logging.

### Class: SecurityManager

```python
from lee.orchestrator.execution.pm_agent.security import SecurityManager, SecurityConfig

config = SecurityConfig(
    max_input_length=5000,
    rate_limit_window=60,
    rate_limit_max_requests=100
)

security = SecurityManager(config)
```

#### Methods

##### sanitize_and_validate_input()

```python
def sanitize_and_validate_input(
    user_input: str,
    session_id: Optional[str] = None
) -> str
```

Sanitize and validate user input.

**Parameters:**
- `user_input` (str): Raw user input
- `session_id` (str, optional): Session ID for rate limiting

**Returns:** Sanitized input

**Raises:** `SecurityError` if validation fails

##### validate_output()

```python
def validate_output(
    output: str,
    user_input: str,
    session_id: Optional[str] = None
) -> bool
```

Validate LLM output.

**Parameters:**
- `output` (str): LLM output
- `user_input` (str): Original user input
- `session_id` (str, optional): Session ID

**Returns:** `True` if valid

**Raises:** `SecurityError` if validation fails

---

## Data Models

### Intent

```python
@dataclass
class Intent:
    type: IntentType
    confidence: float
    reasoning: str
    matched_pattern: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### WorkflowParams

```python
@dataclass
class WorkflowParams:
    workflow_ref: Optional[str] = None
    step_id: Optional[str] = None
    gate_id: Optional[str] = None
    params: Dict[str, Any] = field(default_factory=dict)
    approval_comment: Optional[str] = None
    confidence: float = 0.0
```

### Decision

```python
@dataclass
class Decision:
    intent: Intent
    params: WorkflowParams
    action: str
    allowed: bool = True
    denial_reason: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
```

### ConversationContext

```python
@dataclass
class ConversationContext:
    session_id: str
    user_id: Optional[str] = None
    department: Optional[str] = None
    history: List[Dict[str, Any]] = field(default_factory=list)
    current_workflow_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
```

---

## Exception Handling

### Exception Hierarchy

```
PMAgentException (base)
├── IntentClassificationError
├── ParameterExtractionError
├── PermissionDeniedError
├── ConfigurationError
├── SecurityError
├── LLMExecutionError
├── APIExecutionError
└── WorkflowDiscoveryError
```

### Usage Example

```python
from lee.orchestrator.execution.pm_agent.exceptions import *

try:
    decision = await engine.decide(user_input, context)
except PermissionDeniedError as e:
    print(f"Permission denied: {e.message}")
    print(f"Action: {e.action}")
    print(f"Required: {e.required_permission}")
except IntentClassificationError as e:
    print(f"Classification failed: {e.message}")
except ParameterExtractionError as e:
    print(f"Parameter extraction failed: {e.message}")
```

---

## Configuration

### Intent Classifier Config

```yaml
# config/intent_classifier.yaml

intents:
  query_status:
    description: Query workflow status
    llm_fallback: true
    allowed_tools:
      - lee.workflow.status
    patterns:
      - regex: '^(当前)?状态|status'
        priority: 1
        description: Status keywords

permissions:
  allowed_tools:
    - lee.workflow.run
    - lee.workflow.status
  denied_tools:
    - shell
    - git
```

### Loading Configuration

```python
from lee.orchestrator.execution.pm_agent.config import IntentClassifierConfig

config = IntentClassifierConfig(
    config_path="config/intent_classifier.yaml",
    project_root="."
)

# Validate configuration
errors = config.validate()
if errors:
    print(f"Configuration errors: {errors}")
```

---

For more detailed examples, see:
- [Quick Start Guide](QUICKSTART.md)
- [Usage Examples](EXAMPLES.md)
- [Security Guide](SECURITY-GUIDE.md)
