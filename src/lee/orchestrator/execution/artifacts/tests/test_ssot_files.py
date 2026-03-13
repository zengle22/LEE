from pathlib import Path

from lee.orchestrator.execution.artifacts.ssot_files import lint_ssot_front_matter


def test_lint_ssot_front_matter_accepts_src_scoped_requirement_paths(tmp_path):
    feat_file = tmp_path / "spec" / "requirements" / "SRC-001" / "FEAT-SRC-001-001__user-signup.md"
    feat_file.parent.mkdir(parents=True, exist_ok=True)
    feat_file.write_text(
        "---\n"
        "id: FEAT-SRC-001-001\n"
        "ssot_type: feat\n"
        "title: 用户注册\n"
        "status: draft\n"
        "version: v1\n"
        "parent_id: EPIC-SRC-001-001\n"
        "derived_from_ids: []\n"
        "source_refs:\n"
        "  - SRC-001#scope\n"
        "  - EPIC-SRC-001-001\n"
        "properties:\n"
        "  src_root_id: SRC-001\n"
        "---\n\n"
        "# Feature\n",
        encoding="utf-8",
    )

    assert lint_ssot_front_matter(tmp_path) == []


def test_lint_ssot_front_matter_rejects_wrong_src_scoped_requirement_path(tmp_path):
    feat_file = tmp_path / "spec" / "requirements" / "features" / "FEAT-SRC-001-001__user-signup.md"
    feat_file.parent.mkdir(parents=True, exist_ok=True)
    feat_file.write_text(
        "---\n"
        "id: FEAT-SRC-001-001\n"
        "ssot_type: feat\n"
        "title: 用户注册\n"
        "status: draft\n"
        "version: v1\n"
        "parent_id: EPIC-SRC-001-001\n"
        "derived_from_ids: []\n"
        "source_refs:\n"
        "  - SRC-001#scope\n"
        "  - EPIC-SRC-001-001\n"
        "properties:\n"
        "  src_root_id: SRC-001\n"
        "---\n\n"
        "# Feature\n",
        encoding="utf-8",
    )

    errors = lint_ssot_front_matter(tmp_path)

    assert any("expected placement spec/requirements/SRC-001" in error for error in errors)
