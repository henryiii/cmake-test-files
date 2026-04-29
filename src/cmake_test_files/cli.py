from __future__ import annotations

import argparse
import json
import sys
import typing
from pathlib import Path

from .catalog import Catalog, load_catalog
from .download import download_files

if typing.TYPE_CHECKING:
    from collections.abc import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cmake-test-files")
    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List catalog entries")
    list_parser.add_argument(
        "--license",
        dest="licenses",
        action="append",
        help="Restrict output to a specific SPDX license identifier",
    )
    list_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a tabular text view",
    )

    licenses_parser = subparsers.add_parser("licenses", help="List license groups")
    licenses_parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of a tabular text view",
    )

    download_parser = subparsers.add_parser("download", help="Download catalog files")
    download_parser.add_argument("destination", type=Path)
    download_parser.add_argument(
        "--license",
        dest="licenses",
        action="append",
        help="Restrict downloads to a specific SPDX license identifier",
    )
    download_parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing files even if they do not match the catalog checksum",
    )

    args = parser.parse_args(argv)
    catalog = load_catalog()

    if args.command == "list":
        return _run_list(catalog, licenses=args.licenses, as_json=args.json)
    if args.command == "licenses":
        return _run_licenses(catalog, as_json=args.json)
    if args.command == "download":
        return _run_download(
            catalog,
            destination=args.destination,
            licenses=args.licenses,
            overwrite=args.overwrite,
        )

    msg = f"Unknown command: {args.command}"
    raise ValueError(msg)


def _run_list(catalog: Catalog, *, licenses: list[str] | None, as_json: bool) -> int:
    entries = catalog.filter(licenses)
    if as_json:
        payload = [
            {
                "license": entry.license,
                "path": entry.path.as_posix(),
                "url": entry.url,
                "description": entry.description,
                "sha256": entry.sha256,
            }
            for entry in entries
        ]
        sys.stdout.write(f"{json.dumps(payload, indent=2)}\n")
        return 0

    for entry in entries:
        sys.stdout.write(f"{entry.license}\t{entry.path.as_posix()}\t{entry.url}\n")
    return 0


def _run_licenses(catalog: Catalog, *, as_json: bool) -> int:
    grouped = catalog.entries_by_license()
    if as_json:
        payload = {
            license_name: len(entries) for license_name, entries in grouped.items()
        }
        sys.stdout.write(f"{json.dumps(payload, indent=2, sort_keys=True)}\n")
        return 0

    for license_name, entries in grouped.items():
        sys.stdout.write(f"{license_name}\t{len(entries)}\n")
    return 0


def _run_download(
    catalog: Catalog,
    *,
    destination: Path,
    licenses: list[str] | None,
    overwrite: bool,
) -> int:
    report = download_files(
        destination,
        licenses=licenses,
        overwrite=overwrite,
        entries=catalog.filter(licenses),
    )
    for path in report.downloaded:
        sys.stdout.write(f"downloaded\t{path}\n")
    for path in report.skipped:
        sys.stdout.write(f"skipped\t{path}\n")
    return 0
