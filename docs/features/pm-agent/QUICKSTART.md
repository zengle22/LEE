# PM Agent Quick Start Guide

> **作者**: LEE Team
> **日期**: 2026-02-20
> **版本**: v1.0.0
> **分类**: 快速开始指南

Get started with PM Agent natural language processing in 5 minutes.

## Installation

PM Agent is included in LEE. Ensure you have:

```bash
# Install dependencies
pip install -r requirements.txt

# Configure LLM (optional, for natural language understanding)
export OPENAI_API_KEY="your-api-key"
# Or use local LLM
export LLM_BASE_URL="http://localhost:11434/v1"
export LLM_MODEL="llama2"
```

## Basic Usage

### 1. Using Chat CLI

The simplest way to use PM Agent is through the interactive chat:

```bash
# Start chat with LLM support
lee chat

# Start chat without LLM (basic mode)
lee chat --no-llm
```

**Example Session:**

```
Lee> 当前状态
✓ Action completed: get_state
📊 Workflow State:
  Status: running
  Current step: search_signals
  Ready steps: analyze_signals

Lee> 运行下一步
✓ Action completed: next_step
✓ Step executed: analyze_signals

Lee> 帮助
Available Commands:
  status, 当前状态          - Query workflow status
  run, 运行                - Execute next step
  ...
```

### 2. Using PM Agent Runtime

For programmatic usage:

```python
import asyncio
from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.llm_executor import LLMExecutor

async def main():
    # Initialize components
    store = SQLiteStore(".lee/lee.db")
    await store.connect()

    orchestrator = Orchestrator(store, project_root=".")
    llm_executor = LLMExecutor(profile="default")

    # Create PM Agent Runtime
    runtime = PMAgentRuntime(
        orchestrator=orchestrator,
        llm_executor=llm_executor,
        store=store,
        enable_decision_engine=True
    )

    # Process input
    result = await runtime.process_input(
        user_input="运行下一步",
        session_id="my_session"
    )

    print(f"Status: {result['status']}")
    print(f"Action: {result['action']}")
    print(f"Data: {result['data']}")

asyncio.run(main())
```

### 3. Using Decision Engine Directly

For maximum control:

```python
from lee.orchestrator.execution.pm_agent import (
    DecisionEngine,
    IntentClassifier,
    ParamMapper,
    PermissionChecker,
    ConversationContext,
)

# Initialize components
config = IntentClassifierConfig(project_root=".")
classifier = IntentClassifier(config, llm_executor)
mapper = ParamMapper(llm_executor, template_manager)
checker = PermissionChecker(config)

# Create decision engine
engine = DecisionEngine(
    intent_classifier=classifier,
    param_mapper=mapper,
    permission_checker=checker,
    enable_fallback=True
)

# Make decision
context = ConversationContext(session_id="session_123")
decision = await engine.decide("运行 search_signals", context)

print(f"Intent: {decision.intent.type}")
print(f"Action: {decision.action}")
print(f"Params: {decision.params.workflow_ref}, {decision.params.step_id}")
```

## Configuration

### Creating Custom Intents

Edit `config/intent_classifier.yaml`:

```yaml
intents:
  deploy_prod:
    description: Deploy to production
    llm_fallback: true
    allowed_tools:
      - lee.workflow.run
    requires_params: true
    patterns:
      - regex: '^(部署到生产|deploy.*prod)'
        priority: 1
        description: Deploy to production
```

### Department-Specific Configuration

```yaml
departments:
  dev:
    intents:
      fix_bug:
        description: Fix a bug
        patterns:
          - regex: '修复.*bug|fix.*bug'
            priority: 1

    permissions:
      allowed_tools:
        - lee.workflow.run
        - lee.context.query
      denied_tools:
        - shell
```

## Common Use Cases

### 1. Query Workflow Status

```python
result = await runtime.process_input("当前状态如何", session_id="...")
# Returns: workflow status, current step, ready steps
```

### 2. Execute Specific Step

```python
result = await runtime.process_input("运行 search_signals", session_id="...")
# Executes: search_signals step
```

### 3. Execute Next Step

```python
result = await runtime.process_input("继续", session_id="...")
# Executes: next available step
```

### 4. Approve Gate

```python
result = await runtime.process_input(
    "批准 gate_review，代码看起来不错",
    session_id="..."
)
# Approves: gate_review gate
```

### 5. List Workflows

```python
result = await runtime.process_input("有哪些工作流", session_id="...")
# Lists: all available workflows
```

## Best Practices

### 1. Session Management

Always use session IDs for multi-turn conversations:

```python
session_id = "user_123_session_20250220"

# First turn
result1 = await runtime.process_input("当前状态", session_id)

# Second turn (uses context)
result2 = await runtime.process_input("继续", session_id)
```

### 2. Error Handling

```python
from lee.orchestrator.execution.pm_agent.exceptions import *

try:
    result = await runtime.process_input(user_input, session_id)
except PermissionDeniedError as e:
    print(f"Permission denied: {e.message}")
except SecurityError as e:
    print(f"Security error: {e.message}")
except PMAgentException as e:
    print(f"PM Agent error: {e.message}")
```

### 3. Monitoring

```python
# Get metrics
metrics = runtime.get_metrics()

print(f"Decision Engine: {metrics['decision_engine']}")
print(f"Intent Classifier: {metrics['intent_classifier']}")
print(f"Cache: {metrics.get('cache', {})}")
```

## Troubleshooting

### Problem: LLM not responding

**Solution:** Check LLM configuration

```bash
# Test LLM connection
export OPENAI_API_KEY="your-key"
python -c "from lee.orchestrator.execution.llm_executor import LLMExecutor; \
  executor = LLMExecutor(); \
  print(executor.get_info())"
```

### Problem: Intent not recognized

**Solution:** Add custom pattern to config

```yaml
intents:
  my_intent:
    patterns:
      - regex: 'my.*pattern'
        priority: 1
```

### Problem: Permission denied

**Solution:** Check `agent.yaml` and ensure tool is allowed

```yaml
tools:
  allowed:
    - lee.workflow.run  # Add your tool here
```

## Next Steps

- [API Reference](API-REFERENCE.md) - Complete API documentation
- [Examples](EXAMPLES.md) - More usage examples
- [Security Guide](SECURITY-GUIDE.md) - Security best practices
- [Performance Guide](PERFORMANCE-GUIDE.md) - Performance tuning

## Getting Help

- Check documentation in `docs/features/pm-agent/`
- Run `lee chat --help` for CLI options
- Use `help` or `?` command in chat interface
- Check logs in `.lee/logs/` for debugging
