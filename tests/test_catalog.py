from __future__ import annotations

import urllib.request
from io import BytesIO
from pathlib import Path, PurePosixPath

import pytest

from cmake_test_files.catalog import Catalog, CatalogEntry, load_catalog
from cmake_test_files.download import download_files


def test_load_catalog() -> None:
    catalog = load_catalog()

    assert catalog.schema_version == 1
    assert len(catalog.entries) == 17
    assert catalog.licenses() == ("Apache-2.0", "BSD-3-Clause", "BSL-1.0", "MIT")


def test_catalog_filter_is_case_insensitive() -> None:
    catalog = load_catalog()

    entries = catalog.filter(["mit"])

    assert [entry.id for entry in entries] == [
        "doctest-top-level",
        "nlohmann-json-top-level",
        "fmt-top-level",
        "magic-enum-top-level",
        "spdlog-top-level",
        "yaml-cpp-top-level",
    ]


def test_download_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    entry = CatalogEntry(
        id="example",
        license="MIT",
        path=PurePosixPath("MIT/example/CMakeLists.txt"),
        url="https://example.invalid/CMakeLists.txt",
        source_url="https://example.invalid/source",
        source_repository="https://example.invalid/repo",
        description="Example file",
        sha256="022d843e9eb900dbf96b549eb873ca183d1a46c8f9e8b51e7b132df74b37b074",
        size=14,
    )
    catalog = Catalog(schema_version=1, entries=(entry,))

    def fake_urlopen(request: urllib.request.Request) -> BytesIO:
        assert request.full_url == entry.url
        return BytesIO(b"project(test)\n")

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    report = download_files(tmp_path, entries=catalog.entries)
    output_path = tmp_path / "MIT" / "example" / "CMakeLists.txt"

    assert report.downloaded == (output_path,)
    assert report.skipped == ()
    assert output_path.read_text(encoding="utf-8") == "project(test)\n"

    second_report = download_files(tmp_path, entries=catalog.entries)
    assert second_report.downloaded == ()
    assert second_report.skipped == (output_path,)


def test_download_files_rejects_path_escape(tmp_path: Path) -> None:
    entry = CatalogEntry(
        id="bad-path",
        license="MIT",
        path=PurePosixPath("../escape.txt"),
        url="https://example.invalid/escape.txt",
        source_url="https://example.invalid/source",
        source_repository="https://example.invalid/repo",
        description="Bad path",
        sha256="0" * 64,
        size=0,
    )

    with pytest.raises(ValueError, match="stay within the destination"):
        download_files(tmp_path, entries=(entry,))
