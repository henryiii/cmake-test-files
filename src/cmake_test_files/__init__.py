"""Copyright (c) 2026 Henry Schreiner. All rights reserved.

cmake-test-files: A collection of CMake files for testing.
"""

from __future__ import annotations

from .catalog import Catalog, CatalogEntry, catalog_json, load_catalog
from .download import DownloadReport, download_files

__version__ = "0.1.0"

__all__ = [
    "Catalog",
    "CatalogEntry",
    "DownloadReport",
    "__version__",
    "catalog_json",
    "download_files",
    "load_catalog",
]
