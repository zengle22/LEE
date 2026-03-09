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


def test_schema_validator_resolves_relative_json_refs(tmp_path: Path):
    item_schema_dir = tmp_path / "contracts" / "item" / "v1"
    bundle_schema_dir = tmp_path / "contracts" / "bundle" / "v1"
    item_schema_dir.mkdir(parents=True, exist_ok=True)
    bundle_schema_dir.mkdir(parents=True, exist_ok=True)

    (item_schema_dir / "schema.json").write_text(
        '{"type":"object","required":["id"],"properties":{"id":{"type":"string"}}}',
        encoding="utf-8",
    )
    (bundle_schema_dir / "schema.json").write_text(
        "\n".join(
            [
                "{",
                '  "type": "object",',
                '  "required": ["items"],',
                '  "properties": {',
                '    "items": {',
                '      "type": "array",',
                '      "items": {',
                '        "$ref": "../../item/v1/schema.json"',
                "      }",
                "    }",
                "  }",
                "}",
            ]
        ),
        encoding="utf-8",
    )

    validator = SchemaValidator(project_dir=str(tmp_path))
    result = validator.validate(
        {"items": [{"id": "ITEM-001"}]},
        {"schema_path": str(bundle_schema_dir / "schema.json")},
    )

    assert result.passed


def test_schema_validator_resolves_relative_refs_with_remote_schema_id(tmp_path: Path):
    item_schema_dir = tmp_path / "contracts" / "item" / "v1"
    bundle_schema_dir = tmp_path / "contracts" / "bundle" / "v1"
    item_schema_dir.mkdir(parents=True, exist_ok=True)
    bundle_schema_dir.mkdir(parents=True, exist_ok=True)

    (item_schema_dir / "schema.json").write_text(
        "\n".join(
            [
                "{",
                '  "$id": "https://ai-spec.example.com/contracts/item/v1/schema.json",',
                '  "type": "object",',
                '  "required": ["id"],',
                '  "properties": {',
                '    "id": {"type": "string"}',
                "  }",
                "}",
            ]
        ),
        encoding="utf-8",
    )
    (bundle_schema_dir / "schema.json").write_text(
        "\n".join(
            [
                "{",
                '  "$id": "https://ai-spec.example.com/contracts/bundle/v1/schema.json",',
                '  "type": "object",',
                '  "required": ["items"],',
                '  "properties": {',
                '    "items": {',
                '      "type": "array",',
                '      "items": {',
                '        "$ref": "../../item/v1/schema.json"',
                "      }",
                "    }",
                "  }",
                "}",
            ]
        ),
        encoding="utf-8",
    )

    validator = SchemaValidator(project_dir=str(tmp_path))
    result = validator.validate(
        {"items": [{"id": "ITEM-001"}]},
        {"schema_path": str(bundle_schema_dir / "schema.json")},
    )

    assert result.passed


def test_schema_validator_supports_contract_wrapper_with_validation_rules(tmp_path: Path):
    schema_path = tmp_path / "test-set-contract.yaml"
    schema_path.write_text(
        "\n".join(
            [
                "kind: contract_schema",
                "schema:",
                "  type: object",
                "  required:",
                "    - test_set_id",
                "    - strategy",
                "    - test_focus",
                "    - traceability",
                "  properties:",
                "    test_set_id:",
                "      type: string",
                "    strategy:",
                "      type: object",
                "      properties:",
                "        priority:",
                "          type: string",
                "    test_focus:",
                "      type: object",
                "      properties:",
                "        positive:",
                "          type: array",
                "          items:",
                "            type: string",
                "    traceability:",
                "      type: object",
                "      properties:",
                "        feature_ids:",
                "          type: array",
                "          items:",
                "            type: string",
                "        acceptance_criteria_refs:",
                "          type: array",
                "          items:",
                "            type: string",
                "validation_rules:",
                "  - rule: must_have_test_focus",
                "    error_message: Test Set must include at least one test focus",
                "  - rule: p0_must_have_positive",
                "    error_message: P0 Test Set must include positive focus",
                "  - rule: single_feat_trace_required",
                "    error_message: Test Set must trace to exactly one FEAT",
                "  - rule: ac_coverage_required",
                "    error_message: Test Set must include AC references",
            ]
        ),
        encoding="utf-8",
    )

    validator = SchemaValidator(project_dir=str(tmp_path))
    result = validator.validate(
        {
            "test_set_id": "TS-001",
            "strategy": {"priority": "P0"},
            "test_focus": {"positive": ["happy path"]},
            "traceability": {
                "feature_ids": ["FEAT-001"],
                "acceptance_criteria_refs": ["AC1"],
            },
        },
        {"schema_path": str(schema_path)},
    )

    assert result.passed
    assert result.metadata["validation_rule_count"] == 4


def test_schema_validator_enforces_contract_wrapper_validation_rules(tmp_path: Path):
    schema_path = tmp_path / "test-set-contract.yaml"
    schema_path.write_text(
        "\n".join(
            [
                "kind: contract_schema",
                "schema:",
                "  type: object",
                "  required:",
                "    - test_set_id",
                "    - strategy",
                "    - test_focus",
                "    - traceability",
                "  properties:",
                "    test_set_id:",
                "      type: string",
                "    strategy:",
                "      type: object",
                "      properties:",
                "        priority:",
                "          type: string",
                "    test_focus:",
                "      type: object",
                "      properties:",
                "        positive:",
                "          type: array",
                "          items:",
                "            type: string",
                "    traceability:",
                "      type: object",
                "      properties:",
                "        feature_ids:",
                "          type: array",
                "          items:",
                "            type: string",
                "        acceptance_criteria_refs:",
                "          type: array",
                "          items:",
                "            type: string",
                "validation_rules:",
                "  - rule: must_have_test_focus",
                "    error_message: Test Set must include at least one test focus",
                "  - rule: single_feat_trace_required",
                "    error_message: Test Set must trace to exactly one FEAT",
                "  - rule: ac_coverage_required",
                "    error_message: Test Set must include AC references",
            ]
        ),
        encoding="utf-8",
    )

    validator = SchemaValidator(project_dir=str(tmp_path))
    result = validator.validate(
        {
            "test_set_id": "TS-001",
            "strategy": {"priority": "P1"},
            "test_focus": {},
            "traceability": {
                "feature_ids": ["FEAT-001", "FEAT-002"],
                "acceptance_criteria_refs": [],
            },
        },
        {"schema_path": str(schema_path)},
    )

    assert not result.passed
    codes = {error.code for error in result.errors}
    assert "RULE_MUST_HAVE_TEST_FOCUS" in codes
    assert "RULE_SINGLE_FEAT_TRACE_REQUIRED" in codes
    assert "RULE_AC_COVERAGE_REQUIRED" in codes


def test_schema_validator_enforces_delivery_plan_traceability_requirements():
    repo_root = Path(__file__).resolve().parents[5]
    schema_path = repo_root / "spec-global" / "departments" / "dev" / "contracts" / "development-plan-contract" / "v1" / "schema.json"

    validator = SchemaValidator(project_dir=str(repo_root))
    result = validator.validate(
        {
            "plan_id": "plan-demo",
            "version": "1.0.0",
            "metadata": {
                "project_name": "demo",
                "created_at": "2026-03-08T10:00:00Z",
                "created_by": "agent.product.pm_planner",
                "status": "draft",
            },
            "inputs": {
                "freeze_package": {
                    "id": "FP-001",
                    "prd": "output/feat.yaml",
                    "architecture": "output/tech.yaml",
                }
            },
            "traceability": {
                "feat_ids": ["FEAT-001"],
                "acceptance_criteria_refs": ["AC1"],
            },
            "role_assignments": [
                {"role": "frontend", "owner": "fe-owner"},
            ],
            "executable_tasks": [
                {
                    "task_id": "TASK-FEAT-001-FE-01",
                    "feat_id": "FEAT-001",
                    "lane": "frontend",
                    "owner_role": "frontend",
                    "acceptance_criteria_refs": ["AC1"],
                }
            ],
            "phases": [
                {
                    "phase_id": "phase-demo",
                    "name": "Demo Phase",
                    "type": "feature",
                    "size": "S",
                    "boundary": {
                        "inputs": [{"name": "feat_freeze", "source": "product", "required": True}],
                        "outputs": [{"name": "ui", "path": "output/ui.yaml", "type": "doc"}],
                    },
                    "agent_orchestration": [
                        {"step": 1, "agent_id": "agent.product.pm_planner", "name": "plan"}
                    ],
                    "delivery_criteria": [
                        {"id": "DC-1", "description": "done", "verification": "review"}
                    ],
                }
            ],
            "schedule": {
                "start_date": "2026-03-10",
                "end_date": "2026-03-20",
                "milestones": [
                    {
                        "id": "M1",
                        "name": "kickoff",
                        "date": "2026-03-10",
                        "deliverables": ["plan"],
                    }
                ],
            },
            "entry_conditions": ["UI and TECH frozen"],
            "delivery_standards": {},
        },
        {"schema_path": str(schema_path)},
    )

    assert result.passed


def test_schema_validator_blocks_delivery_plan_missing_ac_traceability():
    repo_root = Path(__file__).resolve().parents[5]
    schema_path = repo_root / "spec-global" / "departments" / "dev" / "contracts" / "development-plan-contract" / "v1" / "schema.json"

    validator = SchemaValidator(project_dir=str(repo_root))
    result = validator.validate(
        {
            "plan_id": "plan-demo",
            "version": "1.0.0",
            "metadata": {
                "project_name": "demo",
                "created_at": "2026-03-08T10:00:00Z",
                "created_by": "agent.product.pm_planner",
                "status": "draft",
            },
            "inputs": {
                "freeze_package": {
                    "id": "FP-001",
                    "prd": "output/feat.yaml",
                    "architecture": "output/tech.yaml",
                }
            },
            "traceability": {
                "feat_ids": ["FEAT-001"],
                "acceptance_criteria_refs": [],
            },
            "role_assignments": [
                {"role": "frontend", "owner": "fe-owner"},
            ],
            "executable_tasks": [
                {
                    "task_id": "TASK-FEAT-001-FE-01",
                    "feat_id": "FEAT-001",
                    "lane": "frontend",
                    "owner_role": "frontend",
                    "acceptance_criteria_refs": [],
                }
            ],
            "phases": [
                {
                    "phase_id": "phase-demo",
                    "name": "Demo Phase",
                    "type": "feature",
                    "size": "S",
                    "boundary": {
                        "inputs": [{"name": "feat_freeze", "source": "product", "required": True}],
                        "outputs": [{"name": "ui", "path": "output/ui.yaml", "type": "doc"}],
                    },
                    "agent_orchestration": [
                        {"step": 1, "agent_id": "agent.product.pm_planner", "name": "plan"}
                    ],
                    "delivery_criteria": [
                        {"id": "DC-1", "description": "done", "verification": "review"}
                    ],
                }
            ],
            "schedule": {
                "start_date": "2026-03-10",
                "end_date": "2026-03-20",
                "milestones": [
                    {
                        "id": "M1",
                        "name": "kickoff",
                        "date": "2026-03-10",
                        "deliverables": ["plan"],
                    }
                ],
            },
            "entry_conditions": ["UI and TECH frozen"],
            "delivery_standards": {},
        },
        {"schema_path": str(schema_path)},
    )

    assert not result.passed
    assert result.errors[0].code == "SCHEMA_VALIDATION_FAILED"
