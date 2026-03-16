from pathlib import Path


def test_shared_input_spec_doc_is_frozen_and_complete():
    doc_path = Path("spec-global/departments/dev/docs/shared-input-spec.md")
    assert doc_path.exists(), "Shared input spec doc not found"

    text = doc_path.read_text(encoding="utf-8")
    assert "State: frozen" in text
    assert "## Schema 定义" in text
    assert "## Validation Checklist" in text
    assert "## Usage Guide" in text
    assert "## Migration Guide" in text
