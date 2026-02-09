---
description: Create Test Set from requirement document using QA workflow
---

# QA Test Set Production

Generate a Test Set design asset from a requirement document.

## Workflow

1. **Requirement Analysis** - Extract testable features from PRD
2. **Strategy Design** - Define test strategy and risk areas
3. **Test Set Generation** - Generate standardized Test Set YAML
4. **Review** - Review and approve the Test Set

## Usage

When user provides a module name and requirement document, run:

```bash
lee qa test-set create <module> --requirement <requirement_doc_path>
```

### Parameters

- `module`: Module name (e.g., `daily-plan`, `onboarding`)
- `requirement`: Path to requirement document (PRD/User Story)
- `tech-design` (optional): Path to technical design document

### Example

```bash
# Create Test Set for daily-plan module
lee qa test-set create daily-plan \
  --requirement docs/prd/daily-plan.md \
  --tech-design docs/tech/daily-plan-design.md
```

## Output

The workflow produces:

```
qa/
└── test-sets/
    ├── ts-{module}.yaml              # Test Set design asset
    └── ts-{module}/
        ├── analysis.md               # Requirement analysis report
        └── strategy-draft.yaml       # Test strategy draft
```

## Human Gates

1. **Analysis Review** - Confirm module boundary and testable features
2. **Strategy Review** - Confirm test focus and risk areas
3. **Final Approval** - Approve the generated Test Set

## List/Show Commands

```bash
# List all Test Sets
lee qa test-set list

# Show Test Set details
lee qa test-set show <test-set-id>
```

## Instructions for Claude

When the user asks to create a Test Set:

1. Ask for the module name if not provided
2. Ask for the requirement document path if not provided
3. Run `lee qa test-set create <module> --requirement <path>`
4. Monitor the workflow execution
5. When blocked at a gate, show the artifacts and ask for approval
6. Use `lee approve <gate-id>` to approve gates
