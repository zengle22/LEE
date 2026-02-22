# PM Agent Usage Examples

> **作者**: LEE Team
> **日期**: 2026-02-20
> **版本**: v1.0.0
> **分类**: 使用示例

Practical examples for common PM Agent use cases.

## Table of Contents

1. [Basic Workflow Operations](#basic-workflow-operations)
2. [Multi-turn Conversations](#multi-turn-conversations)
3. [Department-Specific Workflows](#department-specific-workflows)
4. [Custom Intent Definitions](#custom-intent-definitions)
5. [Error Handling and Recovery](#error-handling-and-recovery)
6. [Performance Optimization](#performance-optimization)

---

## Basic Workflow Operations

### Example 1: Query Status

```python
from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime

runtime = PMAgentRuntime(orchestrator, llm_executor, store)

# Query current status
result = await runtime.process_input(
    user_input="当前状态如何",
    session_id="session_001"
)

# Expected output:
# {
#     'status': 'success',
#     'action': 'get_state',
#     'data': {
#         'state': {
#             'status': 'running',
#             'current_step': 'search_signals',
#             'ready_steps': [...]
#         }
#     },
#     'confidence': 0.9
# }
```

### Example 2: Execute Next Step

```python
# Execute next available step
result = await runtime.process_input(
    user_input="继续",
    session_id="session_001"
)

# Expected output:
# {
#     'status': 'success',
#     'action': 'next_step',
#     'data': {
#         'step_id': 'analyze_signals',
#         'workflow_id': 'workflow_123',
#         'message': 'Step completed'
#     }
# }
```

### Example 3: Execute Specific Step

```python
# Execute specific step by name
result = await runtime.process_input(
    user_input="运行 search_signals 步骤",
    session_id="session_001"
)

# Expected output:
# {
#     'status': 'success',
#     'action': 'run_step',
#     'data': {
#         'step_id': 'search_signals',
#         'workflow_id': 'workflow_123'
#     }
# }
```

---

## Multi-turn Conversations

### Example 4: Context-Aware Conversation

```python
session_id = "user_123_conversation"

# Turn 1: Query status
result1 = await runtime.process_input(
    user_input="当前到哪里了",
    session_id=session_id
)
print(f"Current step: {result1['data']['state']['current_step']}")

# Turn 2: Continue from previous context
result2 = await runtime.process_input(
    user_input="下一步呢",
    session_id=session_id
)
# PM Agent remembers current workflow and executes next step

# Turn 3: Check status again
result3 = await runtime.process_input(
    user_input="现在怎么样了",
    session_id=session_id
)
# Shows updated status
```

### Example 5: Workflow Switching

```python
session_id = "session_002"

# Start with one workflow
result1 = await runtime.process_input(
    user_input="运行商业机会发现工作流",
    session_id=session_id
)

# Switch to different workflow
result2 = await runtime.process_input(
    user_input="切换到 bug 修复工作流",
    session_id=session_id
)
# PM Agent handles workflow switching
```

---

## Department-Specific Workflows

### Example 6: Strategy Department (STG)

```python
# STG department workflow
result = await runtime.process_input(
    user_input="分析市场机会，搜索 AI 和机器学习相关的信号",
    session_id="stg_session"
)

# PM Agent recognizes STG context and executes opportunity discovery workflow
```

### Example 7: Development Department (DEV)

```python
# DEV department workflow
result = await runtime.process_input(
    user_input="修复 login 页面的密码重置 bug",
    session_id="dev_session"
)

# PM Agent triggers bug-fix workflow for development
```

### Example 8: QA Department

```python
# QA department workflow
result = await runtime.process_input(
    user_input="运行用户管理模块的测试套件",
    session_id="qa_session"
)

# PM Agent executes test plan workflow
```

---

## Custom Intent Definitions

### Example 9: Define Custom Intent

```yaml
# config/intent_classifier.yaml

intents:
  deploy_to_env:
    description: Deploy to specific environment
    llm_fallback: true
    allowed_tools:
      - lee.workflow.run
    requires_params: true
    patterns:
      - regex: '^(部署到|deploy.*to)\s*(dev|staging|prod)'
        priority: 1
        description: Deploy to environment
```

### Example 10: Use Custom Intent

```python
result = await runtime.process_input(
    user_input="部署到 staging 环境",
    session_id="session_003"
)

# PM Agent recognizes custom intent and executes deployment
```

---

## Error Handling and Recovery

### Example 11: Handle Permission Denied

```python
from lee.orchestrator.execution.pm_agent.exceptions import PermissionDeniedError

try:
    result = await runtime.process_input(
        user_input="执行 shell 命令删除文件",
        session_id="session_004"
    )
except PermissionDeniedError as e:
    print(f"Permission denied: {e.message}")
    print(f"Action: {e.action}")
    print(f"Required permission: {e.required_permission}")

    # Suggest alternative
    print("Suggestion: Use workflow-based file operations instead")
```

### Example 12: Handle Intent Classification Failure

```python
from lee.orchestrator.execution.pm_agent.exceptions import IntentClassificationError

try:
    result = await runtime.process_input(
        user_input="xyzabc123",
        session_id="session_005"
    )
except IntentClassificationError as e:
    print(f"Could not understand: {e.message}")

    # Ask for clarification
    print("Please rephrase your request")
    print("Examples: '当前状态', '运行下一步', '批准 gate_001'")
```

### Example 13: Handle Parameter Extraction Failure

```python
from lee.orchestrator.execution.pm_agent.exceptions import ParameterExtractionError

try:
    result = await runtime.process_input(
        user_input="运行那个步骤",
        session_id="session_006"
    )
except ParameterExtractionError as e:
    print(f"Ambiguous request: {e.message}")

    # Provide options
    print("Available steps:")
    print("- search_signals")
    print("- analyze_signals")
    print("- build_opportunity")
```

---

## Performance Optimization

### Example 14: Enable Caching

```python
from lee.orchestrator.execution.pm_agent.cache import CompositeCache

# Create cache with custom TTL
cache = CompositeCache(
    intent_cache_size=2000,      # Larger cache
    intent_cache_ttl=600,         # 10 minutes
    workflow_cache_ttl=600,       # 10 minutes
    api_cache_ttl=30              # 30 seconds
)

# Use with runtime (if you need custom cache)
runtime.cache = cache
```

### Example 15: Monitor Performance

```python
# Get performance metrics
metrics = runtime.get_metrics()

# Decision Engine metrics
de_metrics = metrics['decision_engine']
print(f"Total decisions: {de_metrics['total_decisions']}")
print(f"Success rate: {de_metrics['success_rate']:.1%}")
print(f"Fallback rate: {de_metrics['fallback_rate']:.1%}")

# Cache metrics
if 'cache' in metrics:
    cache_metrics = metrics['cache']['intent_cache']
    print(f"Cache hit rate: {cache_metrics['hit_rate']:.1%}")

# API metrics
if 'api_wrapper' in metrics:
    api_metrics = metrics['api_wrapper']
    print(f"API calls: {api_metrics['total_calls']}")
    print(f"Error rate: {api_metrics['error_rate']:.1%}")
```

### Example 16: Batch Processing

```python
# Process multiple inputs efficiently
inputs = [
    "当前状态",
    "运行下一步",
    "查看就绪步骤",
    "批准 gate_001"
]

session_id = "batch_session"
results = []

for user_input in inputs:
    result = await runtime.process_input(user_input, session_id)
    results.append(result)

# Process results
for i, result in enumerate(results):
    print(f"{inputs[i]}: {result['status']}")
```

---

## Advanced Examples

### Example 17: Custom Department Configuration

```yaml
# config/intent_classifier.yaml

departments:
  marketing:
    description: Marketing department specific workflows
    intents:
      create_campaign:
        description: Create marketing campaign
        patterns:
          - regex: '创建.*营销活动|marketing.*campaign'
            priority: 1
        allowed_tools:
          - lee.workflow.run
        requires_params: true

    permissions:
      allowed_tools:
        - lee.workflow.run
        - lee.workflow.status
      denied_tools:
        - shell
        - git
```

### Example 18: Workflow with Parameters

```python
# Execute workflow with specific parameters
result = await runtime.process_input(
    user_input="运行商业机会发现，关键词包括 AI 和机器学习",
    session_id="session_007"
)

# PM Agent extracts:
# - workflow_ref: workflow.stg.opportunity_discovery
# - params: {keywords: ["AI", "机器学习"]}
```

### Example 19: Gate Approval with Comment

```python
# Approve gate with reason
result = await runtime.process_input(
    user_input="批准 gate_review，代码审查通过，测试覆盖率达标",
    session_id="session_008"
)

# PM Agent extracts:
# - gate_id: gate_review
# - approval_comment: "代码审查通过，测试覆盖率达标"
```

### Example 20: Error Recovery Workflow

```python
session_id = "session_009"

try:
    # Step that might fail
    result = await runtime.process_input(
        user_input="运行测试步骤",
        session_id=session_id
    )
except Exception as e:
    print(f"Step failed: {e}")

    # Recovery: check status
    status_result = await runtime.process_input(
        user_input="当前状态",
        session_id=session_id
    )

    # Recovery: retry with different parameters
    retry_result = await runtime.process_input(
        user_input="重新运行测试步骤，跳过慢速测试",
        session_id=session_id
    )
```

---

## Tips and Best Practices

### 1. Use Clear, Specific Language

**Good:**
```
"运行 search_signals 步骤"
"批准 gate_001，测试通过"
```

**Avoid:**
```
"执行那个"  # Too vague
"继续"     # Better: "运行下一步"
```

### 2. Provide Context When Needed

**Good:**
```
"在商业机会发现工作流中，运行分析用户信号的步骤"
```

### 3. Use Session IDs for Multi-turn Conversations

```python
# Good: Use consistent session ID
session_id = f"user_{user_id}_session_{timestamp}"

for input in user_inputs:
    result = await runtime.process_input(input, session_id)
```

### 4. Handle Errors Gracefully

```python
try:
    result = await runtime.process_input(user_input, session_id)
except PMAgentException as e:
    # Log error
    logger.error(f"PM Agent error: {e}")

    # Provide user-friendly message
    print(f"Sorry, I couldn't process that: {e.message}")
```

---

For more examples, see:
- [Quick Start Guide](QUICKSTART.md)
- [API Reference](API-REFERENCE.md)
