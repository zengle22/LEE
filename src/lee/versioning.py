"""LEE version helpers and CI version rules."""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version as package_version
from pathlib import Path
import re


PACKAGE_NAME = "lee-framework"
SOURCE_FALLBACK_VERSION = "0.2.0"
SEMVER_RE = re.compile(r"^v?(?P<version>\d+\.\d+\.\d+)$")


def get_version() -> str:
    """Return the installed package version, with a source fallback."""
    try:
        return package_version(PACKAGE_NAME)
    except PackageNotFoundError:  # pragma: no cover - source-only fallback
        return _read_version_from_pyproject()


def _read_version_from_pyproject() -> str:
    root = Path(__file__).resolve().parents[2]
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return SOURCE_FALLBACK_VERSION

    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'^version = "(?P<version>[^"]+)"$', text, re.MULTILINE)
    if not match:
        return SOURCE_FALLBACK_VERSION
    return match.group("version")


@dataclass(frozen=True)
class VersionScheme:
    """Canonical LEE versioning rules."""

    base_version: str

    def candidate(self, stamp: str, short_sha: str) -> str:
        return f"{self.base_version}.dev{stamp}+{short_sha}"

    def release(self, ref_name: str) -> str:
        match = SEMVER_RE.fullmatch(ref_name)
        if not match:
            raise ValueError(
                f"Release ref '{ref_name}' is invalid; expected format vX.Y.Z or X.Y.Z"
            )
        return match.group("version")


def build_version_scheme(base_version: str | None = None) -> VersionScheme:
    return VersionScheme(base_version=base_version or get_version())
