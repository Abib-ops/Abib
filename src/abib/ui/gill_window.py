# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

import re
import sqlite3
import time
from itertools import islice
from pathlib import Path
from typing import Any

from PySide6.QtCore import QEvent, QPoint, Qt
from PySide6.QtGui import QKeySequence, QMouseEvent, QShortcut, QWheelEvent
from PySide6.QtWidgets import QGridLayout, QPushButton, QTextEdit, QWidget

from abib.core import shared as sh
from abib.domain import scripture_refs
from abib.services.settings import SettingsService
from abib.ui.ui_helpers import SimpleScripturePopup


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
        self._settings_service: SettingsService = settings_service if settings_service is not None else SettingsService()

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
            from abib import Abib
            w = Abib.w
            if hasattr(w, "textEditor") and getattr(w, "textEditor", None) is not None:
                self.viewer.setFont(w.textEditor.font())
                # Also, enforce as the document default so HTML respects app font
                try:
                    self.viewer.document().setDefaultFont(self.viewer.font())
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    pass
        except (ImportError, RuntimeError, AttributeError, TypeError, ValueError):
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

        # Set the initial font size from settings and apply as both widget and document font
        try:
            fs = int(self._settings_service.get_commentary_font_size())
            fs = max(fs, 8)
            fs = min(fs, 40)
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

    def _persist_geometry(self) -> None:
        """Persist the current window geometry to settings."""
        try:
            geom = self.geometry()
            assert self._settings_service is not None
            self._settings_service.save_window_geometry(
                "gill_commentary_window", int(geom.x()), int(geom.y()), int(geom.width()), int(geom.height())
            )
        except (RuntimeError, TypeError, ValueError, AssertionError):
            pass

    # --------- DB helpers ---------
    def _ensure_conn(self) -> sqlite3.Connection | None:
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
        self._persist_geometry()
        self._conn = None
        super().closeEvent(event)

    # Persist geometry on move/resize
    def moveEvent(self, event):  # type: ignore[override]
        self._persist_geometry()
        try:
            return super().moveEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def resizeEvent(self, event):  # type: ignore[override]
        self._persist_geometry()
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
            x = scripture_refs.calculate_book_line(book, chapter, verse, 0)
        except (TypeError, ValueError):
            x = 0
        self.set_position(x)

    def set_position(self, x: int) -> None:
        """Set the current global verse index and display its commentary."""
        try:
            x = int(x)
        except (TypeError, ValueError):
            x = 1
        x = max(x, 0)
        x = min(x, sh.LAST_VERSE_IN_BIBLE)
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
            conn = self._ensure_conn()
            assert conn is not None
            cur = conn.cursor()
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
            assert sh is not None
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
            from abib import Abib
            w = Abib.w
            title_ref = f"{b + 1} {c}:{v_title}"
            if w is not None and hasattr(w, "nwin"):
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
        except (ImportError, RuntimeError, TypeError, ValueError):
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
        s = max(s, 8)
        s = min(s, 40)
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
                from abib import Abib
                w = Abib.w
                # Use a local reference with a type hint to satisfy the linter
                if w is not None:
                    win: Any = w
                    # Only notify if the main window's font size is different
                    if hasattr(win, "apply_font_size") and win.settings_service.get_bible_font_size() != s:
                        win.settings_service.update_bible_font_size(s)
                        win.apply_font_size()

            # Refresh the display to apply the new font size to the HTML content
            self._display_current()
        except (ImportError, RuntimeError, TypeError, ValueError):
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
                        if ph is not None:
                            helper: Any = ph
                            if helper.is_visible() and isinstance(event, QWheelEvent):
                                helper.scroll_by(event.angleDelta().y())
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
                                                is_vis = bool(ph.is_visible and ph.is_visible())  # type: ignore[attr-defined]
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
                                from abib import Abib
                                w = Abib.w
                                if bcv is not None and w is not None:
                                    win: Any = w
                                    if hasattr(win, 'move_to_line') and callable(win.move_to_line):
                                        b, c, v = bcv
                                        try:
                                            current_ln = win.get_line_number() if hasattr(win, 'get_line_number') else 0
                                        except (RuntimeError, AttributeError, TypeError, ValueError):
                                            current_ln = 0
                                        try:
                                            idx = scripture_refs.calculate_book_line(b, c, v, current_ln)
                                            win.display_verse(int(idx))
                                            # For commentary links (#c), also update the Gill window itself
                                            if href.lstrip().startswith(('#c', '#C')):
                                                self.set_position(int(idx))
                                        except (RuntimeError, AttributeError, TypeError, ValueError):
                                            pass
                                self._close_popup()
                                return True
                    except (ImportError, RuntimeError, AttributeError, TypeError, ValueError):
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
        """Parse Gill anchors hrefs robustly and returns verse text plus canonical reference."""
        try:
            # Fast path: return from cache if available
            try:
                cached = self._ref_cache.get(href)
                if cached:
                    return cached
            except (RuntimeError, AttributeError, TypeError, ValueError):
                # If cache not present (older object), create it lazily
                try:
                    self._ref_cache = {}
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    pass
            header = self._split_href_header(href)
            if header is None:
                return None
            b, c, versespec = header
            # Normalise: replace en/em dashes, strip spaces, remove trailing punctuation and letter suffixes
            versespec = versespec.replace('–', '-').replace('—', '-')
            versespec = versespec.strip()
            # Drop trailing punctuation
            versespec = re.sub(r"[ ,;:.')\]}\"”」]+$", "", versespec)
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
            from abib import Abib
            for v in verses_ordered:
                x = self._global_index_for_bcv(b, c, v)
                if x is None:
                    continue
                try:
                    ln = int(next(islice(Abib.Amap, x, None)))
                    texts.append(Abib.KJV[ln])
                except (StopIteration, TypeError, ValueError, IndexError, AttributeError):
                    continue
            if not texts:
                return None

            # Compose canonical reference line
            try:
                book_name = str(b)
                w = Abib.w
                if w is not None and hasattr(w, 'nwin'):
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
                if len(self._ref_cache) > 256:
                    self._ref_cache.clear()
                self._ref_cache[href] = result
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass
            return result
        except (ImportError, RuntimeError, AttributeError, TypeError, ValueError):
            return None

    @staticmethod
    def _split_href_header(href: str) -> tuple[int, int, str] | None:
        """Parse a Gill href into (book, chapter, versespec); returns None if invalid."""
        s = href.strip()
        if not s:
            return None
        # Trim leading '#'
        s = s.removeprefix('#')
        # Tolerate leading 'b', 'B', 'c' or 'C'
        if s and (s[0] in ('b', 'B', 'c', 'C')):
            s = s[1:]
        parts = s.split('.')
        if len(parts) < 2:
            return None
        try:
            b = int(parts[0])
            c = int(parts[1])
        except (TypeError, ValueError):
            return None
        versespec = parts[2] if len(parts) >= 3 else '1'
        return b, c, versespec

    @staticmethod
    def _parse_href_to_bcv(href: str) -> tuple[int, int, int] | None:
        """Return the first verse target (book, chapter, verse) from a Gill href."""
        try:
            header = GillCommentaryWindow._split_href_header(href)
            if header is None:
                return None
            b, c, vpart = header
            vpart = vpart.replace('–', '-').replace('—', '-').strip()
            vpart = re.sub(r"[ ,;:.')\]}\"”」]+$", "", vpart)
            if not vpart:
                vpart = '1'
            first_seg = vpart.split(',')[0].strip()
            first_seg = re.sub(r"(?i)[a-z]+$", "", first_seg).strip()
            if '-' in first_seg:
                first_seg = first_seg.split('-', 1)[0].strip()
            v = int(first_seg)
            v = max(v, 1)
            return b, c, v
        except (TypeError, ValueError, IndexError, AttributeError):
            return None

    @staticmethod
    def _global_index_for_bcv(b: int, c: int, v: int) -> int | None:
        """Resolve (book, chapter, verse) 1-based to global index using sh.Info."""
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
            assert self._popup_helper is not None
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
        """Enable/disable scripture popups at runtime."""
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
        """Update popup timing (hover/hide delays) at runtime."""
        try:
            h = int(hover_ms)
        except (TypeError, ValueError):
            h = self._hover_delay_ms
        try:
            d = int(hide_ms)
        except (TypeError, ValueError):
            d = self._hide_delay_ms
        # Clamp
        h = max(h, 0)
        h = min(h, 5000)
        d = max(d, 0)
        d = min(d, 5000)
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
        candidates = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))
        for dx, dy in candidates:
            try:
                pt = p
                if hasattr(p, 'x') and hasattr(p, 'y'):
                    pt = QPoint(p.x() + dx, p.y() + dy)
                href = self.viewer.anchorAt(pt)
            except (RuntimeError, AttributeError, TypeError, ValueError):
                href = ""
            if isinstance(href, str) and href.lstrip().startswith(("#b", "#B", "#c", "#C")):
                return href
        return ""
