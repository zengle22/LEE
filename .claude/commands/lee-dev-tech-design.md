---
description: Run the LEE dev tech-design workflow to produce a frozen TECH from a frozen FEAT
---

# LEE Dev Tech Design

Run the canonical dev L3 tech-design workflow through the LEE CLI.

## Usage

Prepare a spec file with:

- `formal_ssot_id`: The frozen FEAT ID (e.g., `FEAT-001`)
- `source_refs`: Source references (list of paths)
- `governing_adrs`: List of governing ADR IDs (e.g., `["ADR-008"]`)
- `repo_context`: Repository context object

Example spec file:

```yaml
formal_ssot_id: FEAT-001
source_refs:
  - spec/requirements/shared/FEAT-001__feat-freeze.md
governing_adrs:
  - ADR-008
repo_context:
  repo_id: my-project
  type: backend
```

Then run:

```bash
lee run dev.tech-design-l3 --project-dir <repo> --spec <spec-file>
```

Or use the canonical alias:

```bash
lee run dev.tech_design_l3 --project-dir <repo> --spec <spec-file>
```

## What To Report

- workflow id
- final status
- `tech_spec_ref`: Path to the generated TECH spec
- `decision_refs`: Path to the decision references YAML
- `review_result_ref`: Path to the self review result
- `risk_register_ref`: Path to the risk register
- `tech_package_ref`: Path to the TECH handoff package
- blocking gate or failed step

## Stages

1. **Analyze Feature**: Review the formal FEAT and write design analysis + implementation scope
2. **Draft TECH Spec**: Produce the formal TECH SSOT and decision companion files
3. **Tech Self Review**: Check consistency, feasibility, and traceability
4. **Publish TECH**: Finalize the TECH handoff package for contract design

## Output Artifacts

The workflow produces the following artifacts under the tech bundle directory:

- `design_analysis.md`: Feature-centric technical analysis
- `implementation_scope.md`: Implementation scope and constraints
- `TECH-{id}__tech-design.md`: Formal TECH SSOT markdown
- `decision_refs.yaml`: Decision references for the TECH package
- `frozen-technical-architecture.yaml`: Optional machine-readable TECH companion
- `review_result.md`: Self review findings
- `risk_register.md`: Risk register for the TECH package
- `tech_package.yaml`: TECH handoff package manifest
- `handoff_notes.md`: TECH handoff notes
