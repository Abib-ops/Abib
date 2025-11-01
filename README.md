# Abib Bible Reader

A lightweight, fast desktop Bible reader with powerful navigation and search, plus Spurgeon’s Morning and Evening daily readings. Designed for a small, adjustable footprint that works well alongside sermons (e.g., YouTube, Zoom) and personal study.

This README consolidates and updates project information. It keeps useful details from existing docs and adds sections requested: overview, requirements, setup/run, scripts, environment variables, tests, project structure, and license. Unknowns are marked as TODO.


## Overview
- Platform: Desktop GUI (cross‑platform; primary target Windows)
- Language: Python
- GUI framework: PySide6 (Qt for Python)
- Other key libs: pygame (sound for error), requests, roman
- Packaging: PyInstaller (for building distributables)
- Entry point: `Abib.py`
- Data: KJV/PCE text and indices, Spurgeon’s Morning/Evening, other resources in repo

Main features
- Jump to references quickly (typed refs or UI controls)
- Compact, resizable UI designed to sit beside livestreams/sermons
- Comprehensive Find dialog with multiple search modes
- Morning & Evening devotionals included
- Persistent window geometry and font sizes via per‑user settings


## Requirements
- Operating system: Windows 10/11 recommended. PySide6 is cross‑platform and the app should run on macOS/Linux if dependencies install, but Windows is the focus.
- Python: 3.13 (project has venv folders `venv_3_13` and `venv_3_14_0`; development is on Python 3.13+)
- System font: Cascadia Mono (recommended for intended appearance)
- Disk: ensure all repository data files are present in the same directory as `Abib.py` when running from source.

Python dependencies (see `requirements.txt`)
- PySide6/shiboken6 6.10.0
- pygame 2.6.1
- requests 2.32.5
- roman 5.1
- pyinstaller 6.16.0 (packaging only)
- And related transitive packages listed in `requirements.txt`


## Setup (from source)
1) Clone or download this repository so that all files sit together.
2) Optional: create and activate a virtual environment.
   - Windows (PowerShell):
     ```pwsh
     py -3.13 -m venv .venv
     .\.venv\Scripts\Activate.ps1
     ```
   - Linux/macOS:
     ```bash
     python3.13 -m venv .venv
     source .venv/bin/activate
     ```
3) Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4) (Recommended) Install Cascadia Code/Mono font (see Font section below).


## Run
From the project root (where `Abib.py` and the data files are):
```bash
python Abib.py
```
Notes
- Run from the repository root so that required data files and images are found.
- On first run, user settings are created under a per‑OS config directory (see Settings & Paths).


## Settings & Paths
- The app stores per‑user settings in `settings.json` under an OS‑specific directory (handled in `shared.py`):
  - Windows: `%APPDATA%\Abib\settings.json`
  - macOS: `~/Library/Application Support/Abib/settings.json`
  - Linux: `~/.config/Abib/settings.json`
- The application expects assets like `images/abib_icon0.ico` and `images/Abib_barley.png` to exist relative to the working directory.


## Font (Cascadia Mono)
For best results use Microsoft’s Cascadia Mono/Code font.
- Windows 11: included by default.
- Windows 10: open “Font settings”, then drag‑drop `CascadiaMono.ttf` to install.
- Arch Linux: `sudo pacman -S ttf-cascadia-code`
- Other distros/OS: download from https://github.com/microsoft/cascadia-code/releases and install the `.ttf`.

The repository includes a `font/` folder; you can install from there if present.


## Scripts and Packaging
- Entry point: `Abib.py` contains `if __name__ == "__main__":` and starts a `QApplication` and `MainWindow`.
- Sound: `pygame` is used for a simple error sound; the code suppresses the pygame startup prompt.
- Packaging: PyInstaller is listed in requirements for building executables.
  - Typical (example) command:
    ```bash
    pyinstaller --noconfirm --clean --windowed --name Abib Abib.py
    ```
  - This project does not currently include a `.spec` file in the repo. You may need to add data files (Bible text, JSONs, images, font, license) via `--add-data` options when packaging.
  - TODO: Provide a maintained `.spec` file with the correct `datas` so packaged builds find all resources.


## Environment variables
- `PYGAME_HIDE_SUPPORT_PROMPT=1` is set in code to suppress pygame’s message (no action required).
- `%APPDATA%` (Windows) is used by the app to locate the per‑user settings directory. You normally don’t need to change it.


## Tests
Automated unit tests are included for core, non-Qt logic.

How to run (no GUI required):
- From the repo root:
  - Windows (PowerShell):
    - `python -m unittest discover -s tests -p "test_*.py"`
  - Linux/macOS:
    - `python3 -m unittest discover -s tests -p "test_*.py"`

What’s covered
- `domain.scripture_refs`: reference parsing and line calculation
- `domain.reading_plans`: SME loading and reference extraction (tolerates missing/invalid JSON)

Notes
- Tests avoid importing PySide6 widgets and do not require a running Qt event loop.
- Additional coverage is desirable for window geometry persistence and search helpers in `fcs.py`.


## Project structure (selected)
The repo root includes these notable files and folders:
- `Abib.py` – main application entry point (PySide6 GUI)
- `fcs.py` – functions for searching, text utilities, settings I/O, and helpers
- `shared.py` – shared constants, paths, and data loading of `Info.txt`
- `find.py`, `find.ui`, `ui_find.py` – Find dialog UI and code generated from Qt Designer
- Data files: `KJB_PCE.txt`, `PCE-*.txt`, `list_*.json`, `morning_evening.json`, `bible_data.json`, `Info.txt`, `Amap.txt`, `find_dict.txt`, `lower_dict.txt`, `stripped_dict.txt`, etc.
- `images/` – icons and splash (e.g., `abib_icon0.ico`, `Abib_barley.png`)
- `font/` – CascadiaMono font file(s)
- `requirements.txt` – pinned dependencies
- `LICENSE` – GPLv3 license
- `README.txt`, `HELP.txt`, `ABOUT.txt` – additional documentation
- `venv_3_13`, `venv_3_14_0` – local virtual environments (not required; you can create your own `.venv`)

Run location
- Run `python Abib.py` from the repository root so relative files are found. The code will exit with an error if expected assets (e.g., `images/abib_icon0.ico`) are missing.


## Usage tips (quick)
- Type references like `g50.7` for Genesis 50:7. A period `.` acts as the chapter/verse separator.
- Use the Find dialog for whole‑word, multi‑word, or range‑scoped searches. The dialog is accessible from the UI.
- Font size shortcuts: per `HELP.txt`, use `Ctrl +` and `Ctrl -` to adjust in supported windows.
- Back/forward navigation is available for visited passages.

For more detailed usage, see `HELP.txt`.


## Release builds
- Windows installer builds are sometimes provided externally (see `README.txt` and `HELP.txt`).
- TODO: Document the authoritative release URL for update checks and downloads.


## License
Abib is free software, distributed under the GNU General Public License, version 3 or later. See `LICENSE` for details.


## Credits
- Bible text and resources: see `README.txt` and notes below.
- Splash screen: Photo credit to abibofgod.com.
- Spurgeon’s Morning and Evening readings were obtained from https://www.spurgeon.org and reformatted by Eternal Life Ministries. Additional Bible resources: https://www.spurgeongems.org.

© 2025 Andrew Kingston
