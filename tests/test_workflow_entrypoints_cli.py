from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

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


def test_adr_new_reports_missing_registered_workflow(monkeypatch) -> None:
    _register_commands()
    runner = CliRunner()

    monkeypatch.setattr(entry_module, "load_workflow_registry", lambda: {"workflows": {}})

    result = runner.invoke(cli, ["adr", "new", "--dry-run"])

    assert result.exit_code != 0
    assert "governance.adr-create" in result.output


def test_cli_help_groups_workflow_and_system_commands() -> None:
    _register_commands()
    runner = CliRunner()

    result = runner.invoke(cli, ["--help"])

    assert result.exit_code == 0
    assert "Workflow Commands" in result.output
    assert "System Commands" in result.output
    assert "adr" in result.output
    assert "epic" in result.output
    assert "feat" in result.output
