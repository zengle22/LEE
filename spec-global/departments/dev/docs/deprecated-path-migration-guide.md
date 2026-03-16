# Deprecated Path Migration Guide

## Status

- State: frozen
- Governing spec: `dev.deprecated_paths_spec`

## Mapping

| Old Path | Status | New Entry |
| --- | --- | --- |
| `spec-global/departments/dev/workflows/phase-openspec-flow/v1/workflow.yaml` | deprecated | `template.dev.feature_delivery_l2` |
| `spec-global/departments/dev/workflows/templates/feature-l2-template.yaml` | compat | `template.dev.feature_delivery_l2` |
| `spec-global/departments/dev/workflows/templates/bug-fix-l3-template.yaml` | deprecated | `template.dev.bugfix_delivery_l2` |

## Migration Notes

- new feature work must enter through `template.dev.feature_delivery_l2`
- new bugfix work must enter through `template.dev.bugfix_delivery_l2`
- legacy workflow files remain only for migration reference or compatibility windows
