# LEE Project Configuration

This directory contains the LEE orchestrator configuration for this project.

## Files

- `dirs.yaml`: Directory structure configuration (DO NOT edit manually)
- `schema/`: Schema definitions for validation

## Directory Structure

- **.project**: Project configuration and metadata
- **.workflow**: Workflow execution state and temporary files
- **contracts**: Frozen analysis results and formal contracts
- **docs**: Generated documentation and reports
- **src**: Generated source code
- **outputs**: Intermediate outputs and artifacts
- **tests**: Generated test files
- **specs**: Generated specification documents


## Constraints

- ✅ Strict path validation enabled
- ✅ File creation outside defined directories is forbidden
- ✅ Project initialization is required

## Getting Output Paths

When creating outputs in your workflow, use the configured directory structure:

```python
from flowcore.orchestrator.project_config import get_project_structure

config = get_project_structure(".")
path = config.get_output_path("doc", category="reports", title="My Report")
# Returns: docs/reports/2025-01-25-my-report.md
```

## Re-initializing

To re-initialize the project structure (e.g., after updating the schema):

```bash
python -m flowcore.orchestrator init . --force
```
