from pathlib import Path

from lee.orchestrator.verifier_engine import SchemaVerifier
from lee.orchestrator.verifiers.base import VerifyStatus


def test_schema_verifier_passes_with_valid_payload(tmp_path: Path):
    schema_file = tmp_path / "schema.yaml"
    payload_file = tmp_path / "payload.yaml"

    schema_file.write_text(
        "type: object\n"
        "required: [name]\n"
        "properties:\n"
        "  name:\n"
        "    type: string\n",
        encoding="utf-8",
    )
    payload_file.write_text("name: lee\n", encoding="utf-8")

    result = SchemaVerifier().verify(
        {
            "project_root": str(tmp_path),
            "config": {
                "schema_path": "schema.yaml",
                "file_path": "payload.yaml",
            },
        }
    )

    assert result.status == VerifyStatus.PASSED
    assert "Schema validation passed" in result.message


def test_schema_verifier_fails_on_invalid_payload(tmp_path: Path):
    schema_file = tmp_path / "schema.yaml"
    payload_file = tmp_path / "payload.yaml"

    schema_file.write_text(
        "type: object\n"
        "required: [name]\n"
        "properties:\n"
        "  name:\n"
        "    type: string\n",
        encoding="utf-8",
    )
    payload_file.write_text("name: 123\n", encoding="utf-8")

    result = SchemaVerifier().verify(
        {
            "project_root": str(tmp_path),
            "config": {
                "schema_path": "schema.yaml",
                "file_path": "payload.yaml",
            },
        }
    )

    assert result.status == VerifyStatus.FAILED
    assert "Schema validation failed" in result.message


def test_schema_verifier_requires_payload_source(tmp_path: Path):
    schema_file = tmp_path / "schema.yaml"
    schema_file.write_text("type: object\n", encoding="utf-8")

    result = SchemaVerifier().verify(
        {
            "project_root": str(tmp_path),
            "config": {
                "schema_path": "schema.yaml",
            },
        }
    )

    assert result.status == VerifyStatus.FAILED
    assert "needs one of config.file_path/config.output_path/config.data" in result.message
