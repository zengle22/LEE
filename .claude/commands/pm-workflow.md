---
description: Manage PM workflow execution - query state, list steps, run workflow steps
---

# PM Workflow Command

Use the `pm_workflow` tool to manage the LEE workflow execution.

## Actions

1. **Get state**: View current workflow status
2. **List ready steps**: Show all pending and unblocked steps
3. **Run step**: Execute a specific workflow step
4. **Next step**: Automatically execute the next ready step

## Usage

Get current state:
```python
pm_workflow(action="get_state", project_dir=".")
```

List ready steps:
```python
pm_workflow(action="list_ready_steps", project_dir=".")
```

Run a specific step:
```python
pm_workflow(action="run_step", step_id="<step_id>", project_dir=".")
```

Run next ready step:
```python
pm_workflow(action="next_step", project_dir=".")
```
