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

"""
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

Using PySide6-6.10.2 and python3.14.3 (64-bit).

04/02/2026

1) python -m pip install --upgrade pip wheel
2) python -m pip install -r requirements.txt
----------------------------------------------------------------------------------------------------------------
Linux users — a sincere apology and quick guidance
We’re sorry: Abib is currently Windows‑centric, and our small team hasn’t kept multi‑platform support up to date.
We appreciate your patience, and we welcome improvements from Linux contributors.

Quick start on Linux (unofficial)
•
Ensure the version of Python is between 3.10 and 3.12.
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
import time
from sys import exit, setrecursionlimit
setrecursionlimit(200)

from copy import deepcopy
from pathlib import Path
from itertools import islice

from typing import Any, Dict, Set, List
from history import History
history = History()
back = history.back
forward = history.forward

# Global window 'handle' placeholder; set by app.run() at startup
w: Any | None = None
# Global splash screen reference (kept alive until the user disables it in settings)
splash: Any | None = None

from PySide6.QtWidgets import (QMainWindow, QWidget,
                               QPlainTextEdit, QTextEdit, QLineEdit, QComboBox, QGridLayout, QMessageBox,
                               QPushButton, QVBoxLayout, QStatusBar, QFileDialog, QSplashScreen, QSizePolicy)

from PySide6.QtGui import (QMouseEvent, QKeyEvent, QWheelEvent, QSyntaxHighlighter, QColor, QFont,
                           QTextCursor, QTextCharFormat, QPixmap, QKeySequence, QShortcut)

from PySide6.QtCore import Qt, QRect, QEvent

import fcs
import sqlite3
import shared as sh

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
#     print("Junie Status: PyTorch not found. AI features disabled.")

from ui_helpers import NoZoomPlainTextEdit, SimpleScripturePopup
from services.settings import SettingsService
## Step 5: Reduce import and initialisation cost
# Defer heavy/optional imports to first use instead of module import time.
# - windows.* (secondary/about windows)
# - find_dialog.FindDialog
# - settings_dialog.SettingsDialog
# - ui.themes.ThemeManager/ThemeState
# - ui.actions (setup_shortcuts, setup_menus_and_toolbars)
# - text_window.ExternalTextDocumentWindow
# - domain.scripture_refs (resolve_reference, calculate_book_line)

# Lazy wrappers for scripture reference helpers to avoid importing the module at startup
_scripture_refs_cache: dict[str, Any] | None = None

def parse_ref(bits: Any) -> Any:
    """Lazy wrapper for domain.scripture_refs.resolve_reference."""
    global _scripture_refs_cache
    if _scripture_refs_cache is None:
        from domain import scripture_refs as _sr  # local import
        _scripture_refs_cache = {
            "resolve_reference": _sr.resolve_reference,
            "calculate_book_line": _sr.calculate_book_line,
        }
    return _scripture_refs_cache["resolve_reference"](bits)


def calc_line(book_num: int, chapter: int, verse: int, current_line: int) -> int:
    """Lazy wrapper for domain.scripture_refs.calculate_book_line."""
    global _scripture_refs_cache
    if _scripture_refs_cache is None:
        from domain import scripture_refs as _sr  # local import
        _scripture_refs_cache = {
            "resolve_reference": _sr.resolve_reference,
            "calculate_book_line": _sr.calculate_book_line,
        }
    return _scripture_refs_cache["calculate_book_line"](book_num, chapter, verse, current_line)

# ---- Module-level placeholders (populated at runtime by app.run) ----
# These keep static analysis quiet and preserve runtime assignment from app.py
KJV: tuple | list = ()
Amap: list = []
Ps119: list[int] = []
P119: list = []
book_bounds: list[int] = []
starts_with_italics: list[int] = []
KJB_PCE_LASTLINE: int = 0
EOTNOC: str = ""
Rnew: tuple = ()
Rdic: dict = {}
Rlow: tuple = ()
Ldic: dict = {}
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
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except (AttributeError, OSError) as e:
    # AttributeError: non-Windows (windll is None); OSError: Windows API failure
    print(f"Error setting APP ID: {e}")






def prep_statusbar_message(index: int):
    """Prepare the statusbar message."""

    book = sh.Info[index][0]
    chapter = sh.Info[index][1] + 1
    occurrence = sh.Info[index][2] + 1
    book_name = w.nwin[book]

    if w.occurrence == w.occurring:
        end_message = "."
        w.no_f3_yet = 0
    else:
        end_message = '...'

    ye = f'Occurrence {w.occurrence}/{w.occurring} of "{w.keym}"'

    if book in sh.onechapterbooks:
        w.message = f'{ye}  -  {book_name} {occurrence} KJV{end_message}'
    else:
        w.message = f'{ye}  -  {book_name} {chapter}:{occurrence} KJV{end_message}'


def occurrent1() -> int:
    """Count occurrence(s) of w.key and give current_position and w.y values.

    w.occurs is a list of all the current_position values in the search results.
    w.occur is a corresponding list which gives the start w.y and finish w.yend of
    the searched for item in the particular verse.
    w.occurring is the total number of times the search key was found.
    w.verse is the number of the items in the search list.
    len(w.occur[w.verse]) is the number of search results in a particular verse.
    w.finding is the number of items found within the verse.
    """

    current_position = w.occurs[-1]  # Workaround for PyCharm linter.

    if w.verse < len(w.occurs):
        w.finding += 1
        current_position = w.occurs[w.verse]  # Aligns with w.occur(w.verse)
        if w.finding + 1 <= len(w.occur[w.verse]):
            w.y = w.occur[w.verse][w.finding][0]
            w.yend = w.occur[w.verse][w.finding][1]
            w.occurrence += 1
            prep_statusbar_message(current_position)
        elif w.verse + 1 < len(w.occurs):
            w.verse += 1
            w.finding = 0
            w.y = w.occur[w.verse][w.finding][0]
            w.yend = w.occur[w.verse][w.finding][1]
            w.occurrence += 1
            current_position = w.occurs[w.verse]
            prep_statusbar_message(current_position)
    elif w.verse >= len(w.occurs):
        current_position = w.occurs[-1]  # Last item

    # print(f'len(w.occurs = {len(w.occurs)})')
    # print(f'w.occurring = {w.occurring}')

    return current_position


def findf3_ww_any(x1: int, x2: int, _set: Dict[str, Set], r_list: list, win: 'MainWindow') -> None:
    """Match any word."""

    from services.search_service import findf3_ww_any as _find_any
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
    # w.gent = None
    w.y = 0
    w.hiLita.lineinc = 0
    w.hiLita.keyinc = 0
    w.occurring = 0
    w.occurrence = 0
    w.key = ' '
    w.message = ''
    if w.dlg is not None:
        w.dlg.checks = [1, 0, 5]  # Is this really necessary?
    w.occurs = []
    w.occur = []


def centerer(widt: int, heigh: int) -> tuple:
    """Provide central screen origin points for windows"""

    w_origin = int(half_width - (widt / 2))
    h_origin = int(half_height - (heigh / 2))

    return w_origin, h_origin


def format_status_message(q1, q2, q3):
    """Helper to format a message based on conditions."""

    q4 = w.nwin[q1]
    if q1 in sh.onechapterbooks:
        return f"{q4} {q3} KJV"
    return f"{q4} {q2}:{q3} KJV"


def sizer(window_height: int, window_width: int) -> tuple[int, int]:
    """Adjust window size to fit the screen."""

    if window_height > height:
        window_height = int(height * 0.95)
    if window_width > width:
        window_width = int(width * 0.95)

    return window_height, window_width


class GillCommentaryWindow(QWidget):
    """A simple verse-by-verse commentary reader for John Gill.

    Uses SQLite file (gill.cmt.sqlite) with table 'commentary' columns:
    1:id, 2:book, 3:chapter, 4:fromverse, 5:toverse, 6:data
    Lookup now uses (book, chapter, fromverse) — no reliance on the global id.
    """
    def __init__(self, db_path: Path, parent: QWidget | None = None, settings_service: SettingsService | None = None) -> None:
        # Force this widget to be a top-level window regardless of parent
        super().__init__(parent if parent is None else None)
        self._db_path = Path(db_path)
        self._conn: sqlite3.Connection | None = None
        # Current global verse index within Abib (0 to LAST_VERSE_IN_BIBLE)
        self._x: int = 0
        # Settings service for persisting geometry and font
        self._settings_service = settings_service if settings_service is not None else SettingsService()

        self.setWindowTitle("Gill Commentary")
        try:
            # Ensure it is a standalone window (not embedded in MainWindow)
            self.setWindowFlag(Qt.WindowType.Window, True)
        except (RuntimeError, AttributeError, TypeError):
            pass

        # Restore saved geometry (position and size)
        try:
            gx, gy, gw, gh = self._settings_service.get_window_geometry("gill_commentary_window")
            self.setGeometry(gx, gy, gw, gh)
        except (RuntimeError, TypeError, ValueError):
            # Fall back to a reasonable default size
            try:
                self.resize(820, 640)
            except (RuntimeError, TypeError, ValueError):
                pass

        layout = QGridLayout(self)
        # Switch to a rich-text capable viewer so we can render HTML from the DB
        self.viewer = QTextEdit(self)
        self.viewer.setReadOnly(True)
        # Force a left-to-right layout to avoid right-justified paragraphs due to RTL fragments
        try:
            self.viewer.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except (AttributeError, RuntimeError, TypeError):
            pass
        # Improve interaction: allow selecting text; do NOT make links clickable
        try:
            flags = self.viewer.textInteractionFlags()
            # Enable selection by mouse and keyboard
            flags |= Qt.TextInteractionFlag.TextSelectableByMouse
            flags |= Qt.TextInteractionFlag.TextSelectableByKeyboard
            # Ensure link-clicking is disabled
            try:
                flags &= ~Qt.TextInteractionFlag.LinksAccessibleByMouse
            except (AttributeError, TypeError):
                pass
            try:
                flags &= ~Qt.TextInteractionFlag.LinksAccessibleByKeyboard
            except (AttributeError, TypeError):
                pass
            self.viewer.setTextInteractionFlags(flags)
        except (AttributeError, TypeError, RuntimeError):
            pass
        # Apply the same font as the main Bible window, if available
        try:
            if hasattr(w, "textEditor") and getattr(w, "textEditor", None) is not None:
                self.viewer.setFont(w.textEditor.font())
                # Also, enforce as the document default so HTML respects app font
                try:
                    self.viewer.document().setDefaultFont(self.viewer.font())
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    pass
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        layout.addWidget(self.viewer, 0, 0, 1, 3)

        self.btn_prev = QPushButton("◀ Prev", self)
        self.btn_next = QPushButton("Next ▶", self)
        self.btn_close = QPushButton("Close", self)
        self.btn_prev.clicked.connect(self._on_prev)
        self.btn_next.clicked.connect(self._on_next)
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_prev, 1, 0)
        layout.addWidget(self.btn_close, 1, 1)
        layout.addWidget(self.btn_next, 1, 2)

        # Set the initial the font size from settings and apply as both widget and document font
        try:
            fs = int(self._settings_service.get_commentary_font_size())
            if fs < 8:
                fs = 8
            if fs > 40:
                fs = 40
            fnt = self.viewer.font()
            if hasattr(fnt, "setPointSize"):
                fnt.setPointSize(fs)
                self.viewer.setFont(fnt)
                try:
                    self.viewer.document().setDefaultFont(fnt)
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    pass
                # Provide a gentle default stylesheet so legacy <FONT> tags don't override too much
                try:
                    css = (
                        "body, p, div { "
                        f"font-family: '{fnt.family()}'; "
                        f"font-size: {fnt.pointSize()}pt; "
                        "text-align: left; direction: ltr; }"
                        "a.bible { color: #2160FF; text-decoration: underline; }"
                        "a.bible:hover { background-color: #fff1b8; }"
                    )
                    self.viewer.document().setDefaultStyleSheet(css)
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    pass
        except (TypeError, ValueError):
            pass

        # Keyboard shortcuts for zooming (Ctrl++ / Ctrl+= / Ctrl+-)
        self._shortcuts: list[QShortcut] = []
        try:
            sc_inc1 = QShortcut(QKeySequence("Ctrl++"), self)
            sc_inc1.activated.connect(self.increase_font_size)
            self._shortcuts.append(sc_inc1)
            sc_inc2 = QShortcut(QKeySequence("Ctrl+="), self)
            sc_inc2.activated.connect(self.increase_font_size)
            self._shortcuts.append(sc_inc2)
            sc_dec = QShortcut(QKeySequence("Ctrl+-"), self)
            sc_dec.activated.connect(self.decrease_font_size)
            self._shortcuts.append(sc_dec)
        except (RuntimeError, TypeError, ValueError):
            pass

        # --- Scripture reference hover popup support ---
        self._hover_timer = None
        self._pending_hover_pos = None
        # Hover timing control (load from settings)
        try:
            self._hover_delay_ms: int = int(self._settings_service.get_gill_hover_delay_ms())
        except (RuntimeError, AttributeError, TypeError, ValueError):
            self._hover_delay_ms = 120
        try:
            self._hide_delay_ms: int = int(self._settings_service.get_gill_hide_delay_ms())
        except (RuntimeError, AttributeError, TypeError, ValueError):
            self._hide_delay_ms = 160
        # Master toggle for popups
        try:
            self._popups_enabled: bool = bool(self._settings_service.get_gill_show_popups())
        except (RuntimeError, AttributeError, TypeError, ValueError):
            self._popups_enabled = True
        # Track current hovered href to prevent blinking when the cursor jiggles
        self._current_href: str | None = None
        # Shared tooltip helper
        self._popup_helper: SimpleScripturePopup | None = SimpleScripturePopup()
        self._is_dark: bool = False
        # Debounced hide timer for popup
        try:
            from PySide6.QtCore import QTimer as _QTimer
            self._hide_timer = _QTimer(self)
            self._hide_timer.setSingleShot(True)
            self._hide_timer.setInterval(self._hide_delay_ms)
            self._hide_timer.timeout.connect(self._close_popup)
        except (RuntimeError, AttributeError, TypeError, ImportError):
            self._hide_timer = None
        try:
            # Enable mouse tracking to get hover events
            self.viewer.setMouseTracking(True)
            self.viewer.viewport().setMouseTracking(True)
            self.viewer.viewport().installEventFilter(self)
            # Also, filter key events in the editor itself
            self.viewer.installEventFilter(self)
            # Mark interaction while dragging the scrollbar
            try:
                sb = self.viewer.verticalScrollBar()
                if sb is not None:
                    sb.sliderPressed.connect(self._mark_user_interaction)  # type: ignore[attr-defined]
                    sb.sliderMoved.connect(self._mark_user_interaction)    # type: ignore[attr-defined]
                    sb.sliderReleased.connect(self._mark_user_interaction) # type: ignore[attr-defined]
            except (RuntimeError, AttributeError, TypeError):
                pass
        except (RuntimeError, AttributeError):
            pass

        # (Ctrl-freeze disabled)

        # Click-to-navigate (default on)
        self._click_to_navigate: bool = True
        # Auto-follow feature removed. Keep harmless interaction fields for compatibility.
        self._interacting_until: float = 0.0
        self._interaction_quiet_ms: int = 1200
        # Small per-window cache for href → resolved verse text to avoid repeat work while hovering
        self._ref_cache: dict[str, str] = {}
        # (Auto-follow initialisation removed)

    def apply_theme(self, is_dark: bool) -> None:
        """Update the viewer colours and internal popup helper to match the theme."""
        self._is_dark = is_dark
        try:
            if is_dark:
                # Use identical dark styles as ThemeManager for QPlainTextEdit/QTextEdit
                self.viewer.setStyleSheet("QTextEdit { background-color: #121212; color: #ffffff; }")
            else:
                self.viewer.setStyleSheet("QTextEdit { background-color: #ffffff; color: #000000; }")
        except (RuntimeError, AttributeError):
            pass
        
        # Ensure the popup helper matches the new theme if it exists
        if self._popup_helper is not None:
            try:
                self._popup_helper.apply_theme(is_dark)
            except (RuntimeError, AttributeError):
                pass

    # --------- DB helpers ---------
    def _ensure_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self._db_path))
        return self._conn

    def closeEvent(self, event):  # type: ignore[override]
        # Safety: stop timers and hide popup to prevent stray callbacks after the window closes
        try:
            self._cancel_hover()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            if self._hide_timer is not None:
                self._hide_timer.stop()
        except (RuntimeError, AttributeError):
            pass
        try:
            if self._hover_timer is not None:
                self._hover_timer.stop()
        except (RuntimeError, AttributeError):
            pass
        try:
            self._close_popup()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            if self._conn is not None:
                self._conn.close()
        except sqlite3.Error:
            pass
        # Persist final geometry on close
        try:
            geom = self.geometry()
            self._settings_service.save_window_geometry(
                "gill_commentary_window", int(geom.x()), int(geom.y()), int(geom.width()), int(geom.height())
            )
        except (RuntimeError, TypeError, ValueError):
            pass
        self._conn = None
        super().closeEvent(event)

    # Persist geometry on move/resize
    def moveEvent(self, event):  # type: ignore[override]
        try:
            geom = self.geometry()
            self._settings_service.save_window_geometry(
                "gill_commentary_window", int(geom.x()), int(geom.y()), int(geom.width()), int(geom.height())
            )
        except (RuntimeError, TypeError, ValueError):
            pass
        try:
            return super().moveEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def resizeEvent(self, event):  # type: ignore[override]
        try:
            geom = self.geometry()
            self._settings_service.save_window_geometry(
                "gill_commentary_window", int(geom.x()), int(geom.y()), int(geom.width()), int(geom.height())
            )
        except (RuntimeError, TypeError, ValueError):
            pass
        try:
            return super().resizeEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def showEvent(self, event):  # type: ignore[override]
        try:
            return super().showEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def hideEvent(self, event):  # type: ignore[override]
        try:
            return super().hideEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    # --------- Public API ---------
    def set_reference(self, book: int, chapter: int, verse: int) -> None:
        """Compatibility wrapper: set by the 1-based (book, chapter, verse)."""
        try:
            # Use fast O(1) lookup via calc_line
            x = calc_line(book, chapter, verse, 0)
        except (TypeError, ValueError):
            x = 0
        self.set_position(x)

    def set_position(self, x: int) -> None:
        """Set the current global verse index and display its commentary."""
        try:
            x = int(x)
        except (TypeError, ValueError):
            x = 1
        if x < 0:
            x = 0
        if x > sh.LAST_VERSE_IN_BIBLE:
            x = sh.LAST_VERSE_IN_BIBLE
        self._x = x
        self._display_current()

    # --------- Navigation ---------
    def _on_prev(self) -> None:
        if self._x <= 0:
            return
        self._x -= 1
        self._display_current()

    def _on_next(self) -> None:
        if self._x >= sh.LAST_VERSE_IN_BIBLE:
            return
        self._x += 1
        self._display_current()

    # --------- Queries ---------
    def _fetch_commentary_text(self, book: int, chapter: int, verse: int) -> str | None:
        """Return commentary text for the specific verse (book, chapter, verse)."""
        try:
            b = int(book)
            c = int(chapter)
            v = int(verse)
        except (TypeError, ValueError):
            return None

        try:
            cur = self._ensure_conn().cursor()
            # 1) Try exact match on fromverse
            try:
                cur.execute(
                    "SELECT data FROM commentary WHERE book=? AND chapter=? AND fromverse=? LIMIT 1",
                    (b, c, v),
                )
                row = cur.fetchone()
                if row and row[0] is not None:
                    return str(row[0])
            except sqlite3.Error:
                pass

            # 2) Try range match: v BETWEEN fromverse AND COALESCE(toverse, fromverse)
            try:
                cur.execute(
                    """
                    SELECT data
                    FROM commentary
                    WHERE book=? AND chapter=?
                      AND fromverse <= ?
                      AND COALESCE(toverse, fromverse) >= ?
                    ORDER BY (COALESCE(toverse, fromverse) - fromverse) ASC
                    LIMIT 1
                    """,
                    (b, c, v, v),
                )
                row = cur.fetchone()
                if row and row[0] is not None:
                    return str(row[0])
            except sqlite3.Error:
                pass

            # 3) Cautious fallback: some DBs may store 0-based verses; try v-1
            v0 = v - 1
            if v0 >= 0:
                try:
                    cur.execute(
                        "SELECT data FROM commentary WHERE book=? AND chapter=? AND fromverse=? LIMIT 1",
                        (b, c, v0),
                    )
                    row = cur.fetchone()
                    if row and row[0] is not None:
                        return str(row[0])
                except sqlite3.Error:
                    pass
                try:
                    cur.execute(
                        """
                        SELECT data
                        FROM commentary
                        WHERE book=? AND chapter=?
                          AND fromverse <= ?
                          AND COALESCE(toverse, fromverse) >= ?
                        ORDER BY (COALESCE(toverse, fromverse) - fromverse) ASC
                        LIMIT 1
                        """,
                        (b, c, v0, v0),
                    )
                    row = cur.fetchone()
                    if row and row[0] is not None:
                        return str(row[0])
                except sqlite3.Error:
                    pass
        except (sqlite3.Error, TypeError, ValueError):
            return None
        return None

    def _display_current(self) -> None:
        """Render the current x into the window."""
        # Clear the per-window hover cache when content changes
        try:
            self._ref_cache.clear()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            # Be tolerant if an attribute is missing for any reason
            pass
        try:
            entry = sh.Info[self._x]
            b = int(entry[0])
            c = int(entry[1]) + 1
            v = int(entry[2]) + 1
        except (IndexError, TypeError, ValueError):
            b, c, v = 1, 1, 1

        try:
            db_b = int(b) + 1
        except (TypeError, ValueError):
            db_b = b
        # Special-case: some environments report Gen 1:1 as v=2 via sh.Info; normalise to 1.
        v_db = v
        v_title = v
        if b == 0 and c == 1 and v == 2:
            v_db = 1
            v_title = 1
        text = self._fetch_commentary_text(db_b, c, v_db)
        # Title with book name (e.g. "Exodus 1:1"), falling back to numbers if needed
        try:
            title_ref = f"{b + 1} {c}:{v_title}"
            if hasattr(w, "nwin"):
                try:
                    book_str = w.nwin[int(b)]
                    if book_str:
                        if int(b) in getattr(sh, "onechapterbooks", ()):  # e.g., Jude
                            title_ref = f"{book_str} {v_title}"
                        else:
                            title_ref = f"{book_str} {c}:{v_title}"
                except (TypeError, ValueError, IndexError, AttributeError):
                    pass
            self.setWindowTitle(f"Gill Commentary — {title_ref}")
        except (RuntimeError, TypeError, ValueError):
            self.setWindowTitle("Gill Commentary")

        if text is None or text.strip() == "":
            try:
                self.viewer.setHtml("<p>No commentary for this verse</p>")
            except (RuntimeError, TypeError, ValueError):
                self.viewer.setPlainText("No commentary for this verse")
        else:
            # Wrap in a body so our default stylesheet applies consistently
            try:
                # Enforce left alignment and LTR direction at the HTML root
                # Ensure anchors for scripture references are visually highlighted via CSS
                self.viewer.setHtml(f"<body dir='ltr' style='text-align:left'>{text}</body>")
            except (RuntimeError, TypeError, ValueError):
                # Fallback to plain text if the HTML is severely malformed
                self.viewer.setPlainText(text)

        # After content is set, refresh highlights (CSS) and prepare hover handlers
        try:
            # Nothing to compute for CSS-based highlighting; ensure the popup is closed
            self._close_popup()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    # --------- Font size controls ---------
    def apply_font_size(self, size: int) -> None:
        try:
            s = int(size)
        except (TypeError, ValueError):
            s = 12
        if s < 8:
            s = 8
        if s > 40:
            s = 40
        try:
            fnt = self.viewer.font()
            # Avoid redundant application
            if fnt.pointSize() == s:
                return

            fnt.setPointSize(s)
            self.viewer.setFont(fnt)
            try:
                self.viewer.document().setDefaultFont(fnt)
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass
            try:
                css = (
                    "body, p, div { "
                    f"font-family: '{fnt.family()}'; "
                    f"font-size: {fnt.pointSize()}pt; "
                    "text-align: left; direction: ltr; }"
                )
                self.viewer.document().setDefaultStyleSheet(css)
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass
            self._settings_service.update_commentary_font_size(s)

            # Unified font size support: notify the main window
            if bool(self._settings_service.settings.get("unified_font_size", False)):
                global w
                if w and hasattr(w, "apply_font_size"):
                    # Only notify if the main window's font size is different
                    if w.settings_service.get_bible_font_size() != s:
                        w.settings_service.update_bible_font_size(s)
                        w.apply_font_size()

            # Refresh the display to apply the new font size to the HTML content
            self._display_current()
        except (RuntimeError, TypeError, ValueError):
            pass

    def increase_font_size(self) -> None:
        try:
            current = int(self.viewer.font().pointSize())
        except (TypeError, ValueError):
            current = 12
        self.apply_font_size(current + 1)

    def decrease_font_size(self) -> None:
        try:
            current = int(self.viewer.font().pointSize())
        except (TypeError, ValueError):
            current = 12
        self.apply_font_size(current - 1)

    # --------- Hover popup logic for scripture refs ---------
    def eventFilter(self, obj, event):  # type: ignore[override]
        try:
            et = event.type()
            # Mark interaction on wheel, mouse press/release/drag, and navigation keys
            if obj in (self.viewer, self.viewer.viewport()):
                # (Ctrl-freeze removed: no auto-unfreeze checks)

                if et == QEvent.Type.Wheel:
                    self._mark_user_interaction()
                    # Forward-wheel events to popup helper for scrolling long refs
                    try:
                        ph = getattr(self, "_popup_helper", None)
                        if ph is not None and ph.is_visible() and isinstance(event, QWheelEvent):
                            ph.scroll_by(event.angleDelta().y())
                            return True
                    except (RuntimeError, AttributeError):
                        pass
                elif et in (QEvent.Type.MouseButtonPress, QEvent.Type.MouseButtonRelease):
                    self._mark_user_interaction()
                elif et == QEvent.Type.MouseMove:
                    try:
                        # Consider the user interacting when any mouse button is pressed while moving
                        if isinstance(event, QMouseEvent) and event.buttons() != Qt.MouseButton.NoButton:
                            self._mark_user_interaction()
                    except (RuntimeError, AttributeError, TypeError, ValueError):
                        pass
                elif et == QEvent.Type.KeyPress:
                    # Navigation keys indicate interaction
                    try:
                        self._mark_user_interaction()
                    except (RuntimeError, AttributeError):
                        pass
                    # (Ctrl+C copy and Ctrl-freeze removed)

            if obj is self.viewer.viewport():
                if et == QEvent.Type.Leave:
                    # Always close on leave
                    self._current_href = None
                    self._cancel_hover()
                    self._close_popup()
                elif et == QEvent.Type.MouseMove:
                    # (Ctrl-freeze removed: no bypass of MouseMove)
                    # Respect the global "show popups" toggle: if disabled, ensure none are shown
                    if not getattr(self, "_popups_enabled", True):
                        try:
                            self._cancel_hover()
                            # Start a short hide; or close immediately if timer absent
                            if self._hide_timer is not None:
                                self._hide_timer.start(self._hide_delay_ms)
                            else:
                                self._close_popup()
                        except (RuntimeError, AttributeError, TypeError, ValueError):
                            pass
                        # Skip any hover handling when disabled
                        return False
                    # Use Qt6-compatible mouse position API; avoid accessing attributes on QEvent directly
                    try:
                        if isinstance(event, QMouseEvent):
                            qp = event.position().toPoint()
                            href_now = self._href_at_with_slop(qp)
                            if not href_now:
                                # Schedule a short delayed hide to avoid blinking
                                self._cancel_hover()
                                try:
                                    if self._hide_timer is not None:
                                        self._hide_timer.start(self._hide_delay_ms)
                                except (RuntimeError, AttributeError):
                                    self._close_popup()
                                # Allow re-trigger when we come back to the same href
                                self._current_href = None
                            else:
                                # Over a bible anchor — cancel pending hide and schedule/refresh popup
                                if self._hide_timer is not None and self._hide_timer.isActive():
                                    try:
                                        self._hide_timer.stop()
                                    except (RuntimeError, AttributeError):
                                        pass
                                if href_now != self._current_href:
                                    self._current_href = href_now
                                    self._schedule_hover(qp)
                                else:
                                    # Same href — if a popup is hidden, re-schedule showing it, else follow the cursor
                                    try:
                                        ph = self._popup_helper
                                        if ph is not None:
                                            # Prefer helper API if available
                                            try:
                                                is_vis = bool(getattr(ph, 'is_visible') and ph.is_visible())  # type: ignore[attr-defined]
                                            except (RuntimeError, AttributeError, TypeError, ValueError):
                                                # If helper API missing or failed, assume not visible
                                                # (avoid private access)
                                                is_vis = False
                                            if not is_vis:
                                                self._schedule_hover(qp)
                                            else:
                                                ph.move_to(self.viewer, qp)
                                    except (RuntimeError, AttributeError, TypeError, ValueError):
                                        pass
                    except (RuntimeError, AttributeError, TypeError, ValueError):
                        pass
                elif et == QEvent.Type.MouseButtonRelease and self._click_to_navigate:
                    try:
                        if isinstance(event, QMouseEvent):
                            qp = event.position().toPoint()
                            href = self.viewer.anchorAt(qp)
                            if isinstance(href, str) and href.lstrip().startswith(('#b', '#B', '#c', '#C')):
                                bcv = self._parse_href_to_bcv(href)
                                if bcv is not None and hasattr(w, 'move_to_line') and callable(getattr(w, 'move_to_line')):
                                    b, c, v = bcv
                                    try:
                                        current_ln = w.get_line_number() if hasattr(w, 'get_line_number') else 0
                                    except (RuntimeError, AttributeError, TypeError, ValueError):
                                        current_ln = 0
                                    try:
                                        idx = calc_line(b, c, v, current_ln)
                                        w.display_verse(int(idx))
                                        # For commentary links (#c), also update the Gill window itself
                                        if href.lstrip().startswith(('#c', '#C')):
                                            self.set_position(int(idx))
                                    except (RuntimeError, AttributeError, TypeError, ValueError):
                                        pass
                                self._close_popup()
                                return True
                    except (RuntimeError, AttributeError, TypeError, ValueError):
                        pass
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            return super().eventFilter(obj, event)
        except (RuntimeError, AttributeError, TypeError):
            return False

    def _schedule_hover(self, pos):
        # Respect popups toggle
        if not getattr(self, "_popups_enabled", True):
            return
        self._pending_hover_pos = pos
        try:
            if self._hover_timer is None:
                from PySide6.QtCore import QTimer
                self._hover_timer = QTimer(self)
                self._hover_timer.setSingleShot(True)
                self._hover_timer.timeout.connect(self._perform_hover)
            # Short hover delay for a responsive feel
            self._hover_timer.start(int(self._hover_delay_ms))
        except (RuntimeError, AttributeError, TypeError, ValueError):
            # If timer setup fails, fall back to immediate handling
            self._perform_hover()

    def _cancel_hover(self):
        try:
            if self._hover_timer is not None:
                self._hover_timer.stop()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        self._pending_hover_pos = None

    def _perform_hover(self):
        # Respect popups toggle
        if not getattr(self, "_popups_enabled", True):
            return
        pos = self._pending_hover_pos
        self._pending_hover_pos = None
        if pos is None:
            return
        try:
            href = self._href_at_with_slop(pos)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            href = ""
        if not href:
            # If nothing resolved, begin hide debounce
            try:
                if self._hide_timer is not None:
                    self._hide_timer.start(self._hide_delay_ms)
            except (RuntimeError, AttributeError):
                self._close_popup()
            return
        # Only handle internal bible refs, e.g. #b43.3.16 or #c40.21.33
        if not isinstance(href, str) or not href.lstrip().startswith(('#b', '#B', '#c', '#C')):
            try:
                if self._hide_timer is not None:
                    self._hide_timer.start(self._hide_delay_ms)
            except (RuntimeError, AttributeError):
                self._close_popup()
            return
        ref_text = self._resolve_href_to_text(href)
        if not ref_text:
            try:
                if self._hide_timer is not None:
                    self._hide_timer.start(self._hide_delay_ms)
            except (RuntimeError, AttributeError):
                self._close_popup()
            return
        # Optional polish: stop pending hide before showing to avoid races
        try:
            if self._hide_timer is not None and self._hide_timer.isActive():
                self._hide_timer.stop()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        self._show_popup(ref_text, pos)
        self._current_href = href

    def _resolve_href_to_text(self, href: str) -> str | None:
        """Parse Gill anchors hrefs robustly and returns verse text plus canonical reference.

        Supported examples:
        #b43.3.16
        #c1.2.9 (commentary link)
        #b43.3.16-18
        #b43.3.16,18,20-22
        #B43.3.16 (case-insensitive)
        #b43.3.16,’ (trailing punctuation)
        #b43.3 (chapter only → verse 1)
        #b43.3.16a (letter suffix ignored)
        """
        try:
            # Fast path: return from cache if available
            try:
                cached = self._ref_cache.get(href)  # type: ignore[attr-defined]
                if cached:
                    return cached
            except (RuntimeError, AttributeError, TypeError, ValueError):
                # If cache not present (older object), create it lazily
                try:
                    self._ref_cache = {}
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    pass
            s = href.strip()
            if not s:
                return None
            # Trim leading '#'
            if s.startswith('#'):
                s = s[1:]
            # Tolerate leading 'b', 'B', 'c' or 'C'
            if s and (s[0] in ('b', 'B', 'c', 'C')):
                s = s[1:]
            parts = s.split('.')
            if len(parts) < 2:
                return None
            b = int(parts[0])
            c = int(parts[1])
            versespec = parts[2] if len(parts) >= 3 else '1'
            # Normalise: replace en/em dashes, strip spaces, remove trailing punctuation and letter suffixes
            versespec = versespec.replace('–', '-').replace('—', '-')
            versespec = versespec.strip()
            # Drop trailing punctuation
            versespec = versespec.rstrip(" ,;:.')]}\"”」}")
            # Chapter-only → verse 1
            if not versespec:
                versespec = '1'
            segments = [seg.strip() for seg in versespec.split(',') if seg.strip()]
            verse_list: list[int] = []
            display_segments: list[str] = []
            for seg in segments:
                # Remove letter suffixes like 16a
                seg_norm = re.sub(r"(?i)[a-z]+$", "", seg).strip()
                if not seg_norm:
                    continue
                if '-' in seg_norm:
                    lhs, rhs = seg_norm.split('-', 1)
                    try:
                        v1 = int(lhs)
                        v2 = int(rhs)
                    except (TypeError, ValueError):
                        continue
                    # Clamp to sensible bounds
                    if v1 > v2:
                        v1, v2 = v2, v1
                    v1 = max(1, min(v1, sh.MAX_VERSES_PER_CHAPTER))
                    v2 = max(1, min(v2, sh.MAX_VERSES_PER_CHAPTER))
                    verse_list.extend(range(v1, v2 + 1))
                    display_segments.append(f"{v1}-{v2}")
                else:
                    try:
                        v = int(seg_norm)
                    except (TypeError, ValueError):
                        continue
                    v = max(1, min(v, sh.MAX_VERSES_PER_CHAPTER))
                    verse_list.append(v)
                    display_segments.append(str(v))
            # De-duplicate while preserving order
            seen: set[int] = set()
            verses_ordered: list[int] = []
            for vv in verse_list or [1]:
                if vv not in seen:
                    seen.add(vv)
                    verses_ordered.append(vv)

            # Build verse text(s)
            texts: list[str] = []
            for v in verses_ordered:
                x = self._global_index_for_bcv(b, c, v)
                if x is None:
                    continue
                try:
                    ln = int(next(islice(Amap, x, None)))
                    texts.append(KJV[ln])
                except (StopIteration, TypeError, ValueError, IndexError):
                    continue
            if not texts:
                return None

            # Compose canonical reference line like Other Works: BookName Chap:VerseSpec
            # (or just VerseSpec for 1‑chapter books)
            try:
                book_name = str(b)
                if hasattr(w, 'nwin'):
                    try:
                        nm = w.nwin[int(b) - 1]
                        if nm:
                            book_name = nm
                    except (TypeError, ValueError, IndexError, AttributeError):
                        pass
                # Use the original normalised versespec for display
                versespec_display = ",".join(display_segments) if display_segments else '1'
                if (int(b) - 1) in getattr(sh, 'onechapterbooks', ()):  # one-chapter books, e.g. Jude
                    canonical = f"{book_name} {versespec_display}"
                else:
                    canonical = f"{book_name} {int(c)}:{versespec_display}"
            except (RuntimeError, AttributeError, TypeError, ValueError):
                canonical = f"{b} {c}:{','.join(display_segments) if display_segments else '1'}"

            # Compose the body and then exactly one line break before the canonical reference
            body = "\n".join([str(t).rstrip() for t in texts]).rstrip()
            canonical_line = f"{canonical} KJV"
            result = body + "\n" + canonical_line
            # Store in a small cache (simple cap to prevent unbounded growth)
            try:
                if len(self._ref_cache) > 256:  # type: ignore[attr-defined]
                    self._ref_cache.clear()     # type: ignore[attr-defined]
                self._ref_cache[href] = result   # type: ignore[attr-defined]
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass
            return result
        except (RuntimeError, AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def _parse_href_to_bcv(href: str) -> tuple[int, int, int] | None:
        """Return the first verse target (book, chapter, verse) from a Gill href.

        Accepts ranges/lists and returns the first number; chapter-only → (b, c, 1).
        """
        try:
            s = href.strip()
            if s.startswith('#'):
                s = s[1:]
            if s and (s[0] in ('b', 'B', 'c', 'C')):
                s = s[1:]
            parts = s.split('.')
            if len(parts) < 2:
                return None
            b = int(parts[0])
            c = int(parts[1])
            vpart = parts[2] if len(parts) >= 3 else '1'
            vpart = vpart.replace('–', '-').replace('—', '-').strip()
            vpart = vpart.rstrip(" ,;:.')]}\"”」}")
            if not vpart:
                vpart = '1'
            first_seg = vpart.split(',')[0].strip()
            first_seg = re.sub(r"(?i)[a-z]+$", "", first_seg).strip()
            if '-' in first_seg:
                first_seg = first_seg.split('-', 1)[0].strip()
            v = int(first_seg)
            if v < 1:
                v = 1
            return b, c, v
        except (TypeError, ValueError, IndexError, AttributeError):
            return None

    # (Auto-follow methods removed)

    @staticmethod
    def _global_index_for_bcv(b: int, c: int, v: int) -> int | None:
        """Resolve (book, chapter, verse) 1-based to global index using sh.Info (0-based for all three)."""
        try:
            # sh.Info entries are 0-based: (book0, chapter0, verse0)
            bb, cc, vv = int(b) - 1, int(c) - 1, int(v) - 1
            for i, entry in enumerate(sh.Info[0: sh.LAST_VERSE_IN_BIBLE + 1], start=0):
                if int(entry[0]) == bb and int(entry[1]) == cc and int(entry[2]) == vv:
                    return i
        except (IndexError, TypeError, ValueError):
            return None
        return None

    def _show_popup(self, text: str, pos) -> None:
        try:
            if self._popup_helper is None:
                self._popup_helper = SimpleScripturePopup()
            # Delegate rendering/positioning to the shared helper
            is_dark = self._is_dark
            self._popup_helper.show(self.viewer, text, pos, self.viewer.font(), is_dark=is_dark)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    def _close_popup(self) -> None:
        try:
            if self._popup_helper is not None:
                self._popup_helper.hide()
        except (RuntimeError, AttributeError):
            pass
        # Ensure we don’t stick with a stale href when a popup is closed
        self._current_href = None

    def set_popups_enabled(self, enabled: bool) -> None:
        """Enable/disable scripture popups at runtime.
        When disabling, cancel timers and hide any visible popup immediately.
        """
        self._popups_enabled = bool(enabled)
        if not self._popups_enabled:
            try:
                self._cancel_hover()
                if self._hide_timer is not None:
                    self._hide_timer.stop()
            except (RuntimeError, AttributeError):
                pass
            self._close_popup()

    def set_popup_timing(self, hover_ms: int, hide_ms: int) -> None:
        """Update popup timing (hover/hide delays) at runtime.
        Values are clamped to sensible bounds.
        """
        try:
            h = int(hover_ms)
        except (TypeError, ValueError):
            h = self._hover_delay_ms
        try:
            d = int(hide_ms)
        except (TypeError, ValueError):
            d = self._hide_delay_ms
        # Clamp
        if h < 0:
            h = 0
        if h > 5000:
            h = 5000
        if d < 0:
            d = 0
        if d > 5000:
            d = 5000
        self._hover_delay_ms = h
        self._hide_delay_ms = d
        try:
            if self._hide_timer is not None:
                # Update timer interval for later and current debounced hides
                self._hide_timer.setInterval(self._hide_delay_ms)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    # --------- Interaction & hover helpers ---------
    def _mark_user_interaction(self) -> None:
        """Mark a short quiet period during which auto-follow is paused."""
        try:
            self._interacting_until = time.monotonic() + (self._interaction_quiet_ms / 1000.0)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            self._interacting_until = 0.0

    def _href_at_with_slop(self, p) -> str:
        """Return an anchor href at or very near the point, tolerant to tiny jitter."""
        try:
            from PySide6.QtCore import QPoint
        except ImportError:
            QPoint = None  # type: ignore
        candidates = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))
        for dx, dy in candidates:
            try:
                pt = p
                if QPoint is not None and hasattr(p, 'x'):
                    pt = QPoint(p.x() + dx, p.y() + dy)
                href = self.viewer.anchorAt(pt)
            except (RuntimeError, AttributeError, TypeError, ValueError):
                href = ""
            if isinstance(href, str) and href.lstrip().startswith(("#b", "#B", "#c", "#C")):
                return href
        return ""


def commentary() -> None:
    """Open or focus the John Gill commentary window for the current verse."""
    try:
        if hasattr(w, "open_commentary_window") and callable(w.open_commentary_window):
            w.open_commentary_window()
        else:
            # Fallback message if method not available for any reason
            QMessageBox.information(
                w,
                "Commentary",
                "Commentary feature is not available in this context."
            )
    except Exception as exc:
        # Non-fatal UI error; log to console.
        print("Commentary open error:", exc)


class MainWindow(QMainWindow):
    """MainWindow class."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialise."""
        settings_service = kwargs.pop("settings_service", None)
        super(MainWindow, self).__init__(*args, **kwargs)

        # Load saved settings or initialise default ones.

        # Settings service and window geometry
        self.settings_service = settings_service if settings_service is not None else SettingsService()
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
        self.textEditor = NoZoomPlainTextEdit()
        # Predeclare actions bundle to satisfy linters (assigned in initui)
        self.actions_bundle = None
        
        # Theme manager (extract dark mode logic)
        # Initialise 'ThemeManager' based on persisted settings
        from ui.themes import ThemeManager, ThemeState  # local import (deferred)
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
        self._gill_win: GillCommentaryWindow | None = None

        # Services (lazy-initialised on first use to improve startup time)
        self._audio = None
        self._printing = None
        self._reading_plans = None

        # Store a reference to the secondary window to manage its lifecycle
        self.secondary_window = None

        # Create keyboard shortcuts via the centralised helper (local import to defer)
        from ui.actions import setup_shortcuts  # local import (deferred)
        self.shortcuts_bundle = setup_shortcuts(self)

        #Qt.QTimer.singleShot(0, lambda: self.sme("PM", -1))  # Adjusted to yesterday evening's reading.

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
        self.gent: Any | None = None
        self.no_f3_yet: int = 0
        self.yend: int = 0
        self.finding: int = 0
        self.verse: int = 0
        self.PCE_text: list = []
        self.otherFileFlag: bool = True
        self.y: int = 0

        self.initui()

    # --- Lazy services ---
    @property
    def audio(self):
        """Audio service, created on first use."""
        if self._audio is None:
            try:
                from services.audio import AudioService
                self._audio = AudioService()
            except Exception:
                # Keep this attribute as None on failure and re-raise to surface the issue
                self._audio = None
                raise
        return self._audio

    @property
    def printing(self):
        """Printing service, created on first use."""
        if self._printing is None:
            try:
                from services.printing import PrintingService
                self._printing = PrintingService()
            except Exception:
                self._printing = None
                raise
        return self._printing

    @property
    def reading_plans(self):
        """Spurgeon Morning/Evening reading plans service, created on first use."""
        if self._reading_plans is None:
            try:
                from domain.reading_plans import ReadingPlans
                self._reading_plans = ReadingPlans()
            except Exception:
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
        self.display_verse_input.setFocus()

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Build menus, toolbars, and actions via the centralised helper
        from ui.actions import setup_menus_and_toolbars  # local import (deferred)
        self.actions_bundle = setup_menus_and_toolbars(self)

        self.secondary_window = None
        self.set_theme(self.settings)

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

        self.buttonf13 = QPushButton("Commentary")
        self.buttonf13.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf13.clicked.connect(commentary)
        self.buttonf13.setToolTip("Open Commentaries (Ctrl+Shift+C)")
        self.buttonf13.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.buttonf13, 3, 4)

        try:
            shortcut_cmt = QShortcut(QKeySequence("Ctrl+Shift+C"), self)
            shortcut_cmt.activated.connect(commentary)
        except (RuntimeError, TypeError, AttributeError):
            pass

        try:
            self._normalize_control_heights()
        except (RuntimeError, AttributeError, TypeError):
            pass

    def _setup_other_works(self, grid: QGridLayout) -> None:
        self.other_works_combo = QComboBox()
        self.other_works_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.last_work_btn = QPushButton("Last")
        self.last_work_btn.setStyleSheet("QPushButton { text-align: left; }")
        self.last_work_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.last_work_btn.setToolTip("Open the last read book (Ctrl+L)")
        self.last_work_btn.clicked.connect(self._select_last_other_work)  # type: ignore[attr-defined]

        self.search_work_btn = QPushButton("Search")
        self.search_work_btn.setStyleSheet("QPushButton { text-align: left; }")
        self.search_work_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.search_work_btn.setToolTip("Search in the opened Other Works text (Ctrl+F)")
        self.search_work_btn.clicked.connect(self._open_reader_search)  # type: ignore[attr-defined]
        self.search_work_btn.setEnabled(False)

        grid.addWidget(self.other_works_combo, 5, 0, 1, 2)
        grid.addWidget(self.last_work_btn, 5, 2)
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
                wdg.setSizePolicy(expanding_fixed)

        # Populate
        other_works_dir = Path(sh.str_cwd) / "Other Works"
        if other_works_dir.exists():
            files = sorted([p for p in other_works_dir.glob("*.txt") if p.is_file()])
            self.other_works_map = {p.stem: str(p) for p in files}
            self._refresh_other_works_combo()

            last_work = self.settings.get("last_other_work") if isinstance(self.settings, dict) else None
            if last_work and last_work in self.other_works_map:
                self.other_works_combo.setCurrentText(last_work)
            elif "Pilgrims-Progress" in self.other_works_map:
                self.other_works_combo.setCurrentText("Pilgrims-Progress")

        self.other_works_combo.currentTextChanged.connect(self._open_other_work)  # type: ignore[attr-defined]
        self.other_works_combo.activated.connect(  # type: ignore[attr-defined]
            lambda index: self._open_other_work(self.other_works_combo.itemText(index))
        )

        try:
            self.shortcut_last_work = QShortcut(QKeySequence("Ctrl+L"), self)
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

    # noinspection PyUnresolvedReferences
    def eventFilter(self, source, event):
        """Custom event filter to handle key events on QLineEdit."""

        if source == self.display_verse_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:  # Handle Up Arrow
                if self.command_history and self.history_index > 0:
                    self.history_index -= 1
                    self.display_verse_input.setText(self.command_history[self.history_index])
                elif self.command_history and self.history_index == -1:
                    self.history_index = len(self.command_history) - 1
                    self.display_verse_input.setText(self.command_history[self.history_index])
                return True

            elif event.key() == Qt.Key_Down:  # Handle Down Arrow
                if self.command_history and self.history_index < len(self.command_history) - 1:
                    self.history_index += 1
                    self.display_verse_input.setText(self.command_history[self.history_index])
                elif self.history_index == len(self.command_history) - 1:
                    self.history_index += 1
                    self.display_verse_input.clear()  # Clear input when navigating below the last command
                return True

            elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:  # Handle Enter
                current_text = self.display_verse_input.text().strip()
                if current_text:
                    self.command_history.append(current_text)  # Add current text to history
                    self.history_index = -1  # Reset history index
                    # print(f"Executed: {current_text}")  # Simulate command execution
                    # print("Return key intercepted in eventFilter")  # Debugging
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
        elif source == getattr(self.textEditor, 'viewport', lambda: None)():
            # Only process mouse button presses
            if event.type() == QEvent.MouseButtonPress:
                try:
                    if isinstance(event, QMouseEvent):
                        if event.button() == Qt.MouseButton.LeftButton:
                            # Map click position to document block/line
                            try:
                                pos = event.position() if hasattr(event, 'position') else event.pos()
                            except (RuntimeError, AttributeError):
                                pos = None
                            if pos is None:
                                return super().eventFilter(source, event)
                            try:
                                cursor = self.textEditor.cursorForPosition(pos.toPoint() if hasattr(pos, 'toPoint') else pos)
                                block = cursor.block()
                                line_no = int(block.blockNumber())
                            except (RuntimeError, AttributeError, TypeError, ValueError):
                                return super().eventFilter(source, event)

                            # Resolve the clicked line to the verse index (current_position)
                            # Prefer the nearest verse start at or before the clicked line.
                            current_position = None
                            try:
                                if line_no in Amap:
                                    current_position = Amap.index(line_no)
                                else:
                                    # Search backward first for up to 12 lines, then forward
                                    found = False
                                    for delta in range(1, 13):
                                        ln_back = line_no - delta
                                        if ln_back in Amap:
                                            current_position = Amap.index(ln_back)
                                            found = True
                                            break
                                        ln_fwd = line_no + delta
                                        if ln_fwd in Amap:
                                            current_position = Amap.index(ln_fwd)
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
        return super().eventFilter(source, event)

    def moveEvent(self, event):
        try:
            geometry = self.geometry()
            self.settings_service.save_window_geometry(
                "main_window",
                geometry.x(), geometry.y(), geometry.width(), geometry.height()
            )
        except (RuntimeError, TypeError, ValueError):
            pass
        try:
            return super().moveEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def resizeEvent(self, event):
        try:
            geometry = self.geometry()
            self.settings_service.save_window_geometry(
                "main_window",
                geometry.x(), geometry.y(), geometry.width(), geometry.height()
            )
        except (RuntimeError, TypeError, ValueError):
            pass
        try:
            return super().resizeEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def closeEvent(self, event: Any):
        """Handle window close event - save geometry and close child windows"""
        # Save main window geometry and state
        geometry = self.geometry()
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
            if self._gill_win is not None:
                self._gill_win.close()
        except (RuntimeError, AttributeError):
            pass
            
        try:
            if self.text_edit_window is not None:
                self.text_edit_window.close()
        except (RuntimeError, AttributeError):
            pass
            
        try:
            if self.secondary_window is not None:
                self.secondary_window.close()
        except (RuntimeError, AttributeError):
            pass

        try:
            if self.about_window is not None:
                self.about_window.close()
        except (RuntimeError, AttributeError):
            pass

        try:
            if self.dlg is not None:
                self.dlg.close()
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
                    # Avoid recursive calls: only apply if different
                    if int(getattr(reader, "reader_fontsize", 0)) != self.fontsize:
                        reader.apply_font_size(self.fontsize)
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    pass

            # 2. Gill Commentary Window
            gill = getattr(self, "_gill_win", None)
            if gill:
                try:
                    # Check current font size from viewer
                    current_gill_font = gill.viewer.font()
                    if current_gill_font.pointSize() != self.fontsize:
                        gill.apply_font_size(self.fontsize)
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    pass

            # 3. Secondary (Devotional) Window
            secondary = getattr(self, "secondary_window", None)
            if secondary:
                try:
                    if int(getattr(secondary, "fontsize", 0)) != self.fontsize:
                        secondary.fontsize = self.fontsize
                        secondary.update_font()
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
            from text_window import TextDocumentWindow as ExternalTextDocumentWindow
            self.text_edit_window = ExternalTextDocumentWindow(
                initial_file_path=req_path,
                settings=self.settings,
                settings_path=getattr(self, "user_settings_path", None),
                settings_service=self.settings_service
            )
            # When the user clicks a scripture reference in the reader, navigate here
            try:
                self.text_edit_window.referenceActivated.connect(self._on_reader_reference_activated)
                setattr(self.text_edit_window, "_connected_to_main", True)
            except (AttributeError, RuntimeError, TypeError):
                pass
            # Apply the current theme to the new window and its editor
            try:
                self.text_edit_window.apply_theme(self.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            # Apply palette to the window; ThemeManager handles internal safety
            self.theme.apply_widget(self.text_edit_window)
        else:
            # If the reader is currently loading the same stem/path,
            # then prevent it re-issuing the load.
            try:
                is_loading_file = bool(getattr(reader, "_is_loading_file", False))
                current_stem = getattr(reader, "current_file_stem", None)
                req_stem = Path(req_path).stem
                if is_loading_file and current_stem and str(current_stem) == str(req_stem):
                    # Already loading this work; just bring it to front and apply theme
                    try:
                        reader.apply_theme(self.theme.state.is_dark_mode)
                    except (RuntimeError, AttributeError):
                        pass
                    self.theme.apply_widget(reader)
                    reader.show(); reader.raise_(); reader.activateWindow()
                    return
            except (AttributeError, RuntimeError, TypeError, ValueError, OSError):
                pass
            # Guard: if the requested work is already loaded, avoid reloading
            try:
                current_stem = getattr(reader, "current_file_stem", None)
            except (AttributeError, RuntimeError, TypeError):
                current_stem = None
            req_stem = Path(req_path).stem
            if current_stem and str(current_stem) == str(req_stem):
                # Already showing this work; just refresh the theme/palette and focus
                try:
                    self.text_edit_window.apply_theme(self.theme.state.is_dark_mode)
                except (RuntimeError, AttributeError):
                    pass
                self.theme.apply_widget(self.text_edit_window)
            else:
                self.text_edit_window.load_text_file(req_path)
            # Ensure the signal is connected even if the window already existed
            try:
                if not getattr(self.text_edit_window, "_connected_to_main", False):
                    self.text_edit_window.referenceActivated.connect(self._on_reader_reference_activated)
                    setattr(self.text_edit_window, "_connected_to_main", True)
            except (AttributeError, RuntimeError, TypeError):
                pass
            try:
                self.text_edit_window.apply_theme(self.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            self.theme.apply_widget(self.text_edit_window)
        self.text_edit_window.show()
        self.text_edit_window.raise_()
        self.text_edit_window.activateWindow()
        # Connect visibility signal to toggle the Search button state and enable now
        try:
            if not getattr(self.text_edit_window, "_display_signal_connected", False):
                self.text_edit_window.displayedChanged.connect(self._on_reader_displayed_changed)
                setattr(self.text_edit_window, "_display_signal_connected", True)
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
            if enabled is None:
                reader = getattr(self, "text_edit_window", None)
                state = bool(reader is not None and getattr(reader, "isVisible", None) and reader.isVisible())
            else:
                state = bool(enabled)
            btn.setEnabled(state)
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
            reader.show_find_dialog()
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
                # Just bring the window to front and ensure theme is applied
                try:
                    reader.apply_theme(self.theme.state.is_dark_mode)
                except (RuntimeError, AttributeError):
                    pass
                self.theme.apply_widget(reader)
                reader.show(); reader.raise_(); reader.activateWindow()
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
            idx = self.other_works_combo.findText(last_work)
            if idx < 0:
                return

            # If it's already selected, Qt won't emit signals; open explicitly
            if self.other_works_combo.currentIndex() == idx:
                self._open_other_work(last_work)
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
            self._open_other_work(last_work)
        except (RuntimeError, AttributeError, KeyError, TypeError, ValueError):
            # Be silent on any unexpected issue
            pass

    def show_about_dialog(self):
        """Show the 'About' window when Help -> About is clicked."""

        # Initialize AboutWindow if it hasn't been created
        if self.about_window is None:
            from windows import AboutWindow as ExtAboutWindow  # deferred import
            self.about_window = ExtAboutWindow(f"Abib {CURRENT_VERSION}", settings_service=self.settings_service)
        # Apply the theme palette to the About window (apply_widget is internally safe)
        self.theme.apply_widget(self.about_window)
        self.about_window.show()
        self.about_window.raise_()  # Bring the "About" window to the front
        self.about_window.activateWindow()  # Give the "About" window focus

    def helper(self) -> None:
        """Help section."""

        self.file_open(str(Path(sh.current_directory / 'HELP.txt')))
        # Save current Bible window geometry so we can restore it on Back but
        # only capture it once when leaving the Bible (do not overwrite while
        # switching between auxiliary files like COPYING/README/HELP).
        try:
            if not getattr(self, "_aux_origin_saved", False):
                # Capture geometry once when first switching to an auxiliary file
                self._saved_geometry_before_aux = self.geometry()
                self._aux_origin_saved = True
        except (RuntimeError, AttributeError, TypeError):
            self._saved_geometry_before_aux = None
        winwidth: int = 830
        winheight: int = 1343

        # Allow for small screen sizes
        winheight, winwidth = sizer(winheight, winwidth)

        w_origin, h_origin = centerer(winwidth, winheight)
        self.setGeometry(w_origin, h_origin, winwidth, winheight)
        w.otherFileFlag = True

    def copyright(self) -> None:
        """Licence."""

        self.file_open(str(Path(sh.current_directory / 'COPYING')))
        # Save current Bible window geometry so we can restore it on Back but
        # only capture it once when leaving the Bible (do not overwrite while
        # switching between auxiliary files like COPYING/README/HELP).
        try:
            if not getattr(self, "_aux_origin_saved", False):
                # Capture geometry once when first switching to an auxiliary file
                self._saved_geometry_before_aux = self.geometry()
                self._aux_origin_saved = True
        except (RuntimeError, AttributeError, TypeError):
            self._saved_geometry_before_aux = None
        # Set window width to fit 80 characters of the current editor font
        try:
            fm = self.textEditor.fontMetrics()
            # Use a wide glyph for conservative per-character width
            char_w = fm.horizontalAdvance('M') if fm else 10
            text_w = int(char_w * 80)
            # Add padding for frame, margins, and vertical scrollbar
            frame_pad = getattr(self.textEditor, 'frameWidth', lambda: 2)()
            try:
                scroll_w = self.textEditor.verticalScrollBar().sizeHint().width()
            except (RuntimeError, AttributeError):
                scroll_w = 16
            extra_pad = 12  # small extra to avoid wrapping due to rounding
            winwidth: int = text_w + (frame_pad * 2) + scroll_w + extra_pad
        except (RuntimeError, AttributeError, TypeError, ValueError):
            # Fallback if metrics fail
            winwidth = 760
        winheight: int = 1343

        # Allow for small screen sizes
        winheight, winwidth = sizer(winheight, winwidth)

        w_origin, h_origin = centerer(winwidth, winheight)
        self.setGeometry(w_origin, h_origin, winwidth, winheight)
        w.otherFileFlag = True

    def readme(self) -> None:
        """Readme file."""

        self.file_open(str(Path(sh.current_directory / 'README.txt')))
        # Save current Bible window geometry so we can restore it on Back but
        # only capture it once when leaving the Bible (do not overwrite while
        # switching between auxiliary files like COPYING/README/HELP).
        try:
            if not getattr(self, "_aux_origin_saved", False):
                # Capture geometry once when first switching to an auxiliary file
                self._saved_geometry_before_aux = self.geometry()
                self._aux_origin_saved = True
        except (RuntimeError, AttributeError, TypeError):
            self._saved_geometry_before_aux = None
        winwidth: int = 830
        winheight: int = 1343

        # Allow for small screen sizes
        winheight, winwidth =  sizer(winheight, winwidth)

        w_origin, h_origin = centerer(winwidth, winheight)
        self.setGeometry(w_origin, h_origin, winwidth, winheight)
        w.otherFileFlag = True

    def reload(self) -> None:
        """Reload KJB_PCE.txt"""

        if w.otherFileFlag:
            # print('reloaded')
            w.otherFileFlag = False
            self.file_open(str(Path(sh.current_directory / 'KJB_PCE.txt')))
            # Do NOT re-centre or reset attributes here.
            # When returning from README/COPYING/HELP via Back, preserve window
            # geometry and Bible state so history restoration works correctly.
            try:
                if getattr(self, "_saved_geometry_before_aux", None):
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
            from find_dialog import FindDialog  # deferred import
            self.dlg = FindDialog(self, settings_service=self.settings_service)
            # Apply theme palette to Find dialog (apply_widget is internally safe)
            self.theme.apply_widget(self.dlg)
            self.dlg.exec()
        else:
            self.show_find_window()

    def show_find_window(self) -> None:
        """Show the Find window."""

        if self.dlg is None:
            from find_dialog import FindDialog  # deferred import
            self.dlg = FindDialog(self, settings_service=self.settings_service)
            # Apply theme palette to Find dialog (apply_widget is internally safe)
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

        Return the number of whole words in _key.
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

        p = "():,’;-?[].!<>"
        ae: List[str] = ['aea', 'aeu', 'aes', 'aet', 'aene', 'aeno', 'AEno', 'AEne', 'Aeno', 'Aene']
        ae_unicode: List[str] = ['æa', 'æu', 'æs', 'æt', 'æne', 'æno', 'Æno', 'Æne', 'Æno', 'Æne']
        count = -1
        for _ in ae:
            count += 1
            if _ in w.key:
                index = w.key.find(_)
                j = len(_)
                j += index
                w.key = w.key[:index] + ae_unicode[count] + w.key[j:]
                break
        line = ''
        for _ in w.key:
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

        w.no_f3_yet = 1

        w.keym = w.key
        if w.key == '' or w.key == ' ':
            w.y = -1
            w.no_f3_yet = 0
            w.occurring = 0
            self.statusBar.clearMessage()
            self.statusBar.repaint()
        else:
            self.statusBar.showMessage('Finding...')
            self.statusBar.repaint()
            keylow = w.key.lower()
            w.y = 0
            w.occurring = 0

            if self.dlg.checks[2] == 6:
                self.iterate_regex(Rnew, x1, x2)
                if w.occurring != 0:
                    w.y = w.occur[0][0][0]
                    w.occurrence = 0
                    w.verse = 0
                    w.finding = -1
                    current_position = occurrent1()
                    self.statusBar.showMessage(w.message)
                    self.statusBar.repaint()
            else:
                tv = self.dlg.checks[0] == 1   # Raw
                if not tv:
                    current_position = self.findf3_ww(x1, x2)
                elif tv:
                    # Raw.
                    current_position = self.findf3_raw(current_position, x1, x2, keylow)

        if w.occurring == 0:
            current_position = savedx
            self.on_error('Not found...', 2000, True)
            error_flag = True

        if w.key in ('q', 'Q'):
            self.display_verse_input.clear()
            exit()
        if not error_flag:
            self.goto_line_find(current_position)

    def iterate_regex(self, r: tuple, x1: int, x2: int) -> None:
        """Iterate over R and find all the occurrences of key(s) in liszt."""

        w.occurring = 0
        w.occur = []
        w.occurs = []
        if self.dlg.checks[1] == 1:             # Match case
            pattern = rf"{w.key}"
        else:
            assert self.dlg.checks[1] == 0      # Ignore the case
            pattern = rf"(?i){w.key}"
        # Iterate inclusively within the provided limits [x1, x2]
        for _ in range(x1, x2 + 1):
            coordinate = []
            try:
                for m in re.finditer(pattern, r[_]):
                    w.occurring += 1
                    coordinate.append((m.start(), m.end()))
            except re.error:
                msg = 'Regular Expression Error.'
                self.on_error(msg, 2000, True)
                w.occurring = 0
                break
            if coordinate:
                w.occur.append(coordinate)
                w.occurs.append(_)

    def findf3_raw(self, current_position: int, x1: int, x2: int, keylow: str) -> int:
        """Find Raw."""

        # Count occurrences inclusively within the provided limits [x1, x2]
        if self.dlg.checks[1] == 1:  # Match case
            w.occurring += sum(Rnew[_].count(w.key) for _ in range(x1, x2 + 1))
        elif self.dlg.checks[1] == 0:  # Lower case
            w.occurring += sum(Rlow[_].count(keylow) for _ in range(x1, x2 + 1))

        if w.occurring != 0:
            w.occurrence = 0
            current_position = self.occurrent(x1, x2)
            self.statusBar.showMessage(w.message)
            self.statusBar.repaint()

        return current_position

    def assign_values(self) -> Any:
        """Can't remember what this does."""

        # print('assign_values')
        numwords: int
        w.verse = 0
        if self.dlg.checks[1] == 1:             # Match case.
            dic: Any = stripped_dict
            key: str = w.key
            # set_ and set_dict are dictionaries of words in the KJV Bible.
            # For each word, there is a set of verse/line numbers where the word occurs.
            set_: Dict[Any, Set] = set_dict
            r_list: List | tuple = Rstp
        else:
            assert self.dlg.checks[1] == 0      # The Case isn't checked.
            dic = strpd_low_dict
            key = w.key.lower()
            set_ = set_lowdict
            r_list = Rlsp
        numwords, w.key = self.make_key_whole(key, dic, set_)
        w.keym = w.key  # 16/12/2024

        return numwords, set_, r_list

    def findf3_ww(self, x1: int, x2: int) -> int:
        """Find Whole Words."""

        numwords, set_, r_list = self.assign_values()
        current_position: int = 0  # Pointer to the first verse with the searched for key.
        if numwords == 1:
            self.findf3_ww_1(x1, x2, set_, r_list)   # Match the whole single word.
            if w.occurring != 0:
                w.occurrence = 0
                w.verse = 0
                w.finding = -1
                current_position = occurrent1()
                self.statusBar.showMessage(w.message)
                self.statusBar.repaint()
        elif numwords > 1:
            from services.search_service import findf3_ww_ac, findf3_ww_all
            if self.dlg.checks[0] == 2:
                findf3_ww_ac(x1, x2, numwords, set_, r_list, self)
            elif self.dlg.checks[0] == 3:
                findf3_ww_all(x1, x2, numwords, set_, r_list, self)
            elif self.dlg.checks[0] == 4:
                _, w.key = fcs.any_of_the_words_lookup(w.key, set_)
                findf3_ww_any(x1, x2, set_, r_list, self)
            if w.occurring != 0:
                if self.dlg.checks[0] != 2:     # Not whole words
                    current_position = w.occurs[0]
                    w.occurrence = 1
                    prep_statusbar_message(current_position)
                elif self.dlg.checks[0] == 2:   # Whole words
                    w.occurrence = 0
                    w.verse = 0
                    w.finding = -1
                    current_position = occurrent1()
                self.statusBar.showMessage(w.message)
                self.statusBar.repaint()
        else:
            w.occurring = 0

        return current_position

    def findf3_ww_1(self, x1: int, x2: int, _set: Dict[str, Set], r_list: List) -> None:
        """Match the whole single word."""

        try:
            w.occur = sorted(list(_set[w.key]))
        except KeyError:
            w.occurring = 0
        else:
            w.occurs = []
            for i in w.occur:
                if i < x1 or i > x2:
                    continue
                w.occurs.append(i)
            # List of lists with tuple of the word positions, within the related verse.
            liszt = [w.key]
            if self.dlg.checks[0] == 4:
                from services.search_service import check_count_sort
                check_count_sort(liszt, r_list, self)
            else:
                from services.search_service import iterate_list
                iterate_list(liszt, r_list, self)

            if self.dlg.checks[0] > 2:
                w.occur_ww_1 = deepcopy(w.occur)
                j = -1
                for i in w.occur_ww_1:
                    j += 1
                    li = len(i)
                    if li > 1:
                        a = i[0][0]
                        b = i[li-1][1]
                        _ = w.occur_ww_1.pop(j)
                        w.occur_ww_1.insert(j, [(a, b)])
                w.occurring = len(w.occur_ww_1)   # 16/12/24
        # List of verses containing the searched for item.
        # Number of occurrences of the searchitem within the range x1 to x2.

    def occurrent(self, x1: int, x2: int) -> int:
        """Count occurrences of the item searched for."""

        if w.occurrence == 0:
            self.gent = self.gen(w.key, x1, x2)
        current_position, w.y, w.occurrence = next(self.gent)
        prep_statusbar_message(current_position)

        return current_position

    def find_f4(self) -> None:
        """Repeat find frontend for raw search."""

        if w.occurrence < w.occurring:
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
                current_position, w.y, w.occurrence = next(self.gent)
            except StopIteration:
                # Handle generator exhaustion if needed
                self.statusBar.showMessage("Search completed: no more matches.")
                return

            # Set the status bar message and other UI updates.
            prep_statusbar_message(current_position)
            self.statusBar.showMessage(w.message)
            self.statusBar.repaint()
            self.goto_line_find(current_position)

    def find_f4_alt(self) -> None:
        """Repeat find frontend for Whole words."""

        if len(w.occurs) > 0 and w.occurrence < w.occurring:
            current_position = self.get_line_number()
            if forward:
                history.back_push(w, current_position)
                while forward:
                    b_ = forward.pop()
                    back.append(b_)
            else:
                current_position = w.occurs[w.verse]
                forward.clear()
                history.back_push(w, current_position)

            if self.dlg.checks[0] == 2 or self.dlg.checks[2] == 6:
                current_position = occurrent1()
            elif self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4:
                if w.verse < len(w.occurs) - 1:
                    w.verse += 1
                    current_position = w.occurs[w.verse]
                    w.occurrence += 1
                    prep_statusbar_message(current_position)

            self.statusBar.showMessage(w.message)
            self.statusBar.repaint()
            self.goto_line_find(current_position)

    def gen(self, key: str, x1: int, x2: int):
        """Return the next position of the searched for key."""

        current_position = -1
        d1 = 0
        if self.dlg.checks[1] == 1:
            files_path = Path(sh.current_directory) / "PCE-find.txt"
        else:
            assert self.dlg.checks[1] == 0
            files_path = Path(sh.current_directory) / "PCE-lower.txt"
            key = key.lower()

        # Debugging: Print the file path
        # print(f"Constructed file path: {files_path}")

        # Check if the file exists before opening it
        if not files_path.exists():
            # print(f"Error: File '{files_path}' not found.")
            raise FileNotFoundError(f"File '{files_path}' does not exist.")

        # Open and read the file line by line
        try:
            line = (z for z in files_path.open('r', encoding='utf-8'))
        except FileNotFoundError as e2:
            print(f"Error opening file: {e2}")
            raise

        while True:
            current_position += 1
            yt = 0
            if current_position > x2:
                break
            a = next(line)
            if current_position < x1:
                continue
            while key in a:
                d1 += 1
                w.y = int(a.find(key))
                if w.y != -1:
                    yt = yt + w.y + 1        #  Expected int got '() -> int' instead
                    a = a[w.y + 1:]
                    w.y = yt - 1
                    yield current_position, w.y, d1

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

        add: int
        if '¶ ' in KJV[ln] and truth is True:
            w.y += 2
            end = w.y
        if self.dlg.checks[1] == 0:
            add = fcs.repeat_find(Ldic[current_position], start, end)
        else:
            add = fcs.repeat_find(Rdic[current_position], start, end)
        return add

    def stripped_punctuation_adjust_ki(self, current_position: int, start: int, end: int) -> int:
        """Addition for 'Whole words only'.

        This adjustment allows for no punctuation in the stripped search text.
        """

        add: int
        if self.dlg.checks[1] == 0:
            add = fcs.repeat_find_keyinc(Ldic[current_position], start, end)
        else:
            add = fcs.repeat_find_keyinc(Rdic[current_position], start, end)

        return add

    def adjust_highlighting(self, ln: int, _x: int) -> None:
        """Adjust highlighting for longer length Unicode characters."""

        add = 0
        if self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4:
            w.occur[w.verse].sort(key=lambda _x: _x[0])
            w.y = w.occur[w.verse][0][0]
            lenoccur = len(w.occur[w.verse])
            w.yend = w.occur[w.verse][lenoccur - 1][1]
            w.key = Rstp[_x][w.y:w.yend]
            lkey = len(w.key)
        elif self.dlg.checks[2] == 6:
            lkey = w.yend - w.y
            w.hiLita.length = lkey
        else:
            lkey = len(w.key)

        if self.dlg.checks[0] != 1:
            start = 0
            assert isinstance(w.y, int)
            end: int = w.y
            add = self.stripped_punctuation_adjust(ln, _x, start, end, True)
        lineinc = add

        ignore = [8217]
        litz = []
        lr = len(KJV[ln])
        for _ in range(lr):
            unich = ord(KJV[ln][_])
            if unich not in ignore and unich > 230:
                litz.append(_)
        j = 0
        for i in litz:
            if i < w.y + add:
                j += 1
        lineinc += j
        er = w.y + lkey
        endof = er + add
        w.hiLita.lineinc = lineinc
        self.keyinc_section(endof, add, ln, _x)

    def keyinc_section(self, endof: int, add: int, ln: int, current_position: int) -> None:
        """keyinc section."""

        unich = 32
        num = 0
        ignore = [8217]
        litz = []
        assert isinstance(w.y, int)
        start = w.y + add
        if self.dlg.checks[0] != 1:  # Not Raw
            end = start + len(w.key)  # change w.yend
            num = self.stripped_punctuation_adjust_ki(current_position, start, end)
        lav = len(KJV[ln])
        if not(start > lav or endof > lav):
            for i in range(start, endof + num):
                try:
                    unich = ord(KJV[ln][i])
                except IndexError:
                    pass
                if unich not in ignore and unich > 230:
                    litz.append(i)
        keyinc = len(litz) + num
        w.hiLita.keyinc = keyinc

    def display_verse(self, current_position: int) -> None:
        """Display Bible text in textEditor."""

        # print('display_verse')
        try:
            ln = int(next(islice(Amap, current_position, None)))
        except (StopIteration, TypeError, ValueError):
            ln = 0
        if current_position in starts_with_italics:  # Verses that start with italics.
            w.hiLita.keyinc = 1
        else:
            w.hiLita.keyinc = 0
        self.move_to_line(ln)
        self.display_verse_input.clear()
        if w.message == '':
            self.ref_to_statusbar(current_position)
        # Persist last known Bible position so reload() can restore accurately
        try:
            self._last_bible_position = int(current_position)
            self._last_context_position = int(current_position)
        except (TypeError, ValueError):
            pass

    def move_to_line(self, ln: int) -> None:
        """Display engine."""

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
                w.key = w.store

    def on_text_changed(self, ln: int) -> None:
        """Highlighting."""

        # print('on_text_changed')
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(linehighlightcolor))
        fmt.setForeground(QColor(linetextcolor))

        w.hiLita.clear = True
        w.hiLita.clear_highlight()

        try:
            if self.dlg is not None:
                if self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4:
                    w.store = w.key
                    w.hiLita.clear = False
                    keys = sorted(w.occur[w.verse])
                    current_position = Amap.index(ln)
                    for i in keys:
                        w.key = '+' * (i[1] - i[0])
                        w.y = i[0]
                        self.adjust_highlighting(ln, current_position)

            w.hiLita.setFormat(w.hiLita.position, w.hiLita.length, fmt)
            w.hiLita.highlight_line(ln, fmt)
        except ValueError:
            pass

    def se_display_verse(self, current_position: int) -> None:
        """Display Bible text in textEditor after a back or forward pop."""

        try:
            ln = int(next(islice(Amap, current_position, None)))
        except (StopIteration, TypeError, ValueError):
            ln = 0
        if current_position in starts_with_italics:  # Verses that start with italics.
            w.hiLita.keyinc = 1

        self.textEditor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(linehighlightcolor))
        fmt.setForeground(QColor(linetextcolor))
        w.hiLita.clear = True
        w.hiLita.clear_highlight()
        w.hiLita.setFormat(w.hiLita.position, w.hiLita.length, fmt)
        w.hiLita.highlight_line(ln, fmt)
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

        q1, q2, q3 = sh.Info[current_position][0], sh.Info[current_position][1] + 1, sh.Info[current_position][2] + 1
        message = w.message if w.message else format_status_message(q1, q2, q3)

        self.statusBar.showMessage(message)
        self.statusBar.repaint()

    # ---- Gill Commentary integration ----
    def _get_current_bcv(self) -> tuple[int, int, int]:
        """Return (book, chapter, verse) 1-based from the current context position."""
        try:
            pos = int(self._last_context_position) if getattr(self, "_last_context_position", 0) else int(self.get_line_number())
        except (TypeError, ValueError, AttributeError):
            pos = 0
        try:
            entry = sh.Info[pos]
            # Info stores [book(0..65), chapter(0..), verse(0..)]
            b = int(entry[0]) + 1
            c = int(entry[1]) + 1
            v = int(entry[2]) + 1
            return b, c, v
        except (IndexError, TypeError, ValueError):
            return 1, 1, 1

    def open_commentary_window(self) -> None:
        """Open or focus the Gill commentary window centered on the current verse."""
        # Resolve DB path in the application folder
        db_path = Path(sh.str_cwd) / "gill.cmt.sqlite"
        if not db_path.exists():
            try:
                QMessageBox.warning(self, "Commentary", f"Database not found:\n{db_path}")
            except (RuntimeError, TypeError):
                pass
            return

        b, c, v = self._get_current_bcv()
        # Note: previous usage of a local 'pos' (global verse index) was removed to satisfy linters
        # since we look up commentary by (book, chapter, verse) only.

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
            self._gill_win.show()
            self._gill_win.raise_()
            self._gill_win.activateWindow()
        except (RuntimeError, AttributeError, TypeError):
            pass

    # Auto-follow toggle removed from MainWindow.

    # ENTRY POINT FOR F2 DISPLAY VERSE.
    def goto_line(self, ref: str = '') -> None:
        """Move display to line requested."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        current_position: int = self.get_line_number()
        forward.clear()
        history.back_push(w, current_position)
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
        """Move display to line requested by comboBox_1."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        current_position = self.get_line_number()
        forward.clear()
        history.back_push(w, current_position)
        book: int = self.comboBox_1.currentIndex()
        # book is an index 0-65
        if book == sh.BOOKS_IN_THE_BIBLE - 1:
            b = 22  # Number of chapters in Revelation
        else:
            a: int = sh.Info.index([book + 1, 0, 0])
            b: int = sh.Info[a - 1][1] + 1  # No. of chapters in the book.
        w.nchapters = []
        for _ in range(1, b + 1):
            w.nchapters.append(str(_))
        self.comboBox_2.clear()
        self.comboBox_2.addItems(self.nchapters)
        self.comboBox_3.clear()
        self.nverses = ['1']
        self.comboBox_3.addItems(self.nverses)
        ref = w.nwin[book]
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
        """Move display to line requested by comboBox_2."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        book: int = self.comboBox_1.currentIndex()
        chapter: int = self.comboBox_2.currentIndex()
        if chapter == int(w.nchapters[-1]) - 1:
            # No. of verses in the chapter.
            if book == sh.BOOKS_IN_THE_BIBLE - 1:
                d = 21
            else:
                c: int = sh.Info.index([book + 1, 0, 0]) - 1
                d: int = sh.Info[c][2] + 1
        else:
            try:
                c = sh.Info.index([book, chapter + 1, 0]) - 1
            except ValueError:
                c = sh.Info.index([book + 1, 0, 0]) - 1
            d = sh.Info[c][2] + 1
        w.nverses = []
        for _ in range(1, d + 1):
            w.nverses.append(str(_))
        self.comboBox_3.clear()
        self.comboBox_3.addItems(self.nverses)

        ref = w.nwin[book]
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
        """Move display to line requested by comboBox_3."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        book: int = self.comboBox_1.currentIndex()
        chapter: int = self.comboBox_2.currentIndex()
        verse: int = self.comboBox_3.currentIndex()

        ref = w.nwin[book]
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

        # print(f"2367 Original reference_text: {reference_text}")

        # Clean up prefixes like 'Chap' to prevent incorrect matching
        # Also, remove spaces and convert ':' to '.'
        reference_text = fcs.clean_chap_prefix(reference_text)  # For example, 'Chap2:3' -> '2:3'
        # print(f"2372 After cleaning chapter prefix: {reference_text}")

        # Check for book names that are adjacent to roman chapter references.
        reference_text = fcs.check_roman_chapter_adjacent(reference_text)
        # For example, 'GenesisX.IV' -> 'Genesis.X.IV'

        # print(f"2376 After checking for adjacent book names: {reference_text}")

        # Letters like iv, ix, xl, xc, i, v, x, l, c, d, m,
        # which could be roman numerals need to be distinguished from book names here.
        # If they are alone, they are probably meant as book abbreviations:
        # e.g. i -> Isaiah, l -> Leviticus, c -> Colossians, d -> Deuteronomy and m -> Micah.
        roman_book: List = ['i', 'l', 'c', 'd', 'm']
        # So,
        if reference_text.lower() in roman_book:
            pass  # Here if it's a single letter that must not be converted to numeric.
        else:
            # Convert Roman numerals to numeric values
            reference_text = fcs.convert_roman_to_integer(reference_text)
            reference_text = reference_text.replace(' ', '')
        # print(f"2389 After converting Roman numerals: {reference_text}")

        # Check if the input is in a valid format:
        #   1. "book.chapter.verse" (e.g., genesis.1.2)
        #   2. "chapter.verse" (e.g. 3.4)
        #   3. A single integer (e.g. 7)
        reference_text = reference_text.replace(' ', '.')
        # print(f"2396 Reference Text: '{reference_text}'")

        if (re.match(r"^[1-4]?[a-zA-Z]+\.\d+\.\d+(,\d+)*$", reference_text)) or fcs.is_float_re(reference_text):

            # Input is preformatted, skip additional processing
            # print(f"2401 Input appears to be preformatted: {reference_text}")
            pass
        else:
            # Preprocess the input if it's not in the expected format
            # print(f"2404 Processed reference_text: {reference_text}")

            # Special handling for input formats like "Genesis2:3" or "Genesis2.3"
            pattern = r"^([1-4]?[a-zA-Z]+)(?:\s*|\.)?(\d+)?(?:[.:](\d+))?$"
            matched = re.match(pattern, reference_text)
            if not matched:
                message = "Invalid format. Please enter a valid reference."
                # print(f"2411 Input does not match the expected format: {reference_text}")
                self.on_error(message, 750, True)
                return -1  # Input is invalid

            # Extract the parts based on matched groups
            input_book = matched.group(1)  # Book name
            input_chapter = matched.group(2)  # Chapter (e.g., '3')
            input_verse = matched.group(3)  # Verse (e.g., '4')

            # Use the current context if 'book' or 'chapter' is missing
            book = input_book.strip() if input_book else book  # Default to the current book
            chapter = int(input_chapter) if input_chapter else str(int(chapter + 1))  # Default to current chapter
            verse = int(input_verse) if input_verse else '1'  # Verse stays as-is or '1'

            # Normalise the reference to the standard "book.chapter.verse" format
            if book not in sh.onechapterbooks:
                reference_text = f"{book}.{chapter}.{verse}"

            try:
                if sh.bibledict[book] - 1 in sh.onechapterbooks:
                    # print(f"2434 Book is in onechapterbooks: {book}")
                    # print(f"2435 book: {book}")
                    # print(f"2436 chapter: {chapter}")
                    # print(f"2437 verse: {verse}")
                    if chapter == 1:
                        reference_text = f"{book}.{chapter}.{verse}"
                    else:
                        verse = chapter
                        chapter = '1'
                        reference_text = f"{book}.{chapter}.{verse}"
            except KeyError:
                pass

            # print(f"2447 Fixed reference_text: {reference_text}")

        # Use the processed text for further resolving
        current_line = self.get_line_number()

        # Handle numeric-only references (e.g. "34")
        if self.is_integer(reference_text):
            verse = int(reference_text) - 1
            # print(f"2456 verse: {verse}")
            position = self.calculate_position(current_line, verse)
            # print(f"2458 position: {position}")
            return position  # If it is outside the current chapter, it stays in the same place.

        # Handle floating point-style references (e.g. "23.7")
        reference_text = reference_text.replace(":", ".")
        if fcs.is_float_re(reference_text):
            reference_text = fcs.attach_book_name(reference_text, current_line)

        # Split the reference into parts for resolving
        bits = fcs.split_reference(reference_text)
        # print(f"2469 Split reference: {bits}")

        book_num, chapter, verse = parse_ref(bits)
        # print(f"2064 book_num: {book_num} chapter: {chapter} verse: {verse}")

        if not book_num:
            self.error_invalid_book()

        if book_num is None or chapter is None or verse is None:
            return -1

        try:
            position = calc_line(book_num, chapter, verse, current_line)
            if position is not None:
                return position
        except ValueError:
            self.error_invalid_verse_or_position()

        # If no valid position was found, return -1
        return -1

    # Helper Methods

    @staticmethod
    def calculate_position(current_line: int, new_verse: int) -> int:
        """Calculate the absolute position of a verse from the current line.
           Only allows valid positions within the same chapter."""

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
            w.on_error(message, 750, True)
            return_value = current_line
        else:
            if new_chapter != current_chapter:
                # print("<<<<<<<<<<<<<<")
                w.on_error(message, 750, True)
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

        message: str = f"Not a book name."
        self.on_error(message, 750, True)
        # print(message)

    def error_invalid_verse_or_position(self):
        """Handle invalid chapter/verse errors."""

        message: str = f"Invalid chapter or verse."
        self.on_error(message, 750, True)
        # print(message)

    def get_line_number(self):
        """Find the line number of the verse at the top of the screen."""

        self.textEditor.moveCursor(QTextCursor.MoveOperation.StartOfLine)
        linenumber: int = self.textEditor.textCursor().blockNumber()
        if linenumber in Amap:
            current_position: int = Amap.index(linenumber)
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
                current_position = Amap.index(linenumber)

        return current_position

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Mouse trapping routine."""

        if event.buttons() == Qt.MouseButton.LeftButton:
            current_position: int = self.get_line_number()
            self.ref_to_statusbar(current_position)
        elif event.buttons() == Qt.MouseButton.RightButton:
            pass
        elif event.buttons() == Qt.MouseButton.MiddleButton and w.no_f3_yet == 1:
            self.repeat_find_forward()
        elif event.buttons() == Qt.MouseButton.MiddleButton and w.no_f3_yet == 0:
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

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        if w.key == ' ' or w.no_f3_yet == 0:
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
            self.se_display_verse(current_position)

    def history_forward(self) -> None:
        """Forward key."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        if len(forward) > 0:
            current_position: int = self.get_line_number()
            history.back_push(w, current_position)
            current_position = history.forward_pop(w)
            self.se_display_verse(current_position)

    def open_commentary_window_shortcut(self) -> None:
        """F9 Fullscreen toggle key."""

        self.toggle_fullscreen()

    def show_devotional(self) -> None:
        """F12 Devotional key."""

        self.display_secondary_window()

    @staticmethod
    def C() -> None:
        """Commentary key."""
        commentary()

    def question(self) -> None:
        """Feature key."""
        self.feature()

    def earlier_book(self) -> None:
        """Move to the earlier book."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        current_position: int = self.get_line_number()
        book: int = sh.Info[current_position][0]
        newbook: int = book - 1
        if newbook < 0:
            self.on_error('No earlier book!', 3000, True)
        else:
            current_position = sh.Info.index([newbook, 0, 0])
            forward.clear()
            history.back_push(w, current_position)
            self.display_verse(current_position)

    def later_book(self) -> None:
        """Move to the later book."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        current_position: int = self.get_line_number()
        book: int = sh.Info[current_position][0]
        newbook: int = book + 1
        if newbook > sh.BOOKS_IN_THE_BIBLE - 1:
            self.on_error('No later book!', 3000, True)
        else:
            current_position = sh.Info.index([newbook, 0, 0])
            forward.clear()
            history.back_push(w, current_position)
            self.display_verse(current_position)

    def earlier_chapter(self) -> None:
        """Move to the earlier chapter."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        current_position: int = self.get_line_number()
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
        current_position = sh.Info.index([book, newchapter, 0])
        forward.clear()
        history.back_push(w, current_position)
        self.display_verse(current_position)

    def later_chapter(self) -> None:
        """Move to the later chapter."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        current_position: int = self.get_line_number()
        book: int = sh.Info[current_position][0]
        chapter: int = sh.Info[current_position][1]
        newchapter: int = chapter + 1
        try:
            current_position = sh.Info.index([book, newchapter, 0])
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
        current_position = sh.Info.index([book, newchapter, 0])
        forward.clear()
        history.back_push(w, current_position)
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

                w.PCE_text = text_data
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
                    if EOTNOC and EOTNOC in w.PCE_text:
                        pos = w.PCE_text.find(EOTNOC)
                        if pos != -1:
                            w.PCE_text = w.PCE_text[pos + len(EOTNOC) + 1:]

                # Speed up large text injection by suspending updates/undo
                doc = None
                try:
                    self.textEditor.setUpdatesEnabled(False)
                    doc = self.textEditor.document()
                    try:
                        if doc is not None:
                            doc.setUndoRedoEnabled(False)
                    except (RuntimeError, AttributeError):
                        pass
                    self.textEditor.setPlainText(w.PCE_text)
                finally:
                    try:
                        if doc is not None:
                            doc.setUndoRedoEnabled(True)
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
                    w.otherFileFlag = False
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
                    w.otherFileFlag = True
                    # When opening non-Bible files, ensure any prior Bible highlighting is cleared
                    try:
                        if getattr(w, 'hiLita', None):
                            w.hiLita.clear = True
                            w.hiLita.clear_highlight()
                            # Reset clear flag so future highlights (when the Bible is reopened) work normally
                            w.hiLita.clear = False
                    except (AttributeError, RuntimeError):
                        # Be conservative; highlighting state is non-critical for auxiliary files
                        pass

    def file_print(self) -> None:
        """File print routine."""
        self.printing.print_plain_text(self.textEditor, parent=self)

    def update_title(self) -> None:
        """Title update routine."""

        if Path(self.path1).stem == 'KJB_PCE':
            self.setWindowTitle(f"  THE HOLY BIBLE      Authorized King James Version")
        else:
            title: str = f"{Path(self.path1).stem if self.path1 else ''}"
            title = title.replace("Pilgrims-Progress", "The Pilgrim's Progress by John Bunyan.")
            self.setWindowTitle(title)

    def open_settings_dialog(self):
        """Open the settings dialog.
          Option B behaviour:
        - Clicking 'Reset to defaults' applies defaults immediately (persist + theme and splash).
        - OK/Cancel then simply close the dialog; OK still saves any manual changes made after.
        """
        # Defer import to reduce startup/import-time cost
        from settings_dialog import SettingsDialog

        dialog = SettingsDialog(self, settings_service=self.settings_service)

        # Populate the settings dialog with current settings
        prev_show_splash = bool(self.settings.get("show_splash", False))
        dialog.splash_checkbox.setChecked(prev_show_splash)
        # Populate update-on-startup (default False if missing)
        try:
            dialog.update_checkbox.setChecked(bool(self.settings.get("check_updates_on_startup", False)))
        except (AttributeError, RuntimeError):
            pass
        try:
            dialog.unified_font_size_checkbox.setChecked(bool(self.settings.get("unified_font_size", False)))
        except (AttributeError, RuntimeError):
            pass
        dialog.theme_combobox.setCurrentText(self.settings.get("theme", "Light"))
        # Gill: Show scripture popups
        try:
            dialog.gill_show_popups_checkbox.setChecked(bool(self.settings_service.get_gill_show_popups()))
        except (RuntimeError, AttributeError, TypeError, ValueError):
            dialog.gill_show_popups_checkbox.setChecked(True)
        # Gill popup timing settings
        try:
            dialog.gill_hover_spin.setValue(int(self.settings_service.get_gill_hover_delay_ms()))
        except (RuntimeError, AttributeError, TypeError, ValueError):
            dialog.gill_hover_spin.setValue(120)
        try:
            dialog.gill_hide_spin.setValue(int(self.settings_service.get_gill_hide_delay_ms()))
        except (RuntimeError, AttributeError, TypeError, ValueError):
            dialog.gill_hide_spin.setValue(160)

        # Ensure dialog follows current theme palette
        self.theme.apply_widget(dialog)

        # Option B: apply defaults immediately when the reset button is clicked
        def _apply_defaults_immediately() -> None:
            # Read the current state to determine splash transition
            prev = bool(self.settings.get("show_splash", False))
            default_settings = fcs.get_default_settings()
            defaults_show_splash = bool(default_settings.get("show_splash", False))

            # Replace entire settings with defaults and persist immediately
            try:
                self.settings.clear()
                self.settings.update(default_settings)
            except (AttributeError, TypeError):
                # Fallback: replace the reference if clear/update fails for any reason
                self.settings = dict(default_settings)
            self.settings_service.save(self.settings)

            # Apply theme across UI right away
            self.set_theme(self.settings)

            # Manage splash visibility transitions immediately
            self._update_splash_visibility(prev, defaults_show_splash)

            # Prevent double-application on the OK path (Option A logic)
            dialog.was_reset_to_defaults = False

        try:
            dialog.reset_defaults_btn.clicked.connect(_apply_defaults_immediately)
        except (RuntimeError, AttributeError, TypeError):
            # Ignore failures to connect signal due to Qt object state or missing attributes
            pass

        # Connect the manual "Check for updates now" button: run the check on the UI thread
        # to present dialogs/feedback, then (if accepted) perform the heavy work in the background.
        try:
            from PySide6.QtCore import QThreadPool, QRunnable
            from updater import check_for_updates as _check_for_updates
            from updater import perform_update as _perform_update

            class _RunPerformUpdate(QRunnable):  # local class for this dialog session
                def __init__(self, version: str, exe_url: str) -> None:
                    super().__init__()
                    self.version = version
                    self.exe_url = exe_url

                def run(self) -> None:  # pragma: no cover - background task
                    try:
                        _perform_update(self.version, self.exe_url)
                    except (OSError, RuntimeError, ValueError):
                        # Silent failure; optional: print/log
                        pass

            def _on_update_now_clicked():
                # Run the check synchronously on the UI thread to allow QMessageBox dialogs
                try:
                    result = _check_for_updates(parent=dialog)
                except (RuntimeError, TypeError, ValueError):
                    result = None

                if not result:
                    # Either user declined, already up to date (info shown), or an error (warning shown)
                    return

                try:
                    update_available, version, exe_url = result
                except (TypeError, ValueError):
                    return

                if not update_available:
                    return

                # User accepted update; perform heavy work in the background
                try:
                    QThreadPool.globalInstance().start(_RunPerformUpdate(version, exe_url))
                except (RuntimeError, TypeError):
                    # As a last resort, perform on the current thread (may block)
                    try:
                        _perform_update(version, exe_url)
                    except (OSError, RuntimeError, ValueError):
                        pass

            dialog.update_now_btn.clicked.connect(_on_update_now_clicked)
        except (ImportError, AttributeError, RuntimeError, TypeError):
            # If we cannot wire the button (e.g. missing attrs), ignore gracefully
            pass

        if dialog.exec():  # If the dialog is accepted (OK button)
            # Determine new values; if the user pressed 'Reset to defaults', then use canonical defaults
            # (In Option B we set was_reset_to_defaults = False after immediate applying.)
            if getattr(dialog, "was_reset_to_defaults", False):
                defaults = fcs.get_default_settings()
                new_theme = defaults.get("theme", "Light")
                new_show_splash = bool(defaults.get("show_splash", False))
                # Also set update-on-startup from defaults to avoid uninitialised variable use
                new_update_on_start = bool(defaults.get("check_updates_on_startup", False))
                new_unified_font_size = bool(defaults.get("unified_font_size", False))
                new_gill_show_popups = bool(defaults.get("gill_show_popups", True))
                new_gill_hover = int(defaults.get("gill_hover_delay_ms", 120))
                new_gill_hide = int(defaults.get("gill_hide_delay_ms", 160))
            else:
                new_theme = dialog.theme_combobox.currentText()
                new_show_splash = dialog.splash_checkbox.isChecked()
                try:
                    new_update_on_start = bool(dialog.update_checkbox.isChecked())
                except (AttributeError, RuntimeError):
                    new_update_on_start = bool(self.settings.get("check_updates_on_startup", False))
                try:
                    new_unified_font_size = bool(dialog.unified_font_size_checkbox.isChecked())
                except (AttributeError, RuntimeError):
                    new_unified_font_size = bool(self.settings.get("unified_font_size", False))
                try:
                    new_gill_show_popups = bool(dialog.gill_show_popups_checkbox.isChecked())
                except (RuntimeError, AttributeError):
                    new_gill_show_popups = self.settings_service.get_gill_show_popups()
                try:
                    new_gill_hover = int(dialog.gill_hover_spin.value())
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    new_gill_hover = self.settings_service.get_gill_hover_delay_ms()
                try:
                    new_gill_hide = int(dialog.gill_hide_spin.value())
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    new_gill_hide = self.settings_service.get_gill_hide_delay_ms()

            # Update in-memory settings
            self.settings["theme"] = new_theme
            self.settings["show_splash"] = new_show_splash
            self.settings["check_updates_on_startup"] = new_update_on_start
            self.settings["unified_font_size"] = new_unified_font_size

            # If unified font size was just enabled, sync all font sizes to bible_font_size
            if new_unified_font_size:
                bible_size = self.settings_service.get_bible_font_size()
                self.settings_service.update_reader_font_size(bible_size)
                self.settings_service.update_devotional_font_size(bible_size)
                self.settings_service.update_commentary_font_size(bible_size)
                # Update in-memory settings to match
                self.settings["bible_font_size"] = bible_size
                self.settings["reader_font_size"] = bible_size
                self.settings["devotional_font_size"] = bible_size
                self.settings["gill_font_size"] = bible_size

            # Save settings via service
            self.settings_service.save(self.settings)

            # Persist Gill popup timing via SettingsService APIs
            try:
                self.settings_service.set_gill_hover_delay_ms(int(new_gill_hover))
                self.settings_service.set_gill_hide_delay_ms(int(new_gill_hide))
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass

            # Persist Gill show popups toggle
            try:
                self.settings_service.set_gill_show_popups(bool(new_gill_show_popups))
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass

            # Apply theme (if needed)
            self.set_theme(self.settings)

            # Manage splash visibility based on the checkbox change
            # Use module-level globals maintained by app.run()
            global splash, w
            # Update splash screen visibility based on prior and new states
            self._update_splash_visibility(prev_show_splash, new_show_splash)

            # If the Gill window is open, apply the new popup timing immediately
            try:
                if getattr(self, "_gill_win", None) is not None and isinstance(self._gill_win, GillCommentaryWindow):
                    self._gill_win.set_popup_timing(int(new_gill_hover), int(new_gill_hide))
                    # Also apply popups enabled/disabled immediately
                    self._gill_win.set_popups_enabled(bool(new_gill_show_popups))
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass

    @staticmethod
    def _update_splash_visibility(prev_show: bool, new_show: bool) -> None:
        """Show/hide the splash screen according to previous and new settings.
        Encapsulates the duplicated logic used in the Settings dialog flows.
        Safe against Qt object lifetime issues and missing resources.
        """
        global splash, w
        # Turning splash OFF: finish/close and clear the global reference
        if prev_show and not new_show:
            try:
                if splash is not None:
                    try:
                        splash.finish(w)
                    except (RuntimeError, AttributeError, TypeError):
                        # Be robust for type checkers and stub limitations: call close() if present
                        getattr(splash, 'close', lambda: None)()
            except (RuntimeError, AttributeError):
                pass
            splash = None
        # Turning splash ON: create if absent and show
        if (not prev_show) and new_show:
            try:
                if splash is None:
                    splash_path = sh.current_directory / "images" / "Abib_barley.png"
                    pix = QPixmap(str(splash_path))
                    # Use size().isEmpty() instead of isNull() to avoid stub/type warnings
                    new_splash = QSplashScreen(pix) if not pix.size().isEmpty() else QSplashScreen()
                    new_splash.show()
                    splash = new_splash
            except (RuntimeError, AttributeError, OSError):
                # Ignore failures to avoid disrupting the UI
                pass

    def _refresh_theme_across_ui(self) -> None:
        """Apply the app palette, style the main editor, update secondary windows, and
        re-theme any open dialogs/windows.
         Centralised to avoid duplication."""
        # Apply application-wide palette first so dialogs/menus follow suit
        self.theme.apply_app_palette()
        # Apply to the main editor and secondary window
        self.theme.apply_to_editor(self.textEditor)
        self.update_text_display_theme()
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
            try:
                self._gill_win.apply_theme(self.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            self.theme.apply_widget(self._gill_win)

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
            ref_h = int(ref_btn.sizeHint().height())
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
            try:
                ctrl.setFixedHeight(ref_h)
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

        # Get the SME text (from the sme method)
        try:
            sme_text = self.sme(offset)
        except (KeyError, IndexError, ValueError, TypeError) as e4:
            sme_text = f"Error: {e4}"

        if not self.secondary_window or not self.secondary_window.isVisible():
            # Create a new secondary window if it doesn't exist or is closed
            from windows import SecondaryWindow as ExtSecondaryWindow  # deferred import
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

    def sme(self, adjustment: int = 0) -> str:
        """C H Spurgeon's Morning and Evening Readings.

        Delegates to ReadingPlans service and navigates to the referenced scripture.
        """

        try:
            sme_text, sme_ref = self.reading_plans.get_sme(adjustment)
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


class SyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter."""

    def __init__(self, parent) -> None:
        """Initialise highlighter."""
        super(SyntaxHighlighter, self).__init__(parent)
        self._highlight_lines = {}
        self.lineinc = 0
        self.keyinc = 0
        self.position = 0
        self.length = 1
        self.fmt = None
        self.clear = False

    def highlight_line(self, line_num, fmt) -> None:
        """Highlight lines."""

        if isinstance(line_num, int) and \
                (line_num >= 0) and (isinstance(fmt, QTextCharFormat)):
            self._highlight_lines[line_num] = fmt
            block = self.document().findBlockByLineNumber(line_num)
            self.rehighlightBlock(block)

    def clear_highlight(self) -> None:
        """Clear highlight."""

        if self.clear:
            self._highlight_lines = {}
            self.rehighlight()

    def highlightBlock(self, text) -> None:
        """Highlight a block."""

        # Do not apply search/verse highlighting when viewing non-Bible files
        try:
            if getattr(w, 'otherFileFlag', False):
                return
        except (AttributeError, RuntimeError):
            # If the state is unavailable, fall through and rely on existing guards
            pass

        # Ensure _highlight_lines is populated
        if not self._highlight_lines:
            # print ("Skipping highlight: _highlight_lines not populated yet.")
            return

        blockNumber = self.currentBlock().blockNumber()
        self.fmt = self._highlight_lines.get(blockNumber)
        if self.fmt is not None:
            # noinspection PyTypeChecker
            self.position = w.y + self.lineinc
            if w.dlg is not None:
                if w.dlg.checks[2] != 6:
                    self.length = len(w.key) + self.keyinc
                else:
                    self.length += self.keyinc
            else:
                self.length = len(w.key) + self.keyinc
            self.setFormat(self.position, self.length, self.fmt)
            # print(f'Block {blockNumber} {KJV[blockNumber]}')


if __name__ == '__main__':
    # Bootstrap moved to app.run() for cleaner modularisation (PR10)
    from app import run
    run()
