# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Unit tests for ``NavigationController`` extracted from ``MainWindow``.

The controller only needs a window-like object exposing a handful of methods and
attributes, so it can be exercised with a lightweight stand-in instead of a full
Qt window — demonstrating the testability gained by moving verse navigation out
of ``MainWindow``.
"""

import types
from unittest.mock import MagicMock

import abib.Abib as abib_module
from abib.core import shared as sh
from abib.ui.navigation_controller import NavigationController


def _make_window() -> MagicMock:
    """A minimal fake MainWindow for navigation tests."""
    win = MagicMock()
    win.message = ""
    return win


def _patch_module_state(monkeypatch) -> None:
    """Replace the module-level history/forward and reset_attributes helpers."""
    fake_history = MagicMock()
    fake_forward = MagicMock()
    fake_back = MagicMock()
    monkeypatch.setattr(abib_module, "history", fake_history)
    monkeypatch.setattr(abib_module, "forward", fake_forward)
    monkeypatch.setattr(abib_module, "back", fake_back)
    monkeypatch.setattr(abib_module, "reset_attributes", MagicMock())


def test_earlier_book_at_genesis_reports_error(monkeypatch):
    _patch_module_state(monkeypatch)
    win = _make_window()
    # Position 0 -> Genesis (book index 0); there is no earlier book.
    win.get_line_number.return_value = 0
    monkeypatch.setattr(sh, "Info", [(0, 0, 0)])

    NavigationController(win).earlier_book()

    win.on_error.assert_called_once_with("No earlier book!", 3000, True)
    win.display_verse.assert_not_called()


def test_later_book_past_last_reports_error(monkeypatch):
    _patch_module_state(monkeypatch)
    win = _make_window()
    win.get_line_number.return_value = 0
    # Report the current book as the final book in the Bible.
    last = sh.BOOKS_IN_THE_BIBLE - 1
    monkeypatch.setattr(sh, "Info", [(last, 0, 0)])

    NavigationController(win).later_book()

    win.on_error.assert_called_once_with("No later book!", 3000, True)
    win.display_verse.assert_not_called()


def test_later_book_moves_to_next_book(monkeypatch):
    _patch_module_state(monkeypatch)
    win = _make_window()
    win.get_line_number.return_value = 0
    # Current book 0; book 1 starts at index 5.
    info = [(0, 0, 0), (0, 1, 1), (0, 1, 2), (0, 1, 3), (0, 1, 4), (1, 0, 0)]
    monkeypatch.setattr(sh, "Info", info)

    NavigationController(win).later_book()

    win.on_error.assert_not_called()
    win.display_verse.assert_called_once_with(5)


def test_history_forward_empty_stack_does_nothing(monkeypatch):
    _patch_module_state(monkeypatch)
    # An empty forward stack: len(forward) == 0, so no navigation happens.
    monkeypatch.setattr(abib_module, "forward", [])
    win = _make_window()

    NavigationController(win).history_forward()

    win.reload.assert_called_once()
    win.display_verse_from_history.assert_not_called()


def test_goto_line_delegates_reference_resolution(monkeypatch):
    _patch_module_state(monkeypatch)
    win = _make_window()
    win.get_line_number.return_value = 0
    nav = NavigationController(win)
    # Force reference_to_line_number to a known valid position.
    monkeypatch.setattr(nav, "reference_to_line_number", lambda *a, **k: 42)

    nav.goto_line("John 3.16")

    win.display_verse.assert_called_once_with(42)


def test_goto_line_invalid_reference_clears_input(monkeypatch):
    _patch_module_state(monkeypatch)
    win = _make_window()
    win.get_line_number.return_value = 0
    win.display_verse_input = types.SimpleNamespace(
        text=lambda: "", clear=MagicMock()
    )
    nav = NavigationController(win)
    monkeypatch.setattr(nav, "reference_to_line_number", lambda *a, **k: -1)

    nav.goto_line("bogus")

    win.display_verse_input.clear.assert_called_once()
    win.display_verse.assert_not_called()
