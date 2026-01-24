# LEE Claude Code Tools

This directory contains tool configuration files for Claude Code to interact with the LEE (Low-code Execution Engine) workflow system.

## Tool Overview

### 1. PM Workflow Tool (`pm-workflow.json`)

**Purpose**: Manage workflow execution during PM sessions

**Actions**:
- `get_state` - Get current workflow state
- `list_ready_steps` - List all ready (pending and unblocked) steps
- `run_step` - Execute a specific workflow step
- `next_step` - Automatically execute the next ready step

**Usage Examples**:
```python
# Get workflow state
pm_workflow(action="get_state", project_dir=".")

# List ready steps
pm_workflow(action="list_ready_steps", project_dir=".")

# Run a specific step
pm_workflow(action="run_step", project_dir=".", step_id="search_signals")

# Run next ready step
pm_workflow(action="next_step", project_dir=".")
```

### 2. Gate Approval Tool (`gate-approval.json`)

**Purpose**: Manage human gate approvals during Gate sessions

**Actions**:
- `list_pending` - List all gates pending approval
- `show` - Show gate details with checklist and upstream artifacts
- `decide` - Submit gate decision (approve/reject/revise)

**Usage Examples**:
```python
# List pending gates
gate_approval(action="list_pending", project_dir=".")

# Show gate details
gate_approval(action="show", project_dir=".", gate_id="freeze_approval")

# Approve a gate
gate_approval(
    action="decide",
    project_dir=".",
    gate_id="freeze_approval",
    option="approve",
    comment="All analysis criteria met",
    decided_by="lezeng"
)

# Request revision with checklist
gate_approval(
    action="decide",
    project_dir=".",
    gate_id="acceptance_gate",
    option="revise",
    comment="Need more detail on technical architecture",
    checklist=[
        {"item": "Requirements covered", "ok": True},
        {"item": "Technical feasibility", "ok": False}
    ]
)
```

### 3. Gate Review Tool (`gate-review.json`) ⭐ NEW

**Purpose**: Enhanced gate review with upstream analysis summary and decision recommendations

**Actions**:
- `list` - List all pending gates with summary
- `show` - Show gate details with upstream analysis summary
- `decide` - Submit gate decision with checklist support
- `report` - Generate comprehensive decision report

**Usage Examples**:
```python
# List pending gates
gate_review(action="list", project_dir=".")

# Show gate details with upstream analysis
gate_review(action="show", gate_id="freeze_market_signals", project_dir=".")

# Approve with checklist
gate_review(
    action="decide",
    gate_id="freeze_market_signals",
    decision="approve",
    comment="Analysis consistent, confidence threshold met",
    checklist=[
        {"item": "Consistency", "ok": True, "note": "No contradictions"},
        {"item": "Confidence", "ok": True, "note": ">70%"},
        {"item": "Verifiability", "ok": True, "note": "Testable"}
    ],
    project_dir="."
)

# Generate full report
gate_review(action="report", project_dir=".")
```

## Tools vs Slash Commands

**Important**: This directory contains **Function Tools** (JSON), not Slash Commands.

- **Function Tools** (`.claude/tools/*.json`): AI can call these automatically
- **Slash Commands** (`.claude/commands/*.md`): User types these directly

See `../commands/README.md` for slash command documentation.

### Available Slash Commands
- `/gate-review` - Review and approve gates (uses `gate_review` tool)
- `/gate-approval` - Gate approval tools (uses `gate_approval` tool)
- `/pm-workflow` - PM workflow management (uses `pm_workflow` tool)

## Implementation

These tools are implemented in `flowcore/api.py`:

- `pm_workflow_handler()` - Routes PM workflow actions
- `gate_approval_handler()` - Routes gate approval actions
- API functions: `api_get_state`, `api_list_ready_steps`, `api_run_step`, `api_next_step`, `api_gate_list_pending`, `api_gate_show`, `api_gate_decide`

## Two-Session Architecture

The LEE system uses two separate conversation types:

### PM Session
- **Goal**: Manage workflow execution
- **Tools**: `pm-workflow`
- **User Role**: Make decisions about what to do next
- **PM Agent Responsibilities**:
  - Query current state
  - List ready steps
  - Decide which step to execute
  - Execute steps
  - Monitor progress

### Gate Session
- **Goal**: Handle human approvals
- **Tools**: `gate-approval`
- **User Role**: Review and approve gate checkpoints
- **Gate Assistant Responsibilities**:
  - List pending gates
  - Show gate details (checklist, upstream artifacts)
  - Collect approval/rejection/revision decisions
  - Record decision history

## Workflow State

The workflow state is stored in:
- `.workflow/state.yaml` - Current workflow state
- `.workflow/gates/{gate_id}.yaml` - Individual gate files
- `.workflow/events/{run_id}.log` - Execution event log

## Example Session

### PM Session Example
```
User: What's the current state of the workflow?
Claude: [calls pm_workflow(action="get_state")]
      Workflow has 7 steps total, 2 completed, 0 failed.
      Ready steps: ['search_signals', 'analyze_user_signals']

User: Run the search_signals step
Claude: [calls pm_workflow(action="run_step", step_id="search_signals")]
      Executed search_signals successfully.
      Outputs: ['.workflow/outputs/search_signals/output.json']
```

### Gate Session Example
```
User: Are there any gates pending approval?
Claude: [calls gate_approval(action="list_pending")]
      Found 1 pending gate: freeze_approval

User: Show me the freeze_approval gate details
Claude: [calls gate_approval(action="show", gate_id="freeze_approval")]
      Gate: Market Signal Freeze Approval
      Checklist:
      - Analysis consistency: ✓
      - Confidence threshold (>=50): ✓ (72/100)
      Upstream artifacts: user_signal_analysis, industry_structure_analysis, supply_competition_analysis

User: Approve it
Claude: [calls gate_approval(action="decide", gate_id="freeze_approval", option="approve", ...)]
      Gate 'freeze_approval' has been approved
```

## Integration with Orchestrator

The tools integrate with the orchestrator through:
- `flowcore/orchestrator/state_machine.py` - State management
- `flowcore/orchestrator/engine_commands.py` - Step execution
- `flowcore/orchestrator/workflow_parser.py` - Workflow parsing

## Testing

Test the tools with the STG Opportunity Discovery demo:
```bash
cd examples/stg-opportunity-discovery-demo
python test_workflow.py
```

## Development

When adding new tools:
1. Create JSON configuration in `.claude/tools/`
2. Add handler function in `flowcore/api.py`
3. Export handler in `__all__`
4. Update this README
