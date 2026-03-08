"""
SSOT placement policy.

目录层回答正式 SSOT 主文件应该落在哪个内容目录。
运行态缓存、manifest、registry 仍然保留在 .artifacts/ 下。
"""

from pathlib import Path

from .types import SSOTType


SSOT_PLACEMENT_DIRS = {
    SSOTType.SRC: Path("spec/source"),
    SSOTType.EPIC: Path("spec/requirements/epics"),
    SSOTType.FEAT: Path("spec/requirements/features"),
    SSOTType.RELEASE: Path("spec/delivery/releases"),
    SSOTType.UI: Path("spec/ui"),
    SSOTType.TECH: Path("spec/tech"),
    SSOTType.DEVPLAN: Path("spec/delivery/devplans"),
    SSOTType.TESTPLAN: Path("spec/delivery/testplans"),
    SSOTType.TASK: Path("spec/tasks"),
    SSOTType.TESTSET: Path("spec/testing/testsets"),
    SSOTType.TC: Path("tests/cases"),
    SSOTType.BUG: Path("tests/bugs"),
    SSOTType.REPORT: Path("docs/reports/testing"),
    SSOTType.ADR: Path("spec/adr"),
    SSOTType.EVI: Path("docs/reports/evidence"),
}


def resolve_ssot_relative_dir(ssot_type: SSOTType) -> Path:
    """
    Resolve the project-relative directory for a formal SSOT object.
    """
    try:
        return SSOT_PLACEMENT_DIRS[ssot_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported SSOT placement type: {ssot_type}") from exc
