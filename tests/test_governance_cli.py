from pathlib import Path

from click.testing import CliRunner

from lee.cli.commands.governance import governance


def test_create_brief_generates_front_matter(tmp_path: Path):
    runner = CliRunner()

    result = runner.invoke(
        governance,
        [
            "create-brief",
            "--project-dir",
            str(tmp_path),
            "--id",
            "login-refactor",
            "--title",
            "登录链路重构",
            "--type",
            "refactor",
            "--module",
            "workflow-runtime",
            "--future-ssot-type",
            "feat",
        ],
    )

    assert result.exit_code == 0
    brief = tmp_path / ".project" / "governance" / "ACCEPTANCE_BRIEFS" / "AB-login-refactor-登录链路重构.md"
    assert brief.exists()
    text = brief.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    assert "brief_id: login-refactor" in text
    assert "task_type: refactor" in text
    assert "governed_module: workflow-runtime" in text
    assert "future_ssot_type: feat" in text


def test_create_brief_refuses_overwrite_without_force(tmp_path: Path):
    runner = CliRunner()
    args = [
        "create-brief",
        "--project-dir",
        str(tmp_path),
        "--id",
        "demo-task",
        "--title",
        "Demo Task",
    ]

    first = runner.invoke(governance, args)
    second = runner.invoke(governance, args)

    assert first.exit_code == 0
    assert second.exit_code != 0
    assert "already exists" in second.output


def test_list_briefs_shows_created_brief(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(
        governance,
        [
            "create-brief",
            "--project-dir",
            str(tmp_path),
            "--id",
            "demo-task",
            "--title",
            "Demo Task",
        ],
    )

    result = runner.invoke(
        governance,
        ["list-briefs", "--project-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "demo-task" in result.output
    assert "Demo Task" in result.output


def test_check_brief_validates_created_brief(tmp_path: Path):
    runner = CliRunner()
    runner.invoke(
        governance,
        [
            "create-brief",
            "--project-dir",
            str(tmp_path),
            "--id",
            "demo-task",
            "--title",
            "Demo Task",
        ],
    )

    result = runner.invoke(
        governance,
        ["check-brief", "demo-task", "--project-dir", str(tmp_path)],
    )

    assert result.exit_code == 0
    assert "Acceptance Brief valid" in result.output


def test_check_brief_fails_without_required_fields(tmp_path: Path):
    briefs_dir = tmp_path / ".project" / "governance" / "ACCEPTANCE_BRIEFS"
    briefs_dir.mkdir(parents=True, exist_ok=True)
    brief = briefs_dir / "AB-bad-task.md"
    brief.write_text(
        "---\nbrief_id: bad-task\nstatus: active\n---\n\n# Acceptance Brief\n",
        encoding="utf-8",
    )

    runner = CliRunner()
    result = runner.invoke(
        governance,
        ["check-brief", "bad-task", "--project-dir", str(tmp_path)],
    )

    assert result.exit_code != 0
    assert "missing required field: title" in result.output
