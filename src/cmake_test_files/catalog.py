from __future__ import annotations

import json
import typing
from collections import defaultdict
from dataclasses import dataclass
from importlib import resources
from pathlib import PurePosixPath

import cattrs
from cattrs.errors import BaseValidationError

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterator


@dataclass(frozen=True, slots=True)
class CatalogFile:
    """A single downloadable file within a catalog entry."""

    path: PurePosixPath
    sha256: str


@dataclass(frozen=True, slots=True)
class Catalog:
    """The packaged CMake file catalog."""

    schema_version: int
    entries: tuple[CatalogEntry, ...]

    def licenses(self) -> tuple[str, ...]:
        return tuple(sorted({entry.license for entry in self.entries}))

    def entries_by_license(self) -> dict[str, tuple[CatalogEntry, ...]]:
        grouped: defaultdict[str, list[CatalogEntry]] = defaultdict(list)
        for entry in self.entries:
            grouped[entry.license].append(entry)
        return {key: tuple(value) for key, value in sorted(grouped.items())}

    def filter(
        self, licenses: Collection[str] | None = None
    ) -> tuple[CatalogEntry, ...]:
        if licenses is None:
            return self.entries

        requested = {license_name.casefold() for license_name in licenses}
        return tuple(
            entry for entry in self.entries if entry.license.casefold() in requested
        )

    def iter_paths(
        self, licenses: Collection[str] | None = None
    ) -> Iterator[PurePosixPath]:
        for entry in self.filter(licenses):
            for file in entry.files:
                yield file.path

    def iter_files(
        self, licenses: Collection[str] | None = None
    ) -> Iterator[CatalogFile]:
        for entry in self.filter(licenses):
            yield from entry.files


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """A downloadable project entry in the packaged catalog."""

    license: str
    description: str
    commit_sha: str
    files: tuple[CatalogFile, ...]

    def url_for(self, file: CatalogFile) -> str:
        if len(file.path.parts) < 4:
            msg = (
                f"Catalog path must include license, owner, repo, and file: {file.path}"
            )
            raise ValueError(msg)

        owner = file.path.parts[1]
        repo = file.path.parts[2]
        source_path = PurePosixPath(*file.path.parts[3:]).as_posix()
        return (
            f"https://raw.githubusercontent.com/{owner}/{repo}/"
            f"{self.commit_sha}/{source_path}"
        )


def load_catalog() -> Catalog:
    raw_data = (
        resources.files("cmake_test_files")
        .joinpath("catalog.json")
        .read_text(encoding="utf-8")
    )
    payload = json.loads(raw_data)
    if not isinstance(payload, dict):
        msg = "Catalog payload must be a JSON object"
        raise TypeError(msg)

    entries_data = payload.get("entries")
    if not isinstance(entries_data, list):
        msg = "Catalog entries must be a JSON array"
        raise TypeError(msg)

    try:
        catalog = _CATALOG_CONVERTER.structure(payload, Catalog)
    except BaseValidationError as exc:
        msg = "Catalog payload has invalid structure"
        raise TypeError(msg) from exc
    return catalog


def catalog_json() -> str:
    return (
        resources.files("cmake_test_files")
        .joinpath("catalog.json")
        .read_text(encoding="utf-8")
    )


def _structure_strict_str(value: object, _: type[str]) -> str:
    if not isinstance(value, str):
        msg = "Catalog string fields must contain strings"
        raise TypeError(msg)
    return value


def _structure_strict_int(value: object, _: type[int]) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        msg = "Catalog integer fields must contain integers"
        raise TypeError(msg)
    return value


def _structure_pure_posix_path(value: object, _: type[PurePosixPath]) -> PurePosixPath:
    if not isinstance(value, str):
        msg = "Catalog path fields must contain strings"
        raise TypeError(msg)
    return PurePosixPath(value)


_CATALOG_CONVERTER = cattrs.Converter()
_CATALOG_CONVERTER.register_structure_hook(str, _structure_strict_str)
_CATALOG_CONVERTER.register_structure_hook(int, _structure_strict_int)
_CATALOG_CONVERTER.register_structure_hook(PurePosixPath, _structure_pure_posix_path)
