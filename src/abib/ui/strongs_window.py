# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""A verse-by-verse Strong's-number / original-language lookup window.

This top-level window is a companion to :class:`~abib.ui.gill_window.GillCommentaryWindow`
and reuses the same conventions (geometry/font persistence via
:class:`~abib.services.settings.SettingsService`, ``Ctrl+`` / ``Ctrl-`` zoom,
theme awareness).  It is driven by :class:`~abib.services.strongs_service.StrongsService`.

The window shows, for the current verse, every Strong's-tagged word as a
clickable link.  Clicking a word (or typing a code such as ``H0430`` in the
lookup box) shows the full dictionary entry — lemma in the original script,
transliteration, pronunciation, short/long definitions and the total number of
occurrences across the Bible.

If ``strongs.sqlite`` is missing the service degrades gracefully and the window
simply reports that the data is unavailable rather than crashing.
"""

from __future__ import annotations

from html import escape
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QMouseEvent, QShortcut
from PySide6.QtWidgets import (
    QGridLayout,
    QLineEdit,
    QPushButton,
    QTextEdit,
    QWidget,
)

from abib.core import shared as sh
from abib.services.settings import SettingsService
from abib.services.strongs_service import StrongsService

GEOMETRY_KEY = "strongs_window"


class StrongsWindow(QWidget):
    """A simple verse-by-verse Strong's / original-language reader."""

    def __init__(
        self,
        service: StrongsService | None = None,
        parent: QWidget | None = None,
        settings_service: SettingsService | None = None,
    ) -> None:
        # Force this widget to be a top-level window regardless of parent.
        super().__init__(parent if parent is None else None)
        self._service: StrongsService = service if service is not None else StrongsService()
        self._settings_service: SettingsService = (
            settings_service if settings_service is not None else SettingsService()
        )
        # Current global verse index within Abib (0 to LAST_VERSE_IN_BIBLE).
        self._x: int = 0
        # The Strong's code currently shown in the detail panel (if any).
        self._current_code: str | None = None
        self._is_dark: bool = False

        self.setWindowTitle("Strong's Lookup")
        try:
            self.setWindowFlag(Qt.WindowType.Window, True)
        except (RuntimeError, AttributeError, TypeError):
            pass

        # Restore saved geometry (position and size).
        try:
            gx, gy, gw, gh = self._settings_service.get_window_geometry(GEOMETRY_KEY)
            self.setGeometry(gx, gy, gw, gh)
        except (RuntimeError, TypeError, ValueError):
            try:
                self.resize(480, 560)
            except (RuntimeError, TypeError, ValueError):
                pass

        layout = QGridLayout(self)

        # Top viewer: the tagged words of the current verse (clickable links).
        self.words_view = QTextEdit(self)
        self.words_view.setReadOnly(True)
        try:
            self.words_view.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except (AttributeError, RuntimeError, TypeError):
            pass
        layout.addWidget(self.words_view, 0, 0, 1, 3)

        # Lookup box: type a code (e.g. H0430 / G3056) and press Enter.
        self.code_input = QLineEdit(self)
        self.code_input.setPlaceholderText("Enter a Strong's number, e.g. H0430 or G3056")
        self.code_input.returnPressed.connect(self._on_code_entered)
        layout.addWidget(self.code_input, 1, 0, 1, 3)

        # Detail viewer: the dictionary entry for the selected code.
        self.detail_view = QTextEdit(self)
        self.detail_view.setReadOnly(True)
        try:
            self.detail_view.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        except (AttributeError, RuntimeError, TypeError):
            pass
        layout.addWidget(self.detail_view, 2, 0, 1, 3)

        # "Find all occurrences" button.
        self.btn_find = QPushButton("Find all occurrences", self)
        self.btn_find.clicked.connect(self._on_find_occurrences)
        self.btn_find.setEnabled(False)
        layout.addWidget(self.btn_find, 3, 0, 1, 3)

        # Navigation / close row.
        self.btn_prev = QPushButton("◀ Prev", self)
        self.btn_next = QPushButton("Next ▶", self)
        self.btn_close = QPushButton("Close", self)
        self.btn_prev.clicked.connect(self._on_prev)
        self.btn_next.clicked.connect(self._on_next)
        self.btn_close.clicked.connect(self.close)
        layout.addWidget(self.btn_prev, 4, 0)
        layout.addWidget(self.btn_close, 4, 1)
        layout.addWidget(self.btn_next, 4, 2)

        # Apply the initial font size from settings.
        try:
            fs = int(self._settings_service.get_strongs_font_size())
            self._apply_font_to_widgets(fs)
        except (TypeError, ValueError):
            pass

        # Optional callback used by "Find all occurrences" to hand the verse
        # indices off to the main window's search-results display.  When unset,
        # the button simply reports the total count in the detail panel.
        self.on_find_occurrences: Any | None = None

        # Keyboard shortcuts for zooming (Ctrl++ / Ctrl+= / Ctrl+-).
        self._shortcuts: list[QShortcut] = []
        try:
            for seq in ("Ctrl++", "Ctrl+="):
                sc = QShortcut(QKeySequence(seq), self)
                sc.activated.connect(self.increase_font_size)
                self._shortcuts.append(sc)
            sc_dec = QShortcut(QKeySequence("Ctrl+-"), self)
            sc_dec.activated.connect(self.decrease_font_size)
            self._shortcuts.append(sc_dec)
        except (RuntimeError, TypeError, ValueError):
            pass

        # Enable click-to-lookup on the word list viewer.
        try:
            self.words_view.viewport().installEventFilter(self)
        except (RuntimeError, AttributeError):
            pass

    # --------- Theme ---------
    def apply_theme(self, is_dark: bool) -> None:
        """Update the viewers' colours to match the application theme."""
        self._is_dark = is_dark
        try:
            if is_dark:
                style = "QTextEdit { background-color: #121212; color: #ffffff; }"
            else:
                style = "QTextEdit { background-color: #ffffff; color: #000000; }"
            self.words_view.setStyleSheet(style)
            self.detail_view.setStyleSheet(style)
        except (RuntimeError, AttributeError):
            pass
        # Re-render the current content so the inline word/number colours
        # (baked into the HTML) match the new theme. Without this, switching
        # to dark mode leaves black word text on the dark background because
        # the words were rendered before the theme was applied.
        try:
            self._display_current()
            if self._current_code:
                self._display_entry(self._current_code)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    # --------- Geometry persistence ---------
    def _persist_geometry(self) -> None:
        try:
            geom = self.geometry()
            self._settings_service.save_window_geometry(
                GEOMETRY_KEY, int(geom.x()), int(geom.y()), int(geom.width()), int(geom.height())
            )
        except (RuntimeError, TypeError, ValueError, AssertionError):
            pass

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

    def closeEvent(self, event):  # type: ignore[override]
        self._persist_geometry()
        try:
            self._service.close()
        except (RuntimeError, AttributeError):
            pass
        super().closeEvent(event)

    # --------- Public API ---------
    def set_position(self, x: int) -> None:
        """Set the current global verse index and display its tagged words."""
        try:
            x = int(x)
        except (TypeError, ValueError):
            x = 0
        x = max(x, 0)
        x = min(x, sh.LAST_VERSE_IN_BIBLE)
        self._x = x
        self._display_current()

    def show_word(self, x: int, code: str) -> None:
        """Focus the window on verse *x* and display the entry for *code*.

        Used by the main window when the user clicks a Strong's-tagged word in
        the Bible text, so the lookup window jumps straight to that word.
        """
        self.set_position(x)
        code = (code or "").strip()
        if not code:
            return
        try:
            self.code_input.setText(code)
        except (RuntimeError, AttributeError):
            pass
        self._display_entry(code)

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

    # --------- Rendering ---------
    def _verse_title(self) -> str:
        """Return a human-readable reference (e.g. "Genesis 1:1") for the current verse."""
        try:
            entry = sh.Info[self._x]
            b = int(entry[0])
            c = int(entry[1]) + 1
            v = int(entry[2]) + 1
        except (IndexError, TypeError, ValueError):
            return "Strong's Lookup"
        try:
            from abib import Abib
            w = Abib.w
            if w is not None and hasattr(w, "nwin"):
                book_str = w.nwin[int(b)]
                if book_str:
                    if int(b) in getattr(sh, "onechapterbooks", ()):
                        return f"{book_str} {v}"
                    return f"{book_str} {c}:{v}"
        except (ImportError, RuntimeError, TypeError, ValueError, IndexError, AttributeError):
            pass
        return f"{b + 1} {c}:{v}"

    def _display_current(self) -> None:
        """Render the tagged words of the current verse into the top viewer."""
        title = self._verse_title()
        self.setWindowTitle(f"Strong's Lookup — {title}")

        if not self._service.is_available():
            self.words_view.setHtml(
                "<p>Strong's data is unavailable (strongs.sqlite not found).</p>"
            )
            self.detail_view.setPlainText("")
            self.btn_find.setEnabled(False)
            return

        tags = self._service.get_tags_for_verse(self._x)
        if not tags:
            self.words_view.setHtml(
                f"<p><b>{escape(title)}</b></p>"
                "<p>No Strong's tagging available for this verse.</p>"
            )
            return

        # Colour the tagged words the same as the main-window Bible text
        # (black in light mode, white in dark mode) instead of the default
        # link blue, so the word list matches the Bible reading view. The
        # Strong's-number superscript uses a green that stays readable on
        # both backgrounds (a brighter green in dark mode).
        word_color = "#ffffff" if self._is_dark else "#000000"
        number_color = "#81c995" if self._is_dark else "#188038"
        parts: list[str] = [f"<p><b>{escape(title)}</b></p><p>"]
        for tag in tags:
            surface = escape(tag.surface) if tag.surface else "&nbsp;"
            if not tag.strongs:
                # Trailing/untagged text (e.g. "any" in Proverbs 30:30): show
                # the word as plain text, with no Strong's number or link.
                parts.append(f"{surface} ")
                continue
            code = escape(tag.strongs)
            # Each word links to its own code; a superscript shows the number.
            parts.append(
                f'<a href="{code}" style="color:{word_color};text-decoration:none;">{surface}</a>'
                f'<sup><a href="{code}" style="color:{number_color};text-decoration:none;">'
                f'{code}</a></sup> '
            )
        parts.append("</p>")
        self.words_view.setHtml("".join(parts))

    def _display_entry(self, code: str) -> None:
        """Render the dictionary entry for *code* into the detail viewer."""
        entry = self._service.lookup_strongs(code)
        if entry is None:
            self.detail_view.setHtml(
                f"<p>No dictionary entry found for <b>{escape(code)}</b>.</p>"
            )
            self._current_code = None
            self.btn_find.setEnabled(False)
            return

        self._current_code = entry.strongs
        count = self._service.count_occurrences(entry.strongs)
        lang = entry.language.capitalize() if entry.language else ""
        header_bits = [b for b in (entry.translit, entry.pronunciation, lang) if b]
        header = " · ".join(escape(b) for b in header_bits)

        html = [f"<h2>{escape(entry.strongs)} — {escape(entry.lemma)}</h2>"]
        if header:
            html.append(f"<p><b>{header}</b></p>")
        if entry.short_def:
            html.append(f"<p>{escape(entry.short_def)}</p>")
        if entry.long_def:
            html.append(f"<p>{escape(entry.long_def)}</p>")
        html.append(f"<p><i>Occurs {count} time{'s' if count != 1 else ''} in the Bible.</i></p>")
        self.detail_view.setHtml("".join(html))
        self.btn_find.setEnabled(count > 0)

    # --------- Interaction ---------
    def eventFilter(self, obj, event):  # type: ignore[override]
        try:
            if obj is self.words_view.viewport() and (
                event.type() == event.Type.MouseButtonRelease
                and isinstance(event, QMouseEvent)
            ):
                qp = event.position().toPoint()
                href = self.words_view.anchorAt(qp)
                if href:
                    self._display_entry(href)
                    return True
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            return super().eventFilter(obj, event)
        except (RuntimeError, AttributeError, TypeError):
            return False

    def _on_code_entered(self) -> None:
        code = self.code_input.text().strip()
        if code:
            self._display_entry(code)

    def _on_find_occurrences(self) -> None:
        code = self._current_code
        if not code:
            return
        verses = self._service.find_verses_by_strongs(code)
        if callable(self.on_find_occurrences):
            try:
                self.on_find_occurrences(code, verses)
                return
            except (RuntimeError, TypeError, ValueError, AttributeError):
                pass
        # Fallback: report the count in the detail panel.
        self.detail_view.append(
            f"<p><i>{escape(code)} occurs in {len(verses)} verse"
            f"{'s' if len(verses) != 1 else ''}.</i></p>"
        )

    # --------- Font size controls ---------
    def _apply_font_to_widgets(self, size: int) -> None:
        try:
            s = int(size)
        except (TypeError, ValueError):
            s = 12
        s = max(s, 8)
        s = min(s, 40)
        for view in (self.words_view, self.detail_view):
            try:
                fnt = view.font()
                fnt.setPointSize(s)
                view.setFont(fnt)
                view.document().setDefaultFont(fnt)
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass

    def apply_font_size(self, size: int) -> None:
        try:
            s = int(size)
        except (TypeError, ValueError):
            s = 12
        s = max(s, 8)
        s = min(s, 40)
        current = self.words_view.font().pointSize()
        if current == s:
            return
        self._apply_font_to_widgets(s)
        try:
            self._settings_service.update_strongs_font_size(s)
        except (RuntimeError, TypeError, ValueError):
            pass
        # Re-render so HTML content picks up the new size.
        self._display_current()
        if self._current_code:
            self._display_entry(self._current_code)

    def increase_font_size(self) -> None:
        try:
            current = int(self.words_view.font().pointSize())
        except (TypeError, ValueError):
            current = 12
        self.apply_font_size(current + 1)

    def decrease_font_size(self) -> None:
        try:
            current = int(self.words_view.font().pointSize())
        except (TypeError, ValueError):
            current = 12
        self.apply_font_size(current - 1)
