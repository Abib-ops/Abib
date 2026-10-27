# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Unit tests for ``SearchController`` extracted from ``MainWindow``.

The controller only needs a window-like object exposing a handful of methods and
attributes, so it can be exercised with a lightweight stand-in instead of a full
Qt window — demonstrating the testability gained by moving the Find logic out of
``MainWindow``.
"""

import types
from unittest.mock import MagicMock

import pytest

import abib.Abib as abib_module
from abib.ui.search_controller import SearchController


def _make_window() -> MagicMock:
    """A minimal fake MainWindow for search tests."""
    win = MagicMock()
    win.message = ""
    return win


def _patch_history(monkeypatch) -> None:
    """Replace the module-level history/forward/back stacks."""
    monkeypatch.setattr(abib_module, "history", MagicMock())
    monkeypatch.setattr(abib_module, "forward", [])
    monkeypatch.setattr(abib_module, "back", [])


def test_close_find_window_hides_dialog():
    win = _make_window()
    SearchController(win).close_find_window()
    win.dlg.hide.assert_called_once()


def test_on_find_button_clicked_shows_existing_dialog():
    win = _make_window()
    # dlg already exists -> should route to show_find_window, not create a new one.
    win.dlg = MagicMock()
    ctrl = SearchController(win)
    ctrl.show_find_window = MagicMock()

    ctrl.on_find_button_clicked()

    win.reload.assert_called_once()
    ctrl.show_find_window.assert_called_once()


def test_find_next_whole_word_routes_to_find_f4_alt():
    win = _make_window()
    win.dlg.checks = [3, 0, 5]  # checks[0] != 1 -> whole-word path
    ctrl = SearchController(win)
    ctrl.find_f4_alt = MagicMock()
    ctrl.find_f4 = MagicMock()

    ctrl.find_next()

    ctrl.find_f4_alt.assert_called_once()
    ctrl.find_f4.assert_not_called()


def test_find_next_raw_without_generator_opens_find():
    win = _make_window()
    win.dlg.checks = [1, 0, 5]  # raw search
    win.gent = None
    ctrl = SearchController(win)

    ctrl.find_next()

    win.search_current_word.assert_called_once()


def test_find_next_raw_with_generator_routes_to_find_f4():
    win = _make_window()
    win.dlg.checks = [1, 0, 5]  # raw search
    win.gent = iter([(1, 2, 3)])
    ctrl = SearchController(win)
    ctrl.find_f4 = MagicMock()

    ctrl.find_next()

    ctrl.find_f4.assert_called_once()


def test_find_f4_raises_without_generator(monkeypatch):
    _patch_history(monkeypatch)
    win = _make_window()
    win.occurrence = 0
    win.occurring = 1
    win.get_line_number.return_value = 0
    win.gent = None

    with pytest.raises(ValueError):
        SearchController(win).find_f4()


def test_repeat_find_forward_noop_when_no_key():
    win = _make_window()
    win.key = ' '
    win.no_f3_yet = 1
    ctrl = SearchController(win)
    ctrl.find_next = MagicMock()

    ctrl.repeat_find_forward()

    win.reload.assert_called_once()
    ctrl.find_next.assert_not_called()


def test_repeat_find_forward_runs_find_next_when_key_present():
    win = _make_window()
    win.key = 'love'
    win.no_f3_yet = 1
    ctrl = SearchController(win)
    ctrl.find_next = MagicMock()

    ctrl.repeat_find_forward()

    win.textEditor.setFocus.assert_called_once()
    ctrl.find_next.assert_called_once()


def test_search_current_word_opens_find(monkeypatch):
    _patch_history(monkeypatch)
    win = _make_window()
    win.get_line_number.return_value = 5
    ctrl = SearchController(win)
    ctrl.on_find_button_clicked = MagicMock()

    ctrl.search_current_word()

    win.reload.assert_called_once()
    ctrl.on_find_button_clicked.assert_called_once()


def test_find_in_range_empty_key_clears_status(monkeypatch):
    _patch_history(monkeypatch)
    monkeypatch.setattr(abib_module, "book_bounds", [0, 10, 20, 30])
    win = _make_window()
    win.get_line_number.return_value = 0
    win.key = ' '  # empty key -> no search performed, "Not found" path
    win.occurring = 0
    win.dlg.checks = [1, 0, 5]
    win.display_verse_input = types.SimpleNamespace(clear=MagicMock())

    SearchController(win).find_in_range(0, 1)

    # With an empty key, nothing is found and an error is surfaced.
    win.on_error.assert_called_once_with('Not found...', 2000, True)
    win.update_search_results_panel.assert_called_once()
