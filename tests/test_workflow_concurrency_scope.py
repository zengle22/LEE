from pathlib import Path

from lee.orchestrator.execution.concurrency_scope import derive_concurrency_scope


def test_dev_tech_design_uses_formal_ssot_id_scope(tmp_path: Path) -> None:
    info = derive_concurrency_scope(
        "dev.tech-design-l3",
        {"formal_ssot_id": "FEAT-SRC-041-001"},
        tmp_path,
    )

    assert info.concurrency_scope == "tech:FEAT-SRC-041-001"
    assert info.scope_source == "params.formal_ssot_id"


def test_dev_tech_design_falls_back_without_formal_ssot_id(tmp_path: Path) -> None:
    info = derive_concurrency_scope(
        "dev.tech-design-l3",
        {},
        tmp_path,
    )

    assert info.concurrency_scope.startswith(f"project:{tmp_path.resolve()}:workflow:dev.tech-design-l3")
    assert info.scope_source == "fallback:project+workflow_key"
