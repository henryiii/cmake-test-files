# cmake-test-files

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]

[![PyPI version][pypi-version]][pypi-link]
[![Conda-Forge][conda-badge]][conda-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

[![GitHub Discussion][github-discussions-badge]][github-discussions-link]

[![Coverage][coverage-badge]][coverage-link]

<!-- SPHINX-START -->

<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/scikit-build/cmake-test-files/actions/workflows/ci.yml/badge.svg
[actions-link]:             https://github.com/scikit-build/cmake-test-files/actions
[conda-badge]:              https://img.shields.io/conda/vn/conda-forge/cmake-test-files
[conda-link]:               https://github.com/conda-forge/cmake-test-files-feedstock
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/scikit-build/cmake-test-files/discussions
[pypi-link]:                https://pypi.org/project/cmake-test-files/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/cmake-test-files
[pypi-version]:             https://img.shields.io/pypi/v/cmake-test-files
[rtd-badge]:                https://readthedocs.org/projects/cmake-test-files/badge/?version=latest
[rtd-link]:                 https://cmake-test-files.readthedocs.io/en/latest/?badge=latest
[coverage-badge]:           https://codecov.io/github/scikit-build/cmake-test-files/branch/main/graph/badge.svg
[coverage-link]:            https://codecov.io/github/scikit-build/cmake-test-files

<!-- prettier-ignore-end -->

`cmake-test-files` packages a curated JSON catalog of real-world
`CMakeLists.txt` files together with their matching license files and provides a
small downloader for materializing that catalog locally. Entries are grouped by
license so a parser test suite can target only the files you want to consume.

The starter catalog now includes 33 project entries covering 66 files across
several license groups, with examples from projects such as Abseil, benchmark,
Boost.JSON, Boost.Nowide, Catch2, CLI11, cereal, cxxopts, EnTT, FlatBuffers,
folly, fmt, googletest, magic_enum, nanobind, nlohmann/json, OpenTelemetry C++,
protobuf, pybind11, pybind's `cmake_example`, range-v3, spdlog, thrift, xtensor,
xtl, and yaml-cpp.

## Catalog format

The built-in catalog lives in `cmake_test_files/catalog.json` and uses a simple
schema:

```json
{
  "schema_version": 2,
  "entries": [
    {
      "license": "MIT",
      "description": "Feature-rich top-level configuration for a header-only project.",
      "files": [
        {
          "path": "MIT/nlohmann/json/CMakeLists.txt",
          "url": "https://raw.githubusercontent.com/owner/repo/<commit>/CMakeLists.txt",
          "sha256": "<sha256>"
        },
        {
          "path": "MIT/nlohmann/json/LICENSE.MIT",
          "url": "https://raw.githubusercontent.com/owner/repo/<commit>/LICENSE.MIT",
          "sha256": "<sha256>"
        }
      ]
    }
  ]
}
```

The downloader only requires each file's `path`, `url`, and `sha256`, so you can
move `url` from raw GitHub files to GitHub release assets later without changing
the Python API.

## CLI

```bash
cmake-test-files licenses
cmake-test-files list --license MIT
cmake-test-files download ./fixtures --license Apache-2.0
```

Downloads are written under the catalog path, so the example above would create
directories like `./fixtures/MIT/nlohmann/json/CMakeLists.txt`. Existing files
are skipped when they already match the catalog checksum; otherwise the command
refuses to overwrite unless you pass `--overwrite`.

## Python API

```python
from cmake_test_files import download_files, load_catalog

catalog = load_catalog()
mit_entries = catalog.filter(["MIT"])
report = download_files("fixtures", entries=mit_entries)
```
