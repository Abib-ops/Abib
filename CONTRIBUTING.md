# Contributing to Abib

Thanks for your interest in improving Abib! This guide covers the development
setup, how to run the checks, and how the application is built and packaged.
Abib is free software licensed under **GPL-3.0-or-later**; by contributing you
agree your changes are offered under the same licence.

## Requirements

- **Python 3.14 or newer.** This is the real floor: the code relies on PEP 649
  deferred evaluation of annotations (the default from 3.14), a PEP 695 `type`
  alias (3.12+), and the stdlib `tomllib` module (3.11+).
- **[uv](https://docs.astral.sh/uv/)** for dependency management and running
  tools. (You can use a plain `venv` + `pip` instead, but the commands below
  assume `uv`.)
- A desktop Qt stack for running the GUI. On Linux you may need system Qt/XCB
  packages (see "Running on Linux / macOS" below).

## Getting started

```bash
# Clone, then from the repository root:
uv sync            # installs the project plus the dev tooling group
```

`uv sync` installs the `dev` dependency group by default (pytest, pytest-cov,
mypy, ruff and pyinstaller), so there is no separate "extras" step.

Run the application with:

```bash
uv run python -m abib.Abib
# or
uv run python src/abib/Abib.py
```

## Development checks

The same three gates run in CI (see `.github/workflows/ci.yml`); please run them
locally before opening a pull request:

```bash
# 1. Lint
uv run ruff check .

# 2. Type-check (scoped to the modular core/domain/services/utils packages)
uv run mypy

# 3. Tests (headless — Qt needs a platform plugin)
#   Linux/macOS:
QT_QPA_PLATFORM=offscreen uv run pytest
#   Windows (PowerShell):
$env:QT_QPA_PLATFORM='offscreen'; uv run pytest
```

Coverage is reported (`uv run pytest --cov`) but no minimum threshold is enforced
yet. New code should come with tests, especially for pure logic in `core`,
`domain`, `services` and `utils`.

### Project layout

```
src/abib/
  core/       domain-agnostic building blocks (config, history, sync, updater…)
  domain/     Bible/scripture domain logic
  services/   application services (search, audio, data loading…)
  ui/         PySide6 widgets and the controllers extracted from MainWindow
  utils/      small reusable helpers (files, text, platform…)
  Abib.py     the MainWindow entry point / coordinator
tests/        pytest suite
```

Type checking is currently scoped (in `pyproject.toml`) to the non-UI packages
(`core`, `domain`, `services`, `utils`). The UI layer and the historically large
`Abib.py` are being modularised incrementally; prefer adding new, testable logic
to the non-UI packages where it can be type-checked and unit-tested.

### Cross-platform code

Avoid bare `sys.platform` string checks. Use the helpers in
`abib.utils.platform` instead:

```python
from abib.utils import platform as plat

if plat.is_windows():
    ...
```

Always build paths with `pathlib.Path` (never hard-coded `C:\...` or `/`
separators). Per-user writable locations are resolved for each OS in
`abib.core.shared` (`user_settings_dir`).

## Building the installer (Windows)

Releases are produced with PyInstaller using the committed spec file, and the
Windows installer is built with Inno Setup:

```bash
uv run pyinstaller Abib.spec
# then compile 64Bit_for_Abib.iss with Inno Setup
```

## Pull requests

- Keep changes focused and incremental.
- Make sure `ruff`, `mypy` and `pytest` all pass.
- Add or update tests for behaviour changes.
- Describe the change and the reasoning in the PR description.
