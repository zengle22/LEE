---
description: Gate approval tools - list pending gates, show details, submit decisions
---

# Gate Approval Command

Use the `gate_approval` tool to manage human gate approvals in the LEE workflow.

## Actions

1. **List pending**: Show all gates waiting for approval
2. **Show details**: Display gate checklist and upstream artifacts
3. **Decide**: Submit approval, rejection, or revision

## Usage

List pending gates:
```python
gate_approval(action="list_pending", project_dir=".")
```

Show gate details:
```python
gate_approval(action="show", gate_id="<gate_id>", project_dir=".")
```

Submit decision:
```python
gate_approval(
    action="decide",
    gate_id="<gate_id>",
    option="approve",  # or "reject" or "revise"
    comment="Your reasoning",
    project_dir="."
)
```
