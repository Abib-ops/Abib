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

Using PySide6-6.11.2 and python3.14.7 (64-bit).

12/09/2026

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

import logging
import sqlite3
import sys
import time
import webbrowser
from collections.abc import Iterator
from itertools import islice
from pathlib import Path
from typing import Any, cast

from PySide6.QtCore import QEvent, QObject, QPoint, QRect, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QKeySequence,
    QMouseEvent,
    QShortcut,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QGridLayout,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from abib.core import fcs
from abib.core import shared as sh
from abib.core.history import History
from abib.core.navigation import NavigationCore
from abib.services import search_service
from abib.services.settings import SettingsService
from abib.ui.ui_helpers import NoZoomPlainTextEdit

history = History()
back = history.back
forward = history.forward

# Module logger. Swallowed exceptions are logged here (usually at DEBUG level)
# instead of being silently discarded, so genuine failures can be surfaced.
logger = logging.getLogger(__name__)

# Global window 'handle' placeholder; set by app.run() at startup.
# NOTE: MainWindow's own methods use ``self`` directly; this global remains only
# for the module-level helpers below (``get_next_occurrence``/``reset_attributes``),
# the ``@staticmethod`` shortcut handlers (``commentary_key``/``calculate_position``),
# and external windows (gill_window.py, highlighter.py).
w: Any | None = None
# Global splash screen reference (kept alive until the user disables it in settings)
splash: Any | None = None

# Number of lines to search backward/forward when mapping a clicked editor line
# to its verse index (see eventFilter's click handling).
VERSE_LINE_SEARCH_RADIUS: int = 12


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
# Search data tables (Rnew/Rlow/Rstp/Rlsp and the stripped/set dictionaries) are
# no longer stored here: they are loaded into a SearchData context and registered
# with the search engine via search_service.set_search_data() (see app.run).
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
        cast(Any, windll).shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except (AttributeError, OSError) as e:
    # AttributeError: non-Windows (windll is None); OSError: Windows API failure
    print(f"Error setting APP ID: {e}")


def get_next_occurrence() -> int:
    """Delegate to the search engine, operating on the global window handle."""

    assert w is not None
    return search_service.get_next_occurrence(cast("MainWindow", w))


def find_whole_word_any(x1: int, x2: int, _set: dict[str, set], r_list: list, win: 'MainWindow') -> None:
    """Match any word."""

    search_service.find_whole_word_any(x1, x2, _set, r_list, win)


def make_offset(ln: int) -> int:
    """Enable highlighting of first verses while showing the titles above."""

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
        super().__init__(*args, **kwargs)

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
        # Predeclare UI elements that are instantiated in init_ui to satisfy linters
        self.last_work_btn: QPushButton | None = None
        # Search button for Other Works (instantiated in init_ui)
        self.search_work_btn: QPushButton | None = None
        # Keyboard shortcut for reopening the last Other Work (predeclared for linters)
        self.shortcut_last_work: QShortcut | None = None
        # Placeholder for the 4th-column vertical button layout added in init_ui
        self.side_buttons_col: QVBoxLayout | None = None
        self.other_works_map: dict[str, str] = {}
        # Live map of Other Works checkboxes in the settings menu (populated in init_ui)
        self._works_menu_checkboxes: dict[str, Any] = {}
        self.statusBar: Any = None
        self.okButton: Any = None
        self.dlg: Any = None  # No external window yet.
        # self.textEditor: QPlainTextEdit = QPlainTextEdit()
        self.textEditor: Any = NoZoomPlainTextEdit()
        # Predeclare actions bundle to satisfy linters (assigned in init_ui)
        self.actions_bundle = None
        self.search_results_window: Any = None
        self.concordance_service: Any = None
        self.concordance_window: Any = None
        self.other_works_reference_index: Any = None
        self.other_works_references_window: Any = None
        self.other_works_text_search_service: Any = None
        self.other_works_text_search_window: Any = None
        # Guard flag to avoid recursive move/resize while repositioning the
        # separate Search Results window relative to the main window.
        self.positioning_search_results: bool = False
        
        # Theme manager (extract dark mode logic)
        # Initialise 'ThemeManager' based on persisted settings
        from abib.ui.themes import ThemeManager, ThemeState  # local import (deferred)
        is_dark = self.settings.get("theme", "Light") == "Dark"
        self.theme = ThemeManager(ThemeState(is_dark_mode=is_dark))

        # Theming controller (owns palette/refresh logic; MainWindow delegates to it)
        from abib.ui.theme_controller import ThemeController  # local import (deferred)
        self.theme_ctrl = ThemeController(self)

        # Search Results window manager (owns the results panel lifecycle/geometry)
        from abib.ui.results_window_manager import (
            SearchResultsWindowManager,  # local import (deferred)
        )
        self.results_manager = SearchResultsWindowManager(self)

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
        self.gill_win: Any | None = None

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

        self.nwin: list[str] = [
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
        self.nchapters: list[str] = []
        for _ in range(1, 51):
            self.nchapters.append(str(_))
        self.nverses: list[str] = []
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

        self.init_ui()

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

    def init_ui(self) -> None:
        """Initialise Mainwindow GUI."""
        from abib.ui.highlighter import SyntaxHighlighter  # deferred import

        fixedfont: QFont = QFont("Cascadia Mono", self.fontsize, QFont.Weight.Medium)
        self.textEditor.setFont(fixedfont)
        self.textEditor.setReadOnly(True)
        try:
            self.textEditor.viewport().installEventFilter(self)
        except (RuntimeError, AttributeError):
            logger.debug("Could not install event filter on text editor viewport", exc_info=True)

        self._setup_input_fields()
        self._setup_comboboxes()
        
        self.hiLita: SyntaxHighlighter = SyntaxHighlighter(self.textEditor.document())

        grid: QGridLayout = QGridLayout()
        grid.setSpacing(2)
        self.setLayout(grid)

        for _col in range(5):
            grid.setColumnStretch(_col, 1)

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
        """Delegate to the Search Results window manager."""

        self.results_manager.setup_search_results_panel()

    def _search_results_width(self) -> int:
        """Delegate to the Search Results window manager."""

        return self.results_manager.search_results_width()

    def _release_main_width_limit(self) -> None:
        """Delegate to the Search Results window manager."""

        self.results_manager.release_main_width_limit()

    def _position_search_results_window(self) -> None:
        """Delegate to the Search Results window manager."""

        self.results_manager.position_search_results_window()

    def _update_search_results_panel(self) -> None:
        """Delegate to the Search Results window manager."""

        self.results_manager.update_search_results_panel()

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

    def on_search_result_activated(self, current_position: int) -> None:
        """Jump to the clicked search result."""
        current_line = self.get_line_number()
        if current_line != current_position:
            forward.clear()
            history.back_push(self, current_line)
        self._sync_search_state_for_result(current_position)
        self.display_verse_from_history(current_position)

    def open_concordance(self) -> None:
        """Open the Bible concordance window, creating it on first use."""
        if self.concordance_service is None:
            from abib.services.concordance_service import ConcordanceService
            self.concordance_service = ConcordanceService(KJV, Amap, sh.Info, self.nwin, sh.onechapterbooks)

        if self.concordance_window is None:
            from abib.ui.concordance_window import ConcordanceWindow
            self.concordance_window = ConcordanceWindow(self.concordance_service, self)
            self.concordance_window.referenceActivated.connect(self._on_concordance_reference_activated)

        self.concordance_window.show()
        self.concordance_window.raise_()
        self.concordance_window.activateWindow()

    def _on_concordance_reference_activated(self, current_position: int) -> None:
        """Jump to the clicked concordance reference."""
        current_line = self.get_line_number()
        if current_line != current_position:
            forward.clear()
            history.back_push(self, current_line)
        self.display_verse_from_history(current_position)

    def open_other_works_references(self) -> None:
        """Open the Other Works scripture-reference index browser."""
        from abib.services.other_works_reference_index import OtherWorksReferenceIndex
        from abib.ui.other_works_references_window import OtherWorksReferencesWindow

        show_work = dict(self.settings.get("show_work") or {}) if isinstance(self.settings, dict) else {}
        if self.other_works_reference_index is None:
            self.other_works_reference_index = OtherWorksReferenceIndex(self.other_works_map, show_work)
        else:
            self.other_works_reference_index = OtherWorksReferenceIndex(self.other_works_map, show_work)

        if self.other_works_references_window is None:
            parent = self if isinstance(self, QWidget) else None
            self.other_works_references_window = OtherWorksReferencesWindow(self.other_works_reference_index, parent)
            self.other_works_references_window.occurrenceActivated.connect(self._on_other_work_reference_activated)
        else:
            self.other_works_references_window._service = self.other_works_reference_index
            self.other_works_references_window.clear_search()

        self.other_works_references_window.show()
        self.other_works_references_window.raise_()
        self.other_works_references_window.activateWindow()

    def _on_other_work_reference_activated(self, work_path: str, abs_start: int, length: int) -> None:
        """Open an indexed Other Work occurrence and jump to its character range."""
        self.open_text_file_in_window(work_path)
        try:
            reader: Any = getattr(self, "text_edit_window", None)
            if reader is not None:
                if getattr(reader, "_is_loading_file", False):
                    reader._pending_reference_offset = (int(abs_start), int(length))
                    reader._pending_jump_char = int(abs_start)
                reader.jump_to_reference_offset(abs_start, length)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            logger.debug("Failed to jump to Other Works reference offset", exc_info=True)

    def open_other_works_text_search(self) -> None:
        """Open the Other Works text-search browser."""
        from abib.services.other_works_text_search import OtherWorksTextSearchService
        from abib.ui.other_works_text_search_window import OtherWorksTextSearchWindow

        show_work = dict(self.settings.get("show_work") or {}) if isinstance(self.settings, dict) else {}
        self.other_works_text_search_service = OtherWorksTextSearchService(self.other_works_map, show_work)

        if self.other_works_text_search_window is None:
            parent = self if isinstance(self, QWidget) else None
            self.other_works_text_search_window = OtherWorksTextSearchWindow(self.other_works_text_search_service, parent)
            self.other_works_text_search_window.occurrenceActivated.connect(self._on_other_work_text_search_activated)
        else:
            self.other_works_text_search_window._service = self.other_works_text_search_service
            self.other_works_text_search_window.clear_search()

        self.other_works_text_search_window.show()
        self.other_works_text_search_window.raise_()
        self.other_works_text_search_window.activateWindow()

    def _on_other_work_text_search_activated(self, work_path: str, abs_start: int, length: int) -> None:
        """Open an Other Works text-search occurrence and jump to its character range."""
        MainWindow._on_other_work_reference_activated(self, work_path, abs_start, length)

    def _setup_input_fields(self) -> None:
        self.display_verse_input: QLineEdit = QLineEdit()
        self.display_verse_input.setToolTip("F2, Enter or OK to search for a verse.")
        self.display_verse_input.setStyleSheet("QLineEdit { background-color: #e6f4e6; color: #000000; }")
        self.display_verse_input.setGeometry(QRect(50, 50, 200, 25))
        self.display_verse_input.installEventFilter(self)
        self.command_history = []
        self.history_index = -1

    def _setup_comboboxes(self) -> None:
        # Pale green shade to visually group the Book/Chapter/Verse selectors.
        combo_style = "QComboBox { background-color: #e6f4e6; color: #000000; }"

        self.comboBox_1: QComboBox = QComboBox()
        self.comboBox_1.addItems(self.nwin)
        self.comboBox_1.setCurrentIndex(0)
        self.comboBox_1.setStyleSheet(combo_style)
        self.comboBox_1.activated.connect(self.goto_book)

        self.comboBox_2: QComboBox = QComboBox()
        self.comboBox_2.addItems(self.nchapters)
        self.comboBox_2.setCurrentIndex(0)
        self.comboBox_2.setStyleSheet(combo_style)
        self.comboBox_2.activated.connect(self.goto_chapter)

        self.comboBox_3: QComboBox = QComboBox()
        self.comboBox_3.addItems(self.nverses)
        self.comboBox_3.setCurrentIndex(0)
        self.comboBox_3.setStyleSheet(combo_style)
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
        self.okButton.setStyleSheet("QPushButton { text-align: left; background-color: #e6f4e6; color: #000000; }")
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
        self.buttonf3.setStyleSheet("QPushButton { text-align: left; background-color: #ffe6cc; color: #000000; }")
        self.buttonf3.clicked.connect(self.search_current_word)
        self.buttonf3.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonf3.setToolTip("F3")
        grid.addWidget(self.buttonf3, 3, 0)

        self.buttonf4 = QPushButton("Find Next")
        self.buttonf4.setStyleSheet("QPushButton { text-align: left; background-color: #ffe6cc; color: #000000; }")
        self.buttonf4.clicked.connect(self.repeat_find_forward)
        self.buttonf4.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonf4.setToolTip("F4")
        grid.addWidget(self.buttonf4, 3, 1)

        self.buttonf5 = QPushButton("Back")
        self.buttonf5.setStyleSheet("QPushButton { text-align: left; background-color: #b6d7b0; color: #000000; }")
        self.buttonf5.clicked.connect(self.history_back)
        self.buttonf5.setToolTip("F5")
        self.buttonf5.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.buttonf5, 3, 2)

        self.buttonf6 = QPushButton("Forward")
        self.buttonf6.setStyleSheet("QPushButton { text-align: left; background-color: #b6d7b0; color: #000000; }")
        self.buttonf6.clicked.connect(self.history_forward)
        self.buttonf6.setToolTip("F6")
        self.buttonf6.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.buttonf6, 3, 3)

        # Row 4: Book- (col 0), Book+ (col 1), Chapter- (col 2), Chapter+ (col 3)
        self.buttonf7 = QPushButton("Book-")
        self.buttonf7.setStyleSheet("QPushButton { text-align: left; background-color: #ffffcc; color: #000000; }")
        self.buttonf7.clicked.connect(self.earlier_book)
        self.buttonf7.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonf7.setToolTip("F7")
        grid.addWidget(self.buttonf7, 4, 0)

        self.buttonf8 = QPushButton("Book+")
        self.buttonf8.setStyleSheet("QPushButton { text-align: left; background-color: #ffffcc; color: #000000; }")
        self.buttonf8.clicked.connect(self.later_book)
        self.buttonf8.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonf8.setToolTip("F8")
        grid.addWidget(self.buttonf8, 4, 1)

        self.buttonf10 = QPushButton("Chapter-")
        self.buttonf10.setStyleSheet("QPushButton { text-align: left; background-color: #ffffcc; color: #000000; }")
        self.buttonf10.clicked.connect(self.earlier_chapter)
        self.buttonf10.setToolTip("F10")
        self.buttonf10.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.buttonf10, 4, 2)

        self.buttonf11 = QPushButton("Chapter+")
        self.buttonf11.setStyleSheet("QPushButton { text-align: left; background-color: #ffffcc; color: #000000; }")
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
            logger.debug("Could not create Ctrl+Shift+C commentary shortcut", exc_info=True)

        try:
            self._normalize_control_heights()
        except (RuntimeError, AttributeError, TypeError):
            logger.debug("Could not normalise control heights", exc_info=True)

    def _setup_other_works(self, grid: QGridLayout) -> None:
        self.other_works_combo = QComboBox()
        assert self.other_works_combo is not None
        self.other_works_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.other_works_combo.setStyleSheet("QComboBox { background-color: #ffe6ee; color: #000000; }")

        self.last_work_btn = QPushButton("Open Work")
        assert self.last_work_btn is not None
        self.last_work_btn.setStyleSheet("QPushButton { text-align: left; background-color: #ffe6ee; color: #000000; }")
        self.last_work_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.last_work_btn.setToolTip("Open the last read book (Ctrl+L)")
        self.last_work_btn.clicked.connect(self._select_last_other_work)  # type: ignore[attr-defined]

        self.search_work_btn = QPushButton("Search Work")
        assert self.search_work_btn is not None
        self.search_work_btn.setStyleSheet("QPushButton { text-align: left; background-color: #ffe6ee; color: #000000; }")
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
                self.other_works_combo.setCurrentText(str(last_work or ""))
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
            logger.debug("Could not create Ctrl+L last-work shortcut", exc_info=True)

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
            allowed: list[str] = []
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

    def build_show_works_menu(self, settings_menu) -> None:
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
            from PySide6.QtWidgets import QPushButton, QWidgetAction

            # Ensure we have a live map of checkboxes to update during bulk ops
            if not hasattr(self, "_works_menu_checkboxes") or not isinstance(self._works_menu_checkboxes, dict):
                self._works_menu_checkboxes = {}

            def _set_all_works(visible: bool) -> None:
                current_map = dict(self.settings.get("show_work") or {})
                val = "true" if visible else "false"
                # Use a distinct local name to avoid shadowing outer-scope variables
                for work_stem in self.other_works_map:
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
                    logger.debug("Failed to sync Other Works checkbox states", exc_info=True)
                # Persist and refresh combo
                if getattr(self, "settings_service", None):
                    self.settings_service.save(self.settings)
                self._refresh_other_works_combo()
                if getattr(self, "other_works_reference_index", None) is not None:
                    self.other_works_reference_index.rebuild()

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
            # If widget actions cannot be created, skip the bulk controls
            logger.debug("Could not build bulk Other Works menu controls", exc_info=True)

        show_map = dict(self.settings.get("show_work") or {})
        # Ensure keys exist for current files
        for stem in sorted(self.other_works_map.keys()):
            if stem not in show_map:
                show_map[stem] = "false"

        # Build checkable items that do NOT close the menu on toggle
        try:
            from PySide6.QtWidgets import QCheckBox, QWidgetAction

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
                        if getattr(self, "other_works_reference_index", None) is not None:
                            self.other_works_reference_index.rebuild()
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
                        if getattr(self, "other_works_reference_index", None) is not None:
                            self.other_works_reference_index.rebuild()
                    return _toggle

                act.toggled.connect(_make_toggler(stem))
                settings_menu.addAction(act)

    def eventFilter(self, source: QObject, event: QEvent) -> bool:
        """Custom event filter to handle key events on QLineEdit."""
        if source is None:
            return super().eventFilter(source, event)  # type: ignore[arg-type]

        if source == self.display_verse_input and event.type() == QEvent.Type.KeyPress and isinstance(event, QKeyEvent):
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

            elif event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):  # Handle Enter
                current_text = self.display_verse_input.text().strip()
                if current_text:
                    self.command_history.append(current_text)  # Add current text to history
                    self.history_index = -1  # Reset history index
                    self.goto_line()  # Trigger goto_line manually
                    self.display_verse_input.clear()  # Clear the input field after submission
                return True

        # Handle clicks inside the Bible text editor: when the user clicks
        # on any line, update the status bar to reflect the clicked verse.
        # Do not force any special scrolling; keep behaviour simple.
        # Use the module-level QMouseEvent imported at the top of this file.

        if (hasattr(self.textEditor, 'viewport') and
              source == self.textEditor.viewport() and
              event.type() == QEvent.Type.MouseButtonPress):
            # Only process mouse button presses
            try:
                if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
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
                            for delta in range(1, VERSE_LINE_SEARCH_RADIUS + 1):
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
                                logger.debug("Could not persist last clicked Bible position", exc_info=True)
                    except (RuntimeError, AttributeError, TypeError, ValueError):
                        logger.debug("Could not update status bar for clicked verse", exc_info=True)

                    # Do not consume the event so that the default text selection behaviour
                    # (click, drag to select, double-click to select a word)
                    # continues to work in the Bible view.
                    return False
            except (RuntimeError, AttributeError, TypeError, ValueError):
                # Fall through to default processing on any unexpected error
                logger.debug("Unexpected error handling editor mouse click", exc_info=True)

        # Pass the event to the parent class
        return super().eventFilter(source, event)  # type: ignore[arg-type]

    def _reposition_search_results_window(self) -> None:
        """Delegate to the Search Results window manager."""

        self.results_manager.reposition_search_results_window()

    def moveEvent(self, event):
        try:
            self._reposition_search_results_window()
        except (RuntimeError, AttributeError, TypeError):
            logger.debug("Could not reposition Search Results window on move", exc_info=True)
        try:
            return super().moveEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def resizeEvent(self, event):
        try:
            self._reposition_search_results_window()
        except (RuntimeError, AttributeError, TypeError):
            logger.debug("Could not reposition Search Results window on resize", exc_info=True)
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
            logger.debug("Could not persist last Bible position on close", exc_info=True)

        # Persist the Search Results window width and close it
        try:
            dock: Any = getattr(self, "search_results_window", None)
            if dock is not None:
                dock.save_width()
                dock.close()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            logger.debug("Could not save/close Search Results window on close", exc_info=True)

        try:
            concordance: Any = getattr(self, "concordance_window", None)
            if concordance is not None:
                concordance.close()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            logger.debug("Could not close concordance window on close", exc_info=True)

        try:
            references_window: Any = getattr(self, "other_works_references_window", None)
            if references_window is not None:
                references_window.close()
        except (AttributeError, RuntimeError, TypeError, ValueError):
            logger.debug("Could not close Other Works references window on close", exc_info=True)
        
        # Explicitly close secondary windows to ensure they trigger their own closeEvent/save logic
        try:
            gill: Any = getattr(self, "gill_win", None)
            if gill is not None:
                gill.close()
        except (RuntimeError, AttributeError):
            logger.debug("Could not close Gill commentary window on close", exc_info=True)
            
        try:
            reader: Any = getattr(self, "text_edit_window", None)
            if reader is not None:
                reader.close()
        except (RuntimeError, AttributeError):
            logger.debug("Could not close reader window on close", exc_info=True)
            
        try:
            secondary: Any = getattr(self, "secondary_window", None)
            if secondary is not None:
                secondary.close()
        except (RuntimeError, AttributeError):
            logger.debug("Could not close secondary window on close", exc_info=True)

        try:
            about: Any = getattr(self, "about_window", None)
            if about is not None:
                about.close()
        except (RuntimeError, AttributeError):
            logger.debug("Could not close about window on close", exc_info=True)

        try:
            find_dlg: Any = getattr(self, "dlg", None)
            if find_dlg is not None:
                find_dlg.close()
        except (RuntimeError, AttributeError):
            logger.debug("Could not close find dialog on close", exc_info=True)

        event.accept()

    def increase_font_size(self):
        current_size = self.settings_service.get_bible_font_size()
        new_size = min(current_size + 2, 72)  # Max size of 72
        self.settings_service.update_bible_font_size(new_size)
        self.apply_font_size()

    def decrease_font_size(self):
        current_size = self.settings_service.get_bible_font_size()
        new_size = max(current_size - 2, 8)  # Min size of 8
        self.settings_service.update_bible_font_size(new_size)
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
                    logger.debug("Could not propagate font size to reader window", exc_info=True)

            # 2. Gill Commentary Window
            gill = getattr(self, "gill_win", None)
            if gill:
                try:
                    g: Any = gill
                    # Check the current font size from the viewer
                    current_gill_font = g.viewer.font()
                    if current_gill_font.pointSize() != self.fontsize:
                        g.apply_font_size(self.fontsize)
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    logger.debug("Could not propagate font size to Gill commentary window", exc_info=True)

            # 3. Secondary (Devotional) Window
            secondary = getattr(self, "secondary_window", None)
            if secondary:
                try:
                    s: Any = secondary
                    if int(getattr(s, "fontsize", 0)) != self.fontsize:
                        s.fontsize = self.fontsize
                        s.update_font()
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    logger.debug("Could not propagate font size to secondary window", exc_info=True)

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
                self.open_text_file_in_window(path)

    @staticmethod
    def open_github_releases() -> None:
        """Open the GitHub releases page in the default web browser."""
        webbrowser.open("https://github.com/Abib-ops/Abib/releases")

    def open_text_file_in_window(self, path: str) -> None:
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
            from abib.ui.text_window import (
                TextDocumentWindow as ExternalTextDocumentWindow,
            )
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
                win._connected_to_main = True
            except (AttributeError, RuntimeError, TypeError):
                logger.debug("Could not connect reader referenceActivated signal", exc_info=True)
            # Apply the current theme to the new window and its editor
            try:
                win.apply_theme(self.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                logger.debug("Could not apply theme to new reader window", exc_info=True)
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
                if is_loading_file and current_stem and str(current_stem or "") == str(req_stem):
                    # Already loading this work; just bring it to the front and apply the theme
                    try:
                        win.apply_theme(self.theme.state.is_dark_mode)
                    except (RuntimeError, AttributeError):
                        logger.debug("Could not apply theme to loading reader window", exc_info=True)
                    self.theme.apply_widget(win)
                    win.show()
                    win.raise_()
                    win.activateWindow()
                    return
            except (AttributeError, RuntimeError, TypeError, ValueError, OSError):
                logger.debug("Could not fast-path an already-loading reader window", exc_info=True)
            # Guard: if the requested work is already loaded, avoid reloading
            try:
                current_stem = getattr(win, "current_file_stem", None)
            except (AttributeError, RuntimeError, TypeError):
                current_stem = None
            req_stem = Path(req_path).stem
            if current_stem and str(current_stem or "") == str(req_stem):
                # Already showing this work; just refresh the theme/palette and focus
                try:
                    win.apply_theme(self.theme.state.is_dark_mode)
                except (RuntimeError, AttributeError):
                    logger.debug("Could not refresh theme on existing reader window", exc_info=True)
                self.theme.apply_widget(win)
            else:
                win.load_text_file(req_path)
            # Ensure the signal is connected even if the window already existed
            try:
                if not getattr(win, "_connected_to_main", False):
                    win.referenceActivated.connect(self._on_reader_reference_activated)
                    win._connected_to_main = True
            except (AttributeError, RuntimeError, TypeError):
                logger.debug("Could not reconnect reader referenceActivated signal", exc_info=True)
            try:
                win.apply_theme(self.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                logger.debug("Could not apply theme to reused reader window", exc_info=True)
            self.theme.apply_widget(win)
            win_to_show = win
        win_to_show.show()
        win_to_show.raise_()
        win_to_show.activateWindow()
        # Connect visibility signal to toggle the Search button state and enable now
        try:
            if not getattr(win_to_show, "_display_signal_connected", False):
                win_to_show.displayedChanged.connect(self._on_reader_displayed_changed)
                win_to_show._display_signal_connected = True
        except (AttributeError, RuntimeError, TypeError):
            logger.debug("Could not connect reader displayedChanged signal", exc_info=True)
        self.update_other_works_search_button(True)

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
                logger.debug("Could not raise main window after reader navigation", exc_info=True)
        except (ValueError, TypeError, KeyError, IndexError, RuntimeError):
            # Be resilient: if parsing fails, do not propagate the error
            logger.debug("Could not navigate to reader-activated reference %r", ref, exc_info=True)

    def _on_reader_displayed_changed(self, visible: bool) -> None:
        """Enable/disable the Search button based on reader visibility."""
        self.update_other_works_search_button(bool(visible))

    def update_other_works_search_button(self, enabled: bool | None = None) -> None:
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
            logger.debug("Could not update Other Works search button state", exc_info=True)

    def _open_reader_search(self) -> None:
        """Open or focus the Search dialog for the Other Works reader window."""
        reader = getattr(self, "text_edit_window", None)
        if not reader:
            # No reader open; keep the button disabled just in case
            self.update_other_works_search_button(False)
            return
        try:
            win: Any = reader
            win.show_find_dialog()
            self.update_other_works_search_button(True)
        except (AttributeError, RuntimeError, TypeError):
            logger.debug("Could not open reader search dialog", exc_info=True)

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
                    logger.debug("Could not apply theme when reopening current Other Work", exc_info=True)
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
                    logger.debug("Could not persist last Other Work selection", exc_info=True)
                return
        except (AttributeError, RuntimeError, TypeError, ValueError, OSError):
            # If any attribute access fails, fall back to the normal open path
            logger.debug("Could not fast-path already-open Other Work; using normal path", exc_info=True)
        # Open/update the reader window
        self.open_text_file_in_window(path)
        # Persist last selected work in settings so the combo defaults next launch
        try:
            if isinstance(self.settings, dict):
                self.settings["last_other_work"] = stem
                # Save via settings service if available
                if getattr(self, "settings_service", None):
                    self.settings_service.save(self.settings)
        except (OSError, TypeError, ValueError, RuntimeError):
            # Be tolerant: failure to persist should not break the opening
            logger.debug("Could not persist last Other Work selection", exc_info=True)

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
            idx = self.other_works_combo.findText(str(last_work or ""))
            if idx < 0:
                return

            # If it's already selected, Qt won't emit signals; open explicitly
            if self.other_works_combo.currentIndex() == idx:
                self._open_other_work(str(last_work or ""))
                return

            # Otherwise, switch selection without emitting signals twice, then open explicitly
            try:
                self.other_works_combo.blockSignals(True)
                self.other_works_combo.setCurrentIndex(idx)
            finally:
                try:
                    self.other_works_combo.blockSignals(False)
                except (RuntimeError, AttributeError, TypeError):
                    logger.debug("Could not re-enable Other Works combo signals", exc_info=True)
            # Ensure the reader opens even if a platform doesn't emit currentTextChanged
            self._open_other_work(str(last_work or ""))
        except (RuntimeError, AttributeError, KeyError, TypeError, ValueError):
            logger.debug("Could not select/open the last Other Work", exc_info=True)

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
        self.open_text_file_in_window(help_path)

    def copyright(self) -> None:
        """Open the Licence in a separate window."""
        copying_path = str(Path(sh.current_directory / 'COPYING'))
        self.open_text_file_in_window(copying_path)

    def readme(self) -> None:
        """Open the Readme file in a separate window."""
        readme_path = str(Path(sh.current_directory / 'README.txt'))
        self.open_text_file_in_window(readme_path)

    def reload(self) -> None:
        """Reload KJB_PCE.txt"""

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self

        if win.otherFileFlag:
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
                logger.debug("Could not restore geometry when reloading the Bible view", exc_info=True)
            # Signal to Back handler that we just restored the Bible view, 
            # so the very next Back press should be ignored to preserve
            # the restored verse position.
            try:
                self._just_restored_from_aux = True
            except (AttributeError, RuntimeError):
                logger.debug("Could not set the just-restored-from-aux flag", exc_info=True)

    # ENTRY POINT FOR F3 FIND.
    # Create a slot for launching the find dialog box.

    def on_find_button_clicked(self) -> None:
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

    def make_key_whole(self, _key: str, _dict: dict, _set: dict[str, set]) -> tuple[int, str]:
        """Delegate to the search engine."""

        return search_service.make_key_whole(self, _key, _dict, _set)

    def prepare_key_for_find(self) -> None:
        """Delegate to the search engine."""

        search_service.prepare_key_for_find(self)

    def find_in_range(self, x_start: int, x_end: int) -> None:
        """Find function."""

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self

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
                self.iterate_regex(search_service.get_search_data().Rnew, x1, x2)
                if win.occurring != 0:
                    win.y = win.occur[0][0][0]
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
                    current_position = self.find_whole_word(x1, x2)
                elif tv:
                    # Raw.
                    current_position = self.find_raw(current_position, x1, x2, keylow)

        if win.occurring == 0:
            current_position = savedx
            self.on_error('Not found...', 2000, True)
            error_flag = True

        if win.key in ('q', 'Q'):
            self.display_verse_input.clear()
            sys.exit()
        if not error_flag:
            self.goto_line_find(current_position)
        self._update_search_results_panel()

    def iterate_regex(self, r: tuple, x1: int, x2: int) -> None:
        """Delegate to the search engine."""

        search_service.iterate_regex(self, r, x1, x2)

    def find_raw(self, current_position: int, x1: int, x2: int, keylow: str) -> int:
        """Delegate to the search engine."""

        return search_service.find_raw(self, current_position, x1, x2, keylow)

    def assign_values(self) -> Any:
        """Delegate to the search engine."""

        return search_service.assign_values(self)

    def find_whole_word(self, x1: int, x2: int) -> int:
        """Delegate to the search engine."""

        return search_service.find_whole_word(self, x1, x2)

    def find_whole_word_single(self, x1: int, x2: int, _set: dict[str, set], r_list: list) -> None:
        """Delegate to the search engine."""

        search_service.find_whole_word_single(self, x1, x2, _set, r_list)

    def occurrent(self, x1: int, x2: int) -> int:
        """Delegate to the search engine."""

        return search_service.occurrent(self, x1, x2)

    def find_f4(self) -> None:
        """Repeat find frontend for raw search."""

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self

        if win.occurrence < win.occurring:
            current_position = self.get_line_number()

            if forward:
                history.back_push(self, current_position)
                while forward:
                    b_ = forward.pop()
                    back.append(b_)
            else:
                forward.clear()
                history.back_push(self, current_position)

            # Ensure self.gent is a valid generator
            gent = self.gent
            if gent is None:
                raise ValueError(
                    "self.gent has not been initialized. It must be assigned a valid generator before calling find_f4.")

            try:
                current_position, win.y, win.occurrence = next(gent)
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
        win: Any = self

        if len(win.occurs) > 0 and win.occurrence < win.occurring:
            current_position = self.get_line_number()
            if forward:
                history.back_push(self, current_position)
                while forward:
                    b_ = forward.pop()
                    back.append(b_)
            else:
                forward.clear()
                history.back_push(self, current_position)

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
        """Delegate to the search engine."""

        return search_service.gen(self, key, x1, x2)

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
        win: Any = self

        add: int
        if '¶ ' in KJV[ln] and truth is True:
            win.y += 2
            end = win.y
        search_data = search_service.get_search_data()
        if self.dlg.checks[1] == 0:
            add = fcs.repeat_find(search_data.Rlow[current_position], start, end)
        else:
            add = fcs.repeat_find(search_data.Rnew[current_position], start, end)
        return add

    def stripped_punctuation_adjust_ki(self, current_position: int, start: int, end: int) -> int:
        """Addition for 'Whole words only'.

        This adjustment allows for no punctuation in the stripped search text.
        """

        add: int
        search_data = search_service.get_search_data()
        if self.dlg.checks[1] == 0:
            add = fcs.repeat_find_keyinc(search_data.Rlow[current_position], start, end)
        else:
            add = fcs.repeat_find_keyinc(search_data.Rnew[current_position], start, end)

        return add

    def adjust_highlighting(self, ln: int, _x: int) -> None:
        """Adjust highlighting for longer length Unicode characters."""

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self

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
        win: Any = self

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
        win: Any = self

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
            logger.debug("Could not persist last Bible position", exc_info=True)

    def move_to_line(self, ln: int) -> None:
        """Display engine."""

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self

        self.textEditor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.on_text_changed(ln)
        ln = make_offset(ln)
        linecursor = QTextCursor(
            self.textEditor.document().findBlockByLineNumber(ln))
        self.textEditor.moveCursor(QTextCursor.MoveOperation.End)
        self.textEditor.setTextCursor(linecursor)
        self.textEditor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        if self.dlg is not None and (self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4):
            win.key = win.store

    def on_text_changed(self, ln: int) -> None:
        """Highlighting."""

        fmt = QTextCharFormat()
        assert linehighlightcolor is not None
        assert linetextcolor is not None
        fmt.setBackground(QColor(linehighlightcolor))
        fmt.setForeground(QColor(linetextcolor))

        win: Any = self

        win.hiLita.clear = True
        win.hiLita.clear_highlight()
        should_highlight = True

        try:
            if self.dlg is not None and (self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4):
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
            logger.debug("Could not compute multi-highlight for line %r", ln, exc_info=True)

    def display_verse_from_history(self, current_position: int) -> None:
        """Display Bible text in textEditor after a back or forward pop."""

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self

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
                logger.debug("Could not resync search state from history", exc_info=True)
        elif (self.dlg is not None and self.dlg.checks[0] in (1, 2)
              and self.dlg.checks[2] != 6 and current_position in win.occurs):
            # Single-highlight search modes (Raw / Whole words) store match
            # positions as search-text indices. When a result is reached via the
            # results panel or history navigation, recompute the display-text
            # highlight offsets for the current win.y, mirroring the find path
            # (goto_line_find -> adjust_highlighting). Without this the highlight
            # reuses stale lineinc/keyinc and starts at the wrong character.
            self.adjust_highlighting(ln, current_position)

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
            logger.debug("Could not persist last Bible position", exc_info=True)

    def ref_to_statusbar(self, current_position: int) -> None:
        """Display messages in the status bar."""

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self

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
                logger.debug("Could not show commentary database-not-found warning", exc_info=True)
            return

        try:
            current_position = int(self.get_line_number())
        except (RuntimeError, AttributeError, TypeError, ValueError):
            try:
                current_position = int(self._last_bible_position)
            except (AttributeError, TypeError, ValueError):
                current_position = 0
        current_position = max(current_position, 0)
        current_position = min(current_position, sh.LAST_VERSE_IN_BIBLE)
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
        if self.gill_win is None:
            try:
                # Create as a true top-level window (no parent) so it can be viewed independently
                # Share the same settings service to avoid cache divergence
                self.gill_win = GillCommentaryWindow(db_path=db_path, parent=None, settings_service=self.settings_service)
            except (RuntimeError, TypeError, sqlite3.Error) as exc:
                try:
                    QMessageBox.critical(self, "Commentary", f"Unable to open commentary window.\n{exc}")
                except (RuntimeError, TypeError):
                    logger.debug("Could not show commentary open-failure dialog", exc_info=True)
                self.gill_win = None
                return

        # Update content and show the window
        try:
            # Use (book, chapter, fromverse) lookups per current DB access strategy
            if isinstance(self.gill_win, GillCommentaryWindow):
                self.gill_win.set_reference(b, c, v)
                # Apply the current theme
                try:
                    self.gill_win.apply_theme(self.theme.state.is_dark_mode)
                    self.theme.apply_widget(self.gill_win)
                except (RuntimeError, AttributeError):
                    logger.debug("Could not apply theme to commentary window", exc_info=True)
        except (AttributeError, TypeError, ValueError):
            logger.debug("Could not set commentary reference", exc_info=True)
        try:
            assert self.gill_win is not None
            self.gill_win.show()
            self.gill_win.raise_()
            self.gill_win.activateWindow()
        except (RuntimeError, AttributeError, TypeError, AssertionError):
            logger.debug("Could not show/raise commentary window", exc_info=True)

    # Auto-follow toggle removed from MainWindow.

    # ENTRY POINT FOR F2 DISPLAY VERSE.
    def goto_line(self, ref: str = '') -> None:
        """Move the display to the line requested."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = self.get_line_number()
        forward.clear()
        history.back_push(self, current_position)
        reset_attributes()
        if not ref:
            ref = self.display_verse_input.text()
        ref = fcs.remove_junk(ref)
        if ref in ('q', 'Q'):
            self.display_verse_input.clear()
            sys.exit()

        current_position = self.reference_to_line_number(ref)
        if current_position == -1:
            self.display_verse_input.clear()
        else:
            current_position = max(current_position, 0)
            current_position = min(current_position, sh.LAST_VERSE_IN_BIBLE)
            self.display_verse(current_position)

    def  goto_book(self, _index: int) -> None:
        """Move the display to the line requested by comboBox_1."""

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position = self.get_line_number()
        forward.clear()
        history.back_push(self, current_position)
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
        current_position = self.reference_to_line_number(ref, book)
        current_position = max(current_position, 0)
        current_position = min(current_position, sh.LAST_VERSE_IN_BIBLE)
        self.display_verse(current_position)
        self.goto_chapter(_index)

    def goto_chapter(self, _index: int) -> None:
        """Move the display to the line requested by comboBox_2."""

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = self.get_line_number()
        forward.clear()
        history.back_push(self, current_position)
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
        ref = f"{ref} {chapter + 1!s}"

        current_position = self.reference_to_line_number(ref, book, chapter)
        current_position = max(current_position, 0)
        current_position = min(current_position, sh.LAST_VERSE_IN_BIBLE)
        self.display_verse(current_position)

    def goto_verse(self, _index: int) -> None:
        """Move the display to the line requested by comboBox_3."""

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = self.get_line_number()
        forward.clear()
        history.back_push(self, current_position)
        reset_attributes()
        book: int = self.comboBox_1.currentIndex()
        chapter: int = self.comboBox_2.currentIndex()
        verse: int = self.comboBox_3.currentIndex()

        ref = win.nwin[book]
        ref = ref.replace(' ', '')
        ref = f"{ref} {chapter + 1!s}.{verse + 1}"
        current_position = self.reference_to_line_number(ref, book, chapter)
        current_position = max(current_position, 0)
        current_position = min(current_position, sh.LAST_VERSE_IN_BIBLE)
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

        inf: list = sh.Info[current_line]
        current_chapter: int = inf[1]
        current_verse = inf[2]

        if new_verse >= 0:
            new_line: int = current_line - current_verse + new_verse
        else:
            new_line = current_line + new_verse + 1
            new_verse = current_verse + new_verse + 1

        message = f"Out of bounds. No verse {new_verse + 1} here!"
        try:
            new_chapter: int = sh.Info[new_line][1]
        except IndexError:
            win.on_error(message, 750, True)
            return_value = current_line
        else:
            if new_chapter != current_chapter:
                win.on_error(message, 750, True)
                return_value = current_line
            else:
                return_value = new_line

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

    def error_invalid_verse_or_position(self):
        """Handle invalid chapter/verse errors."""

        message: str = "Invalid chapter or verse."
        self.on_error(message, 750, True)

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
        win: Any = self

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
            Qt.Key.Key_C: self.commentary_key,
            Qt.Key.Key_Question: self.feature,
            Qt.Key.Key_F12: self.show_devotional,
            Qt.Key.Key_Q: sys.exit}

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
        history.back_push(self, current_position)
        self.on_find_button_clicked()

    def repeat_find_forward(self) -> None:
        """Find the next key F4."""

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self

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
        self.message = ''
        if len(back) > 0:
            current_position: int = self.get_line_number()
            history.forward_push(self, current_position)
            current_position = history.back_pop(self)
            self.display_verse_from_history(current_position)

    def history_forward(self) -> None:
        """Forward key."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        if len(forward) > 0:
            current_position: int = self.get_line_number()
            history.back_push(self, current_position)
            current_position = history.forward_pop(self)
            self.display_verse_from_history(current_position)

    def open_commentary_window_shortcut(self) -> None:
        """F9 Fullscreen toggle key."""

        self.toggle_fullscreen()

    def show_devotional(self) -> None:
        """F12 Devotional key."""

        self.display_secondary_window()

    @staticmethod
    def commentary_key() -> None:
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
            history.back_push(self, current_position)
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
            history.back_push(self, current_position)
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
        history.back_push(self, old_position)
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
        history.back_push(self, old_position)
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
            self.message = ''

    def beep(self, current_position: int, lm: float) -> None:
        """Makes a beep sound and clears the message."""

        # Play error sound via audio service (non-blocking and safe)
        self.audio.play_error()

        self.statusBar.repaint()

        # Delay for 'lm' second.
        time.sleep(lm)

        self.message = ''
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
        win: Any = self

        if path1:
            pass
        else:
            path1, _ = QFileDialog.getOpenFileName(
                self, "Open file", "",
                "Text documents (*.txt);All files (*.*)")
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
                                sys.exit()
                            start_idx = loc + len(EOTNOC) + 1
                            text_data = original[start_idx:]
                            # Best-effort cache write (do not fail to open if this causes an error)
                            try:
                                with cache.open("w", encoding="utf-8", buffering=(1 << 20)) as f_out:
                                    assert text_data is not None
                                    f_out.write(text_data)
                            except (OSError, PermissionError):
                                logger.debug("Could not write stripped Bible cache", exc_info=True)
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
                if prev_is_bible and str(Path(path1).name) != "KJB_PCE.txt":
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
                        logger.debug("Could not disable undo/redo before text load", exc_info=True)
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
                        logger.debug("Could not re-enable undo/redo after text load", exc_info=True)
                    try:
                        self.textEditor.setUpdatesEnabled(True)
                    except (RuntimeError, AttributeError):
                        logger.debug("Could not re-enable editor updates after text load", exc_info=True)
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
                    last_pos = max(last_pos, 0)
                    last_pos = min(last_pos, sh.LAST_VERSE_IN_BIBLE)
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
                        # Highlighting state is non-critical for auxiliary files
                        logger.debug("Could not clear highlighting for auxiliary file", exc_info=True)

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
        """Delegate to the theming controller."""

        self.theme_ctrl.refresh_theme_across_ui()

    def _normalize_control_heights(self) -> None:
        """Delegate to the theming controller."""

        self.theme_ctrl.normalize_control_heights()

    def set_theme(self, the_settings):
        """Delegate to the theming controller."""

        self.theme_ctrl.set_theme(the_settings)

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
            from abib.ui.windows import (
                SecondaryWindow as ExtSecondaryWindow,  # deferred import
            )
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
                # Navigation failed; still show the devotional text
                logger.debug("Could not navigate to devotional reference %r", sme_ref, exc_info=True)
        return sme_text

    def toggle_dark_mode(self):
        """Delegate to the theming controller."""

        self.theme_ctrl.toggle_dark_mode()

    def update_text_display_theme(self) -> None:
        """Delegate to the theming controller."""

        self.theme_ctrl.update_text_display_theme()
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ End of MainWindow class ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~




if __name__ == '__main__':
    # Bootstrap moved to app.run() for cleaner modularisation (PR10)
    try:
        from abib.app import run
    except ImportError:
        from app import run
    run()
