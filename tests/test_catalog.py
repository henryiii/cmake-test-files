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

    assert catalog.schema_version == 3
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
            "schema_version": 3,
            "entries": [
                {
                    "license": "MIT",
                    "description": "Example file",
                    "commit_sha": "1234abcd",
                    "files": [
                        {
                            "path": "MIT/example/project/CMakeLists.txt",
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
            commit_sha="1234abcd",
            files=(
                CatalogFile(
                    path=PurePosixPath("MIT/example/project/CMakeLists.txt"),
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
        {"schema_version": 3, "entries": {"license": "MIT"}},
    )

    with pytest.raises(TypeError, match="Catalog entries must be a JSON array"):
        load_catalog()


@pytest.mark.parametrize(
    ("payload"),
    [
        {"schema_version": "1", "entries": []},
        {
            "schema_version": 3,
            "entries": [
                {
                    "license": 1,
                    "description": "Example file",
                    "files": [],
                }
            ],
        },
        {
            "schema_version": 3,
            "entries": [
                {
                    "license": "MIT",
                    "description": 1,
                    "files": [],
                }
            ],
        },
        {
            "schema_version": 3,
            "entries": [
                {
                    "license": "MIT",
                    "description": "Example file",
                    "commit_sha": 1,
                    "files": [],
                }
            ],
        },
        {
            "schema_version": 3,
            "entries": [
                {
                    "license": "MIT",
                    "description": "Example file",
                    "commit_sha": "1234abcd",
                    "files": {
                        "path": "MIT/example/CMakeLists.txt",
                    },
                }
            ],
        },
        {
            "schema_version": 3,
            "entries": [
                {
                    "license": "MIT",
                    "description": "Example file",
                    "commit_sha": "1234abcd",
                    "files": [
                        {
                            "path": 1,
                            "sha256": "0" * 64,
                        }
                    ],
                }
            ],
        },
        {"schema_version": 3, "entries": [1]},
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
        commit_sha="1234abcd",
        files=(
            CatalogFile(
                path=PurePosixPath("MIT/example/project/CMakeLists.txt"),
                sha256="022d843e9eb900dbf96b549eb873ca183d1a46c8f9e8b51e7b132df74b37b074",
            ),
            CatalogFile(
                path=PurePosixPath("MIT/example/project/LICENSE"),
                sha256="267f7a2e19dfa9df99af774520985a0e521925293ea5b7e767ab06969d06bf91",
            ),
        ),
    )
    catalog = Catalog(schema_version=3, entries=(entry,))
    responses = {
        "https://raw.githubusercontent.com/example/project/1234abcd/CMakeLists.txt": (
            b"project(test)\n"
        ),
        "https://raw.githubusercontent.com/example/project/1234abcd/LICENSE": (
            b"MIT License\n"
        ),
    }

    def fake_urlopen(request: urllib.request.Request) -> BytesIO:
        return BytesIO(responses[request.full_url])

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    report = download_files(tmp_path, entries=catalog.entries)
    cmake_path = tmp_path / "MIT" / "example" / "project" / "CMakeLists.txt"
    license_path = tmp_path / "MIT" / "example" / "project" / "LICENSE"

    assert report.downloaded == (cmake_path, license_path)
    assert report.skipped == ()
    assert cmake_path.read_text(encoding="utf-8") == "project(test)\n"
    assert license_path.read_text(encoding="utf-8") == "MIT License\n"

    second_report = download_files(tmp_path, entries=catalog.entries)
    assert second_report.downloaded == ()
    assert second_report.skipped == (cmake_path, license_path)


def test_download_files_skips_crlf_converted_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Files with CRLF line endings (e.g., Windows git checkout) should be treated as matching."""
    entry = CatalogEntry(
        license="MIT",
        description="Example file",
        commit_sha="1234abcd",
        files=(
            CatalogFile(
                path=PurePosixPath("MIT/example/project/CMakeLists.txt"),
                sha256="022d843e9eb900dbf96b549eb873ca183d1a46c8f9e8b51e7b132df74b37b074",
            ),
        ),
    )
    cmake_path = tmp_path / "MIT" / "example" / "project" / "CMakeLists.txt"
    cmake_path.parent.mkdir(parents=True)
    cmake_path.write_bytes(b"project(test)\r\n")

    monkeypatch.setattr(urllib.request, "urlopen", lambda _: BytesIO(b""))

    report = download_files(tmp_path, entries=(entry,))
    assert report.downloaded == ()
    assert report.skipped == (cmake_path,)


def test_download_files_rejects_path_escape(tmp_path: Path) -> None:
    entry = CatalogEntry(
        license="MIT",
        description="Bad path",
        commit_sha="1234abcd",
        files=(
            CatalogFile(
                path=PurePosixPath("../escape.txt"),
                sha256="0" * 64,
            ),
        ),
    )

    with pytest.raises(ValueError, match="stay within the destination"):
        download_files(tmp_path, entries=(entry,))


def test_catalog_entry_url_for() -> None:
    entry = CatalogEntry(
        license="MIT",
        description="Example file",
        commit_sha="1234abcd",
        files=(
            CatalogFile(
                path=PurePosixPath("MIT/example/project/cmake/CMakeLists.txt"),
                sha256="0" * 64,
            ),
        ),
    )

    assert (
        entry.url_for(entry.files[0])
        == "https://raw.githubusercontent.com/example/project/1234abcd/cmake/CMakeLists.txt"
    )


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
