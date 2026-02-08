# LEE CLI Guide

This document describes the available `lee` CLI commands, common options, and usage examples.

## Install
The project uses `pyproject.toml` as the single source of truth for dependencies.

```bash
pip install -e .
```

If you prefer the demo requirements file:
```bash
pip install -r demo_l3_orchestration/requirements.txt
```

## Commands

### `lee run`
Run a registered workflow.

```bash
lee run <workflow_key> [--spec PATH] [--env ENV] [--version VERSION] [--branch BRANCH] [--project-dir DIR] [--max-steps N]
```

Examples:
```bash
lee run dev.feature --spec spec/feature-spec.json --branch demo/l3
lee run qa.regression --spec spec/test-plan.json --env staging --version v0.0.0-demo
lee run devops.deploy --env staging --version v0.0.0-demo
```

Workflow registry:
- `config/workflow-registry.yaml`

### `lee status`
Show workflow status. If `workflow_id` is omitted, lists all workflows.

```bash
lee status [workflow_id] [--project-dir DIR]
```

### `lee approve`
Approve a human gate.

```bash
lee approve <workflow_id> <gate_id> --approver NAME [--comments TEXT] [--project-dir DIR]
```

### `lee init`
Initialize project directories and templates.

```bash
lee init [--project-dir DIR]
```

### `lee demo`
Run Dev/QA/DevOps L3 demos and optionally auto-approve gates.

```bash
lee demo [--project-dir DIR] [--branch BRANCH] [--env ENV] [--version VERSION] [--feature-spec PATH] [--test-plan PATH] [--deploy-config PATH] [--max-steps N] [--approve/--no-approve] [--approver NAME] [--comments TEXT] [--init-specs/--no-init-specs]
```

Examples:
```bash
LEE_DEMO_MODE=1 lee demo
LEE_DEMO_MODE=1 lee demo --no-approve
```

## Environment Variables
- `LEE_DEMO_MODE=1`  
  Enables demo mode. Uses mock LLM executor and skips verifiers to keep flows running locally.
- `LEE_LLM_MOCK=1`  
  Forces mock LLM executor regardless of demo mode.
- `LLM_PROFILE=zhipu`  
  Selects the LLM profile for real LLM runs.

## Notes
- `lee run` requires required parameters defined in the registry entry.
- `lee demo` can generate placeholder specs automatically (`--init-specs`).
