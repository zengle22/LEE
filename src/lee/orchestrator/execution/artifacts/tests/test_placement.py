from pathlib import Path

import pytest

from lee.orchestrator.execution.artifacts.placement import (
    resolve_ssot_relative_dir,
    resolve_transfer_package_relative_dir,
)
from lee.orchestrator.execution.artifacts.types import SSOTType


def test_resolve_ssot_relative_dir_keeps_formal_tech_in_spec() -> None:
    resolved = resolve_ssot_relative_dir(
        SSOTType.TECH,
        parent_id="FEAT-SRC-041-005",
        artifact_id="TECH-FEAT-SRC-041-005",
    )

    assert resolved == Path("spec/tech/SRC-041")


def test_resolve_transfer_package_relative_dir_places_tech_support_in_output() -> None:
    resolved = resolve_transfer_package_relative_dir("tech_design", "FEAT-SRC-041-005")

    assert resolved == Path("output/tech-packages/FEAT-SRC-041-005")


def test_resolve_transfer_package_relative_dir_rejects_unknown_kind() -> None:
    with pytest.raises(ValueError, match="Unsupported transfer package kind"):
        resolve_transfer_package_relative_dir("unknown", "FEAT-SRC-041-005")
