# LEE PM Agent + Gate Assistant Integration Demo

This demo showcases the complete integration between PM Agent and Gate Assistant in the LEE system.

## Architecture

```
┌─────────────────┐
│   PM Session    │  Workflow management
│  (Claude Code)  │  - Query state
│   pm-workflow   │  - Execute steps
└────────┬────────┘  - Make decisions
         │
         ├──────────────────────────────┐
         │                              │
         ▼                              ▼
┌─────────────────┐          ┌─────────────────┐
│   Orchestrator  │          │ Gate Session    │
│  (flowcore)     │◄─────────│  (Claude Code)  │
│                 │          │  gate-approval  │
│ - StateMachine  │          │  - List gates   │
│ - Engine        │          │  - Show details │
│ - WorkflowParser│          │  - Approve      │
└─────────────────┘          └─────────────────┘
```

## Features Demonstrated

### 1. PM Session Tools
- `get_state` - Query workflow state
- `list_ready_steps` - List executable steps
- `run_step` - Execute specific step
- `next_step` - Auto-execute next step

### 2. Gate Session Tools
- `list_pending` - List pending gates
- `show` - Show gate details with checklist
- `decide` - Submit approval/rejection/revision

### 3. Tool Handlers
- `pm_workflow_handler` - Routes PM actions
- `gate_approval_handler` - Routes gate actions

## Installation

```bash
# Install dependencies (if needed)
pip install -r requirements.txt

# Ensure flowcore is in Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

## Usage

### Run Complete Demo

```bash
cd examples/pm-gate-integration-demo
python test_pm_gate_integration.py
```

### Run Individual Demos

```python
# PM Session demo
from test_pm_gate_integration import demo_pm_session
demo_pm_session("../../spec-global/departments/stg")

# Gate Session demo
from test_pm_gate_integration import demo_gate_session
demo_gate_session("../../spec-global/departments/stg")

# Tool Handlers demo
from test_pm_gate_integration import demo_tool_handlers
demo_tool_handlers("../../spec-global/departments/stg")

# Complete workflow demo
from test_pm_gate_integration import demo_complete_workflow
demo_complete_workflow("../../spec-global/departments/stg")
```

## API Usage Examples

### PM Session

```python
from flowcore.api import api_get_state, api_list_ready_steps, api_run_step, api_next_step

# Get current state
state = api_get_state(".")
print(f"Workflow: {state['workflow_name']}")
print(f"Progress: {state['completed_steps']}/{state['total_steps']}")

# List ready steps
ready_steps = api_list_ready_steps(".")
for step in ready_steps:
    print(f"Ready: {step['id']} - {step['description']}")

# Execute specific step
result = api_run_step(".", "search_signals")
if result['status'] == 'completed':
    print(f"Step completed: {result['outputs']}")

# Execute next ready step
result = api_next_step(".")
print(f"Executed: {result['step_id']}")
```

### Gate Session

```python
from flowcore.api import api_gate_list_pending, api_gate_show, api_gate_decide

# List pending gates
gates = api_gate_list_pending(".")
for gate in gates:
    print(f"Pending: {gate['id']}")

# Show gate details
details = api_gate_show(".", "freeze_approval")
print(f"Description: {details['description']}")
print(f"Checklist: {details['checklist']}")
print(f"Upstream: {details['upstream_artifacts']}")

# Approve gate
result = api_gate_decide(
    project_dir=".",
    gate_id="freeze_approval",
    option="approve",
    comment="All criteria met",
    decided_by="lezeng"
)
print(f"Result: {result['message']}")
```

### Using Tool Handlers

```python
from flowcore.api import pm_workflow_handler, gate_approval_handler

# PM workflow via handler
result = pm_workflow_handler(
    action="get_state",
    project_dir="."
)

# Gate approval via handler
result = gate_approval_handler(
    action="decide",
    project_dir=".",
    gate_id="freeze_approval",
    option="approve",
    comment="Approved",
    decided_by="user"
)
```

## Two-Session Architecture

### PM Session
**Purpose**: Manage workflow execution

**Responsibilities**:
- Query current state
- Decide which step to execute
- Execute agent/skill steps
- Monitor progress

**When to use**: Automated workflow progression

### Gate Session
**Purpose**: Handle human approvals

**Responsibilities**:
- List pending gates
- Show gate details
- Collect approval decisions
- Record decision history

**When to use**: Human checkpoint reviews

## Workflow State

State is stored in:
- `.workflow/state.yaml` - Current workflow state
- `.workflow/gates/{gate_id}.yaml` - Individual gate files
- `.workflow/events/{run_id}.log` - Execution event log

## Integration with Claude Code

The tool configurations are in `.claude/tools/`:
- `pm-workflow.json` - PM session tool
- `gate-approval.json` - Gate session tool

These tools are automatically loaded by Claude Code and can be called directly.

## Testing with Real Workflows

To test with a real workflow:

```bash
# Initialize a workflow
cd examples/stg-opportunity-discovery-demo
python -m flowcore.orchestrator.cli init

# Run workflow steps
python -m flowcore.orchestrator.cli run search_signals

# Test PM tools
cd ../pm-gate-integration-demo
python test_pm_gate_integration.py
```

## Troubleshooting

### ImportError: No module named 'flowcore'
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)/src"
```

### Workflow not initialized
```bash
python -m flowcore.orchestrator.cli init
```

### Gate file not found
Make sure the workflow has been run at least once and has reached a gate step.

## Related Documentation

- **Architecture**: `docs/architecture.md`
- **Orchestrator**: `docs/Orchestrator-Architecture.md`
- **PM Agent Protocol**: `docs/PM_AGENT_PROTOCOL.md`
- **API Reference**: `flowcore/api.py`
- **Tool Configuration**: `.claude/tools/README.md`

## Next Steps

1. ✅ Run this demo to verify integration
2. ✅ Test with real workflow data
3. ⬜ Configure Claude Code with tool definitions
4. ⬜ Test two-session architecture in separate conversations
5. ⬜ Add error handling and validation
6. ⬜ Create user documentation
