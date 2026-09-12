# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Search-Results window manager extracted from ``MainWindow``.

Owns the separate Search Results window: its creation, width handling and the
geometry logic that keeps it glued to the right of the main window. ``MainWindow``
keeps thin delegators (including the ``moveEvent``/``resizeEvent`` hooks and the
``_update_search_results_panel`` entry point used by the search flow).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from abib.core import shared as sh

if TYPE_CHECKING:
    from abib.Abib import MainWindow

# QWidget maximum size sentinel (QWIDGETSIZE_MAX)
QWIDGETSIZE_MAX = 16777215
# Default Search Results window width (px) when no preference is stored
DEFAULT_SEARCH_RESULTS_WIDTH = 400


class SearchResultsWindowManager:
    """Encapsulate the Search Results window lifecycle and geometry."""

    def __init__(self, window: MainWindow) -> None:
        self._win = window

    def setup_search_results_panel(self) -> None:
        """Create the separate Search Results window."""
        from abib.ui.search_results import SearchResultsWindow  # deferred import

        win = self._win
        win.search_results_window = SearchResultsWindow(win, win.settings_service)
        win.search_results_window.resultActivated.connect(win.on_search_result_activated)
        win.search_results_window.hide()

    def search_results_width(self) -> int:
        """Return the persisted width (in pixels) for the Search Results window."""
        win = self._win
        if win.settings_service is None:
            return DEFAULT_SEARCH_RESULTS_WIDTH
        try:
            return int(win.settings_service.get_search_results_width())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return DEFAULT_SEARCH_RESULTS_WIDTH

    def release_main_width_limit(self) -> None:
        """Remove the width cap that reserves room for the Search Results window."""
        win = self._win
        try:
            win.setMaximumWidth(QWIDGETSIZE_MAX)
        except (RuntimeError, AttributeError):
            pass

    def position_search_results_window(self) -> None:
        """Glue the Search Results window to the right of the main window.

        The main window's width is capped (and shrunk if necessary) so that the
        Search Results window always fits on screen; a maximised/fullscreen main
        window is restored to a normal size to make room.
        """
        win = self._win
        results: Any = getattr(win, "search_results_window", None)
        if results is None:
            return
        if win.positioning_search_results:
            return
        win.positioning_search_results = True
        try:
            panel_width = self.search_results_width()
            try:
                screen = win.screen().availableGeometry()
            except (AttributeError, RuntimeError):
                from PySide6.QtWidgets import QApplication
                screen = QApplication.primaryScreen().availableGeometry()

            # Un-maximise so the main window can make room on the right.
            if win.isMaximized() or win.isFullScreen():
                win.showNormal()

            # Cap the main window width so the results window always fits.
            max_main_width = max(300, screen.width() - panel_width)
            win.setMaximumWidth(max_main_width)

            geo = win.geometry()
            if geo.width() > max_main_width:
                win.resize(max_main_width, geo.height())
                geo = win.geometry()

            # Keep the main window far enough left to leave room on the right.
            max_left = screen.right() - panel_width - geo.width() + 1
            if geo.left() > max_left:
                win.move(max(screen.left(), max_left), geo.top())
                geo = win.geometry()

            results.setGeometry(geo.right() + 1, geo.top(), panel_width, geo.height())
        finally:
            win.positioning_search_results = False

    def update_search_results_panel(self) -> None:
        """Populate the Search Results window from the current search state."""
        win = self._win
        dock = win.search_results_window
        if dock is None:
            return
        if win.dlg is None or win.occurring == 0 or not win.occurs:
            dock.clear_results()
            dock.hide()
            self.release_main_width_limit()
            return

        from abib.Abib import KJV, Amap
        from abib.ui.search_results import (
            SearchResult,
            format_reference,
            highlight_result_text,
            result_verse_text,
        )

        search_text = win.keym or win.key
        search_mode = win.dlg.checks[0]
        case_sensitive = win.dlg.checks[1] == 1
        results: list[SearchResult] = []
        for current_position in win.occurs:
            try:
                verse_text = result_verse_text(current_position, KJV, Amap)
                reference = format_reference(current_position, sh.Info, win.nwin, sh.onechapterbooks)
            except (IndexError, TypeError, ValueError):
                continue
            html_text = highlight_result_text(verse_text, search_text, search_mode, case_sensitive)
            results.append(SearchResult(current_position, reference, verse_text, html_text))

        if results:
            dock.set_results(results, search_text)
            # Suppress width persistence while the window is shown and positioned
            # programmatically; otherwise the transient natural size (~100px) that
            # Qt applies on show() would overwrite the saved preference.
            dock._positioning = True
            try:
                dock.show()
                self.position_search_results_window()
            finally:
                dock._positioning = False
            dock.raise_()
        else:
            dock.clear_results()
            dock.hide()
            self.release_main_width_limit()

    def reposition_search_results_window(self) -> None:
        """Keep the Search Results window glued to the main window when visible."""
        win = self._win
        if win.positioning_search_results:
            return
        results: Any = getattr(win, "search_results_window", None)
        if results is not None and results.isVisible():
            self.position_search_results_window()
