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
        ],
    }
    _write(
        repo_root / ".artifacts" / "active" / "reverse-epic-feat-ssot-output.json",
        json.dumps(bundle, ensure_ascii=False, indent=2),
    )


def _args(repo_root: Path, framework_root: Path, ssot_schema_path: str = "") -> Namespace:
    return Namespace(
        repo_root=str(repo_root),
        framework_root=str(framework_root),
        specs_dir="spec",
        docs_dir="docs",
        artifacts_dir=".artifacts",
        request_id="",
        strict_evidence=False,
        ssot_schema_path=ssot_schema_path,
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
