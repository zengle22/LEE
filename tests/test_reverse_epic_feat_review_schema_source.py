from argparse import Namespace
import json
from pathlib import Path

from scripts import reverse_epic_feat as reverse_epic_feat_script


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _prepare_repo(repo_root: Path) -> None:
    _write(repo_root / "src" / "ok.py", "print('ok')\n")
    bundle = {
        "contract_version": "1.0",
        "workflow_id": "core.reverse-epic-feat",
        "run_id": "run-1",
        "outputs": [
            {
                "key": "src_reverse_ssot_chain",
                "identity_kind": "ssot",
                "ssot_type": "src",
                "title": "SRC",
                "description": "SRC desc",
                "content": "# SRC",
                "source_refs": ["src/ok.py"],
                "primary_refs": ["src/ok.py"],
                "evidence_layers": {
                    "impl_refs": ["src/ok.py"],
                    "api_refs": [],
                    "test_refs": [],
                    "doc_refs": [],
                },
                "evidence_strategy": dict(reverse_epic_feat_script.EVIDENCE_STRATEGY),
                "tags": ["reverse-ssot", "src"],
            },
            {
                "key": "epic_key",
                "identity_kind": "ssot",
                "ssot_type": "epic",
                "title": "Epic",
                "description": "Epic desc",
                "content": "# EPIC",
                "source_refs": ["src/ok.py"],
                "primary_refs": ["src/ok.py"],
                "evidence_layers": {
                    "impl_refs": ["src/ok.py"],
                    "api_refs": [],
                    "test_refs": [],
                    "doc_refs": [],
                },
                "evidence_strategy": dict(reverse_epic_feat_script.EVIDENCE_STRATEGY),
                "tags": ["reverse-ssot", "epic"],
            },
            {
                "key": "feat_key",
                "identity_kind": "ssot",
                "ssot_type": "feat",
                "title": "Feat",
                "description": "Feat desc",
                "content": "# FEAT",
                "parent": "epic_key",
                "source_refs": ["src/ok.py"],
                "primary_refs": ["src/ok.py"],
                "evidence_layers": {
                    "impl_refs": ["src/ok.py"],
                    "api_refs": [],
                    "test_refs": [],
                    "doc_refs": [],
                },
                "evidence_strategy": dict(reverse_epic_feat_script.EVIDENCE_STRATEGY),
                "tags": ["reverse-ssot", "feat"],
            },
            {
                "key": "delivery_prep_seed",
                "identity_kind": "non_ssot",
                "artifact_type": "HANDOVER",
                "category": "seed",
                "title": "Delivery Seed",
                "description": "Seed desc",
                "content": "{\"seed_targets\":[\"ui\",\"tech\",\"task\"]}",
                "source_refs": ["src/ok.py"],
                "tags": ["reverse-ssot", "seed"],
            },
            {
                "key": "qa_handoff_seed",
                "identity_kind": "non_ssot",
                "artifact_type": "HANDOVER",
                "category": "seed",
                "title": "QA Seed",
                "description": "QA seed desc",
                "content": "{\"seed_targets\":[\"testset\"]}",
                "source_refs": ["src/ok.py"],
                "tags": ["reverse-ssot", "seed"],
            },
            {
                "key": "evidence_trace_view",
                "identity_kind": "non_ssot",
                "artifact_type": "DOCUMENT",
                "category": "view",
                "title": "Evidence View",
                "description": "Evidence view desc",
                "content": "{\"view_targets\":[\"tc\",\"report\",\"bug\",\"evi\"]}",
                "source_refs": ["src/ok.py"],
                "tags": ["reverse-ssot", "view"],
            },
        ],
    }
    _write(
        repo_root / ".artifacts" / "active" / "reverse-epic-feat-ssot-output.json",
        json.dumps(bundle, ensure_ascii=False, indent=2),
    )


def _args(
    repo_root: Path,
    framework_root: Path,
    ssot_schema_path: str = "",
    feature_registry_schema_path: str = "",
) -> Namespace:
    return Namespace(
        repo_root=str(repo_root),
        framework_root=str(framework_root),
        specs_dir="spec",
        docs_dir="docs",
        artifacts_dir=".artifacts",
        request_id="",
        strict_evidence=False,
        ssot_schema_path=ssot_schema_path,
        feature_registry_schema_path=feature_registry_schema_path,
        max_capabilities=12,
        max_features_per_capability=8,
    )


def test_run_review_uses_framework_schema_by_default(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    framework_root = tmp_path / "framework"
    _prepare_repo(repo_root)
    _write(
        framework_root / "spec-global" / "core" / "contracts" / "ssot-agent-output" / "v1" / "schema.json",
        '{"$id":"framework"}',
    )

    captured = {}

    def fake_validate(*, instance, schema):
        captured["schema_id"] = schema.get("$id")

    monkeypatch.setattr(reverse_epic_feat_script, "validate", fake_validate)

    rc = reverse_epic_feat_script.run_review(_args(repo_root, framework_root))

    assert rc == 0
    assert captured["schema_id"] == "framework"


def test_run_review_respects_ssot_schema_override(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    framework_root = tmp_path / "framework"
    _prepare_repo(repo_root)
    _write(
        framework_root / "spec-global" / "core" / "contracts" / "ssot-agent-output" / "v1" / "schema.json",
        '{"$id":"framework"}',
    )
    override_schema = tmp_path / "override-schema.json"
    _write(override_schema, '{"$id":"override"}')

    captured = {}

    def fake_validate(*, instance, schema):
        captured["schema_id"] = schema.get("$id")

    monkeypatch.setattr(reverse_epic_feat_script, "validate", fake_validate)

    rc = reverse_epic_feat_script.run_review(_args(repo_root, framework_root, str(override_schema)))

    assert rc == 0
    assert captured["schema_id"] == "override"


def _sample_capabilities() -> list[dict]:
    return [
        {
            "id": "CAP-001",
            "features": [
                {
                    "id": "FEAT-001",
                    "key": "feat_key",
                    "title": "Feat",
                    "summary": "summary",
                    "acceptance_checks": [
                        {
                            "id": "AC-1",
                            "scenario": "ok",
                            "given": "given",
                            "when": "when",
                            "then": "then",
                            "trace_hints": ["src/ok.py"],
                        }
                    ],
                    "preconditions": ["pre"],
                    "main_flow": ["flow"],
                    "edge_cases": ["edge"],
                    "state_updates": ["state"],
                    "code_refs": ["src/ok.py"],
                    "all_refs": ["src/ok.py"],
                    "evidence_layers": {
                        "impl_refs": ["src/ok.py"],
                        "api_refs": [],
                        "test_refs": [],
                        "doc_refs": [],
                    },
                }
            ],
        }
    ]


def test_run_feature_registry_uses_framework_schema_by_default(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    framework_root = tmp_path / "framework"
    _prepare_repo(repo_root)
    _write(
        framework_root / "spec-global" / "core" / "contracts" / "reverse-feature-registry" / "v2" / "schema.json",
        '{"$id":"framework-registry"}',
    )

    monkeypatch.setattr(reverse_epic_feat_script, "_selected_capabilities", lambda *_: _sample_capabilities())
    captured = {}

    def fake_validate(*, instance, schema):
        captured["schema_id"] = schema.get("$id")

    monkeypatch.setattr(reverse_epic_feat_script, "validate", fake_validate)

    rc = reverse_epic_feat_script.run_feature_registry(_args(repo_root, framework_root))

    assert rc == 0
    assert captured["schema_id"] == "framework-registry"


def test_run_feature_registry_respects_schema_override(tmp_path: Path, monkeypatch) -> None:
    repo_root = tmp_path / "repo"
    framework_root = tmp_path / "framework"
    _prepare_repo(repo_root)
    _write(
        framework_root / "spec-global" / "core" / "contracts" / "reverse-feature-registry" / "v2" / "schema.json",
        '{"$id":"framework-registry"}',
    )
    override_schema = tmp_path / "feature-override-schema.json"
    _write(override_schema, '{"$id":"override-registry"}')

    monkeypatch.setattr(reverse_epic_feat_script, "_selected_capabilities", lambda *_: _sample_capabilities())
    captured = {}

    def fake_validate(*, instance, schema):
        captured["schema_id"] = schema.get("$id")

    monkeypatch.setattr(reverse_epic_feat_script, "validate", fake_validate)

    rc = reverse_epic_feat_script.run_feature_registry(
        _args(repo_root, framework_root, feature_registry_schema_path=str(override_schema))
    )

    assert rc == 0
    assert captured["schema_id"] == "override-registry"
