from scripts.git_ssot_hook_checks import collect_release_ids, is_ssot_related_path


def test_is_ssot_related_path_detects_formal_ssot_and_runtime_paths():
    assert is_ssot_related_path("spec/delivery/releases/REL-1.4.0__march.md")
    assert is_ssot_related_path("tests/bugs/BUG-FEAT-001-001__bug.md")
    assert is_ssot_related_path("docs/reports/release/REPORT-REL-1.4.0-RELEASE-001__report.md")
    assert is_ssot_related_path("src/lee/orchestrator/execution/artifacts/ssot_service.py")
    assert not is_ssot_related_path("README.md")


def test_collect_release_ids_reads_release_front_matter(tmp_path):
    release_file = tmp_path / "spec" / "delivery" / "releases" / "REL-1.4.0__march.md"
    release_file.parent.mkdir(parents=True, exist_ok=True)
    release_file.write_text(
        "---\n"
        "id: REL-1.4.0\n"
        "ssot_type: release\n"
        "title: March release\n"
        "status: planned\n"
        "version: v1\n"
        "derived_from_ids: []\n"
        "source_refs: []\n"
        "properties: {}\n"
        "---\n\n"
        "# Release\n",
        encoding="utf-8",
    )

    from scripts import git_ssot_hook_checks as hook_checks

    original_root = hook_checks.REPO_ROOT
    hook_checks.REPO_ROOT = tmp_path
    try:
        assert collect_release_ids(["spec/delivery/releases/REL-1.4.0__march.md"]) == ["REL-1.4.0"]
    finally:
        hook_checks.REPO_ROOT = original_root
