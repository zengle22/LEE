# Shared Input Schema

## Status

- State: frozen
- Governing ADR: `ADR-008`

## Required Fields

- `formal_ssot_id`
- `source_refs`
- `governing_adrs`
- `repo_context`

## Rules

### formal_ssot_id

- must match canonical SSOT id format
- must refer to a frozen upstream object

### source_refs

- at least one upstream reference is required
- each ref may include an optional `#anchor`

### governing_adrs

- at least one ADR is required
- each ADR must be explicit and traceable

### repo_context

- must include `repo_id`
- must include `branch`
- branch must follow allowed execution branch conventions
