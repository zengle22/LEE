from pathlib import Path


def test_deprecated_workflow_headers_expose_status_replacement_and_deadline():
    targets = [
        Path("spec-global/departments/dev/workflows/phase-openspec-flow/v1/workflow.yaml"),
        Path("spec-global/departments/dev/workflows/templates/feature-l2-template.yaml"),
        Path("spec-global/departments/dev/workflows/templates/bug-fix-l3-template.yaml"),
    ]

    for path in targets:
        content = path.read_text(encoding="utf-8")
        assert "# lifecycle_status:" in content
        assert "# replacement:" in content
        assert "# migration_deadline:" in content
