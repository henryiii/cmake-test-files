from __future__ import annotations

import json
import urllib.request
from io import BytesIO
from pathlib import Path, PurePosixPath

import pytest

from cmake_test_files.catalog import Catalog, CatalogEntry, CatalogFile, load_catalog
from cmake_test_files.download import download_files


def test_load_catalog() -> None:
    catalog = load_catalog()

    assert catalog.schema_version == 2
    assert len(catalog.entries) == 33
    assert catalog.licenses() == (
        "Apache-2.0",
        "BSD-3-Clause",
        "BSL-1.0",
        "MIT",
        "MPL-2.0",
        "Zlib",
    )


def test_catalog_filter_is_case_insensitive() -> None:
    catalog = load_catalog()

    entries = catalog.filter(["mit"])

    assert [file.path.as_posix() for entry in entries for file in entry.files] == [
        "MIT/doctest/doctest/CMakeLists.txt",
        "MIT/doctest/doctest/LICENSE.txt",
        "MIT/nlohmann/json/CMakeLists.txt",
        "MIT/nlohmann/json/LICENSE.MIT",
        "MIT/fmtlib/fmt/CMakeLists.txt",
        "MIT/fmtlib/fmt/LICENSE",
        "MIT/Neargye/magic_enum/CMakeLists.txt",
        "MIT/Neargye/magic_enum/LICENSE",
        "MIT/gabime/spdlog/CMakeLists.txt",
        "MIT/gabime/spdlog/LICENSE",
        "MIT/jbeder/yaml-cpp/CMakeLists.txt",
        "MIT/jbeder/yaml-cpp/LICENSE",
        "MIT/jarro2783/cxxopts/CMakeLists.txt",
        "MIT/jarro2783/cxxopts/LICENSE",
        "MIT/skypjack/entt/CMakeLists.txt",
        "MIT/skypjack/entt/LICENSE",
        "MIT/libuv/libuv/CMakeLists.txt",
        "MIT/libuv/libuv/LICENSE",
        "MIT/c-ares/c-ares/CMakeLists.txt",
        "MIT/c-ares/c-ares/LICENSE.md",
    ]


def test_load_catalog_structures_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _patch_catalog_payload(
        tmp_path,
        monkeypatch,
        {
            "schema_version": 2,
            "entries": [
                {
                    "license": "MIT",
                    "description": "Example file",
                    "files": [
                        {
                            "path": "MIT/example/CMakeLists.txt",
                            "url": "https://example.invalid/CMakeLists.txt",
                            "sha256": "0" * 64,
                        }
                    ],
                }
            ],
        },
    )

    catalog = load_catalog()

    assert catalog.entries == (
        CatalogEntry(
            license="MIT",
            description="Example file",
            files=(
                CatalogFile(
                    path=PurePosixPath("MIT/example/CMakeLists.txt"),
                    url="https://example.invalid/CMakeLists.txt",
                    sha256="0" * 64,
                ),
            ),
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
        {"schema_version": 2, "entries": {"license": "MIT"}},
    )

    with pytest.raises(TypeError, match="Catalog entries must be a JSON array"):
        load_catalog()


@pytest.mark.parametrize(
    ("payload"),
    [
        {"schema_version": "1", "entries": []},
        {
            "schema_version": 2,
            "entries": [
                {
                    "license": 1,
                    "description": "Example file",
                    "files": [],
                }
            ],
        },
        {
            "schema_version": 2,
            "entries": [
                {
                    "license": "MIT",
                    "description": 1,
                    "files": [],
                }
            ],
        },
        {
            "schema_version": 2,
            "entries": [
                {
                    "license": "MIT",
                    "description": "Example file",
                    "files": {
                        "path": "MIT/example/CMakeLists.txt",
                    },
                }
            ],
        },
        {
            "schema_version": 2,
            "entries": [
                {
                    "license": "MIT",
                    "description": "Example file",
                    "files": [
                        {
                            "path": 1,
                            "url": "https://example.invalid/CMakeLists.txt",
                            "sha256": "0" * 64,
                        }
                    ],
                }
            ],
        },
        {"schema_version": 2, "entries": [1]},
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
        description="Example file",
        files=(
            CatalogFile(
                path=PurePosixPath("MIT/example/CMakeLists.txt"),
                url="https://example.invalid/CMakeLists.txt",
                sha256="022d843e9eb900dbf96b549eb873ca183d1a46c8f9e8b51e7b132df74b37b074",
            ),
            CatalogFile(
                path=PurePosixPath("MIT/example/LICENSE"),
                url="https://example.invalid/LICENSE",
                sha256="267f7a2e19dfa9df99af774520985a0e521925293ea5b7e767ab06969d06bf91",
            ),
        ),
    )
    catalog = Catalog(schema_version=2, entries=(entry,))
    responses = {
        "https://example.invalid/CMakeLists.txt": b"project(test)\n",
        "https://example.invalid/LICENSE": b"MIT License\n",
    }

    def fake_urlopen(request: urllib.request.Request) -> BytesIO:
        return BytesIO(responses[request.full_url])

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    report = download_files(tmp_path, entries=catalog.entries)
    cmake_path = tmp_path / "MIT" / "example" / "CMakeLists.txt"
    license_path = tmp_path / "MIT" / "example" / "LICENSE"

    assert report.downloaded == (cmake_path, license_path)
    assert report.skipped == ()
    assert cmake_path.read_text(encoding="utf-8") == "project(test)\n"
    assert license_path.read_text(encoding="utf-8") == "MIT License\n"

    second_report = download_files(tmp_path, entries=catalog.entries)
    assert second_report.downloaded == ()
    assert second_report.skipped == (cmake_path, license_path)


def test_download_files_rejects_path_escape(tmp_path: Path) -> None:
    entry = CatalogEntry(
        license="MIT",
        description="Bad path",
        files=(
            CatalogFile(
                path=PurePosixPath("../escape.txt"),
                url="https://example.invalid/escape.txt",
                sha256="0" * 64,
            ),
        ),
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
