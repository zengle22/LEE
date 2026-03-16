from click.testing import CliRunner

from lee.cli.main import cli


def test_cli_version_option_outputs_current_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["--version"])

    assert result.exit_code == 0
    assert result.output.startswith("cli ")


def test_cli_short_version_option_outputs_current_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli, ["-v"])

    assert result.exit_code == 0
    assert result.output.startswith("cli ")
