"""
SSOT placement policy.

目录层回答正式 SSOT 主文件应该落在哪个内容目录。
运行态缓存、manifest、registry 仍然保留在 .artifacts/ 下。
"""

from pathlib import Path
from typing import Any, Iterable, Optional

from .types import SSOTType
from .id_parser import parse_src_root


SSOT_PLACEMENT_DIRS = {
    SSOTType.SRC: Path("spec/source"),
    SSOTType.EPIC: Path("spec/requirements"),
    SSOTType.FEAT: Path("spec/requirements"),
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

LEGACY_REQUIREMENT_DIRS = {
    SSOTType.EPIC: Path("spec/requirements/epics"),
    SSOTType.FEAT: Path("spec/requirements/features"),
}

def resolve_src_root_id(
    artifact_id: Optional[str] = None,
    parent_id: Optional[str] = None,
    source_refs: Optional[Iterable[str]] = None,
    properties: Optional[dict[str, Any]] = None,
) -> Optional[str]:
    """Resolve the SRC root identity for a SSOT object."""
    properties = properties or {}
    explicit = properties.get("src_root_id")
    if isinstance(explicit, str) and explicit:
        return explicit

    for candidate in (artifact_id, parent_id):
        resolved = parse_src_root(candidate or "")
        if resolved:
            return resolved

    for source_ref in source_refs or []:
        base_id = str(source_ref).split("#", 1)[0]
        resolved = parse_src_root(base_id)
        if resolved:
            return resolved

    return None


def resolve_ssot_relative_dir(
    ssot_type: SSOTType,
    parent_id: Optional[str] = None,
    source_refs: Optional[Iterable[str]] = None,
    artifact_id: Optional[str] = None,
    properties: Optional[dict[str, Any]] = None,
) -> Path:
    """
    Resolve the project-relative directory for a formal SSOT object.
    """
    try:
        base_dir = SSOT_PLACEMENT_DIRS[ssot_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported SSOT placement type: {ssot_type}") from exc

    src_root_id = resolve_src_root_id(
        artifact_id=artifact_id,
        parent_id=parent_id,
        source_refs=source_refs,
        properties=properties,
    )

    if ssot_type in (SSOTType.EPIC, SSOTType.FEAT) and src_root_id:
        return base_dir / src_root_id

    if ssot_type in LEGACY_REQUIREMENT_DIRS:
        return LEGACY_REQUIREMENT_DIRS[ssot_type]

    if ssot_type == SSOTType.TASK and parent_id:
        return (base_dir / src_root_id / parent_id) if src_root_id else (base_dir / parent_id)

    if ssot_type in (SSOTType.TECH, SSOTType.TESTSET, SSOTType.TC, SSOTType.BUG, SSOTType.EVI, SSOTType.REPORT, SSOTType.UI) and src_root_id:
        return base_dir / src_root_id

    return base_dir
