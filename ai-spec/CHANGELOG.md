# Changelog

All notable changes to the AI Spec will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-01-06

### Added

- Initial directory structure for centralized AI spec management
- `cli/claude/` - Claude Code plugin configuration
  - Migrated agents (16 files)
  - Migrated commands (14 files)
  - Migrated skills (5 files)
  - Migrated templates (12 files)
- `specs/contracts/` - Data contracts with versioning
  - business-opportunity-contract
  - fact-collection-contract
  - frozen-analysis-contract
  - google-keyword-contract
  - opportunity-builder-contract
  - supply-analysis-contract
  - trend-research-contract
  - user-signal-input-contract
  - user-signal-output-contract
- `specs/workflows/` - Workflow definitions
  - product-pipeline (Stage 2 sub-stages)
- `specs/org/prd/` - PRD domain as independent organization unit
- `AI-CONSTITUTION.md` - Core governance rules (top-level)
- `core.yaml` - Core configuration spec (top-level)
- `README.md` - Management rules and directory structure documentation
