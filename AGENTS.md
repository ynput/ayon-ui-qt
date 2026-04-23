# AGENTS.md

## Development Setup

- Install dependencies: `uv sync`
- Run tests: `uv run pytest`
- Run a single test: `uv run pytest tests/<file>::<test> -v`
- Format code: `uv run ruff format <file>`
- Lint: `uv run ruff check <file>` (CI runs `ruff-action` on PRs to `develop`)
- Build package: `python create_package.py` (generates `dist/ui_qt-{version}.zip`)
  - `--skip-zip`: output unzipped server folder structure
  - `--only-client -o <dir>`: extract only client code for development
  - `--output <dir>`: custom output directory (purged if exists)

## Testing

- Tests set `QT_QPA_PLATFORM=offscreen` in `tests/conftest.py` before any Qt import
- Visual regression tests use `pytest-regressions[image]`; run with `--show-images` to view failed image comparisons in a Qt window
- Test paths: `tests/` directory (pytest `testpaths` config)
- `pythonpath` in pytest config: `["tests", "client"]` — import `ayon_ui_qt` directly
- Fixtures automatically reset `AsyncTaskQueue` between tests to prevent segfaults from stale worker threads
- Python version: `>=3.9.1,<3.10` (strict upper bound)

## Code Style

- Use DRY (Dont Repeat Yourself)
- Enforce separation of responsbilities.
- Avoid long functions and methods.
- Line length: 79 characters
- Docstrings: Google format
- Use `qtpy` instead of `PySide6` directly
- Type hints with `from __future__ import annotations`
- Fail early with descriptive error messages
- Use `logging` module instead of `print`

## Project Structure

- Client addon code: `client/ayon_ui_qt/` (components, style, resources, vendor)
- Server addon: `server/` (settings, `__init__.py`)
- AYON package definition: `package.py` (addon name: `ui_qt`, version from `version`)
- Build script: `create_package.py` — handles client zip, server files, optional frontend build
- Dependencies in `pyproject.toml`: PySide6 >=6.7.1, qtpy >=2.3.1, ruff >=0.11.4
- `client/ayon_ui_qt/old/` is excluded from builds (legacy code)
