---
description: Review and approve pending human gates in the LEE workflow system
---

# Gate Review Command

Please use the `gate_review` tool to list pending gates and show their details.

## Actions

1. **List pending gates**: Show all gates that are waiting for approval
2. **Show gate details**: Display specific gate information including:
   - Approval criteria
   - Upstream analysis summary
   - Current checklist status
3. **Submit decision**: Approve, reject, or request revision for a gate

## Usage

Start by listing all pending gates:
```python
gate_review(action="list", project_dir=".")
```

Then show details for a specific gate:
```python
gate_review(action="show", gate_id="<gate_id>", project_dir=".")
```

Finally, submit your decision:
```python
gate_review(
    action="decide",
    gate_id="<gate_id>",
    decision="approve",  # or "reject" or "revise"
    comment="Your reasoning here",
    project_dir="."
)
```

## Available Gates

Common gate IDs include:
- `freeze_market_signals` - Freeze market signal analysis
- `freeze_business_opportunity` - Freeze business opportunity analysis
- `phase_acceptance_gate` - Phase completion acceptance
