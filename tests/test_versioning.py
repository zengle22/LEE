import pytest

from lee.versioning import VersionScheme, get_version


def test_get_version_returns_a_string() -> None:
    assert isinstance(get_version(), str)
    assert get_version()


def test_candidate_version_format() -> None:
    scheme = VersionScheme(base_version="0.2.0")
    assert scheme.candidate("20260310", "7899f86") == "0.2.0.dev20260310+7899f86"


def test_release_version_accepts_tag_or_plain_semver() -> None:
    scheme = VersionScheme(base_version="0.2.0")
    assert scheme.release("v0.3.0") == "0.3.0"
    assert scheme.release("0.3.1") == "0.3.1"


def test_release_version_rejects_invalid_refs() -> None:
    scheme = VersionScheme(base_version="0.2.0")
    with pytest.raises(ValueError):
        scheme.release("release-0.3.0")
