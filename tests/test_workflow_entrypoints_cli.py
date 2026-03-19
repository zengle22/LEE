from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner
import yaml

from lee.cli.main import _register_commands, cli
from lee.cli.commands import ssot as ssot_module
from lee.cli.commands import workflow_entrypoints as entry_module


def test_ssot_create_requires_internal_or_admin(monkeypatch) -> None:
    _register_commands()
    runner = CliRunner()

    result = runner.invoke(
        cli,
        ["ssot", "create", "--type", "src", "--title", "demo"],
    )

    assert result.exit_code != 0
    assert "internal materialization command" in result.output
    assert "lee epic new" in result.output


def test_ssot_help_hides_create_command() -> None:
    _register_commands()
    runner = CliRunner()

    result = runner.invoke(cli, ["ssot", "--help"])

    assert result.exit_code == 0
    assert "create" not in result.output


def test_ssot_create_allows_internal_mode(monkeypatch) -> None:
    _register_commands()
    runner = CliRunner()

    class DummyArtifact:
        id = "SRC-999"
        path = "spec/source/SRC-999__demo.md"

    class DummyManager:
        def create_ssot(self, **kwargs):
            return DummyArtifact()

    monkeypatch.setattr(ssot_module, "ArtifactManager", lambda: DummyManager())

    result = runner.invoke(
        cli,
        ["ssot", "create", "--type", "src", "--title", "demo", "--internal"],
    )

    assert result.exit_code == 0
    assert "created SRC-999" in result.output


def test_epic_new_dispatches_to_product_src_to_epic(monkeypatch, tmp_path: Path) -> None:
    _register_commands()
    runner = CliRunner()
    spec_file = tmp_path / "src.yaml"
    spec_file.write_text("src: spec/source/SRC-001.md\n", encoding="utf-8")
    captured = {}

    monkeypatch.setattr(
        entry_module,
        "load_workflow_registry",
        lambda: {"workflows": {"product.src-to-epic": {}}},
    )

    def fake_run(**kwargs):
        captured.update(kwargs)

    monkeypatch.setattr(entry_module.run, "callback", fake_run)

    result = runner.invoke(
        cli,
        ["epic", "new", "--spec", str(spec_file), "--project-dir", str(tmp_path), "--skip-plan"],
    )

    assert result.exit_code == 0, result.output
    assert captured["workflow_key"] == "product.src-to-epic"
    assert captured["spec"] == str(spec_file.resolve())
    assert captured["skip_plan"] is True


def test_feat_new_dry_run_shows_workflow_alias(monkeypatch, tmp_path: Path) -> None:
    _register_commands()
    runner = CliRunner()
    spec_file = tmp_path / "epic.yaml"
    spec_file.write_text("epic_freeze: spec/requirements/epics/EPIC-003.md\n", encoding="utf-8")

    monkeypatch.setattr(
        entry_module,
        "load_workflow_registry",
        lambda: {"workflows": {"product.epic-to-feat": {}}},
    )

    result = runner.invoke(
        cli,
        ["feat", "new", "--spec", str(spec_file), "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "lee feat new -> lee run product.epic-to-feat" in result.output


def test_src_new_dry_run_shows_workflow_alias(monkeypatch, tmp_path: Path) -> None:
    _register_commands()
    runner = CliRunner()
    spec_file = tmp_path / "raw.md"
    spec_file.write_text("# Demo raw requirement\n", encoding="utf-8")

    monkeypatch.setattr(
        entry_module,
        "load_workflow_registry",
        lambda: {"workflows": {"product.raw-to-src": {}}},
    )

    result = runner.invoke(
        cli,
        ["src", "new", "--spec", str(spec_file), "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "lee src new -> lee run product.raw-to-src" in result.output


def test_delivery_prep_new_dry_run_shows_workflow_alias(monkeypatch, tmp_path: Path) -> None:
    _register_commands()
    runner = CliRunner()
    spec_file = tmp_path / "feat.md"
    spec_file.write_text("# Demo FEAT\n", encoding="utf-8")

    monkeypatch.setattr(
        entry_module,
        "load_workflow_registry",
        lambda: {"workflows": {"product.feat-to-delivery-prep": {}}},
    )

    result = runner.invoke(
        cli,
        ["delivery-prep", "new", "--spec", str(spec_file), "--dry-run"],
    )

    assert result.exit_code == 0, result.output
    assert "lee delivery-prep new -> lee run product.feat-to-delivery-prep" in result.output


def test_chain_validate_dispatches_direct_inputs_without_spec(monkeypatch, tmp_path: Path) -> None:
    _register_commands()
    runner = CliRunner()
    source_freeze = tmp_path / "src.md"
    source_freeze.write_text("# SRC\n", encoding="utf-8")
    epic_bundle = tmp_path / "epic-freeze.yaml"
    epic_bundle.write_text("epics: []\n", encoding="utf-8")
    feat_bundle = tmp_path / "feat-freeze.yaml"
    feat_bundle.write_text("feats: []\n", encoding="utf-8")
    delivery_bundle = tmp_path / "delivery-prep.yaml"
    delivery_bundle.write_text("bundle: {}\n", encoding="utf-8")
    captured = {}

    monkeypatch.setattr(
        entry_module,
        "load_workflow_registry",
        lambda: {"workflows": {"product.requirement-chain-validation": {}}},
    )

    def fake_run(**kwargs):
        captured.update(kwargs)
        captured["spec_doc"] = yaml.safe_load(Path(kwargs["spec"]).read_text(encoding="utf-8"))

    monkeypatch.setattr(entry_module.run, "callback", fake_run)

    result = runner.invoke(
        cli,
        [
            "chain",
            "validate",
            "--project-dir",
            str(tmp_path),
            "--skip-plan",
            "--source-freeze",
            str(source_freeze),
            "--epic-freeze-bundle",
            str(epic_bundle),
            "--feat-freeze-bundle",
            str(feat_bundle),
            "--delivery-prep-bundle",
            str(delivery_bundle),
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["workflow_key"] == "product.requirement-chain-validation"
    assert captured["skip_plan"] is True
    assert captured["spec_doc"] == {
        "source_freeze": str(source_freeze.resolve()),
        "epic_freeze_bundle": str(epic_bundle.resolve()),
        "feat_freeze_bundle": str(feat_bundle.resolve()),
        "delivery_prep_bundle": str(delivery_bundle.resolve()),
    }


def test_adr_new_reports_missing_registered_workflow(monkeypatch) -> None:
    _register_commands()
    runner = CliRunner()

    monkeypatch.setattr(entry_module, "load_workflow_registry", lambda: {"workflows": {}})

    result = runner.invoke(cli, ["adr", "new", "--dry-run"])

    assert result.exit_code != 0
    assert "governance.adr-create" in result.output


def test_adr_update_dispatches_to_governance_adr_update(monkeypatch, tmp_path: Path) -> None:
    """Test that lee adr update dispatches to governance.adr-update workflow with correct params."""
    _register_commands()
    runner = CliRunner()
    adr_file = tmp_path / "ADR-024__test.md"
    adr_file.write_text("# ADR Test\n", encoding="utf-8")
    captured = {}

    monkeypatch.setattr(
        entry_module,
        "load_workflow_registry",
        lambda: {"workflows": {"governance.adr-update": {}}},
    )

    def fake_run(**kwargs):
        captured.update(kwargs)
        # Store the spec content before it's deleted
        if kwargs.get("spec"):
            captured["spec_doc"] = yaml.safe_load(Path(kwargs["spec"]).read_text(encoding="utf-8"))

    monkeypatch.setattr(entry_module.run, "callback", fake_run)

    result = runner.invoke(
        cli,
        [
            "adr",
            "update",
            "--spec",
            str(adr_file),
            "--change-request",
            "测试更新",
            "--project-dir",
            str(tmp_path),
            "--skip-plan",
        ],
    )

    assert result.exit_code == 0, result.output
    assert captured["workflow_key"] == "governance.adr-update"
    assert captured["skip_plan"] is True
    # Verify params were passed correctly via the spec doc
    assert captured["spec_doc"]["spec_kind"] == "adr"
    assert captured["spec_doc"]["action"] == "update"
    assert captured["spec_doc"]["change_request"] == "测试更新"
    assert str(adr_file.resolve()) in captured["spec_doc"]["target_path"]


def test_adr_update_dry_run_shows_workflow_alias(monkeypatch, tmp_path: Path) -> None:
    """Test that dry-run shows the correct workflow alias."""
    _register_commands()
    runner = CliRunner()
    adr_file = tmp_path / "ADR-024__test.md"
    adr_file.write_text("# ADR Test\n", encoding="utf-8")

    monkeypatch.setattr(
        entry_module,
        "load_workflow_registry",
        lambda: {"workflows": {"governance.adr-update": {}}},
    )

    result = runner.invoke(
        cli,
        [
            "adr",
            "update",
            "--spec",
            str(adr_file),
            "--change-request",
            "测试更新",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0, result.output
    assert "lee adr update -> lee run governance.adr-update" in result.output


def test_cli_help_groups_workflow_and_system_commands() -> None:
    _register_commands()
    runner = CliRunner()

    result = runner.invoke(cli, ["--help"])
    normalized_output = " ".join(result.output.split())

    assert result.exit_code == 0
    assert "Workflow Commands" in result.output
    assert "System Commands" in result.output
    assert "adr" in result.output
    assert "src" in result.output
    assert "epic" in result.output
    assert "feat" in result.output
    assert "delivery-prep" in result.output
    assert "chain" in result.output
    assert "lee src new --spec <raw.md>" in normalized_output
    assert "lee delivery-prep new --spec <frozen-feat.md>" in normalized_output
    assert "lee chain validate --source-freeze <src>" in normalized_output
