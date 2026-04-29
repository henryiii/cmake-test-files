from __future__ import annotations

import json
import typing
from collections import defaultdict
from dataclasses import dataclass
from importlib import resources
from pathlib import PurePosixPath

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterator


@dataclass(frozen=True, slots=True)
class CatalogEntry:
    """A single downloadable CMake file in the packaged catalog."""

    license: str
    path: PurePosixPath
    url: str
    description: str
    sha256: str

    @classmethod
    def from_dict(cls, data: dict[str, object]) -> CatalogEntry:
        return cls(
            license=_string_field(data, "license"),
            path=PurePosixPath(_string_field(data, "path")),
            url=_string_field(data, "url"),
            description=_string_field(data, "description"),
            sha256=_string_field(data, "sha256"),
        )


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
            yield entry.path


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

    entries = tuple(
        CatalogEntry.from_dict(_entry_dict(entry)) for entry in entries_data
    )
    return Catalog(
        schema_version=_int_field(payload, "schema_version"), entries=entries
    )


def catalog_json() -> str:
    return (
        resources.files("cmake_test_files")
        .joinpath("catalog.json")
        .read_text(encoding="utf-8")
    )


def _string_field(data: dict[str, object], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        msg = f"Catalog field {key!r} must be a string"
        raise TypeError(msg)
    return value


def _int_field(data: dict[str, object], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        msg = f"Catalog field {key!r} must be an integer"
        raise TypeError(msg)
    return value


def _entry_dict(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        msg = "Catalog entries must contain JSON objects"
        raise TypeError(msg)
    return value
