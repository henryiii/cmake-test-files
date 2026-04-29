from __future__ import annotations

import json
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

    assert [entry.path.as_posix() for entry in entries] == [
        "MIT/doctest/doctest/CMakeLists.txt",
        "MIT/nlohmann/json/CMakeLists.txt",
        "MIT/fmtlib/fmt/CMakeLists.txt",
        "MIT/Neargye/magic_enum/CMakeLists.txt",
        "MIT/gabime/spdlog/CMakeLists.txt",
        "MIT/jbeder/yaml-cpp/CMakeLists.txt",
    ]


def test_load_catalog_structures_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_catalog_payload(
        tmp_path,
        monkeypatch,
        {
            "schema_version": 1,
            "entries": [
                {
                    "license": "MIT",
                    "path": "MIT/example/CMakeLists.txt",
                    "url": "https://example.invalid/CMakeLists.txt",
                    "description": "Example file",
                    "sha256": "0" * 64,
                }
            ],
        },
    )

    catalog = load_catalog()

    assert catalog.entries == (
        CatalogEntry(
            license="MIT",
            path=PurePosixPath("MIT/example/CMakeLists.txt"),
            url="https://example.invalid/CMakeLists.txt",
            description="Example file",
            sha256="0" * 64,
        ),
    )


def test_load_catalog_rejects_non_object_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_catalog_payload(tmp_path, monkeypatch, [])

    with pytest.raises(TypeError, match="Catalog payload must be a JSON object"):
        load_catalog()


def test_load_catalog_rejects_non_array_entries(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_catalog_payload(
        tmp_path,
        monkeypatch,
        {"schema_version": 1, "entries": {"license": "MIT"}},
    )

    with pytest.raises(TypeError, match="Catalog entries must be a JSON array"):
        load_catalog()


@pytest.mark.parametrize(
    ("payload"),
    [
        {"schema_version": "1", "entries": []},
        {
            "schema_version": 1,
            "entries": [
                {
                    "license": 1,
                    "path": "MIT/example/CMakeLists.txt",
                    "url": "https://example.invalid/CMakeLists.txt",
                    "description": "Example file",
                    "sha256": "0" * 64,
                }
            ],
        },
        {
            "schema_version": 1,
            "entries": [
                {
                    "license": "MIT",
                    "path": 1,
                    "url": "https://example.invalid/CMakeLists.txt",
                    "description": "Example file",
                    "sha256": "0" * 64,
                }
            ],
        },
        {"schema_version": 1, "entries": [1]},
    ],
)
def test_load_catalog_rejects_invalid_structure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    _patch_catalog_payload(tmp_path, monkeypatch, payload)

    with pytest.raises(TypeError, match="Catalog payload has invalid structure"):
        load_catalog()


def test_download_files(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    entry = CatalogEntry(
        license="MIT",
        path=PurePosixPath("MIT/example/CMakeLists.txt"),
        url="https://example.invalid/CMakeLists.txt",
        description="Example file",
        sha256="022d843e9eb900dbf96b549eb873ca183d1a46c8f9e8b51e7b132df74b37b074",
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
        license="MIT",
        path=PurePosixPath("../escape.txt"),
        url="https://example.invalid/escape.txt",
        description="Bad path",
        sha256="0" * 64,
    )

    with pytest.raises(ValueError, match="stay within the destination"):
        download_files(tmp_path, entries=(entry,))


def _patch_catalog_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    package_dir = tmp_path / "cmake_test_files"
    package_dir.mkdir()
    package_dir.joinpath("catalog.json").write_text(
        json.dumps(payload), encoding="utf-8"
    )
    monkeypatch.setattr(
        "cmake_test_files.catalog.resources.files", lambda _package: package_dir
    )
