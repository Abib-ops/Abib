#!/usr/bin/env python

# Abib — Copyright © 2003–2026 The Abib Contributors

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

r"""
Third-party materials and attributions:
- Pure Cambridge Edition of the KJV — see source and terms at bibleprotector.com
- Spurgeon resources — see spurgeon.org and Eternal Life Ministries for terms

                      .
               .               .
            .                      .                      .
          .                            .             .
        .      O                           .     .
       .                                      .
        .                                  .     .
          .                            .             .
            .                      .                      .
               .               .
                       .


Abib Bible Reader אביב

Using PySide6-6.11.1 and python3.14.6 (64-bit).

15/06/2026

# Automatically upgrade all packages to their latest versions
uv sync --all-extras --upgrade

----------------------------------------------------------------------------------------------------------------
Linux users — a sincere apology and quick guidance
We’re sorry: Abib is currently Windows‑centric, and our small team hasn’t kept multi‑platform support up to date.
We appreciate your patience, and we welcome improvements from Linux contributors.

Quick start on Linux (unofficial)
•
Copy the Abib folder to your home directory.
•
In a terminal, from that folder:

# (optional but recommended)
python3 -m venv .venv && source .venv/bin/activate
python3 -m pip install --upgrade pip wheel
python3 -m pip install pyside6

# make the main script executable if needed
chmod +x Abib.py

# run it
python3 Abib.py
# or, if it has a shebang
./Abib.py

If Qt errors occur, install system Qt/XCB deps (e.g. libxcb, xcb-util, xcb-util-keysyms,
Wayland/X11 plugins) via your distro’s package manager.

Tips for porting (small but high‑impact)
•
Replace Windows paths (backslashes, drive letters) with pathlib.Path throughout;
avoid hard‑coded C:\… and use relative paths.
•
Gate platform code with sys.platform.startswith('win') and provide Linux alternatives.
•
Use forward‑slash paths or Path methods when building file locations.
•
Avoid shell‑only Windows commands; prefer Python equivalents (file I/O, env vars).
•
Test with QT_QPA_PLATFORM=xcb (X11) or ensure Wayland plugins are present.
"""

import re
import sqlite3
import time
import webbrowser
from itertools import islice
from pathlib import Path
from sys import exit
from typing import Any, Dict, Set, List, Iterator

from PySide6.QtCore import Qt, QRect, QEvent, QObject, QPoint
from PySide6.QtGui import (QMouseEvent, QKeyEvent, QColor, QFont,
                           QTextCursor, QTextCharFormat, QKeySequence, QShortcut)
from PySide6.QtWidgets import (QMainWindow, QWidget,
                               QPlainTextEdit, QLineEdit, QComboBox, QGridLayout, QMessageBox,
                               QPushButton, QVBoxLayout, QStatusBar, QFileDialog, QSizePolicy)

from abib.core import fcs
from abib.core import shared as sh
from abib.core.history import History
from abib.core.navigation import NavigationCore
from abib.services.settings import SettingsService
from abib.ui.ui_helpers import NoZoomPlainTextEdit

history = History()
back = history.back
forward = history.forward

# Global window 'handle' placeholder; set by app.run() at startup
w: Any | None = None
# Global splash screen reference (kept alive until the user disables it in settings)
splash: Any | None = None

# try:
#     import torch
#     HAS_TORCH = True
#     CUDA_AVAILABLE = torch.cuda.is_available()
#     device_name = torch.cuda.get_device_name(0) if CUDA_AVAILABLE else "CPU"
#     print(f"Junie Status: PyTorch Loaded | Device: {device_name} | CUDA: {CUDA_AVAILABLE}")
# except ImportError:
#     torch = None
#     HAS_TORCH = False
#     CUDA_AVAILABLE = False
#     print ("Junie Status: PyTorch not found. AI features disabled.")


## Step 5: Reduce import and initialisation cost
# Defer heavy/optional imports to first use instead of module import time.
# - windows.* (secondary/about windows)
# - find_dialog.FindDialog
# - settings_dialog.SettingsDialog
# - ui.themes.ThemeManager/ThemeState
# - ui.actions (setup_shortcuts, setup_menus_and_toolbars)
# - text_window.ExternalTextDocumentWindow
# - domain.scripture_refs (resolve_reference, calculate_book_line)

# ---- Module-level placeholders (populated at runtime by app.run) ----
# These keep static analysis quiet and preserve runtime assignment from app.py
KJV: tuple | list = ()
Amap: list = []
Amap_rev: dict[int, int] = {}
Ps119: list[int] = []
P119: list = []
book_bounds: list[int] = []
starts_with_italics: list[int] = []
KJB_PCE_LASTLINE: int = 0
EOTNOC: str = ""
Rnew: tuple = ()

Rlow: tuple = ()

Rstp: tuple = ()
Rlsp: tuple = ()
# Search dictionaries and sources
stripped_dict: dict = {}
strpd_low_dict: dict = {}
set_dict: dict = {}
set_lowdict: dict = {}
# Screen metrics
width: int = 0
height: int = 0
half_width: float = 0.0
half_height: float = 0.0
# Colours
linehighlightcolor = None
linetextcolor = None

try:
    from ctypes import windll  # Only exists on Windows.
except ImportError:
    windll = None  # Linux or Mac if here.

CURRENT_VERSION = sh.CURRENT_VERSION

try:
    myappid = f"Abib Bible Reader.{CURRENT_VERSION}"
    if windll:
        from typing import cast
        cast(Any, windll).shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except (AttributeError, OSError) as e:
    # AttributeError: non-Windows (windll is None); OSError: Windows API failure
    print(f"Error setting APP ID: {e}")


def get_next_occurrence() -> int:
    """Count occurrence(s) of w.key and give current_position and w.y values.

    w.occurs is a list of all the current_position values in the search results.
    w.occur is a corresponding list which gives the start w.y and finish w.yend of
    the searched for item in the particular verse.
    w.occurring is the total number of times the search key was found.
    w.verse is the number of the items in the search list.
    len(w.occur[w.verse]) is the number of search results in a particular verse.
    w.finding is the number of items found within the verse.
    """

    assert w is not None
    # 1. Create a local reference with a type hint to satisfy the linter
    win: Any = w

    if win.dlg is not None and win.dlg.checks[0] in (3, 4):
        current_position = win.occurs[win.verse]
        win.finding = 0
        if win.occur[win.verse]:
            win.occur[win.verse].sort(key=lambda _x: _x[0])
            win.y = win.occur[win.verse][0][0]
            win.yend = win.occur[win.verse][0][1]
        win.occurrence += 1
        win.statusBar.showMessage(win.nav.get_status_message(current_position))
        return current_position

    # 2. Use the local reference 'win' for all attribute access and assignments
    current_position = win.occurs[-1]

    if win.verse < len(win.occurs):
        win.finding += 1
        current_position = win.occurs[win.verse]
        if win.finding + 1 <= len(win.occur[win.verse]):
            win.y = win.occur[win.verse][win.finding][0]
            win.yend = win.occur[win.verse][win.finding][1]
            win.occurrence += 1
            win.statusBar.showMessage(win.nav.get_status_message(current_position))
        elif win.verse + 1 < len(win.occurs):
            win.verse += 1
            win.finding = 0
            win.y = win.occur[win.verse][win.finding][0]
            win.yend = win.occur[win.verse][win.finding][1]
            win.occurrence += 1
            current_position = win.occurs[win.verse]
            win.statusBar.showMessage(win.nav.get_status_message(current_position))
    elif win.verse >= len(win.occurs):
        current_position = win.occurs[-1]

    # print(f'len(win.occurs = {len(win.occurs)})')
    # print(f'win.occurring = {win.occurring}')

    return current_position


def findf3_ww_any(x1: int, x2: int, _set: Dict[str, Set], r_list: list, win: 'MainWindow') -> None:
    """Match any word."""

    from abib.services.search_service import findf3_ww_any as _find_any
    _find_any(x1, x2, _set, r_list, win)


def make_offset(ln: int) -> int:
    """Enable highlighting of first verses while showing the titles above."""

    # print('make_offset')
    n: str = KJV[ln][0]
    m: str
    spacesfound: int = 0
    # Determine the start of Psalms dynamically (avoid magic number 13940)
    try:
        psalms_book_idx: int = sh.bibledict['psalms'] - 1  # 0-based book index
        # Use islice to avoid direct indexing, keeping linters/type-checkers happy
        psalms_start_verse_idx: int = next(islice(book_bounds, psalms_book_idx, None))
    except (KeyError, StopIteration, TypeError):
        psalms_start_verse_idx = 13940  # Fallback if data not yet loaded
    # Avoid direct indexing into Amap; use islice with safe fallbacks
    try:
        lx_source = next(islice(Amap, psalms_start_verse_idx, None))
        lx: int = int(lx_source) - 1
    except (StopIteration, TypeError, ValueError):
        # Fallbacks if Amap not ready; use known Psalms start or zero
        try:
            lx: int = int(next(islice(Amap, 13940, None))) - 1
        except (StopIteration, TypeError, ValueError):
            lx = 0
    ec: int = 2
    if n.isalpha() or ln in P119:
        if ln in P119:
            ec = 1
        while spacesfound < 2:
            if spacesfound == ec:
                break
            ln -= 1
            n = KJV[ln][0]
            m = KJV[ln][1]
            if n == ' ':
                spacesfound += 1
            elif n == 'P' and m == 'S' and ln != lx:
                ec = 1

    return ln


def reset_attributes() -> None:
    """Instance attribute resetting routine."""

    # print('reset_attributes')
    
    assert w is not None
    # 1. Create a local reference with a type hint to satisfy the linter
    win: Any = w

    # 2. Use the local reference 'win' for all attribute access and assignments

    # win.gent = None
    win.y = 0
    win.hiLita.lineinc = 0
    win.hiLita.keyinc = 0
    win.occurring = 0
    win.occurrence = 0
    win.key = ' '
    win.keym = ''
    win.message = ''
    if win.dlg is not None:
        win.dlg.checks = [1, 0, 5]  # Is this really necessary?
    win.occurs = []
    win.occur = []


class MainWindow(QMainWindow):
    """MainWindow class."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialise."""
        settings_service = kwargs.pop("settings_service", None)
        super(MainWindow, self).__init__(*args, **kwargs)

        # Load saved settings or initialise default ones.

        # Settings service and window geometry
        self.settings_service: SettingsService = settings_service if settings_service is not None else SettingsService()
        x6, y6, width6, height6 = self.settings_service.get_window_geometry("main_window")
        self.setGeometry(x6, y6, width6, height6)

        # self.feature = None
        self.text_edit_window = None
        self.text_edit = None
        self.history_index = None
        self.command_history = None
        self.about_window = None
        # Use SettingsService-managed settings dict
        self.settings = self.settings_service.settings
        # self.textEditor: None = None
        self.path1: Any = None
        self.display_verse_input: Any = None
        self.comboBox_1: Any = None
        self.comboBox_2: Any = None
        self.comboBox_3: Any = None
        self.hiLita: Any = None
        # Theme toggle button (replaces the old Quit button in the UI)
        self.buttonTheme: Any = None
        self.buttonf3: Any = None
        self.buttonf4: Any = None
        self.buttonf5: Any = None
        self.buttonf6: Any = None
        self.buttonf7: Any = None
        self.buttonf8: Any = None
        self.buttonf9: Any = None
        self.buttonf10: Any = None
        self.buttonf11: Any = None
        self.buttonf12: Any = None
        self.buttonf13: Any = None
        self.buttonf14: Any = None
        self.other_works_combo: QComboBox | None = None
        # Predeclare UI elements that are instantiated in initui to satisfy linters
        self.last_work_btn: QPushButton | None = None
        # Search button for Other Works (instantiated in initui)
        self.search_work_btn: QPushButton | None = None
        # Keyboard shortcut for reopening the last Other Work (predeclared for linters)
        self.shortcut_last_work: QShortcut | None = None
        # Placeholder for the 4th-column vertical button layout added in initui
        self.side_buttons_col: QVBoxLayout | None = None
        self.other_works_map: Dict[str, str] = {}
        self.statusBar: Any = None
        self.okButton: Any = None
        self.dlg: Any = None  # No external window yet.
        # self.textEditor: QPlainTextEdit = QPlainTextEdit()
        self.textEditor: Any = NoZoomPlainTextEdit()
        # Predeclare actions bundle to satisfy linters (assigned in initui)
        self.actions_bundle = None
        self.search_results_dock: Any = None
        
        # Theme manager (extract dark mode logic)
        # Initialise 'ThemeManager' based on persisted settings
        from abib.ui.themes import ThemeManager, ThemeState  # local import (deferred)
        is_dark = self.settings.get("theme", "Light") == "Dark"
        self.theme = ThemeManager(ThemeState(is_dark_mode=is_dark))

        # Initialise the last known Bible position from settings.
        # This is updated at various navigation points.
        self._last_bible_position: int = self.settings_service.get_last_bible_position()
        # Track the last explicitly clicked position in the Bible view (used for context actions)
        self._last_clicked_position: int = 0
        # Track the last general context position used by features like Commentary
        self._last_context_position: int = 0
        # Track whether we've already captured the origin geometry before switching to
        # auxiliary files (HELP/README/COPYING).
        # Initialise here to satisfy linters and avoid defining the instance attribute outside __init__.
        self._aux_origin_saved: bool = False
        # Store the main window geometry before switching to auxiliary files so it can
        # be restored when returning to the Bible view.
        # Initialise to None and avoid defining this attribute outside __init__.
        self._saved_geometry_before_aux: QRect | None = None
        # Flag used to inform Back-handler logic that we've just returned from
        # an auxiliary file (README/HELP/COPYING) to the Bible view; the very
        # next Back press should be ignored to preserve the restored position.
        # Initialise here to avoid defining the attribute outside __init__.
        self._just_restored_from_aux: bool = False

        # Gill commentary window (lazy-created on first use)
        self._gill_win: Any | None = None

        # Navigation core
        self.nav = NavigationCore(self)

        # Services (lazy-initialised on first use to improve startup time)
        self._audio = None
        self._printing = None
        self._reading_plans = None

        # Store a reference to the secondary window to manage its lifecycle
        self.secondary_window = None

        # Create keyboard shortcuts via the centralised helper (local import to defer)
        from abib.ui.actions import setup_shortcuts  # local import (deferred)
        self.shortcuts_bundle = setup_shortcuts(self)

        #Qt.QTimer.singleShot(0, lambda: self.display_devotional("PM", -1))  # Adjusted to yesterday evening's reading.

        self.nwin: List[str] = [
            'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy',
            'Joshua', 'Judges', 'Ruth', 'I Samuel', 'II Samuel', 'I Kings',
            'II Kings', 'I Chronicles', 'II Chronicles', 'Ezra', 'Nehemiah',
            'Esther', 'Job', 'Psalms', 'Proverbs', 'Ecclesiastes',
            'Song of Solomon', 'Isaiah', 'Jeremiah', 'Lamentations',
            'Ezekiel', 'Daniel', 'Hosea', 'Joel', 'Amos', 'Obadiah', 'Jonah',
            'Micah', 'Nahum', 'Habakkuk', 'Zephaniah', 'Haggai', 'Zechariah',
            'Malachi', 'Matthew', 'Mark', 'Luke', 'John', 'Acts', 'Romans',
            'I Corinthians', 'II Corinthians', 'Galatians', 'Ephesians',
            'Philippians', 'Colossians', 'I Thessalonians',
            'II Thessalonians', 'I Timothy', 'II Timothy', 'Titus',
            'Philemon', 'Hebrews', 'James', 'I Peter', 'II Peter', 'I John',
            'II John', 'III John', 'Jude', 'Revelation']

        # Set up for Genesis 1:1
        self.nchapters: List[str] = []
        for _ in range(1, 51):
            self.nchapters.append(str(_))
        self.nverses: List[str] = []
        for _ in range(1, 32):
            self.nverses.append(str(_))

        # noa: int = len(argv)
        self.fontsize: int = 14
        # self.winwidth: int = width6  # Initial width of Abib Bible.
        # self.winheight: int = height6  # Initial height of Abib Bible.
        """
        if noa > 1:
            try:
                self.fontsize = int(argv[1])
                self.winwidth = int(argv[2])
                self.winheight = int(argv[3])
            except ValueError:
                pass
        """

        # Search and runtime state
        self.occurring: int = 0
        self.occurrence: int = 0
        self.occur: list = []
        self.occurs: list = []
        self.count: list = []
        self.key: str = ' '
        self.keym: str = ''
        self.message: str = ''
        self.store: str = ' '
        self.gent: Iterator | None = None
        self.no_f3_yet: int = 0
        self.yend: int = 0
        self.finding: int = 0
        self.verse: int = 0
        self.PCE_text: str | list = []
        self.otherFileFlag: bool = True
        self.y: int = 0

        self.initui()

    @property
    def last_context_position(self) -> int:
        """The last general context position used by features like Commentary."""
        return self._last_context_position

    # --- Lazy services ---
    @property
    def audio(self):
        """Audio service, created on first use."""
        if self._audio is None:
            try:
                from abib.services.audio import AudioService
                self._audio = AudioService()
            except (ImportError, RuntimeError, OSError):
                # Keep this attribute as None on failure and re-raise to surface the issue
                self._audio = None
                raise
        return self._audio

    @property
    def printing(self):
        """Printing service, created on first use."""
        if self._printing is None:
            try:
                from abib.services.printing import PrintingService
                self._printing = PrintingService()
            except (ImportError, RuntimeError):
                self._printing = None
                raise
        return self._printing

    @property
    def reading_plans(self):
        """Spurgeon Morning/Evening reading plans service, created on first use."""
        if self._reading_plans is None:
            try:
                from abib.domain.reading_plans import ReadingPlans
                self._reading_plans = ReadingPlans()
            except (ImportError, FileNotFoundError, KeyError, OSError):
                self._reading_plans = None
                raise
        return self._reading_plans

    def update_other_works_search_button(self, enabled: bool | None = None) -> None:
        """Public proxy for toggling the Other Works search button.

        Provides a non-underscored API for external callers and delegates
        to the internal implementation.
        """
        try:
            self._update_other_works_search_button(enabled)
        except (RuntimeError, AttributeError, TypeError):
            # Match existing guarded usage pattern (best-effort toggle)
            pass

    def initui(self) -> None:
        """Initialise Mainwindow GUI."""
        from abib.ui.highlighter import SyntaxHighlighter  # deferred import

        fixedfont: QFont = QFont("Cascadia Mono", self.fontsize, QFont.Weight.Medium)
        self.textEditor.setFont(fixedfont)
        self.textEditor.setReadOnly(True)
        try:
            self.textEditor.viewport().installEventFilter(self)
        except (RuntimeError, AttributeError):
            pass

        self._setup_input_fields()
        self._setup_comboboxes()
        
        self.hiLita: SyntaxHighlighter = SyntaxHighlighter(self.textEditor.document())

        grid: QGridLayout = QGridLayout()
        grid.setSpacing(2)
        self.setLayout(grid)

        for _col in range(5):
            try:
                grid.setColumnStretch(_col, 1)
            except (RuntimeError, AttributeError, TypeError):
                pass

        grid.addWidget(self.textEditor, 0, 0, 1, 5)
        self.textEditor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._layout_widgets(grid)
        self._setup_other_works(grid)

        container: QWidget = QWidget()
        container.setLayout(grid)
        self.setCentralWidget(container)
        self._setup_search_results_panel()
        self.display_verse_input.setFocus()

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Build menus, toolbars, and actions via the centralised helper
        from abib.ui.actions import setup_menus_and_toolbars  # local import (deferred)
        self.actions_bundle = setup_menus_and_toolbars(self)

        self.secondary_window = None
        self.set_theme(self.settings)

    def _setup_search_results_panel(self) -> None:
        """Create the dockable Search Results panel."""
        from abib.ui.search_results import SearchResultsDock  # deferred import

        self.search_results_dock = SearchResultsDock(self)
        self.search_results_dock.resultActivated.connect(self._on_search_result_activated)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.search_results_dock)
        self.search_results_dock.hide()

    def _update_search_results_panel(self) -> None:
        """Populate the Search Results panel from the current search state."""
        dock = self.search_results_dock
        if dock is None:
            return
        if self.dlg is None or self.occurring == 0 or not self.occurs:
            dock.clear_results()
            dock.hide()
            return

        from abib.ui.search_results import SearchResult, format_reference, highlight_result_text, result_verse_text

        search_text = self.keym or self.key
        search_mode = self.dlg.checks[0]
        case_sensitive = self.dlg.checks[1] == 1
        results: list[SearchResult] = []
        for current_position in self.occurs:
            try:
                verse_text = result_verse_text(current_position, KJV, Amap)
                reference = format_reference(current_position, sh.Info, self.nwin, sh.onechapterbooks)
            except (IndexError, TypeError, ValueError):
                continue
            html_text = highlight_result_text(verse_text, search_text, search_mode, case_sensitive)
            results.append(SearchResult(current_position, reference, verse_text, html_text))

        if results:
            dock.set_results(results, search_text)
            dock.show()
            dock.raise_()
        else:
            dock.clear_results()
            dock.hide()

    def _sync_search_state_for_result(self, current_position: int) -> None:
        """Make the current search state match a clicked result verse."""
        try:
            verse_index = self.occurs.index(current_position)
        except ValueError:
            return

        self.verse = verse_index
        if self.dlg is not None and self.dlg.checks[0] in (3, 4):
            self.finding = 0
            self.occurrence = verse_index + 1
        else:
            self.finding = 0
            self.occurrence = 0
            for prior_spans in self.occur[:verse_index]:
                self.occurrence += len(prior_spans)
            if verse_index < len(self.occur) and self.occur[verse_index]:
                self.occurrence += 1

        if verse_index < len(self.occur) and self.occur[verse_index]:
            self.occur[verse_index].sort(key=lambda _x: _x[0])
            self.y = self.occur[verse_index][0][0]
            self.yend = self.occur[verse_index][0][1]

    def _on_search_result_activated(self, current_position: int) -> None:
        """Jump to the clicked search result."""
        current_line = self.get_line_number()
        if current_line != current_position:
            forward.clear()
            history.back_push(w, current_line)
        self._sync_search_state_for_result(current_position)
        self.display_verse_from_history(current_position)

    def _setup_input_fields(self) -> None:
        self.display_verse_input: QLineEdit = QLineEdit()
        self.display_verse_input.setToolTip("F2, Enter or OK to search for a verse.")
        self.display_verse_input.setGeometry(QRect(50, 50, 200, 25))
        self.display_verse_input.installEventFilter(self)
        self.command_history = []
        self.history_index = -1

    def _setup_comboboxes(self) -> None:
        self.comboBox_1: QComboBox = QComboBox()
        self.comboBox_1.addItems(self.nwin)
        self.comboBox_1.setCurrentIndex(0)
        self.comboBox_1.activated.connect(self.goto_book)

        self.comboBox_2: QComboBox = QComboBox()
        self.comboBox_2.addItems(self.nchapters)
        self.comboBox_2.setCurrentIndex(0)
        self.comboBox_2.activated.connect(self.goto_chapter)

        self.comboBox_3: QComboBox = QComboBox()
        self.comboBox_3.addItems(self.nverses)
        self.comboBox_3.setCurrentIndex(0)
        self.comboBox_3.activated.connect(self.goto_verse)

    def _layout_widgets(self, grid: QGridLayout) -> None:
        # Row 1: Books (cols 0-1), Chapters (col 2), Verses (col 3), Fullscreen (col 4)
        grid.addWidget(self.comboBox_1, 1, 0, 1, 2)
        self.comboBox_1.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.comboBox_2, 1, 2)
        self.comboBox_2.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.comboBox_3, 1, 3)
        self.comboBox_3.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Row 2: Input (cols 0-1), OK (col 2), Theme (col 3), Devotional (col 4)
        grid.addWidget(self.display_verse_input, 2, 0, 1, 2)
        self.display_verse_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.okButton = QPushButton("OK")
        self.okButton.setStyleSheet("QPushButton { text-align: left; }")
        self.okButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.okButton.setToolTip("Enter")
        self.display_verse_input.returnPressed.connect(self.goto_line)
        self.okButton.clicked.connect(self.goto_line)
        grid.addWidget(self.okButton, 2, 2)

        self.buttonTheme = QPushButton("Light/Dark")
        self.buttonTheme.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonTheme.clicked.connect(self.toggle_dark_mode)
        self.buttonTheme.setToolTip("Toggle Light/Dark theme")
        self.buttonTheme.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.buttonTheme, 2, 3)

        # Row 3: Find (col 0), Find Next (col 1), Back (col 2), Forward (col 3), Commentary (col 4)
        self.buttonf3 = QPushButton("Find", self)
        self.buttonf3.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf3.clicked.connect(self.search_current_word)
        self.buttonf3.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonf3.setToolTip("F3")
        grid.addWidget(self.buttonf3, 3, 0)

        self.buttonf4 = QPushButton("Find Next")
        self.buttonf4.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf4.clicked.connect(self.repeat_find_forward)
        self.buttonf4.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonf4.setToolTip("F4")
        grid.addWidget(self.buttonf4, 3, 1)

        self.buttonf5 = QPushButton("Back")
        self.buttonf5.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf5.clicked.connect(self.history_back)
        self.buttonf5.setToolTip("F5")
        self.buttonf5.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.buttonf5, 3, 2)

        self.buttonf6 = QPushButton("Forward")
        self.buttonf6.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf6.clicked.connect(self.history_forward)
        self.buttonf6.setToolTip("F6")
        self.buttonf6.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.buttonf6, 3, 3)

        # Row 4: Book- (col 0), Book+ (col 1), Chapter- (col 2), Chapter+ (col 3)
        self.buttonf7 = QPushButton("Book-")
        self.buttonf7.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf7.clicked.connect(self.earlier_book)
        self.buttonf7.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonf7.setToolTip("F7")
        grid.addWidget(self.buttonf7, 4, 0)

        self.buttonf8 = QPushButton("Book+")
        self.buttonf8.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf8.clicked.connect(self.later_book)
        self.buttonf8.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonf8.setToolTip("F8")
        grid.addWidget(self.buttonf8, 4, 1)

        self.buttonf10 = QPushButton("Chapter-")
        self.buttonf10.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf10.clicked.connect(self.earlier_chapter)
        self.buttonf10.setToolTip("F10")
        self.buttonf10.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.buttonf10, 4, 2)

        self.buttonf11 = QPushButton("Chapter+")
        self.buttonf11.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf11.clicked.connect(self.later_chapter)
        self.buttonf11.setToolTip("F11")
        self.buttonf11.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.buttonf11, 4, 3)

        # Specialized Buttons
        self.buttonf9 = QPushButton("Fullscreen")
        self.buttonf9.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf9.clicked.connect(self.open_commentary_window_shortcut)
        self.buttonf9.setToolTip("F9")
        self.buttonf9.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.buttonf9, 1, 4)

        self.buttonf12 = QPushButton("Devotional")
        self.buttonf12.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf12.clicked.connect(self.show_devotional)
        self.buttonf12.setToolTip("F12")
        self.buttonf12.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.buttonf12, 2, 4)

        self.buttonf13 = QPushButton("Gill's Commentary")
        self.buttonf13.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf13.clicked.connect(self.open_commentary_window)
        self.buttonf13.setToolTip("Open Gill's Commentaries (Ctrl+Shift+C)")
        self.buttonf13.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.buttonf13, 3, 4)

        try:
            shortcut_cmt = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
            shortcut_cmt.activated.connect(self.open_commentary_window)
        except (RuntimeError, TypeError, AttributeError):
            pass

        try:
            self._normalize_control_heights()
        except (RuntimeError, AttributeError, TypeError):
            pass

    def _setup_other_works(self, grid: QGridLayout) -> None:
        self.other_works_combo = QComboBox()
        assert self.other_works_combo is not None
        self.other_works_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.last_work_btn = QPushButton("Last")
        assert self.last_work_btn is not None
        self.last_work_btn.setStyleSheet("QPushButton { text-align: left; }")
        self.last_work_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.last_work_btn.setToolTip("Open the last read book (Ctrl+L)")
        self.last_work_btn.clicked.connect(self._select_last_other_work)  # type: ignore[attr-defined]

        self.search_work_btn = QPushButton("Search")
        assert self.search_work_btn is not None
        self.search_work_btn.setStyleSheet("QPushButton { text-align: left; }")
        self.search_work_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.search_work_btn.setToolTip("Search in the opened Other Works text (Ctrl+F)")
        self.search_work_btn.clicked.connect(self._open_reader_search)  # type: ignore[attr-defined]
        self.search_work_btn.setEnabled(False)

        assert self.other_works_combo is not None
        grid.addWidget(self.other_works_combo, 5, 0, 1, 2)
        assert self.last_work_btn is not None
        grid.addWidget(self.last_work_btn, 5, 2)
        assert self.search_work_btn is not None
        grid.addWidget(self.search_work_btn, 5, 3)

        # Set the sizing policy for all controls
        expanding_fixed = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        controls = [
            'comboBox_1', 'comboBox_2', 'comboBox_3', 'display_verse_input', 'okButton', 'buttonTheme',
            'buttonf3', 'buttonf4', 'buttonf5', 'buttonf6', 'buttonf7', 'buttonf8', 'buttonf9',
            'buttonf10', 'buttonf11', 'buttonf12', 'buttonf13', 'other_works_combo', 'last_work_btn', 'search_work_btn'
        ]
        for name in controls:
            wdg = getattr(self, name, None)
            if wdg:
                control: Any = wdg
                control.setSizePolicy(expanding_fixed)

        # Populate
        other_works_dir = Path(sh.str_cwd) / "Other Works"
        if other_works_dir.exists():
            files = sorted([p for p in other_works_dir.glob("*.txt") if p.is_file()])
            self.other_works_map = {p.stem: str(p) for p in files}
            self._refresh_other_works_combo()

            last_work = self.settings.get("last_other_work") if isinstance(self.settings, dict) else None
            if last_work and last_work in self.other_works_map:
                self.other_works_combo.setCurrentText(str(last_work))
            elif "Pilgrims-Progress" in self.other_works_map:
                self.other_works_combo.setCurrentText("Pilgrims-Progress")

        assert self.other_works_combo is not None
        self.other_works_combo.currentTextChanged.connect(self._open_other_work)  # type: ignore[attr-defined]
        def _on_activated(index: int) -> None:
            if self.other_works_combo:
                self._open_other_work(self.other_works_combo.itemText(index))

        self.other_works_combo.activated.connect(_on_activated)  # type: ignore[attr-defined]

        try:
            self.shortcut_last_work = QShortcut(QKeySequence("Ctrl+L"), self)
            assert self.shortcut_last_work is not None
            self.shortcut_last_work.setContext(Qt.ShortcutContext.WindowShortcut)
            self.shortcut_last_work.activated.connect(self._select_last_other_work)  # type: ignore[attr-defined]
        except (RuntimeError, AttributeError, TypeError):
            pass

        # self.update_title()
        self.show()

        # Placeholder for the AboutWindow (lazy-loaded)
        self.about_window = None

        self.apply_font_size()  # Set an initial font size from settings

    def _refresh_other_works_combo(self) -> None:
        """Repopulate the Other Works combo according to settings['show_work'] filter."""
        if not self.other_works_combo:
            return
        self.other_works_combo.blockSignals(True)
        try:
            self.other_works_combo.clear()
            allowed: List[str] = []
            try:
                show_map = dict(self.settings.get("show_work") or {})
            except (TypeError, ValueError, AttributeError):
                # If settings are not a mapping, or the value cannot be cast to dict,
                # fall back to an empty mapping without swallowing unrelated errors.
                show_map = {}
            for stem in sorted(self.other_works_map.keys()):
                if str(show_map.get(stem, "false")).lower() == "true":
                    allowed.append(stem)
            if allowed:
                self.other_works_combo.addItems(allowed)
        finally:
            self.other_works_combo.blockSignals(False)

    def _build_show_works_menu(self, settings_menu) -> None:
        """Populate the given Settings submenu with a tickable list of Other Works.

        Toggling an item updates settings['show_work'] and refreshes the combo box.
        """
        # Clear any prior dynamic actions after the first static action (Open Settings...)
        # We'll rebuild from scratch to reflect file system and settings changes.
        # Remove all actions after the first if the first is our 'Open Settings...' action
        actions = settings_menu.actions()
        # Keep the first (Open Settings...) if present, clear the rest
        for act in actions[1:]:
            settings_menu.removeAction(act)

        # Separator between Open Settings and the list
        settings_menu.addSeparator()

        # Convenience: Select all / Deselect all controls that keep the menu open
        # Use QWidgetAction with a QPushButton so clicking doesn't close the menu,
        # allowing multiple changes in one go.
        try:
            from PySide6.QtWidgets import QWidgetAction, QPushButton

            # Ensure we have a live map of checkboxes to update during bulk ops
            if not hasattr(self, "_works_menu_checkboxes") or not isinstance(getattr(self, "_works_menu_checkboxes"), dict):
                self._works_menu_checkboxes = {}

            def _set_all_works(visible: bool) -> None:
                current_map = dict(self.settings.get("show_work") or {})
                val = "true" if visible else "false"
                # Use a distinct local name to avoid shadowing outer-scope variables
                for work_stem in self.other_works_map.keys():
                    current_map[work_stem] = val
                self.settings["show_work"] = current_map
                # Update the checkbox widgets in-place without closing the menu
                try:
                    for work_stem, checkbox in getattr(self, "_works_menu_checkboxes", {}).items():
                        # Block signals so we don't double-save while syncing UI
                        bs = checkbox.blockSignals(True)
                        try:
                            checkbox.setChecked(visible)
                        finally:
                            checkbox.blockSignals(bs)
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    pass
                # Persist and refresh combo
                if getattr(self, "settings_service", None):
                    self.settings_service.save(self.settings)
                self._refresh_other_works_combo()

            # Build non-closing buttons inside the menu
            select_all_btn = QPushButton("Select all Other Works", settings_menu)
            select_all_btn.clicked.connect(lambda _=False: _set_all_works(True))
            select_all_wa = QWidgetAction(settings_menu)
            select_all_wa.setDefaultWidget(select_all_btn)
            settings_menu.addAction(select_all_wa)

            deselect_all_btn = QPushButton("Deselect all Other Works", settings_menu)
            deselect_all_btn.clicked.connect(lambda _=False: _set_all_works(False))
            deselect_all_wa = QWidgetAction(settings_menu)
            deselect_all_wa.setDefaultWidget(deselect_all_btn)
            settings_menu.addAction(deselect_all_wa)

            # Separator between bulk actions and individual list
            settings_menu.addSeparator()
        except (ImportError, AttributeError, RuntimeError, TypeError, ValueError):
            # If widget actions cannot be created, silently skip bulk controls
            pass

        show_map = dict(self.settings.get("show_work") or {})
        # Ensure keys exist for current files
        for stem in sorted(self.other_works_map.keys()):
            if stem not in show_map:
                show_map[stem] = "false"

        # Build checkable items that do NOT close the menu on toggle
        try:
            from PySide6.QtWidgets import QWidgetAction, QCheckBox

            # Reset and rebuild the checkbox map
            self._works_menu_checkboxes = {}

            for stem in sorted(self.other_works_map.keys()):
                checked = str(show_map.get(stem, "false")).lower() == "true"
                cb = QCheckBox(stem, settings_menu)
                cb.setChecked(checked)

                def _make_toggle_cb(name: str):
                    def _toggle(_checked: bool) -> None:
                        show_map_local = dict(self.settings.get("show_work") or {})
                        show_map_local[name] = "true" if _checked else "false"
                        self.settings["show_work"] = show_map_local
                        if getattr(self, "settings_service", None):
                            self.settings_service.save(self.settings)
                        self._refresh_other_works_combo()
                    return _toggle

                cb.toggled.connect(_make_toggle_cb(stem))
                wa = QWidgetAction(settings_menu)
                wa.setDefaultWidget(cb)
                settings_menu.addAction(wa)
                self._works_menu_checkboxes[stem] = cb
        except (ImportError, AttributeError, RuntimeError, TypeError, ValueError):
            # Fallback: if QWidgetAction/QCheckBox not available, use plain QActions
            # (The menu will close on toggle)
            from PySide6.QtGui import QAction
            for stem in sorted(self.other_works_map.keys()):
                checked = str(show_map.get(stem, "false")).lower() == "true"
                act = QAction(stem, self)
                act.setCheckable(True)
                act.setChecked(checked)

                def _make_toggler(name: str):
                    def _toggle(_checked: bool):
                        show_map_local = dict(self.settings.get("show_work") or {})
                        show_map_local[name] = "true" if _checked else "false"
                        self.settings["show_work"] = show_map_local
                        if getattr(self, "settings_service", None):
                            self.settings_service.save(self.settings)
                        self._refresh_other_works_combo()
                    return _toggle

                act.toggled.connect(_make_toggler(stem))
                settings_menu.addAction(act)

    # Public wrapper used by ui.actions to avoid accessing a protected member from outside
    def build_show_works_menu(self, settings_menu) -> None:
        """Public entry point to build the tickable Other Works list under Settings.

        Delegates to the internal implementation. Exists to satisfy linters that
        warn about external access to protected members (methods prefixed with underscore).
        """
        try:
            self._build_show_works_menu(settings_menu)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            # Fail-safe: ignore errors so the rest of the menu remains functional
            pass

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        """Custom event filter to handle key events on QLineEdit."""
        if source is None:
            return super().eventFilter(source, event)  # type: ignore[arg-type]

        if source == self.display_verse_input and event.type() == QEvent.Type.KeyPress:
            if isinstance(event, QKeyEvent):
                if event.key() == Qt.Key.Key_Up:  # Handle Up Arrow
                    if self.command_history and self.history_index > 0:
                        self.history_index -= 1
                        self.display_verse_input.setText(self.command_history[self.history_index])
                    elif self.command_history and self.history_index == -1:
                        self.history_index = len(self.command_history) - 1
                        self.display_verse_input.setText(self.command_history[self.history_index])
                    return True

                elif event.key() == Qt.Key.Key_Down:  # Handle Down Arrow
                    if self.command_history and self.history_index < len(self.command_history) - 1:
                        self.history_index += 1
                        self.display_verse_input.setText(self.command_history[self.history_index])
                    elif self.history_index == len(self.command_history) - 1:
                        self.history_index += 1
                        self.display_verse_input.clear()  # Clear input when navigating below the last command
                    return True

                elif event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:  # Handle Enter
                    current_text = self.display_verse_input.text().strip()
                    if current_text:
                        self.command_history.append(current_text)  # Add current text to history
                        self.history_index = -1  # Reset history index
                        # print(f"Executed: {current_text}") # Simulate command execution
                        # print ("Return key intercepted in eventFilter") # Debugging
                        self.goto_line()  # Trigger goto_line manually
                        self.display_verse_input.clear()  # Clear the input field after submission
                    return True

        # Handle clicks inside the Bible text editor: when the user clicks
        # on any line, update the status bar to reflect the clicked verse.
        # Do not force any special scrolling; keep behaviour simple.
        # Use the module-level QMouseEvent imported at the top of this file.

        if source == getattr(self, 'textEditor', None) and source is not None:
            # If the source is the editor itself (rare), prefer viewport below
            pass
        elif source == getattr(self, 'textEditor', None) and hasattr(source, 'viewport'):
            # Defensive placeholder; real handling is for viewport object
            pass
        elif (hasattr(self.textEditor, 'viewport') and 
              source == self.textEditor.viewport()):
            # Only process mouse button presses
            if event.type() == QEvent.Type.MouseButtonPress:
                try:
                    if isinstance(event, QMouseEvent):
                        if event.button() == Qt.MouseButton.LeftButton:
                            # Map click position to document block/line
                            try:
                                pos = event.position() if hasattr(event, 'position') else event.pos()
                            except (RuntimeError, AttributeError):
                                pos = None
                            if pos is None:
                                return super().eventFilter(source, event)  # type: ignore[arg-type]
                            try:
                                # event.position() (PySide6 6.11+) returns QPointF; 
                                # cursorForPosition requires QPoint.
                                point = pos.toPoint() if hasattr(pos, 'toPoint') else pos
                                assert isinstance(point, QPoint)
                                cursor = self.textEditor.cursorForPosition(point)
                                block = cursor.block()
                                line_no = int(block.blockNumber())
                            except (RuntimeError, AttributeError, TypeError, ValueError, AssertionError):
                                return super().eventFilter(source, event)  # type: ignore[arg-type]

                            # Resolve the clicked line to the verse index (current_position)
                            # Prefer the nearest verse start at or before the clicked line.
                            current_position = None
                            try:
                                if line_no in Amap:
                                    current_position = Amap_rev[line_no]
                                else:
                                    # Search backward first for up to 12 lines, then forward
                                    found = False
                                    for delta in range(1, 13):
                                        ln_back = line_no - delta
                                        if ln_back in Amap:
                                            current_position = Amap_rev[ln_back]
                                            found = True
                                            break
                                        ln_fwd = line_no + delta
                                        if ln_fwd in Amap:
                                            current_position = Amap_rev[ln_fwd]
                                            found = True
                                            break
                                    if not found:
                                        # Fallback: use existing top-of-screen detection
                                        current_position = self.get_line_number()
                            except (RuntimeError, AttributeError, TypeError, ValueError):
                                current_position = self.get_line_number()

                            # Do not force-scroll the view; keep the current scroll position.

                            # Update the status bar to reflect the clicked verse
                            try:
                                if isinstance(current_position, int):
                                    self.ref_to_statusbar(current_position)
                                    # Persist the last Bible position so any reload restores here
                                    try:
                                        self._last_bible_position = int(current_position)
                                        # Remember the last explicitly clicked position for context-sensitive actions
                                        self._last_clicked_position = int(current_position)
                                        # Also update the general last-context position used by Commentary
                                        self._last_context_position = int(current_position)
                                    except (TypeError, ValueError):
                                        pass
                            except (RuntimeError, AttributeError, TypeError, ValueError):
                                pass

                            # Do not consume the event so that the default text selection behaviour
                            # (click, drag to select, double-click to select a word)
                            # continues to work in the Bible view.
                            return False
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    # Fall through to default processing on any unexpected error
                    pass

        # Pass the event to the parent class
        return super().eventFilter(source, event)  # type: ignore[arg-type]

    def moveEvent(self, event):
        try:
            return super().moveEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def resizeEvent(self, event):
        try:
            return super().resizeEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def closeEvent(self, event: Any):
        """Handle window close event - save geometry and close child windows"""
        # Save main window geometry and state
        geometry = self.geometry()
        assert self.settings_service is not None
        self.settings_service.save_window_geometry(
            "main_window",
            geometry.x(), geometry.y(), geometry.width(), geometry.height()
        )

        # Persist last Bible position
        try:
            self.settings_service.update_last_bible_position(int(self._last_bible_position))
        except (AttributeError, TypeError, ValueError):
            pass
        
        # Explicitly close secondary windows to ensure they trigger their own closeEvent/save logic
        try:
            gill: Any = getattr(self, "_gill_win", None)
            if gill is not None:
                gill.close()
        except (RuntimeError, AttributeError):
            pass
            
        try:
            reader: Any = getattr(self, "text_edit_window", None)
            if reader is not None:
                reader.close()
        except (RuntimeError, AttributeError):
            pass
            
        try:
            secondary: Any = getattr(self, "secondary_window", None)
            if secondary is not None:
                secondary.close()
        except (RuntimeError, AttributeError):
            pass

        try:
            about: Any = getattr(self, "about_window", None)
            if about is not None:
                about.close()
        except (RuntimeError, AttributeError):
            pass

        try:
            find_dlg: Any = getattr(self, "dlg", None)
            if find_dlg is not None:
                find_dlg.close()
        except (RuntimeError, AttributeError):
            pass

        event.accept()

    def increase_font_size(self):
        current_size = self.settings_service.get_bible_font_size()
        new_size = min(current_size + 2, 72)  # Max size of 72
        self.settings_service.update_bible_font_size(new_size)
        # print(f"DEBUG: Increase Bible fontsize to: {new_size}")
        self.apply_font_size()

    def decrease_font_size(self):
        current_size = self.settings_service.get_bible_font_size()
        new_size = max(current_size - 2, 8)  # Min size of 8
        self.settings_service.update_bible_font_size(new_size)
        # print(f"DEBUG: Decrease Bible fontsize to: {new_size}")
        self.apply_font_size()

    def apply_font_size(self):
        self.fontsize = self.settings_service.get_bible_font_size()
        # Create a QFont object and apply it to the QPlainTextEdit
        font = QFont("Cascadia Mono", self.fontsize)
        self.textEditor.setFont(font)

        # Propagate to other windows if the unified font size is enabled
        if bool(self.settings.get("unified_font_size", False)):
            # 1. Reader Window
            reader = getattr(self, "text_edit_window", None)
            if reader:
                try:
                    r: Any = reader
                    # Avoid recursive calls: only apply if different
                    if int(getattr(r, "reader_fontsize", 0)) != self.fontsize:
                        r.apply_font_size(self.fontsize)
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    pass

            # 2. Gill Commentary Window
            gill = getattr(self, "_gill_win", None)
            if gill:
                try:
                    g: Any = gill
                    # Check the current font size from the viewer
                    current_gill_font = g.viewer.font()
                    if current_gill_font.pointSize() != self.fontsize:
                        g.apply_font_size(self.fontsize)
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    pass

            # 3. Secondary (Devotional) Window
            secondary = getattr(self, "secondary_window", None)
            if secondary:
                try:
                    s: Any = secondary
                    if int(getattr(s, "fontsize", 0)) != self.fontsize:
                        s.fontsize = self.fontsize
                        s.update_font()
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    pass

    def feature(self) -> None:
        """Open the Other Works reader window for the currently selected item."""
        current_stem = None
        combo = getattr(self, "other_works_combo", None)
        if isinstance(combo, QComboBox):
            try:
                current_stem = combo.currentText()
            except RuntimeError:
                # The widget may have been deleted/disposed by Qt
                current_stem = None
        if current_stem and hasattr(self, "other_works_map"):
            self._open_other_work(current_stem)
        else:
            # Fallback: open default Pilgrims Progress if available
            other_works_dir = Path(sh.str_cwd) / "Other Works"
            pp = other_works_dir / "Pilgrims-Progress.txt"
            path = str(pp) if pp.exists() else None
            if path:
                self._open_text_file_in_window(path)

    @staticmethod
    def open_github_releases() -> None:
        """Open the GitHub releases page in the default web browser."""
        webbrowser.open("https://github.com/Abib-ops/Abib/releases")

    def open_text_file_in_window(self, path: str) -> None:
        """Public wrapper to open or update the external text reader window."""
        self._open_text_file_in_window(path)

    def _open_text_file_in_window(self, path: str) -> None:
        """Open the ExternalTextDocumentWindow with the given file path 
           or update existing, then focus it."""
        # Normalise the incoming path for consistent comparisons
        try:
            req_path = str(Path(path).resolve())
        except (OSError, RuntimeError, ValueError, TypeError):
            req_path = str(path)

        reader = getattr(self, "text_edit_window", None)
        if reader is None:
            # Defer import to reduce startup cost
            from abib.ui.text_window import TextDocumentWindow as ExternalTextDocumentWindow
            new_reader = ExternalTextDocumentWindow(
                initial_file_path=req_path,
                settings_path=getattr(self, "user_settings_path", None),
                settings_service=self.settings_service
            )
            self.text_edit_window = new_reader
            win: Any = new_reader
            # When the user clicks a scripture reference in the reader, navigate here
            try:
                win.referenceActivated.connect(self._on_reader_reference_activated)
                setattr(win, "_connected_to_main", True)
            except (AttributeError, RuntimeError, TypeError):
                pass
            # Apply the current theme to the new window and its editor
            try:
                win.apply_theme(self.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            # Apply palette to the window; ThemeManager handles internal safety
            self.theme.apply_widget(win)
            win_to_show = win
        else:
            win: Any = reader
            # If the reader is currently loading the same stem/path,
            # then prevent it re-issuing the load.
            try:
                is_loading_file = bool(getattr(win, "_is_loading_file", False))
                current_stem = getattr(win, "current_file_stem", None)
                req_stem = Path(req_path).stem
                if is_loading_file and current_stem and str(current_stem) == str(req_stem):
                    # Already loading this work; just bring it to the front and apply the theme
                    try:
                        win.apply_theme(self.theme.state.is_dark_mode)
                    except (RuntimeError, AttributeError):
                        pass
                    self.theme.apply_widget(win)
                    win.show()
                    win.raise_()
                    win.activateWindow()
                    return
            except (AttributeError, RuntimeError, TypeError, ValueError, OSError):
                pass
            # Guard: if the requested work is already loaded, avoid reloading
            try:
                current_stem = getattr(win, "current_file_stem", None)
            except (AttributeError, RuntimeError, TypeError):
                current_stem = None
            req_stem = Path(req_path).stem
            if current_stem and str(current_stem) == str(req_stem):
                # Already showing this work; just refresh the theme/palette and focus
                try:
                    win.apply_theme(self.theme.state.is_dark_mode)
                except (RuntimeError, AttributeError):
                    pass
                self.theme.apply_widget(win)
            else:
                win.load_text_file(req_path)
            # Ensure the signal is connected even if the window already existed
            try:
                if not getattr(win, "_connected_to_main", False):
                    win.referenceActivated.connect(self._on_reader_reference_activated)
                    setattr(win, "_connected_to_main", True)
            except (AttributeError, RuntimeError, TypeError):
                pass
            try:
                win.apply_theme(self.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            self.theme.apply_widget(win)
            win_to_show = win
        win_to_show.show()
        win_to_show.raise_()
        win_to_show.activateWindow()
        # Connect visibility signal to toggle the Search button state and enable now
        try:
            if not getattr(win_to_show, "_display_signal_connected", False):
                win_to_show.displayedChanged.connect(self._on_reader_displayed_changed)
                setattr(win_to_show, "_display_signal_connected", True)
        except (AttributeError, RuntimeError, TypeError):
            pass
        self._update_other_works_search_button(True)

    def _on_reader_reference_activated(self, ref: str) -> None:
        """Navigate the Bible main window to the clicked reference from the reader window."""
        try:
            # Use existing navigation, which handles all parsing and UI updates
            self.goto_line(ref)
            # Bring the main window to the front so the user sees the context
            try:
                self.show()
                self.raise_()
                self.activateWindow()
            except (RuntimeError, AttributeError):
                pass
        except (ValueError, TypeError, KeyError, IndexError, RuntimeError):
            # Be resilient: if parsing fails, ignore silently
            pass

    def _on_reader_displayed_changed(self, visible: bool) -> None:
        """Enable/disable the Search button based on reader visibility."""
        self._update_other_works_search_button(bool(visible))

    def _update_other_works_search_button(self, enabled: bool | None = None) -> None:
        """Set the Search button enabled state. If enabled is None, inferred from reader visibility."""
        btn = getattr(self, "search_work_btn", None)
        if btn is None:
            return
        try:
            b: Any = btn
            if enabled is None:
                reader = getattr(self, "text_edit_window", None)
                if reader is not None:
                    win: Any = reader
                    state = bool(getattr(win, "isVisible", None) and win.isVisible())
                else:
                    state = False
            else:
                state = bool(enabled)
            b.setEnabled(state)
        except (RuntimeError, AttributeError, TypeError):
            pass

    def _open_reader_search(self) -> None:
        """Open or focus the Search dialog for the Other Works reader window."""
        reader = getattr(self, "text_edit_window", None)
        if not reader:
            # No reader open; keep the button disabled just in case
            self._update_other_works_search_button(False)
            return
        try:
            win: Any = reader
            win.show_find_dialog()
            self._update_other_works_search_button(True)
        except (AttributeError, RuntimeError, TypeError):
            pass

    def _open_other_work(self, stem: str) -> None:
        """Open or update the TextDocumentWindow for the selected Other Works item."""
        if not stem or not hasattr(self, "other_works_map"):
            return
        path = self.other_works_map.get(stem)
        if not path:
            return
        # If the reader already has this work loaded, avoid reloading to prevent loops
        try:
            reader = getattr(self, "text_edit_window", None)
            if reader is not None and getattr(reader, "current_file_stem", None) == stem:
                # Use a local reference with a type hint to satisfy the linter
                win: Any = reader
                # Just bring the window to the front and ensure the theme is applied
                try:
                    win.apply_theme(self.theme.state.is_dark_mode)
                except (RuntimeError, AttributeError):
                    pass
                self.theme.apply_widget(win)
                win.show()
                win.raise_()
                win.activateWindow()
                # Persist last selected work as usual
                try:
                    if isinstance(self.settings, dict):
                        self.settings["last_other_work"] = stem
                        if getattr(self, "settings_service", None):
                            self.settings_service.save(self.settings)
                except (OSError, TypeError, ValueError, RuntimeError):
                    pass
                return
        except (AttributeError, RuntimeError, TypeError, ValueError, OSError):
            # If any attribute access fails, fall back to the normal open path
            pass
        # Open/update the reader window
        self._open_text_file_in_window(path)
        # Persist last selected work in settings so the combo defaults next launch
        try:
            if isinstance(self.settings, dict):
                self.settings["last_other_work"] = stem
                # Save via settings service if available
                if getattr(self, "settings_service", None):
                    self.settings_service.save(self.settings)
        except (OSError, TypeError, ValueError, RuntimeError):
            # Be tolerant: failure to persist should not break the opening
            pass

    def _select_last_other_work(self) -> None:
        """Re-select and open the last read Other Works item in the combo box.

        Implements Option A (button) and is also used by Option B (Ctrl+L shortcut).
        """
        try:
            if not hasattr(self, "other_works_map"):
                return
            last_work = self.settings.get("last_other_work") if isinstance(self.settings, dict) else None
            if not last_work:
                return
            if last_work not in self.other_works_map:
                return

            # Find the index in the combo for robustness
            assert self.other_works_combo is not None
            idx = self.other_works_combo.findText(str(last_work))
            if idx < 0:
                return

            # If it's already selected, Qt won't emit signals; open explicitly
            if self.other_works_combo.currentIndex() == idx:
                self._open_other_work(str(last_work))
                return

            # Otherwise, switch selection without emitting signals twice, then open explicitly
            try:
                self.other_works_combo.blockSignals(True)
                self.other_works_combo.setCurrentIndex(idx)
            finally:
                try:
                    self.other_works_combo.blockSignals(False)
                except (RuntimeError, AttributeError, TypeError):
                    pass
            # Ensure the reader opens even if a platform doesn't emit currentTextChanged
            self._open_other_work(str(last_work))
        except (RuntimeError, AttributeError, KeyError, TypeError, ValueError):
            # Be silent on any unexpected issue
            pass

    def show_about_dialog(self):
        """Show the 'About' window when Help -> About is clicked."""

        # Initialize AboutWindow if it hasn't been created
        if self.about_window is None:
            from abib.ui.windows import AboutWindow as ExtAboutWindow  # deferred import
            self.about_window = ExtAboutWindow(f"Abib {CURRENT_VERSION}", settings_service=self.settings_service)
        # Apply the theme palette to the About window (apply_widget is internally safe)
        self.theme.apply_widget(self.about_window)
        self.about_window.show()
        self.about_window.raise_()  # Bring the "About" window to the front
        self.about_window.activateWindow()  # Give the "About" window focus

    def helper(self) -> None:
        """Open the Help section in a separate window."""
        help_path = str(Path(sh.current_directory / 'HELP.txt'))
        self._open_text_file_in_window(help_path)

    def copyright(self) -> None:
        """Open the Licence in a separate window."""
        copying_path = str(Path(sh.current_directory / 'COPYING'))
        self._open_text_file_in_window(copying_path)

    def readme(self) -> None:
        """Open the Readme file in a separate window."""
        readme_path = str(Path(sh.current_directory / 'README.txt'))
        self._open_text_file_in_window(readme_path)

    def reload(self) -> None:
        """Reload KJB_PCE.txt"""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        if win.otherFileFlag:
            # print('reloaded')
            win.otherFileFlag = False
            self.file_open(str(Path(sh.current_directory / 'KJB_PCE.txt')))
            # Do NOT re-centre or reset attributes here.
            # When returning from README/COPYING/HELP via Back, preserve window
            # geometry and Bible state so history restoration works correctly.
            try:
                if getattr(self, "_saved_geometry_before_aux", None):
                    assert self._saved_geometry_before_aux is not None
                    self.setGeometry(self._saved_geometry_before_aux)
                    self._saved_geometry_before_aux = None
                # Clear aux origin flag now that we restored the Bible
                if getattr(self, "_aux_origin_saved", False):
                    self._aux_origin_saved = False
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass
            # Signal to Back handler that we just restored the Bible view, 
            # so the very next Back press should be ignored to preserve
            # the restored verse position.
            try:
                self._just_restored_from_aux = True
            except (AttributeError, RuntimeError):
                pass

    # ENTRY POINT FOR F3 FIND.
    # Create a slot for launching the find dialog box.

    def onFindBtnClicked(self) -> None:
        """Launch the Find dialog box."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.

        if self.dlg is None:
            from abib.ui.find_dialog import FindDialog  # deferred import
            self.dlg = FindDialog(self, settings_service=self.settings_service)
            # Apply the theme palette to the Find dialog (apply_widget is internally safe)
            self.theme.apply_widget(self.dlg)
            self.dlg.exec()
        else:
            self.show_find_window()

    def show_find_window(self) -> None:
        """Show the Find window."""

        if self.dlg is None:
            from abib.ui.find_dialog import FindDialog  # deferred import
            self.dlg = FindDialog(self, settings_service=self.settings_service)
            # Apply the theme palette to the Find dialog (apply_widget is internally safe)
            self.theme.apply_widget(self.dlg)
            self.dlg.show()
        else:
            # Ensure the theme is applied before showing
            self.theme.apply_widget(self.dlg)
            self.dlg.show()

    def close_find_window(self) -> None:
        """Close the Find window."""

        self.dlg.hide()

    def toggle_fullscreen(self) -> None:
        """Fullscreen."""

        if self.windowState() & Qt.WindowState.WindowFullScreen:
            self.showNormal()
        else:
            self.showFullScreen()

    # ENTRY POINT FOR F4 FIND NEXT.
    def find_next(self) -> None:
        """Spaghetti Junction."""

        self.display_verse_input.setFocus()

        if self.dlg.checks[0] != 1 or self.dlg.checks[2] == 6:
            self.find_f4_alt()
        elif self.dlg.checks[0] == 1:
            if self.gent is None:
                self.search_current_word()
            else:
                self.find_f4()

    def make_key_whole(self, _key: str, _dict: Dict, _set: Dict[str, Set]) -> tuple[int, str]:
        """Make _key conform to Match whole word only.

        Return the number of whole words in the _key variable.
        """

        numstart, _key = fcs.split_strip(_key)
        words: List = _key.split()
        words = [item for item in words if item in _dict]
        _key = ''
        for i in words:
            _key += i + ' '
        _key = _key[:-1]  # Remove the last space character.
        num = len(words)
        if num != numstart and (self.dlg.checks[0] == 2 or self.dlg.checks[1] == 3):
            # A word or part of a word was removed.
            num = 0

        return num, _key

    def prepare_key_for_find(self) -> None:
        """Adjust 'key' for searching in Rnew, which has no Unicode italics.

        It also has a different apostrophe and uses æ and Æ.
        """

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        p = "():,’;-?[].!<>"
        ae: List[str] = ['aea', 'aeu', 'aes', 'aet', 'aene', 'aeno', 'AEno', 'AEne', 'Aeno', 'Aene']
        ae_unicode: List[str] = ['æa', 'æu', 'æs', 'æt', 'æne', 'æno', 'Æno', 'Æne', 'Æno', 'Æne']
        count = -1
        for _ in ae:
            count += 1
            if _ in win.key:
                index = win.key.find(_)
                j = len(_)
                j += index
                w.key = win.key[:index] + ae_unicode[count] + win.key[j:]
                break
        line = ''
        for _ in win.key:
            if _ in p:
                if _ == '-' and self.dlg.checks[0] != 1:
                    continue
                else:
                    line += _
                    continue
            ch = ord(_)
            if ch in range(119860, 119885):
                ch -= 119795
                line += chr(ch)
            elif ch in range(119886, 119911):
                ch -= 119789
                line += chr(ch)
            elif ch == 119997:
                ch = 104
                line += chr(ch)
            elif ch == 39:
                ch = 8217
                line += chr(ch)
            else:
                line += _
        w.key = line

    def findf3(self, x_start: int, x_end: int) -> None:
        """Find function."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        #self.display_verse_input.setFocus()
        current_position = self.get_line_number()
        savedx = current_position
        error_flag = False

        self.prepare_key_for_find()
        try:
            x1 = int(next(islice(book_bounds, x_start, None)))
        except (StopIteration, TypeError, ValueError):
            x1 = 0
        try:
            x2 = int(next(islice(book_bounds, x_end + 1, None))) - 1
        except (StopIteration, TypeError, ValueError):
            x2 = sh.LAST_VERSE_IN_BIBLE
        current_position = x1

        win.no_f3_yet = 1

        win.keym = win.key
        if win.key == '' or win.key == ' ':
            win.y = -1
            win.no_f3_yet = 0
            win.occurring = 0
            self.statusBar.clearMessage()
            self.statusBar.repaint()
        else:
            self.statusBar.showMessage('Finding...')
            self.statusBar.repaint()
            keylow = win.key.lower()
            win.y = 0
            win.occurring = 0

            if self.dlg.checks[2] == 6:
                self.iterate_regex(Rnew, x1, x2)
                if win.occurring != 0:
                    w.y = win.occur[0][0][0]
                    win.occurrence = 0
                    win.verse = 0
                    win.finding = -1
                    current_position = get_next_occurrence()
                    if win.message:
                        self.statusBar.showMessage(win.message)
                    self.statusBar.repaint()
            else:
                tv = self.dlg.checks[0] == 1   # Raw
                if not tv:
                    current_position = self.findf3_ww(x1, x2)
                elif tv:
                    # Raw.
                    current_position = self.findf3_raw(current_position, x1, x2, keylow)

        if win.occurring == 0:
            current_position = savedx
            self.on_error('Not found...', 2000, True)
            error_flag = True

        if win.key in ('q', 'Q'):
            self.display_verse_input.clear()
            exit()
        if not error_flag:
            self.goto_line_find(current_position)
        self._update_search_results_panel()

    def iterate_regex(self, r: tuple, x1: int, x2: int) -> None:
        """Iterate over R and find all the occurrences of key(s) in liszt."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        win.occurring = 0
        win.occur = []
        win.occurs = []
        if self.dlg.checks[1] == 1:             # Match case
            pattern = rf"{win.key}"
        else:
            assert self.dlg.checks[1] == 0      # Ignore the case
            pattern = rf"(?i){win.key}"
        # Iterate inclusively within the provided limits [x1, x2]
        for _ in range(x1, x2 + 1):
            coordinate = []
            try:
                for m in re.finditer(pattern, r[_]):
                    win.occurring += 1
                    coordinate.append((m.start(), m.end()))
            except re.error:
                msg = 'Regular Expression Error.'
                self.on_error(msg, 2000, True)
                w.occurring = 0
                break
            if coordinate:
                win.occur.append(coordinate)
                win.occurs.append(_)

    def findf3_raw(self, current_position: int, x1: int, x2: int, keylow: str) -> int:
        """Find Raw."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        win.occurs = []
        win.occur = []

        # Count occurrences inclusively within the provided limits [x1, x2]
        if self.dlg.checks[1] == 1:  # Match case
            source = Rnew
            search_key = win.key
        elif self.dlg.checks[1] == 0:  # Lower case
            source = Rlow
            search_key = keylow
        else:
            source = Rnew
            search_key = win.key

        for i in range(x1, x2 + 1):
            coordinate = []
            start_search = 0
            while True:
                y = source[i].find(search_key, start_search)
                if y == -1:
                    break
                coordinate.append((y, y + len(search_key)))
                win.occurring += 1
                start_search = y + 1
            if coordinate:
                win.occur.append(coordinate)
                win.occurs.append(i)

        if win.occurring != 0:
            win.occurrence = 0
            current_position = self.occurrent(x1, x2)
            if win.message:
                self.statusBar.showMessage(win.message)
            self.statusBar.repaint()

        return current_position

    def assign_values(self) -> Any:
        """Can't remember what this does."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        # print('assign_values')
        numwords: int
        win.verse = 0
        if self.dlg.checks[1] == 1:             # Match case.
            dic: Any = stripped_dict
            key: str = win.key
            # set_ and set_dict are dictionaries of words in the KJV Bible.
            # For each word, there is a set of verse/line numbers where the word occurs.
            set_: Dict[Any, Set] = set_dict
            r_list: List | tuple = Rstp
        else:
            assert self.dlg.checks[1] == 0      # The Case isn't checked.
            dic = strpd_low_dict
            key = win.key.lower()
            set_ = set_lowdict
            r_list = Rlsp
        numwords, win.key = self.make_key_whole(key, dic, set_)
        win.keym = win.key  # 16/12/2024

        return numwords, set_, r_list

    def findf3_ww(self, x1: int, x2: int) -> int:
        """Find Whole Words."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        numwords, set_, r_list = self.assign_values()
        current_position: int = 0  # Pointer to the first verse with the searched for key.
        if numwords == 1:
            self.find_whole_word_single(x1, x2, set_, r_list)   # Match the whole single word.
            if self.dlg.checks[0] in (3, 4):
                win.occurring = len(win.occurs)
            if win.occurring != 0:
                win.occurrence = 0
                win.verse = 0
                win.finding = -1
                current_position = get_next_occurrence()
                if win.message:
                    self.statusBar.showMessage(win.message)
                self.statusBar.repaint()
        elif numwords > 1:
            from abib.services.search_service import findf3_ww_ac, findf3_ww_all
            if self.dlg.checks[0] == 2:
                findf3_ww_ac(x1, x2, numwords, set_, r_list, self)
            elif self.dlg.checks[0] == 3:
                findf3_ww_all(x1, x2, numwords, set_, r_list, self)
            elif self.dlg.checks[0] == 4:
                _, win.key = fcs.any_of_the_words_lookup(win.key, set_)
                findf3_ww_any(x1, x2, set_, r_list, self)
            if win.occurring != 0:
                if self.dlg.checks[0] in (2, 3, 4):
                    win.occurrence = 0
                    win.verse = 0
                    win.finding = -1
                    current_position = get_next_occurrence()
                if win.message:
                    self.statusBar.showMessage(win.message)
                self.statusBar.repaint()
        else:
            win.occurring = 0

        return current_position

    def find_whole_word_single(self, x1: int, x2: int, _set: Dict[str, Set], r_list: List) -> None:
        """Match the whole single word."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        try:
            win.occur = sorted(list(_set[win.key]))
        except KeyError:
            win.occurring = 0
        else:
            win.occurs = []
            for i in win.occur:
                if i < x1 or i > x2:
                    continue
                win.occurs.append(i)
            # List of lists with tuple of the word positions, within the related verse.
            liszt = [win.key]
            if self.dlg.checks[0] == 4:
                from abib.services.search_service import check_count_sort
                check_count_sort(liszt, r_list, self)
            else:
                from abib.services.search_service import iterate_list
                iterate_list(liszt, r_list, self)
        # List of verses containing the searched for item.
        # Number of occurrences of the searchitem within the range x1 to x2.

    def occurrent(self, x1: int, x2: int) -> int:
        """Count occurrences of the item searched for."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        if win.occurrence == 0:
            self.gent = self.gen(win.key, x1, x2)
        assert self.gent is not None
        current_position, win.y, win.occurrence = next(self.gent)
        win.statusBar.showMessage(win.nav.get_status_message(current_position))

        return current_position

    def find_f4(self) -> None:
        """Repeat find frontend for raw search."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        if win.occurrence < win.occurring:
            current_position = self.get_line_number()

            if forward:
                history.back_push(w, current_position)
                while forward:
                    b_ = forward.pop()
                    back.append(b_)
            else:
                forward.clear()
                history.back_push(w, current_position)

            # Ensure self.gent is a valid generator
            if self.gent is None:
                raise ValueError(
                    "self.gent has not been initialized. It must be assigned a valid generator before calling find_f4.")

            try:
                current_position, win.y, win.occurrence = next(self.gent)
            except StopIteration:
                # Handle generator exhaustion if needed
                self.statusBar.showMessage("Search completed: no more matches.")
                return

            # Set the status bar message and other UI updates.
            win.statusBar.showMessage(win.nav.get_status_message(current_position))
            if win.message:
                self.statusBar.showMessage(win.message)
            self.statusBar.repaint()
            self.goto_line_find(current_position)

    def find_f4_alt(self) -> None:
        """Repeat find frontend for Whole words."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        if len(win.occurs) > 0 and win.occurrence < win.occurring:
            current_position = self.get_line_number()
            if forward:
                history.back_push(w, current_position)
                while forward:
                    b_ = forward.pop()
                    back.append(b_)
            else:
                forward.clear()
                history.back_push(w, current_position)

            if self.dlg.checks[0] in (3, 4):
                win.verse += 1
                current_position = win.occurs[win.verse]
                win.finding = -1
            if self.dlg.checks[0] in (2, 3, 4) or self.dlg.checks[2] == 6:
                current_position = get_next_occurrence()

            if win.message:
                self.statusBar.showMessage(win.message)
            self.statusBar.repaint()
            self.goto_line_find(current_position)

    def gen(self, key: str, x1: int, x2: int):
        """Return the next position of the searched for key using in-memory data."""
        assert w is not None
        win: Any = w
        d1 = 0
        if self.dlg.checks[1] == 1:
            source = Rnew
        else:
            source = Rlow
            key = key.lower()

        for current_position in range(x1, x2 + 1):
            if current_position >= len(source):
                break
            a = source[current_position]
            start_search = 0
            while True:
                y = a.find(key, start_search)
                if y == -1:
                    break
                d1 += 1
                win.y = y
                start_search = y + 1
                yield current_position, win.y, d1

    def goto_line_find(self, current_position: int) -> None:
        """Find function - prepare for output."""

        try:
            ln = int(next(islice(Amap, current_position, None)))
        except (StopIteration, TypeError, ValueError):
            ln = 0
        self.adjust_highlighting(ln, current_position)
        self.move_to_line(ln)

    def stripped_punctuation_adjust(self, ln: int, current_position: int, start: int, end: int, truth: bool) -> int:
        """Addition for 'Whole words only'.

        This adjustment allows for no punctuation in the stripped search text.
        """

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        add: int
        if '¶ ' in KJV[ln] and truth is True:
            win.y += 2
            end = win.y
        if self.dlg.checks[1] == 0:
            add = fcs.repeat_find(Rlow[current_position], start, end)
        else:
            add = fcs.repeat_find(Rnew[current_position], start, end)
        return add

    def stripped_punctuation_adjust_ki(self, current_position: int, start: int, end: int) -> int:
        """Addition for 'Whole words only'.

        This adjustment allows for no punctuation in the stripped search text.
        """

        add: int
        if self.dlg.checks[1] == 0:
            add = fcs.repeat_find_keyinc(Rlow[current_position], start, end)
        else:
            add = fcs.repeat_find_keyinc(Rnew[current_position], start, end)

        return add

    def adjust_highlighting(self, ln: int, _x: int) -> None:
        """Adjust highlighting for longer length Unicode characters."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        add = 0
        # In multi-word modes (3 and 4) we highlight individual spans; rely on provided win.key and win.y
        if self.dlg.checks[2] == 6:
            # File/other view mode uses explicit y/yend
            lkey = win.yend - win.y
            win.hiLita.length = lkey
        else:
            lkey = len(win.key)

        if self.dlg.checks[0] != 1:
            start = 0
            assert isinstance(win.y, int)
            end: int = win.y
            add = self.stripped_punctuation_adjust(ln, _x, start, end, True)
        lineinc = add

        ignore = [8217]
        litz = [i for i, c in enumerate(KJV[ln]) if ord(c) > 230 and ord(c) not in ignore]
        j = 0
        for i in litz:
            if i < win.y + add:
                j += 1
        lineinc += j
        er = win.y + lkey
        endof = er + add
        win.hiLita.lineinc = lineinc
        self.keyinc_section(endof, add, ln, _x)

    def keyinc_section(self, endof: int, add: int, ln: int, current_position: int) -> None:
        """keyinc section."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        num = 0
        ignore = [8217]
        litz = []
        assert isinstance(win.y, int)
        start = win.y + add
        if self.dlg.checks[0] != 1:  # Not Raw
            end = start + len(win.key)  # change win.yend
            num = self.stripped_punctuation_adjust_ki(current_position, start, end)
        lav = len(KJV[ln])
        if not (start > lav or endof > lav):
            litz = [i for i in range(start, endof + num) if i < lav and ord(KJV[ln][i]) > 230 and ord(KJV[ln][i]) not in ignore]
        keyinc = len(litz) + num
        win.hiLita.keyinc = keyinc

    def display_verse(self, current_position: int) -> None:
        """Display Bible text in textEditor."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        # print('display_verse')
        try:
            ln = int(next(islice(Amap, current_position, None)))
        except (StopIteration, TypeError, ValueError):
            ln = 0
        if current_position in starts_with_italics:  # Verses that start with italics.
            win.hiLita.keyinc = 1
        else:
            win.hiLita.keyinc = 0
        self.move_to_line(ln)
        self.display_verse_input.clear()
        if win.message == '':
            self.ref_to_statusbar(current_position)
        # Persist last known Bible position so reload() can restore accurately
        try:
            self._last_bible_position = int(current_position)
            self._last_context_position = int(current_position)
        except (TypeError, ValueError):
            pass

    def move_to_line(self, ln: int) -> None:
        """Display engine."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        # print('move_to_line')
        self.textEditor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.on_text_changed(ln)
        ln = make_offset(ln)
        linecursor = QTextCursor(
            self.textEditor.document().findBlockByLineNumber(ln))
        self.textEditor.moveCursor(QTextCursor.MoveOperation.End)
        self.textEditor.setTextCursor(linecursor)
        self.textEditor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        if self.dlg is not None:
            if self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4:
                win.key = win.store

    def on_text_changed(self, ln: int) -> None:
        """Highlighting."""

        # print('on_text_changed')
        fmt = QTextCharFormat()
        assert linehighlightcolor is not None
        assert linetextcolor is not None
        fmt.setBackground(QColor(linehighlightcolor))
        fmt.setForeground(QColor(linetextcolor))

        assert w is not None
        win: Any = w

        win.hiLita.clear = True
        win.hiLita.clear_highlight()
        should_highlight = True

        try:
            if self.dlg is not None:
                if self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4:
                    should_highlight = False
                    win.store = win.key
                    saved_y = win.y
                    current_position = Amap_rev[ln]
                    if (0 <= win.verse < len(win.occurs) and win.verse < len(win.occur)
                            and win.occurs[win.verse] == current_position):
                        should_highlight = True
                        win.hiLita.clear = False
                        keys = sorted(win.occur[win.verse])
                        for i in keys:
                            assert isinstance(i, (list, tuple))
                            win.key = '+' * (i[1] - i[0])
                            win.y = i[0]
                            self.adjust_highlighting(ln, current_position)
                            pos = win.y + win.hiLita.lineinc
                            length = len(win.key) + win.hiLita.keyinc
                            win.hiLita.add_multi_highlight(ln, pos, length)
                    win.y = saved_y

            if should_highlight:
                win.hiLita.highlight_line(ln, fmt)
        except ValueError:
            pass

    def display_verse_from_history(self, current_position: int) -> None:
        """Display Bible text in textEditor after a back or forward pop."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        try:
            ln = int(next(islice(Amap, current_position, None)))
        except (StopIteration, TypeError, ValueError):
            ln = 0
        if current_position in starts_with_italics:  # Verses that start with italics.
            win.hiLita.keyinc = 1

        if self.dlg is not None and self.dlg.checks[0] in (3, 4):
            try:
                win.verse = win.occurs.index(current_position)
                win.finding = 0
                win.occurrence = win.verse + 1
                if win.occur[win.verse]:
                    win.occur[win.verse].sort(key=lambda _x: _x[0])
                    win.y = win.occur[win.verse][0][0]
                    win.yend = win.occur[win.verse][0][1]
            except (ValueError, IndexError):
                pass

        self.textEditor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.on_text_changed(ln)
        ln = make_offset(ln)
        linecursor = QTextCursor(
            self.textEditor.document().findBlockByLineNumber(ln))
        self.textEditor.moveCursor(QTextCursor.MoveOperation.End)
        self.textEditor.setTextCursor(linecursor)
        self.textEditor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.ref_to_statusbar(current_position)
        # Persist last known Bible position so reload() can restore accurately
        try:
            self._last_bible_position = int(current_position)
            self._last_context_position = int(current_position)
        except (TypeError, ValueError):
            pass

    def ref_to_statusbar(self, current_position: int) -> None:
        """Display messages in the status bar."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        message = win.message if win.message else self.nav.get_status_message(current_position)

        self.statusBar.showMessage(message)
        self.statusBar.repaint()

    def open_commentary_window(self) -> None:
        """Open or focus the Gill commentary window centered on the current verse."""
        from abib.ui.gill_window import GillCommentaryWindow  # deferred import
        # Resolve DB path in the application folder
        db_path = Path(sh.str_cwd) / "gill.cmt.sqlite"
        if not db_path.exists():
            try:
                QMessageBox.warning(self, "Commentary", f"Database not found:\n{db_path}")
            except (RuntimeError, TypeError):
                pass
            return

        try:
            current_position = int(self.get_line_number())
        except (RuntimeError, AttributeError, TypeError, ValueError):
            try:
                current_position = int(self._last_bible_position)
            except (AttributeError, TypeError, ValueError):
                current_position = 0
        if current_position < 0:
            current_position = 0
        if current_position > sh.LAST_VERSE_IN_BIBLE:
            current_position = sh.LAST_VERSE_IN_BIBLE
        try:
            entry = sh.Info[current_position]
            b = int(entry[0]) + 1
            c = int(entry[1]) + 1
            v = int(entry[2]) + 1
            self._last_bible_position = current_position
            self._last_context_position = current_position
        except (IndexError, TypeError, ValueError):
            b, c, v = self.nav.get_current_bcv()

        # Lazily create the window
        if self._gill_win is None:
            try:
                # Create as a true top-level window (no parent) so it can be viewed independently
                # Share the same settings service to avoid cache divergence
                self._gill_win = GillCommentaryWindow(db_path=db_path, parent=None, settings_service=self.settings_service)
            except (RuntimeError, TypeError, sqlite3.Error) as exc:
                try:
                    QMessageBox.critical(self, "Commentary", f"Unable to open commentary window.\n{exc}")
                except (RuntimeError, TypeError):
                    pass
                self._gill_win = None
                return

        # Update content and show the window
        try:
            # Use (book, chapter, fromverse) lookups per current DB access strategy
            if isinstance(self._gill_win, GillCommentaryWindow):
                self._gill_win.set_reference(b, c, v)
                # Apply the current theme
                try:
                    self._gill_win.apply_theme(self.theme.state.is_dark_mode)
                    self.theme.apply_widget(self._gill_win)
                except (RuntimeError, AttributeError):
                    pass
        except (AttributeError, TypeError, ValueError):
            pass
        try:
            assert self._gill_win is not None
            self._gill_win.show()
            self._gill_win.raise_()
            self._gill_win.activateWindow()
        except (RuntimeError, AttributeError, TypeError, AssertionError):
            pass

    # Auto-follow toggle removed from MainWindow.

    # ENTRY POINT FOR F2 DISPLAY VERSE.
    def goto_line(self, ref: str = '') -> None:
        """Move the display to the line requested."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = self.get_line_number()
        forward.clear()
        history.back_push(w, current_position)
        reset_attributes()
        if not ref:
            ref = self.display_verse_input.text()
            # print(f"ref: {ref}")
        ref = fcs.remove_junk(ref)
        if ref in ('q', 'Q'):
            self.display_verse_input.clear()
            exit()

        # print(f"ref in goto_line: {ref}")
        current_position = self.reference_to_line_number(ref)
        if current_position == -1:
            self.display_verse_input.clear()
        else:
            if current_position < 0:
                current_position = 0
            if current_position > sh.LAST_VERSE_IN_BIBLE:
                current_position = sh.LAST_VERSE_IN_BIBLE
            self.display_verse(current_position)

    def  goto_book(self, _index: int) -> None:
        """Move the display to the line requested by comboBox_1."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position = self.get_line_number()
        forward.clear()
        history.back_push(w, current_position)
        reset_attributes()
        book: int = self.comboBox_1.currentIndex()
        # book is an index 0-65
        if book == sh.BOOKS_IN_THE_BIBLE - 1:
            b = 22  # Number of chapters in Revelation
        else:
            a: int = sh.Info.index((book + 1, 0, 0))
            b: int = sh.Info[a - 1][1] + 1  # No. of chapters in the book.
        win.nchapters = []
        for _ in range(1, b + 1):
            win.nchapters.append(str(_))
        self.comboBox_2.clear()
        self.comboBox_2.addItems(self.nchapters)
        self.comboBox_3.clear()
        self.nverses = ['1']
        self.comboBox_3.addItems(self.nverses)
        ref = win.nwin[book]
        ref = ref.replace(' ', '')
        # print(f"ref in goto_book: {ref}")
        current_position = self.reference_to_line_number(ref, book)
        if current_position < 0:
            current_position = 0
        if current_position > sh.LAST_VERSE_IN_BIBLE:
            current_position = sh.LAST_VERSE_IN_BIBLE
        self.display_verse(current_position)
        self.goto_chapter(_index)

    def goto_chapter(self, _index: int) -> None:
        """Move the display to the line requested by comboBox_2."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = self.get_line_number()
        forward.clear()
        history.back_push(w, current_position)
        reset_attributes()
        book: int = self.comboBox_1.currentIndex()
        chapter: int = self.comboBox_2.currentIndex()
        if chapter == int(win.nchapters[-1]) - 1:
            # No. of verses in the chapter.
            if book == sh.BOOKS_IN_THE_BIBLE - 1:
                d = 21
            else:
                c: int = sh.Info.index((book + 1, 0, 0)) - 1
                d: int = sh.Info[c][2] + 1
        else:
            try:
                c = sh.Info.index((book, chapter + 1, 0)) - 1
            except ValueError:
                c = sh.Info.index((book + 1, 0, 0)) - 1
            d = sh.Info[c][2] + 1
        win.nverses = []
        for _ in range(1, d + 1):
            win.nverses.append(str(_))
        self.comboBox_3.clear()
        self.comboBox_3.addItems(self.nverses)

        ref = win.nwin[book]
        ref = ref.replace(' ', '')
        ref = f"{ref} {str(chapter + 1)}"

        # print(f"ref in goto_chapter: {ref}")
        current_position = self.reference_to_line_number(ref, book, chapter)
        if current_position < 0:
            current_position = 0
        if current_position > sh.LAST_VERSE_IN_BIBLE:
            current_position = sh.LAST_VERSE_IN_BIBLE
        self.display_verse(current_position)

    def goto_verse(self, _index: int) -> None:
        """Move the display to the line requested by comboBox_3."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = self.get_line_number()
        forward.clear()
        history.back_push(w, current_position)
        reset_attributes()
        book: int = self.comboBox_1.currentIndex()
        chapter: int = self.comboBox_2.currentIndex()
        verse: int = self.comboBox_3.currentIndex()

        ref = win.nwin[book]
        ref = ref.replace(' ', '')
        ref = f"{ref} {str(chapter + 1)}.{verse + 1}"
        # print(f"ref in goto_verse: {ref}")
        current_position = self.reference_to_line_number(ref, book, chapter)
        if current_position < 0:
            current_position = 0
        if current_position > sh.LAST_VERSE_IN_BIBLE:
            current_position = sh.LAST_VERSE_IN_BIBLE
        # print(f"current_position in goto_verse: {current_position}")
        self.display_verse(current_position)

    def reference_to_line_number(self, reference_text: str, book: int = 0, chapter: int = 0) -> int:
        """Convert reference text to a line number in the Bible."""
        from abib.domain.scripture_refs import normalize_reference
        
        current_line = self.get_line_number()
        normalized = normalize_reference(reference_text, book, chapter)
        
        if not normalized:
            self.on_error("Invalid format. Please enter a valid reference.", 750, True)
            return -1

        # Handle numeric-only (verse in current chapter)
        if normalized.isdigit():
            verse = int(normalized) - 1
            return self.calculate_position(current_line, verse)

        # Handle floating point-style (e.g. "23.7" -> current book)
        if fcs.is_float_re(normalized):
             normalized = fcs.attach_book_name(normalized, current_line)

        bits = fcs.split_reference(normalized)
        book_num, chapter, verse = self.nav.resolve_reference(bits)

        if not book_num:
            self.error_invalid_book()

        if book_num is None or chapter is None or verse is None:
            return -1

        try:
            position = self.nav.calculate_line(book_num, chapter, verse, current_line)
            if position is not None:
                return position
        except ValueError:
            self.error_invalid_verse_or_position()

        return -1

    # Helper Methods

    @staticmethod
    def calculate_position(current_line: int, new_verse: int) -> int:
        """Calculate the absolute position of a verse from the current line.
           Only allows valid positions within the same chapter."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        inf: List = sh.Info[current_line]
        current_chapter: int = inf[1]
        # print(f"2474 current_chapter: {current_chapter}")
        current_verse = inf[2]
        # print(f"2475 current_verse: {current_verse}")
        # print(f"2476 current_line: {current_line}")
        # print(f"new_verse: {new_verse}")

        if new_verse >= 0:
            new_line: int = current_line - current_verse + new_verse
        else:
            new_line = current_line + new_verse + 1
            new_verse = current_verse + new_verse + 1

        # print(f"2477 new_line: {new_line}")

        message = f"Out of bounds. No verse {new_verse + 1} here!"
        try:
            new_chapter: int = sh.Info[new_line][1]
            # print(f"2484 new_chapter: {new_chapter}")
        except IndexError:
            # print(">>>>>>>>>>>>>>>")
            win.on_error(message, 750, True)
            return_value = current_line
        else:
            if new_chapter != current_chapter:
                # print("<<<<<<<<<<<<<<")
                win.on_error(message, 750, True)
                return_value = current_line
            else:
                return_value = new_line

        # print(f"2476 return_value: {return_value}")

        return return_value

    @staticmethod
    def is_integer(value: Any) -> bool:
        """True if the value is an integer."""

        val: str = str(value)
        if val.startswith('-'):
            return val[1:].isdigit()

        return val.isdigit()

    def error_invalid_book(self):
        """Handle book not found."""

        message: str = "Not a book name."
        self.on_error(message, 750, True)
        # print(message)

    def error_invalid_verse_or_position(self):
        """Handle invalid chapter/verse errors."""

        message: str = "Invalid chapter or verse."
        self.on_error(message, 750, True)
        # print(message)

    def get_line_number(self):
        """Find the line number of the verse at the top of the screen."""

        self.textEditor.moveCursor(QTextCursor.MoveOperation.StartOfLine)
        linenumber: int = self.textEditor.textCursor().blockNumber()
        if linenumber in Amap:
            current_position: int = Amap_rev[linenumber]
        else:
            # Safely get the first element of Amap without direct indexing (for linters/type-checkers)
            try:
                first_amap = int(next(islice(Amap, 0, None)))
            except (StopIteration, TypeError, ValueError):
                first_amap = 0
            if linenumber < first_amap:
                current_position = 0
            elif linenumber > KJB_PCE_LASTLINE - 118:
                current_position = sh.LAST_VERSE_IN_BIBLE
            else:
                for _ in range(10):
                    if linenumber + _ in Amap:
                        linenumber += _
                        break
                else:
                    return sh.LAST_VERSE_IN_BIBLE
                current_position = Amap_rev[linenumber]

        return current_position

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Mouse trapping routine."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        if event.buttons() == Qt.MouseButton.LeftButton:
            current_position: int = self.get_line_number()
            self.ref_to_statusbar(current_position)
        elif event.buttons() == Qt.MouseButton.RightButton:
            pass
        elif event.buttons() == Qt.MouseButton.MiddleButton and win.no_f3_yet == 1:
            self.repeat_find_forward()
        elif event.buttons() == Qt.MouseButton.MiddleButton and win.no_f3_yet == 0:
            current_position = self.get_line_number()
            self.ref_to_statusbar(current_position)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Key trapping routine."""

        qtcore_keys_dict = {
            Qt.Key.Key_F2: self.navigate_to_verse,
            Qt.Key.Key_F3: self.search_current_word,
            Qt.Key.Key_F4: self.repeat_find_forward,
            Qt.Key.Key_F5: self.history_back,
            Qt.Key.Key_F6: self.history_forward,
            Qt.Key.Key_F7: self.earlier_book,
            Qt.Key.Key_F8: self.later_book,
            Qt.Key.Key_F9: self.open_commentary_window_shortcut,
            Qt.Key.Key_F10: self.earlier_chapter,
            Qt.Key.Key_F11: self.later_chapter,
            Qt.Key.Key_C: self.C,
            Qt.Key.Key_Question: self.feature,
            Qt.Key.Key_F12: self.show_devotional,
            Qt.Key.Key_Q: exit}

        if event.key():
            try:
                qtcore_keys_dict[event.key()]()
            except KeyError:
                pass
        else:
            pass

    def navigate_to_verse(self) -> None:
        """F2 key for passage reference entry."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        self.display_verse_input.setFocus()
        self.statusBar.clearMessage()

    def search_current_word(self) -> None:
        """F3 key for find key entry."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = self.get_line_number()
        forward.clear()
        history.back_push(w, current_position)
        self.onFindBtnClicked()

    def repeat_find_forward(self) -> None:
        """Find the next key F4."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        if win.key == ' ' or win.no_f3_yet == 0:
            pass
        else:
            self.textEditor.setFocus()
            self.find_next()

    def history_back(self) -> None:
        """Back key."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        # If we have just returned from an auxiliary file (README/COPYING/HELP),
        # skip one Back action to keep the restored verse position, rather than
        # popping history to an unrelated location (often Genesis 1:1).
        if getattr(self, "_just_restored_from_aux", False):
            self._just_restored_from_aux = False
            return
        w.message = ''
        if len(back) > 0:
            current_position: int = self.get_line_number()
            history.forward_push(w, current_position)
            current_position = history.back_pop(w)
            self.display_verse_from_history(current_position)

    def history_forward(self) -> None:
        """Forward key."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        if len(forward) > 0:
            current_position: int = self.get_line_number()
            history.back_push(w, current_position)
            current_position = history.forward_pop(w)
            self.display_verse_from_history(current_position)

    def open_commentary_window_shortcut(self) -> None:
        """F9 Fullscreen toggle key."""

        self.toggle_fullscreen()

    def show_devotional(self) -> None:
        """F12 Devotional key."""

        self.display_secondary_window()

    @staticmethod
    def C() -> None:
        """Commentary key."""
        # Use a local reference with a type hint to satisfy the linter
        win: Any = w
        if win is not None:
            win.open_commentary_window()

    def question(self) -> None:
        """Feature key."""
        self.feature()

    def earlier_book(self) -> None:
        """Move to the earlier book."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = self.get_line_number()
        book: int = sh.Info[current_position][0]
        newbook: int = book - 1
        if newbook < 0:
            self.on_error('No earlier book!', 3000, True)
        else:
            forward.clear()
            history.back_push(w, current_position)
            reset_attributes()
            current_position = sh.Info.index((newbook, 0, 0))
            self.display_verse(current_position)

    def later_book(self) -> None:
        """Move to the later book."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = self.get_line_number()
        book: int = sh.Info[current_position][0]
        newbook: int = book + 1
        if newbook > sh.BOOKS_IN_THE_BIBLE - 1:
            self.on_error('No later book!', 3000, True)
        else:
            forward.clear()
            history.back_push(w, current_position)
            reset_attributes()
            current_position = sh.Info.index((newbook, 0, 0))
            self.display_verse(current_position)

    def earlier_chapter(self) -> None:
        """Move to the earlier chapter."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = self.get_line_number()
        old_position = current_position
        book: int = sh.Info[current_position][0]
        chapter: int = sh.Info[current_position][1]
        newchapter: int = chapter - 1
        if newchapter < 0:
            newbook: int = book - 1
            if newbook < 0:
                self.on_error('No earlier chapter!', 3000, True)
                return
            while True:
                if sh.Info[current_position][0] == book:
                    current_position -= 1
                else:
                    break
            newchapter = sh.Info[current_position][1]
            book = newbook
        current_position = sh.Info.index((book, newchapter, 0))
        forward.clear()
        history.back_push(w, old_position)
        reset_attributes()
        self.display_verse(current_position)

    def later_chapter(self) -> None:
        """Move to the later chapter."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = self.get_line_number()
        old_position = current_position
        book: int = sh.Info[current_position][0]
        chapter: int = sh.Info[current_position][1]
        newchapter: int = chapter + 1
        try:
            current_position = sh.Info.index((book, newchapter, 0))
        except ValueError:
            newbook: int = book + 1
            if newbook > sh.BOOKS_IN_THE_BIBLE - 1:
                self.on_error('No later chapter!', 3000, True)
                return
            while True:
                if sh.Info[current_position][0] == book:
                    current_position += 1
                else:
                    break
            newchapter = sh.Info[current_position][1]
            book = newbook
        current_position = sh.Info.index((book, newchapter, 0))
        forward.clear()
        history.back_push(w, old_position)
        reset_attributes()
        self.display_verse(current_position)

    def on_error(self, message: str, millisecond_delay: int, clearbool: bool) -> None:
        """Error message handler."""

        current_position: int = self.get_line_number()
        self.statusBar.showMessage(message)
        self.statusBar.repaint()

        lm: float = millisecond_delay / 1000 + len(message) / 25
        self.beep(current_position, lm)

        if clearbool:
            self.statusBar.clearMessage()
            w.message = ''

    def beep(self, current_position: int, lm: float) -> None:
        """Makes a beep sound and clears the message."""

        # Play error sound via audio service (non-blocking and safe)
        self.audio.play_error()

        self.statusBar.repaint()

        # Delay for 'lm' second.
        time.sleep(lm)

        w.message = ''
        self.ref_to_statusbar(current_position)
        self.statusBar.repaint()

    def dialog_critical(self, exception_text: str) -> None:
        """Error message dialog."""

        dlg: QMessageBox = QMessageBox(self)
        dlg.setText(exception_text)
        dlg.setIcon(QMessageBox.Icon.Critical)
        dlg.show()

    def file_open(self, path1: str) -> None:
        """File opening routine."""

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        # print('file_open ', path1)
        if path1:
            pass
        else:
            path1, _ = QFileDialog.getOpenFileName(
                self, "Open file", "",
                "Text documents (*.txt);All files (*.*)")
            # print(path1, ' Opened')
        if path1:
            try:
                text_data: str | None = None
                # Fast path for the main Bible text: use a cached, pre-stripped file if available
                is_bible_file = str(Path(path1).name) == "KJB_PCE.txt"
                if is_bible_file:
                    try:
                        src = Path(path1)
                        cache = src.with_name("KJB_PCE_stripped.txt")
                        # If the cache exists, and up to date, read it; else build and refresh it
                        if cache.is_file() and cache.stat().st_mtime >= src.stat().st_mtime:
                            with cache.open("r", encoding="utf-8", buffering=(1 << 20)) as f_cache:
                                text_data = f_cache.read()
                        else:
                            # Read source with a large buffer, strip copyright, then write cache
                            with src.open("r", encoding="utf-8", buffering=(1 << 20)) as f_src:
                                original = f_src.read()
                            loc = original.find(EOTNOC)
                            if loc == -1:
                                # Keep legacy behaviour (fail loudly) if marker missing
                                print('Failed to find the line ', EOTNOC)
                                print('Cannot continue until this is put right.')
                                exit()
                            start_idx = loc + len(EOTNOC) + 1
                            text_data = original[start_idx:]
                            # Best-effort cache write (do not fail to open if this causes an error)
                            try:
                                with cache.open("w", encoding="utf-8", buffering=(1 << 20)) as f_out:
                                    assert text_data is not None
                                    f_out.write(text_data)
                            except (OSError, PermissionError):
                                pass
                    except (OSError, UnicodeDecodeError, ValueError):
                        # Fall back to generic read if anything goes wrong in the optimised path
                        text_data = None

                if text_data is None:
                    # Generic read path (other files or fallback), use a large buffer
                    with open(path1, "r", encoding="utf-8", buffering=(1 << 20)) as f_open:
                        text_data = f_open.read()

                win.PCE_text = text_data
            except (FileNotFoundError, PermissionError, OSError, UnicodeDecodeError) as e3:
                self.dialog_critical(str(e3))
            else:
                # If we are switching away from the Bible to another file, remember the last Bible position
                try:
                    prev_is_bible = isinstance(getattr(self, "path1", None), str) and str(Path(self.path1).name) == "KJB_PCE.txt"
                except (OSError, TypeError, ValueError):
                    prev_is_bible = False
                if prev_is_bible and not str(Path(path1).name) == "KJB_PCE.txt":
                    try:
                        self._last_bible_position = int(self.get_line_number())
                    except (RuntimeError, TypeError, ValueError):
                        # Default to Genesis 1:1 if we cannot determine it
                        self._last_bible_position = 0

                self.path1 = path1
                if path1[-11:] == r'KJB_PCE.txt':
                    # For the Bible file, w.PCE_text is already stripped if loaded via the fast path.
                    # If it wasn't, do a safety strip (covers first-run without cache).
                    assert win.PCE_text is not None
                    if EOTNOC:
                        pos = win.PCE_text.find(EOTNOC)
                        if pos != -1:
                            win.PCE_text = win.PCE_text[pos + len(EOTNOC) + 1:]

                # Speed up large text injection by suspending updates/undo
                try:
                    self.textEditor.setUpdatesEnabled(False)
                    doc_obj: Any = self.textEditor.document()
                    try:
                        if doc_obj is not None:
                            doc_obj.setUndoRedoEnabled(False)
                    except (RuntimeError, AttributeError):
                        pass
                    assert win.PCE_text is not None
                    self.textEditor.setPlainText(win.PCE_text)
                finally:
                    # Retrieve the document object again in case the first retrieval
                    # failed or was scoped too narrowly.
                    # Using a local, non-None type-hinted object for the final block.
                    doc_final: Any = self.textEditor.document()
                    try:
                        if doc_final is not None:
                            doc_final.setUndoRedoEnabled(True)
                    except (RuntimeError, AttributeError):
                        pass
                    try:
                        self.textEditor.setUpdatesEnabled(True)
                    except (RuntimeError, AttributeError):
                        pass
                self.update_title()

                if path1[-11:] == r'KJB_PCE.txt':
                    # We are (re)loading the Bible text in the main window.
                    # Do NOT force a jump to Genesis 1:1.
                    # Restore the last known Bible position if available.
                    win.otherFileFlag = False
                    try:
                        last_pos = int(getattr(self, "_last_bible_position", 0))
                    except (TypeError, ValueError):
                        last_pos = 0
                    # Clamp to valid range
                    if last_pos < 0:
                        last_pos = 0
                    if last_pos > sh.LAST_VERSE_IN_BIBLE:
                        last_pos = sh.LAST_VERSE_IN_BIBLE
                    self.display_verse(last_pos)
                else:
                    win.otherFileFlag = True
                    # When opening non-Bible files, ensure any prior Bible highlighting is cleared
                    try:
                        if getattr(win, 'hiLita', None):
                            win.hiLita.clear = True
                            win.hiLita.clear_highlight()
                            # Reset clear flag so future highlights (when the Bible is reopened) work normally
                            win.hiLita.clear = False
                    except (AttributeError, RuntimeError):
                        # Be conservative; highlighting state is non-critical for auxiliary files
                        pass

    def file_print(self) -> None:
        """File print routine."""
        self.printing.print_plain_text(self.textEditor, parent=self)

    def update_title(self) -> None:
        """Title update routine."""

        if Path(self.path1).stem == 'KJB_PCE':
            self.setWindowTitle("  THE HOLY BIBLE      Authorized King James Version")
        else:
            title: str = f"{Path(self.path1).stem if self.path1 else ''}"
            title = title.replace("Pilgrims-Progress", "The Pilgrim's Progress by John Bunyan.")
            self.setWindowTitle(title)

    def open_settings_dialog(self):
        """Open the settings dialog."""
        # Defer import to reduce startup/import-time cost
        from abib.ui.settings_dialog import SettingsDialog

        dialog = SettingsDialog(self, settings_service=self.settings_service)

        # Ensure the dialog follows the current theme palette
        self.theme.apply_widget(dialog)

        dialog.exec()

    # _update_splash_visibility moved to SettingsDialog.


    def _refresh_theme_across_ui(self) -> None:
        """Apply the app palette, style the main editor, update secondary windows, and
        re-theme any open dialogs/windows.
         Centralised to avoid duplication."""
        # Apply application-wide palette first so dialogs/menus follow suit
        self.theme.apply_app_palette()
        # Apply to the main editor and secondary window
        self.theme.apply_to_editor(self.textEditor)
        self.update_text_display_theme()
        # Per user request: the verse input / search box should always have a white background and black text
        # in both themes to distinguish it from other dark controls.
        if self.theme.state.is_dark_mode:
            self.display_verse_input.setStyleSheet(
                "QLineEdit { background-color: #ffffff; color: #000000; border: 1px solid #3a3a3a; }"
            )
        else:
            self.display_verse_input.setStyleSheet(
                "QLineEdit { background-color: #ffffff; color: #000000; border: 1px solid #b5b5b5; }"
            )
        # Keep control heights consistent with the active style/theme
        try:
            self._normalize_control_heights()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        # Also refresh any currently open dialogs/windows
        if getattr(self, 'dlg', None):
            self.theme.apply_widget(self.dlg)
        if getattr(self, 'about_window', None):
            self.theme.apply_widget(self.about_window)
        if getattr(self, 'text_edit_window', None):
            try:
                self.text_edit_window.apply_theme(self.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            self.theme.apply_widget(self.text_edit_window)
        if getattr(self, '_gill_win', None):
            # Use a local reference with a type hint to satisfy the linter
            gw: Any = self._gill_win
            try:
                gw.apply_theme(self.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            self.theme.apply_widget(gw)

    def _normalize_control_heights(self) -> None:
        """Make QComboBox controls the same height as pushbuttons.

        Uses the current style's sizeHint for a reference QPushButton (OK)
        to compute a DPI- and theme-aware height, then applies it to the
        main comboboxes.
        Called after UI setup and whenever the theme changes.
        """
        try:
            ref_btn = getattr(self, 'okButton', None)
            if not ref_btn:
                return
            # Use a local reference with a type hint to satisfy the linter
            r: Any = ref_btn
            ref_h = int(r.sizeHint().height())
        except (RuntimeError, AttributeError, TypeError, ValueError):
            ref_h = 0
        if not ref_h:
            return
        # Controls to normalise to the same height as pushbuttons
        for ctrl_name in (
            'comboBox_1',
            'comboBox_2',
            'comboBox_3',
            'other_works_combo',
            'display_verse_input',  # F2 text entry box
        ):
            ctrl = getattr(self, ctrl_name, None)
            if ctrl is None:
                continue
            # Use a local reference with a type hint to satisfy the linter
            c: Any = ctrl
            try:
                c.setFixedHeight(ref_h)
            except (RuntimeError, AttributeError, TypeError, ValueError):
                # Be tolerant of lifecycle/style changes
                pass

    def set_theme(self, the_settings):
        """Apply the theme from settings using ThemeManager without legacy globals."""

        theme_key = 'theme'
        current_theme = the_settings.get(theme_key, 'Light')

        # Set ThemeManager state explicitly to match settings
        self.theme.state.is_dark_mode = (current_theme == 'Dark')

        # Apply the palette and refresh all open UI elements
        self._refresh_theme_across_ui()

        # Ensure settings reflect what's applied and persist
        self.settings[theme_key] = 'Dark' if self.theme.state.is_dark_mode else 'Light'
        self.settings_service.save(self.settings)

    def display_secondary_window(self, offset: int = 0) -> None:
        """Creates and displays the secondary window to show SME text.
        Ensures the secondary window is non-blocking."""

        # Get the SME text (from the display_devotional method)
        try:
            sme_text = self.display_devotional(offset)
        except (KeyError, IndexError, ValueError, TypeError) as e4:
            sme_text = f"Error: {e4}"

        if not self.secondary_window or not self.secondary_window.isVisible():
            # Create a new secondary window if it doesn't exist or is closed
            from abib.ui.windows import SecondaryWindow as ExtSecondaryWindow  # deferred import
            self.secondary_window = ExtSecondaryWindow(
                sme_text,
                navigate_left_cb=lambda: self.display_secondary_window(-12),
                navigate_right_cb=lambda: self.display_secondary_window(12),
                settings_service=self.settings_service
            )
            self.secondary_window.show()
        else:
            # If the window is already open, update its contents.
            self.secondary_window.update_content(sme_text)
            self.secondary_window.raise_()
            self.secondary_window.activateWindow()

        self.update_text_display_theme()

    def display_devotional(self, adjustment: int = 0) -> str:
        """C H Spurgeon's Morning and Evening Readings.

        Delegates to ReadingPlans service and navigates to the referenced scripture.
        """

        try:
            sme_text, sme_ref = self.reading_plans.get_devotional_entry(adjustment)
        except (KeyError, TypeError, ValueError) as err:
            # Narrow exception handling to expected data/parsing issues
            return f"Error retrieving SME: {err}"

        if sme_ref:
            try:
                self.goto_line(sme_ref)
            except (ValueError, TypeError, KeyError, IndexError):
                # Ignore navigation errors; still show text
                pass
        return sme_text

    def toggle_dark_mode(self):
        """Toggle dark mode using ThemeManager and persist to settings."""

        # Toggle via ThemeManager
        is_dark = self.theme.toggle()

        # Persist selection in settings
        self.settings["theme"] = "Dark" if is_dark else "Light"
        self.settings_service.save(self.settings)

        # Apply the palette and refresh all open UI elements
        self._refresh_theme_across_ui()

    def update_text_display_theme(self) -> None:
        """Update the text display theme using ThemeManager."""

        # Apply to the secondary window if available
        if self.secondary_window and getattr(self.secondary_window, 'text_display', None):
            self.theme.apply_to_secondary(self.secondary_window)
            return
        # If the secondary window (or its text display) does not exist yet, exit quietly.
        # This method can be called during startup/theme changes before the window is created.
        return
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ End of MainWindow class ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~




if __name__ == '__main__':
    # Bootstrap moved to app.run() for cleaner modularisation (PR10)
    try:
        from abib.app import run
    except ImportError:
        from app import run
    run()
