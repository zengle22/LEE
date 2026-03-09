# EPIC-001 工作流模板与实例生成

## Summary
维护 workflow 模板、注册表，并将模板渲染为运行时 instance。

## Scope
覆盖模板文件、registry 与 template 渲染链，不包含具体业务步骤执行。

## Child Features
- `FEAT-001`
- `FEAT-002`
- `FEAT-003`

## Code Refs
- `config/workflow-registry.yaml`
- `spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml`
- `src/lee/cli/commands/run.py`
- `src/lee/orchestrator/execution/template_manager.py`
