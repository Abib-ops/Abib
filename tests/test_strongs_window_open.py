# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

import sys
from types import ModuleType, SimpleNamespace
from typing import cast

from abib import Abib as AbibModule
from tests._window_open_helpers import make_window_open_env


def test_open_strongs_window_uses_current_bible_line(monkeypatch, tmp_path):
    # A real (if empty) file so the existence check passes.
    db_path = tmp_path / "strongs.sqlite"
    db_path.write_bytes(b"")

    positions: list[int] = []

    class FakeStrongsService:
        def __init__(self, path) -> None:
            self.path = path

    class FakeStrongsWindow:
        def __init__(self, **kwargs) -> None:
            pass

        # noinspection PyMethodMayBeStatic
        def set_position(self, x: int) -> None:
            positions.append(x)

        def apply_theme(self, is_dark: bool) -> None:
            pass

        def show(self) -> None:
            pass

        def raise_(self) -> None:
            pass

        def activateWindow(self) -> None:
            pass

    fake_service_mod = ModuleType("abib.services.strongs_service")
    fake_service_mod.StrongsService = FakeStrongsService
    fake_window_mod = ModuleType("abib.ui.strongs_window")
    fake_window_mod.StrongsWindow = FakeStrongsWindow
    monkeypatch.setitem(sys.modules, "abib.services.strongs_service", fake_service_mod)
    monkeypatch.setitem(sys.modules, "abib.ui.strongs_window", fake_window_mod)

    window = make_window_open_env(monkeypatch, tmp_path)
    window.strongs_win = None

    AbibModule.MainWindow.open_strongs_window(cast(AbibModule.MainWindow, cast(object, window)))

    assert positions == [2]
    assert window._last_bible_position == 2
    assert window._last_context_position == 2


def test_open_strongs_window_missing_db_warns(monkeypatch, tmp_path):
    # No strongs.sqlite present -> should warn and not create a window.
    warnings: list[str] = []
    monkeypatch.setattr(AbibModule.sh, "str_cwd", str(tmp_path))
    monkeypatch.setattr(
        AbibModule.QMessageBox, "warning",
        staticmethod(lambda *args, **kwargs: warnings.append(args[-1])),
    )

    window = SimpleNamespace()
    window.strongs_win = None

    AbibModule.MainWindow.open_strongs_window(cast(AbibModule.MainWindow, cast(object, window)))

    assert window.strongs_win is None
    assert len(warnings) == 1


class _FakeDock:
    def __init__(self) -> None:
        self.results = None
        self.search_text = None
        self.shown = False
        self.cleared = False
        self._positioning = False

    def set_results(self, results, search_text) -> None:
        self.results = results
        self.search_text = search_text

    def clear_results(self) -> None:
        self.cleared = True

    def show(self) -> None:
        self.shown = True

    def hide(self) -> None:
        self.shown = False

    def raise_(self) -> None:
        pass


def _make_results_window(dock):
    window = SimpleNamespace()
    window.search_results_window = dock
    window.strongs_win = SimpleNamespace(_service=None)
    window.nwin = ["Genesis"]
    window._position_search_results_window = lambda: None
    window._release_main_width_limit = lambda: None
    window._setup_search_results_panel = lambda: None
    window.errors = []
    window.on_error = lambda message, *a: window.errors.append(message)
    return window


def test_show_strongs_occurrences_populates_results(monkeypatch):
    monkeypatch.setattr(AbibModule.sh, "Info", [[0, 0, 0], [0, 0, 1]])
    monkeypatch.setattr(AbibModule.sh, "onechapterbooks", ())
    monkeypatch.setattr(
        AbibModule, "KJV",
        ["1 In the beginning God created the heaven and the earth.",
         "2 And God said, Let there be light."],
    )
    monkeypatch.setattr(AbibModule, "Amap", [0, 1])

    dock = _FakeDock()
    window = _make_results_window(dock)
    # A service that highlights "God" in verse 0 only.
    window.strongs_win._service = SimpleNamespace(
        get_tags_for_verse=lambda pos: (
            [SimpleNamespace(surface="God", strongs="H0430")] if pos == 0 else []
        )
    )

    AbibModule.MainWindow._show_strongs_occurrences(
        cast(AbibModule.MainWindow, cast(object, window)), "H0430", [0, 1]
    )

    assert dock.shown is True
    assert dock.search_text == "H0430"
    assert dock.results is not None
    assert [r.position for r in dock.results] == [0, 1]
    assert dock.results[0].reference == "Genesis 1:1"
    # Verse 0 tagged word is highlighted; verse 1 (no tags) is plain escaped text.
    assert "background-color" in dock.results[0].html_text
    assert "background-color" not in dock.results[1].html_text


def test_show_strongs_occurrences_empty_hides_and_warns(monkeypatch):
    monkeypatch.setattr(AbibModule.sh, "Info", [[0, 0, 0]])
    monkeypatch.setattr(AbibModule.sh, "onechapterbooks", ())
    monkeypatch.setattr(AbibModule, "KJV", ["1 In the beginning."])
    monkeypatch.setattr(AbibModule, "Amap", [0])

    dock = _FakeDock()
    window = _make_results_window(dock)

    AbibModule.MainWindow._show_strongs_occurrences(
        cast(AbibModule.MainWindow, cast(object, window)), "G9999", []
    )

    assert dock.cleared is True
    assert dock.shown is False
    assert len(window.errors) == 1
    assert "G9999" in window.errors[0]
