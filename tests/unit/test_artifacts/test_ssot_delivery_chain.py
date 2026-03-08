from pathlib import Path

from click.testing import CliRunner
import pytest

from lee.cli.commands.ssot import ssot
from lee.orchestrator.execution.artifacts import (
    ArtifactManager,
    SSOTContractMaterializer,
    SSOTIDGenerator,
    SSOTType,
    SSOTValidator,
    parse_parent,
    validate_id_format,
)
from lee.orchestrator.execution.artifacts.ssot_service import SSOTService


def _build_release_chain(
    project_root: Path,
    with_blocker_bug: bool = False,
    create_plans: bool = True,
) -> ArtifactManager:
    manager = ArtifactManager(
        root_path=project_root / ".artifacts",
        project_root=project_root,
    )

    feat = manager.create_ssot(
        ssot_type=SSOTType.FEAT,
        title="User registration",
        content="# FEAT",
        run_id="RUN-001",
    )
    testset = manager.create_ssot(
        ssot_type=SSOTType.TESTSET,
        title="Registration testset",
        content="# TESTSET",
        run_id="RUN-001",
        parent_id=feat.id,
    )
    release = manager.create_ssot(
        ssot_type=SSOTType.RELEASE,
        title="March MVP release",
        content="# RELEASE",
        run_id="RUN-001",
        derived_from=[{"id": feat.id, "version": "v1", "required": True, "slice_key": "feat-001-core"}],
        properties={
            "release_version": "1.4.0",
            "scope_frozen_at": "2026-03-08T10:00:00+08:00",
            "rollback_plan": "rollback to previous stable deployment",
        },
    )
    if create_plans:
        devplan = manager.create_ssot(
            ssot_type=SSOTType.DEVPLAN,
            title="Dev plan",
            content="# DEVPLAN",
            run_id="RUN-001",
            parent_id=release.id,
            derived_from=[{"id": feat.id, "version": "v1", "required": True, "slice_key": "feat-001-core"}],
            properties={
                "coverage_summary": "coverage",
                "slices": [
                    {
                        "slice_key": "feat-001-core",
                        "feat_id": feat.id,
                        "feat_version": "v1",
                        "required": True,
                        "dependencies": [],
                    }
                ]
            },
        )
        manager.create_ssot(
            ssot_type=SSOTType.TESTPLAN,
            title="Test plan",
            content="# TESTPLAN",
            run_id="RUN-001",
            parent_id=release.id,
            derived_from=[
                {"id": feat.id, "version": "v1", "required": True, "slice_key": "feat-001-core"},
                {"id": testset.id, "version": "v1", "required": True, "slice_key": "feat-001-core"},
            ],
            properties={
                "coverage_summary": "coverage",
                "environment_matrix": ["staging"],
                "slices": [
                    {
                        "slice_key": "feat-001-core",
                        "feat_id": feat.id,
                        "feat_version": "v1",
                        "required": True,
                        "dependencies": [],
                    }
                ]
            },
        )
        manager.create_ssot(
            ssot_type=SSOTType.TASK,
            title="Implement registration",
            content="# TASK",
            run_id="RUN-001",
            parent_id=devplan.id,
            derived_from=[{"id": feat.id, "version": "v1", "slice_key": "feat-001-core"}],
            properties={"slice_key": "feat-001-core"},
        )
    for report_kind in ("release", "test_execution", "go_no_go"):
        manager.create_ssot(
            ssot_type=SSOTType.REPORT,
            title=f"{report_kind} report",
            content="# REPORT",
            run_id="RUN-001",
            parent_id=release.id,
            properties={
                "report_kind": report_kind,
                "subject_id": release.id,
                "result": "pass",
                "evidence_refs": [],
            },
        )

    if with_blocker_bug:
        manager.create_ssot(
            ssot_type=SSOTType.BUG,
            title="Blocker bug",
            content="# BUG",
            run_id="RUN-001",
            parent_id=feat.id,
            properties={
                "bug_state": "open",
                "severity": "blocker",
                "found_in_release": release.id,
                "source_report_id": f"REPORT-{release.id}-TEST_EXECUTION-001",
            },
        )

    return manager


def test_id_generator_and_parser_support_release_delivery_ids(tmp_path: Path):
    generator = SSOTIDGenerator(tmp_path / ".artifacts")

    release_id = generator.generate_id(SSOTType.RELEASE, suffix="1.4.0")
    devplan_id = generator.generate_id(SSOTType.DEVPLAN, parent_id=release_id)
    task_id = generator.generate_id(SSOTType.TASK, parent_id=devplan_id)
    report_id = generator.generate_id(SSOTType.REPORT, parent_id=release_id, suffix="test_execution")

    assert release_id == "REL-1.4.0"
    assert devplan_id == "DEVPLAN-REL-1.4.0"
    assert task_id == "TASK-DEVPLAN-REL-1.4.0-001"
    assert report_id == "REPORT-REL-1.4.0-TEST_EXECUTION-001"
    assert parse_parent(devplan_id) == release_id
    assert parse_parent(task_id) == devplan_id
    assert validate_id_format(release_id, SSOTType.RELEASE)
    assert validate_id_format(devplan_id, SSOTType.DEVPLAN)
    assert validate_id_format(task_id, SSOTType.TASK)


def test_id_generator_independent_types_avoid_existing_spec_ids(tmp_path: Path):
    (tmp_path / "spec" / "adr").mkdir(parents=True)
    (tmp_path / "spec" / "adr" / "ADR-001__existing.md").write_text(
        "---\nid: ADR-001\nssot_type: adr\ntitle: Existing\nstatus: frozen\nversion: v1\n---\n\n# Existing\n",
        encoding="utf-8",
    )

    generator = SSOTIDGenerator(tmp_path / ".artifacts")

    assert generator.generate_id(SSOTType.ADR) == "ADR-002"


def test_validator_accepts_release_delivery_chain(tmp_path: Path):
    manager = _build_release_chain(tmp_path)

    release = manager.get("REL-1.4.0")
    devplan = manager.get("DEVPLAN-REL-1.4.0")
    testplan = manager.get("TESTPLAN-REL-1.4.0")
    task = manager.get("TASK-DEVPLAN-REL-1.4.0-001")
    report = manager.get("REPORT-REL-1.4.0-RELEASE-001")

    validator = SSOTValidator(manager.registry)

    assert validator.validate_p0(release.id).errors == []
    assert validator.validate_p0(devplan.id).errors == []
    assert validator.validate_p0(testplan.id).errors == []
    assert validator.validate_p0(task.id).errors == []
    assert validator.validate_p0(report.id).errors == []

    release_check = SSOTService(manager).release_check(release.id)
    assert release_check["passed"] is True
    assert release_check["errors"] == []


def test_release_check_cli_fails_with_blocker_bug(tmp_path: Path, monkeypatch):
    _build_release_chain(tmp_path, with_blocker_bug=True)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(ssot, ["release-check", "REL-1.4.0", "--enforce"])

    assert result.exit_code != 0
    assert "blocker bug" in result.output


def test_rebuild_registry_from_front_matter_files(tmp_path: Path, monkeypatch):
    _build_release_chain(tmp_path)
    manager = ArtifactManager(root_path=tmp_path / ".artifacts", project_root=tmp_path)
    registry_file = tmp_path / ".artifacts" / ".registry.json"
    if registry_file.exists():
        registry_file.unlink()

    rebuilt_count = manager.rebuild_ssot_registry()
    assert rebuilt_count >= 1
    assert manager.get("REL-1.4.0") is not None
    assert manager.get("DEVPLAN-REL-1.4.0") is not None


def test_release_cut_cli_creates_release(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(
        ssot,
        [
            "release-cut",
            "1.5.0",
            "--title",
            "May release",
            "--feat",
            "FEAT-001:v2",
        ],
    )

    assert result.exit_code == 0
    assert "REL-1.5.0" in result.output


def test_create_cli_creates_adr_draft_with_front_matter(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "spec" / "adr").mkdir(parents=True)
    (tmp_path / "spec" / "adr" / "ADR-001__existing.md").write_text(
        "---\nid: ADR-001\nssot_type: adr\ntitle: Existing\nstatus: frozen\nversion: v1\n---\n\n# Existing\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        ssot,
        [
            "create",
            "--type",
            "adr",
            "--title",
            "Windows hook portability gap",
            "--body",
            "# Decision\n\nTrack this as a draft governance gap.\n",
            "--status",
            "draft",
            "--owner",
            "governance",
            "--tag",
            "ssot",
            "--tag",
            "windows",
            "--source-ref",
            "ADR-001",
            "--property",
            "adr_kind=strategic_followup",
            "--property",
            "risk_area=windows_hook_portability",
        ],
    )

    assert result.exit_code == 0
    assert "ADR-002" in result.output
    adr_file = tmp_path / "spec" / "adr" / "ADR-002__windows-hook-portability-gap.md"
    text = adr_file.read_text(encoding="utf-8")
    assert "ssot_type: adr" in text
    assert "status: draft" in text
    assert "owner: governance" in text
    assert "adr_kind: strategic_followup" in text
    assert "risk_area: windows_hook_portability" in text


def test_plan_derive_cli_creates_missing_plans(tmp_path: Path, monkeypatch):
    _build_release_chain(tmp_path, create_plans=False)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(ssot, ["plan-derive", "REL-1.4.0"])

    assert result.exit_code == 0
    assert "DEVPLAN-REL-1.4.0" in result.output
    assert "TESTPLAN-REL-1.4.0" in result.output


def test_lint_cli_passes_for_valid_ssot_files(tmp_path: Path, monkeypatch):
    _build_release_chain(tmp_path)
    (tmp_path / "tests").mkdir(exist_ok=True)
    (tmp_path / "tests" / "README.md").write_text(
        "---\ntitle: Generated test files\nversion: 1.0\n---\n\n# Generated test files\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(ssot, ["lint"])

    assert result.exit_code == 0
    assert "SSOT lint passed" in result.output


def test_render_view_cli_outputs_release_dashboard(tmp_path: Path, monkeypatch):
    _build_release_chain(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        ssot,
        ["render-view", "release-dashboard", "--release-id", "REL-1.4.0"],
    )

    assert result.exit_code == 0
    assert "View: release-dashboard" in result.output
    assert "Gate passed: True" in result.output


def test_render_view_cli_outputs_feat_delivery_matrix_json(tmp_path: Path, monkeypatch):
    _build_release_chain(tmp_path)
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        ssot,
        ["render-view", "feat-delivery-matrix", "--release-id", "REL-1.4.0", "--format", "json"],
    )

    assert result.exit_code == 0
    assert '"view": "feat-delivery-matrix"' in result.output
    assert '"feat_id": "FEAT-001"' in result.output


def test_show_chain_uses_source_refs_for_adr_follow_up(tmp_path: Path):
    manager = ArtifactManager(root_path=tmp_path / ".artifacts", project_root=tmp_path)
    manager.create_ssot(
        ssot_type=SSOTType.ADR,
        title="Base governance ADR",
        content="# ADR-001",
        run_id="RUN-001",
        status=_draft_to_frozen(),
    )
    manager.create_ssot(
        ssot_type=SSOTType.ADR,
        title="Windows Hook Portability Gap",
        content="# ADR-002",
        run_id="RUN-001",
        source_refs=["ADR-001"],
    )

    chain = SSOTService(manager).show_chain("ADR-002")
    assert [entry["id"] for entry in chain] == ["ADR-001", "ADR-002"]
    assert chain[-1]["relation"] == "source_ref -> ADR-001"


def _draft_to_frozen():
    from lee.orchestrator.execution.artifacts.types import ArtifactStatus

    return ArtifactStatus.FROZEN


def test_create_cli_requires_release_version_for_release_type(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    result = CliRunner().invoke(
        ssot,
        [
            "create",
            "--type",
            "release",
            "--title",
            "Bad release",
            "--body",
            "# Release",
        ],
    )

    assert result.exit_code != 0
    assert "--release-version is required" in result.output


def test_ssot_contract_schema_rejects_invalid_release_properties(tmp_path: Path):
    manager = ArtifactManager(root_path=tmp_path / ".artifacts", project_root=tmp_path)
    materializer = SSOTContractMaterializer(manager)

    invalid_contract = {
        "contract_version": "1.0",
        "run_id": "RUN-001",
        "outputs": [
            {
                "key": "release_scope",
                "identity_kind": "ssot",
                "ssot_type": "release",
                "title": "March release",
                "derived_from_ids": [{"id": "FEAT-001", "version": "v1"}],
                "properties": {
                    "scope_frozen_at": "2026-03-08T10:00:00+08:00"
                },
            }
        ],
    }

    with pytest.raises(ValueError):
        materializer.validate_contract(invalid_contract)


def test_ssot_contract_schema_accepts_strict_release_report_bug_shapes(tmp_path: Path):
    manager = ArtifactManager(root_path=tmp_path / ".artifacts", project_root=tmp_path)
    materializer = SSOTContractMaterializer(manager)

    valid_contract = {
        "contract_version": "1.0",
        "run_id": "RUN-001",
        "outputs": [
            {
                "key": "release_scope",
                "identity_kind": "ssot",
                "ssot_type": "release",
                "title": "March release",
                "derived_from_ids": [{"id": "FEAT-001", "version": "v1", "required": True}],
                "properties": {
                    "release_version": "1.4.0",
                    "rollback_plan": "rollback",
                    "recuts": [
                        {
                            "recut_id": "recut-001",
                            "reason": "scope change",
                            "old_refs": [{"id": "FEAT-001", "version": "v1"}],
                            "new_refs": [{"id": "FEAT-001", "version": "v2"}],
                            "approved_by": "release_manager",
                            "changed_at": "2026-03-08T10:00:00+08:00",
                        }
                    ],
                },
            },
            {
                "key": "release_report",
                "identity_kind": "ssot",
                "ssot_type": "report",
                "title": "Release report",
                "parent": "release_scope",
                "properties": {
                    "report_kind": "release",
                    "subject_id": "REL-1.4.0",
                    "result": "pass",
                    "evidence_refs": ["EVI-001"],
                },
            },
            {
                "key": "release_bug",
                "identity_kind": "ssot",
                "ssot_type": "bug",
                "title": "Release bug",
                "properties": {
                    "bug_state": "closed",
                    "severity": "major",
                    "found_in_release": "REL-1.4.0",
                    "source_report_id": "REPORT-REL-1.4.0-RELEASE-001",
                },
            },
        ],
    }

    materializer.validate_contract(valid_contract)


def test_ssot_contract_schema_accepts_reverse_epic_feat_evidence_fields(tmp_path: Path):
    manager = ArtifactManager(root_path=tmp_path / ".artifacts", project_root=tmp_path)
    materializer = SSOTContractMaterializer(manager)

    valid_contract = {
        "contract_version": "1.0",
        "run_id": "RUN-REVERSE-001",
        "outputs": [
            {
                "key": "epic_growth_infra",
                "identity_kind": "ssot",
                "ssot_type": "epic",
                "title": "增长基础设施",
                "source_refs": ["src/lee/cli/commands/run.py"],
                "primary_refs": ["src/lee/cli/commands/run.py"],
                "evidence_layers": {
                    "impl_refs": ["src/lee/cli/commands/run.py"],
                    "api_refs": [],
                    "test_refs": ["tests/test_run_spec_governance.py"],
                    "doc_refs": ["spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml"],
                },
                "evidence_strategy": {
                    "primary_selection": "ordered_impl_api_first",
                    "ranking_signals": [
                        "path_quality",
                        "semantic_path_match",
                        "page_content_match",
                        "onboarding_local_rerank",
                    ],
                },
                "tags": ["reverse-ssot", "epic"],
            }
        ],
    }

    materializer.validate_contract(valid_contract)


def test_ssot_contract_materializer_uses_framework_schema_outside_repo_root(tmp_path: Path, monkeypatch):
    outside_cwd = tmp_path / "external-project"
    outside_cwd.mkdir(parents=True, exist_ok=True)
    monkeypatch.chdir(outside_cwd)

    manager = ArtifactManager(root_path=tmp_path / ".artifacts", project_root=tmp_path)
    materializer = SSOTContractMaterializer(manager)

    assert materializer.schema_path.exists()
    assert materializer.schema_path == (
        Path(__file__).resolve().parents[3]
        / "spec-global"
        / "core"
        / "contracts"
        / "ssot-agent-output"
        / "v1"
        / "schema.json"
    ).resolve()
