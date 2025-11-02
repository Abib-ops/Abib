# Abib Bible Reader

A lightweight, fast desktop Bible reader focused on speed, small screen footprint, and powerful navigation/search.

It includes Spurgeon’s Morning and Evening daily readings and is designed to sit neatly beside livestreams (YouTube, Zoom) and personal study.

This README reflects the recent refactor and module layout. 
It replaces older notes and consolidates information from README.txt and HELP.txt.


## Overview
- Platform: Desktop GUI (cross‑platform; primary focus Windows)
- Language: Python 3.13
- GUI framework: PySide6 (Qt for Python)
- Key libs: requests (update checks), pygame (short UI sound), roman
- Packaging: PyInstaller (Windows builds)
- Entry points (from source):
  - Preferred: `python -m app` or `python app.py`
  - Also supported: `python Abib.py` (delegates to app.run())
- Data: KJV/PCE text and indices, Spurgeon’s Morning & Evening JSON, images, fonts, and helper lists bundled in the repo.

Main features
- Fast jump to scripture references (typed refs or UI controls)
- Find dialog with whole‑word, any/all words, and range options
- Morning & Evening devotional in a secondary window with easy next/previous navigation
- Other Works library: Pilgrim’s Progress plus 9 classic books; open from the bottom‑right drop‑down
- Theme support (Light/Dark) with a settings dialog
- Small, resizable window suited to side‑by‑side viewing
- Per‑user settings for window geometry and font sizes that persist across sessions
- Optional splash screen
- Built‑in update check against GitHub releases (Windows)


## What changed recently (high‑level)
- New bootstrap in `app.py` (centralised startup and screen metrics)
- Services layer: `services.settings`, `services.data_loader`, `services.audio`, `services.printing`
- UI helpers: `ui.actions` (menus/toolbars/shortcuts), `ui.themes` (ThemeManager)
- Domain logic moved to `domain.*` (e.g., reading plans and scripture ref parsing)
- Update check moved to `updater.py` using GitHub Releases API
- Tests added for non‑GUI logic (see Tests)


## Requirements
- OS: Windows 10/11 recommended. The code is largely cross‑platform, but Windows is the target for packaged builds.
- Python: 3.13 (developed on 3.13.9)
- Font: Cascadia Mono/Code recommended for the best alignment and appearance
- Disk layout: run from the repository root so that data files and images are found next to the code

Python dependencies (see `requirements.txt`)
- PySide6/shiboken6 6.10.0
- pygame 2.6.1
- requests 2.32.5
- roman 5.1
- pyinstaller 6.16.0 (for packaging)
- And transitive packages pinned in `requirements.txt`


## Setup (from source)
1) Clone or download this repository keeping all files together.
2) Optional: create and activate a virtual environment.
   - Windows (PowerShell)
     - `py -3.13 -m venv .venv`
     - `.\.venv\Scripts\Activate.ps1`
   - Linux/macOS
     - `python3.13 -m venv .venv`
     - `source .venv/bin/activate`
3) Install dependencies:
   - `pip install -r requirements.txt`
4) (Recommended) Install the Cascadia Code/Mono font (see Font section).


## Run
From the project root (where the data files and images are):
- Preferred: `python -m app`
- Or: `python app.py`
- Also works: `python Abib.py`

Notes
- Run from the repository root so required data files and images are found.
- On the first run, user settings are created under your OS’s per‑user config directory (see Settings & Paths).
- On Windows, an update check runs at startup and may offer to download a newer installer.


## Settings & Paths
- Per‑user settings are stored in `settings.json`:
  - Windows: `%APPDATA%\Abib\settings.json`
  - macOS: `~/Library/Application Support/Abib/settings.json`
  - Linux: `~/.config/Abib/settings.json`
- Settings include:
  - `theme`: "Light" or "Dark"
  - `show_splash`: whether to show the barley splash on startup
  - Remembered window positions/sizes and font sizes (main/devotional)
- Assets expected at runtime relative to the working directory, e.g.:
  - `images/abib_icon0.ico` (application icon)
  - `images/Abib_barley.png` (optional splash)


## Font (Cascadia Mono)
For best results use Microsoft’s Cascadia Mono/Code font.
- Windows 11: included by default
- Windows 10: open “Font settings”, then drag‑drop `CascadiaMono.ttf` to install
- Arch Linux: `sudo pacman -S ttf-cascadia-code`
- Other: download from https://github.com/microsoft/cascadia-code/releases and install the `.ttf`

The repository includes a `font/` folder for convenience.


## Using Abib (quick guide)
- Reference entry
  - Type refs like `g50.7` for Genesis 50:7 (a period `.` separates chapter/verse)
  - Book shortcuts are supported (see HELP.txt for many examples, e.g., `php` → Philippians)
- Find dialog
  - Whole‑word, any/all words, and range searches; open via the menu/toolbar
- Navigation
  - Back/forward through visited passages
  - Morning & Evening: open the secondary window and use the left/right controls
- Shortcuts
  - Increase/decrease font size: `Ctrl+=`/`Ctrl++` and `Ctrl+-`
  - Toggle theme: via Settings, or use the menu item if provided by your build
- Printing
  - File → Print… will print the visible text via the system print dialog

See `HELP.txt` for detailed usage, tips, and reference formats.

## Other Works (Pilgrim's Progress + 9 other texts)
- Access: Click the bottom-right drop-down (button in older builds) in the main window to open these texts in a separate reader window. The default selection is Pilgrims-Progress.
- Location: Files live under the `Other Works/` folder next to the app; each is a `.txt` file.
- Included titles
  - Pilgrims-Progress.txt — The Pilgrim's Progress (John Bunyan)
  - The Holy War.txt — John Bunyan
  - Institutes.txt — John Calvin
  - Of Prayer - Calvin.txt — John Calvin
  - Catechisms John Owen.txt — John Owen
  - Pneumatologia.txt — John Owen
  - Puritan Catechism.txt — Spurgeon’s Puritan Catechism
  - Naves Topical Bible.txt — Nave’s topical index
  - Election A. W. Pink.txt — A. W. Pink
  - Election C. D. Cole.txt — C. D. Cole

Note: Some builds may include additional titles; the drop-down lists whatever `.txt` files are present in `Other Works/`.


## Data files expected beside the app
- `KJB_PCE.txt` (Bible text)
- `Amap.txt`, `Info.txt`
- Search indexes: `PCE-find.txt`, `PCE-lower.txt`, `PCE-stripped.txt`, `PCE-stripped_lower.txt`
- Dictionaries: `stripped_dict.txt`, `strpd_low_dict.txt`, `list_dict.json`, `list_lowdict.json`
- Devotional: `morning_evening.json`
- Images: `images/abib_icon0.ico`, `images/Abib_barley.png`, plus toolbar icons
- Other Works: `Other Works/` folder containing Pilgrim’s Progress and 9 included books (see section above)
- Optional: `font/` with CascadiaMono fonts


## Packaging (PyInstaller)
This project ships the source; Windows installers are built with PyInstaller.
- Example command (from the project root):
  - `pyinstaller --noconfirm --clean --windowed --name Abib app.py`
- You may need to include data files explicitly using `--add-data` (the format differs by OS shell). Example on Windows PowerShell:
  - `--add-data "KJB_PCE.txt;." --add-data "Amap.txt;." --add-data "Info.txt;."`
  - `--add-data "PCE-find.txt;." --add-data "PCE-lower.txt;." --add-data "PCE-stripped.txt;." --add-data "PCE-stripped_lower.txt;."`
  - `--add-data "stripped_dict.txt;." --add-data "strpd_low_dict.txt;." --add-data "list_dict.json;." --add-data "list_lowdict.json;."`
  - `--add-data "morning_evening.json;." --add-data "images;images" --add-data "Other Works;Other Works" --add-data "font;font" --add-data "LICENSE;."`
- A `.spec` file is recommended to keep these in one place. TODO: add a maintained spec to the repo.


## Environment variables
- `PYGAME_HIDE_SUPPORT_PROMPT=1` is set in code to suppress pygame’s console message.
- `%APPDATA%` (Windows) is used by the app to locate the per‑user settings directory.


## Tests
Automated tests cover core non‑Qt logic.

Run from the repo root:
- Windows: `python -m unittest discover -s tests -p "test_*.py"`
- Linux/macOS: `python3 -m unittest discover -s tests -p "test_*.py"`

Coverage highlights
- `domain.scripture_refs`: reference parsing and line calculation
- `domain.reading_plans`: Morning & Evening loading and reference extraction; tolerant of missing/invalid JSON

Notes
- Tests avoid importing Qt widgets and do not require a running event loop.


## Project structure (selected)
- `app.py` – application bootstrap and window creation
- `Abib.py` – main window and core UI logic (still supports `python Abib.py`)
- `domain/`
  - `scripture_refs.py` – parse references and map to lines
  - `reading_plans.py` – Spurgeon’s Morning & Evening service
- `services/`
  - `settings.py` – settings service and geometry helpers
  - `data_loader.py` – centralised loading of Bible text and search indexes
  - `audio.py` – safe wrapper for short UI sounds
  - `printing.py` – Qt printing wrapper
- `ui/`
  - `actions.py` – menus, toolbars, and shortcuts
  - `themes.py` – ThemeManager (Light/Dark)
- Other UI and helpers: `find.py`, `find.ui`, `ui_find.py`, `find_dialog.py`, `text_window.py`, `settings_dialog.py`, `windows.py`, `ui_helpers.py`
- Core helpers: `fcs.py`, `shared.py`
- Updater: `updater.py` (GitHub Releases)
- Data and assets: see Data files above
- Docs: `README.txt`, `HELP.txt`, `ABOUT.txt`
- Tests: `tests/` with unit tests for domain logic

Run location
- Run from the repository root so relative data files and images are found. The app will exit with an error if essential assets (e.g., `images/abib_icon0.ico`) are missing.


## Troubleshooting
- The app exits early or cannot find files
  - Make sure you are running from the repository root and that required data files exist
- Missing icons or splash
  - Ensure the `images/` folder is present and contains the expected files
- No sound on error
  - pygame is optional; if unavailable or the sound file is missing, the app continues silently
- Update prompt does not appear
  - Network issues are tolerated; the app will continue without updating


## Release builds
- Official Windows installers (when available):
  - https://github.com/Abib-ops/Abib/releases


## License
Abib is free software, distributed under the GNU General Public License, version 3 or later. See `LICENSE` for details.


## Credits
- Bible text and resources: see `README.txt` and notes
- Splash screen: Photo credit to abibofgod.com
- Spurgeon’s Morning and Evening readings from https://www.spurgeon.org, reformatted by Eternal Life Ministries. Additional resources: https://www.spurgeongems.org

© 2025 Andrew Kingston
