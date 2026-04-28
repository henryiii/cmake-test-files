# AGENTS.md

## Build system

- **Build backend:** `uv_build` (not `setuptools`/`hatchling`).
- **Package manager:** `uv`. Use `uv sync` to install the package and deps.
- No `uv.lock` is tracked (library project; this is intentional per `.gitignore`
  comments).

## Developer commands

- **Noxfile is self-executable** via `uv run --script` (has inline script
  metadata). Use any of:
  - `uv run noxfile.py -s <session>`
  - `uvx nox -s <session>`
  - `nox -s <session>` (if Nox is globally installed)
- Key sessions defined in `noxfile.py`:
  - `lint` — runs `prek run --all-files --show-diff-on-failure`
  - `pylint` — installs package editable and runs `pylint cmake_test_files`
    (slower; CI uses this)
  - `tests` — installs test deps and runs `pytest`
  - `docs` — builds Sphinx docs; auto-serves via
    `sphinx-autobuild --open-browser` if interactive and builder is `html`
  - `build_api_docs` — regenerates `sphinx-apidoc` output into `docs/api/`
  - `build` — builds sdist and wheel via `python -m build`

## Lint & type-check

- **Linting is done with `prek`**, not plain `pre-commit run`. In CI the lint
  job uses `j178/prek-action@v2` followed by `uvx nox -s pylint`.
- Pre-commit hooks include `ruff`, `mypy`, `codespell`, `shellcheck`,
  `validate-pyproject`, `check-jsonschema`, `blacken-docs`, and `prettier`.
- `mypy` is strict but globally allows untyped defs; the override
  `module = "cmake_test_files.*"` requires typed defs for the package itself.

## Tests

- Test runner: `pytest`. Run via `uv run pytest` or `nox -s tests`.
- Pytest config in `pyproject.toml`: `strict = true`,
  `filterwarnings = ["error"]`, testpaths = `tests/`.
- Single test: `uv run pytest tests/test_package.py`.

## Docs

- Sphinx with `myst_parser` and `furo` theme. Build via `uv sync --group docs`
  then `uv run sphinx-build` or `nox -s docs`.
- ReadTheDocs config (`.readthedocs.yaml`) installs `uv` via `asdf` and runs
  `uv sync --group docs`, then `sphinx-build`.

## Release

- CD workflow builds with `hynek/build-and-inspect-python-package@v2`.
- Publishing targets **Test PyPI**
  (`repository-url: https://test.pypi.org/legacy/`). The comment in `cd.yml`
  says to remove that line to publish to real PyPI.

## Style conventions

- Ruff lint ignores: `PLR09` (too many), `PLR2004` (magic values).
- Tests and `noxfile.py` are allowed `T20` (print/debugger) via per-file
  ignores.
- Pre-commit has a custom local hook disallowing improper capitalization for
  names such as Pybind, NumPy, CMake, ccache, GitHub, and pytest.
