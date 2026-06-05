# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
import sys
from types import ModuleType, SimpleNamespace
from typing import cast

from abib import Abib as app


def test_open_commentary_window_uses_current_bible_line_not_stale_context(monkeypatch, tmp_path):
    db_path = tmp_path / "gill.cmt.sqlite"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE commentary (id, book, chapter, fromverse, toverse, data)")
    conn.close()

    references: list[tuple[int, int, int]] = []

    class FakeGillCommentaryWindow:
        def __init__(self, **kwargs) -> None:
            pass

        def set_reference(self, book: int, chapter: int, verse: int) -> None:
            references.append((book, chapter, verse))

        def apply_theme(self, is_dark: bool) -> None:
            pass

        def show(self) -> None:
            pass

        def raise_(self) -> None:
            pass

        def activateWindow(self) -> None:
            pass

    fake_module = ModuleType("abib.ui.gill_window")
    fake_module.GillCommentaryWindow = FakeGillCommentaryWindow
    monkeypatch.setitem(sys.modules, "abib.ui.gill_window", fake_module)
    monkeypatch.setattr(app.sh, "str_cwd", str(tmp_path))
    monkeypatch.setattr(app.sh, "LAST_VERSE_IN_BIBLE", 2)
    monkeypatch.setattr(app.sh, "Info", [[0, 0, 0], [8, 0, 0], [9, 1, 2]])

    window = SimpleNamespace()
    window._gill_win = None
    window.settings_service = SimpleNamespace()
    window.theme = SimpleNamespace(
        state=SimpleNamespace(is_dark_mode=False),
        apply_widget=lambda widget: None,
    )
    window.nav = SimpleNamespace(get_current_bcv=lambda: (9, 1, 1))
    window._last_bible_position = 1
    window._last_context_position = 1
    window.get_line_number = lambda: 2

    app.MainWindow.open_commentary_window(cast(app.MainWindow, cast(object, window)))

    assert references == [(10, 2, 3)]
    assert window._last_bible_position == 2
    assert window._last_context_position == 2