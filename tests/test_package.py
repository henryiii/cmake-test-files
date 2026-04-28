from __future__ import annotations

import importlib.metadata

import cmake_test_files as m


def test_version() -> None:
    assert importlib.metadata.version("cmake-test-files") == m.__version__
