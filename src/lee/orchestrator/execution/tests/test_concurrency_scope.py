from pathlib import Path

from lee.orchestrator.execution.concurrency_scope import derive_concurrency_scope


def test_product_src_to_epic_uses_source_freeze_artifact_id() -> None:
    info = derive_concurrency_scope(
        "product.src-to-epic",
        {"source_freeze": {"artifact_id": "SRC-009"}},
        Path(r"E:\ai\LEE"),
    )

    assert info.concurrency_scope == "src:SRC-009"
    assert info.scope_source == "params.source_freeze.artifact_id"


def test_product_src_to_epic_uses_source_freeze_path_stem() -> None:
    info = derive_concurrency_scope(
        "product.src-to-epic",
        {
            "source_freeze": {
                "path": r"E:\ai\LEE\spec\source\SRC-009__dev-department-ssot-alignment-normalized-goal-anal.md"
            }
        },
        Path(r"E:\ai\LEE"),
    )

    assert info.concurrency_scope == "src_path:SRC-009__dev-department-ssot-alignment-normalized-goal-anal"
    assert info.scope_source == "params.source_freeze.path"


def test_product_src_to_epic_falls_back_without_source_freeze_identity() -> None:
    info = derive_concurrency_scope(
        "product.src-to-epic",
        {"source_freeze": {}},
        Path(r"E:\ai\LEE"),
    )

    assert info.concurrency_scope == "project:E:\\ai\\LEE:workflow:product.src-to-epic"
    assert info.scope_source == "fallback:project+workflow_key"
