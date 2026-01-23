# Codex CLI Spec Bridge

This directory wires the `specs/common` canonical definitions into a Codex-ready
bundle. Instead of copying agent/skill/contract/workflow files, Codex relies on
the `spec-manifest.yaml` registry to resolve each spec directly from the shared
tree.

## Layout

```
cli/codex/
├── README.md             # This file
├── plugin.json           # Codex specific plugin metadata
└── spec-manifest.yaml    # Registry that maps spec IDs to shared definitions
```

## Workflow

1. Update or add general specs under `specs/common/**`.
2. Run through the manifest and ensure the new entry is listed (one line edit).
3. Codex tooling reads `plugin.json` → `spec-manifest.yaml` to fetch the latest
   agent/skill/contract/workflow definitions without duplicating files.
