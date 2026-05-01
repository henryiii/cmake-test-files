from __future__ import annotations

import hashlib
import tempfile
import typing
import urllib.request
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from .catalog import CatalogEntry, CatalogFile, load_catalog

if typing.TYPE_CHECKING:
    from collections.abc import Collection, Iterable


@dataclass(frozen=True, slots=True)
class DownloadReport:
    """Paths that were downloaded or skipped during a sync."""

    downloaded: tuple[Path, ...]
    skipped: tuple[Path, ...]


def download_files(
    destination: Path | str,
    *,
    licenses: Collection[str] | None = None,
    overwrite: bool = False,
    entries: Iterable[CatalogEntry] | None = None,
) -> DownloadReport:
    target_root = Path(destination)
    selected_entries = (
        tuple(entries) if entries is not None else load_catalog().filter(licenses)
    )

    downloaded: list[Path] = []
    skipped: list[Path] = []
    for entry, file in _iter_files(selected_entries):
        relative_path = _safe_relative_path(file.path)
        output_path = target_root / relative_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.exists() and not overwrite:
            if _matches_existing_file(output_path, file):
                skipped.append(output_path)
                continue

            msg = (
                f"Refusing to overwrite {output_path} because it does not match "
                f"the catalog entry for {file.path.as_posix()!r}"
            )
            raise FileExistsError(msg)

        data = _download_entry(entry, file)
        _write_file(output_path, data)
        downloaded.append(output_path)

    return DownloadReport(downloaded=tuple(downloaded), skipped=tuple(skipped))


def _safe_relative_path(path: PurePosixPath) -> Path:
    if path.is_absolute() or ".." in path.parts:
        msg = f"Catalog path must be relative and stay within the destination: {path}"
        raise ValueError(msg)
    return Path(*path.parts)


def _iter_files(
    entries: Iterable[CatalogEntry],
) -> Iterable[tuple[CatalogEntry, CatalogFile]]:
    for entry in entries:
        for file in entry.files:
            yield entry, file


def _download_entry(catalog_entry: CatalogEntry, entry: CatalogFile) -> bytes:
    request = urllib.request.Request(
        catalog_entry.url_for(entry),
        headers={"User-Agent": "cmake-test-files/0.1.0"},
    )
    with urllib.request.urlopen(request) as response:
        data = response.read()
    if not isinstance(data, bytes):
        msg = f"Expected a bytes payload for {entry.path.as_posix()!r}"
        raise TypeError(msg)

    digest = hashlib.sha256(data).hexdigest()
    if digest != entry.sha256:
        msg = (
            f"SHA256 mismatch for {entry.path.as_posix()!r}: "
            f"expected {entry.sha256}, got {digest}"
        )
        raise ValueError(msg)

    return data


def _matches_existing_file(path: Path, entry: CatalogFile) -> bool:
    data = path.read_bytes()
    if hashlib.sha256(data).hexdigest() == entry.sha256:
        return True
    # Also accept CRLF line endings (e.g., Windows git checkout with core.autocrlf)
    normalized = data.replace(b"\r\n", b"\n")
    return normalized != data and hashlib.sha256(normalized).hexdigest() == entry.sha256


def _write_file(path: Path, data: bytes) -> None:
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as tmp_file:
        tmp_file.write(data)
        tmp_name = tmp_file.name

    Path(tmp_name).replace(path)
