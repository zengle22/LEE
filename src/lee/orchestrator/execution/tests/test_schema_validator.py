from pathlib import Path

from lee.orchestrator.execution.validators.schema_validator import SchemaValidator


def test_schema_validator_supports_yaml_schema_file(tmp_path: Path):
    schema_path = tmp_path / "schema.yaml"
    schema_path.write_text(
        "\n".join(
            [
                "type: object",
                "required:",
                "  - test_set_id",
                "properties:",
                "  test_set_id:",
                "    type: string",
            ]
        ),
        encoding="utf-8",
    )

    validator = SchemaValidator(project_dir=str(tmp_path))
    result = validator.validate(
        {"test_set_id": "TS-001"},
        {"schema_path": str(schema_path)},
    )

    assert result.passed


def test_schema_validator_supports_yaml_payload_string(tmp_path: Path):
    schema_path = tmp_path / "schema.json"
    schema_path.write_text(
        '{"type":"object","required":["module"],"properties":{"module":{"type":"string"}}}',
        encoding="utf-8",
    )

    validator = SchemaValidator(project_dir=str(tmp_path))
    result = validator.validate(
        "module: 用户注册\n",
        {"schema_path": str(schema_path)},
    )

    assert result.passed
