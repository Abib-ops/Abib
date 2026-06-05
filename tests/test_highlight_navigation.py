# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from abib import Abib as app


class FakeHighlighter:
    def __init__(self) -> None:
        self.clear = False
        self.lineinc = 0
        self.keyinc = 0
        self.ranges: list[tuple[int, int, int]] = []
        self.lines: list[int] = []

    def clear_highlight(self) -> None:
        self.ranges.clear()

    def add_multi_highlight(self, line_num: int, pos: int, length: int) -> None:
        self.ranges.append((line_num, pos, length))

    def highlight_line(self, line_num, fmt) -> None:
        self.lines.append(line_num)


def test_normal_verse_navigation_does_not_reuse_previous_multi_word_search_highlights(monkeypatch):
    window = SimpleNamespace()
    highlighter = FakeHighlighter()
    window.dlg = SimpleNamespace(checks=[3, 0, 5])
    window.hiLita = highlighter
    window.key = "passing"
    window.store = "passing"
    window.y = 5
    window.occur = [[(5, 12), (20, 24)]]
    window.occurs = [2]
    window.verse = 0

    monkeypatch.setattr(app, "w", window)
    monkeypatch.setattr(app, "KJV", ["", "And Saul took him that day."])
    monkeypatch.setattr(app, "Amap_rev", {1: 0})
    monkeypatch.setattr(app, "linehighlightcolor", "#fff59d")
    monkeypatch.setattr(app, "linetextcolor", "#000000")
    window.adjust_highlighting = lambda ln, current_position: None

    app.MainWindow.on_text_changed(cast(app.MainWindow, cast(object, window)), 1)

    assert highlighter.ranges == []
    assert highlighter.lines == []


def test_active_multi_word_search_result_still_highlights(monkeypatch):
    window = SimpleNamespace()
    highlighter = FakeHighlighter()
    window.dlg = SimpleNamespace(checks=[3, 0, 5])
    window.hiLita = highlighter
    window.key = "passing"
    window.store = "passing"
    window.y = 5
    window.occur = [[(5, 12), (20, 24)]]
    window.occurs = [0]
    window.verse = 0

    monkeypatch.setattr(app, "w", window)
    monkeypatch.setattr(app, "KJV", ["", "And Saul took him that day."])
    monkeypatch.setattr(app, "Amap_rev", {1: 0})
    monkeypatch.setattr(app, "linehighlightcolor", "#fff59d")
    monkeypatch.setattr(app, "linetextcolor", "#000000")
    window.adjust_highlighting = lambda ln, current_position: None

    app.MainWindow.on_text_changed(cast(app.MainWindow, cast(object, window)), 1)

    assert highlighter.ranges == [(1, 5, 7), (1, 20, 4)]
    assert highlighter.lines == [1]


def test_find_next_history_uses_top_verse_shown_in_main_window(monkeypatch):
    window = SimpleNamespace()
    window.dlg = SimpleNamespace(checks=[3, 0, 5])
    window.occurs = [10, 20]
    window.occur = [[(1, 5)], [(2, 6)]]
    window.count = [1, 1]
    window.occurrence = 0
    window.occurring = 2
    window.verse = 0
    window.finding = 0
    window.y = 1
    window.yend = 5
    window.hiLita = SimpleNamespace(lineinc=0, keyinc=0, fmt=None, length=4)
    window.no_f3_yet = 1
    window.key = "soul"
    window.keym = "soul"
    window.store = "soul"
    window.message = ""

    pushed_positions: list[int] = []
    fake_self = SimpleNamespace(
        dlg=window.dlg,
        get_line_number=lambda: 99,
        statusBar=SimpleNamespace(repaint=lambda: None),
        goto_line_find=lambda current_position: None,
    )

    monkeypatch.setattr(app, "w", window)
    app.forward.clear()
    monkeypatch.setattr(app.history, "back_push", lambda win, current_position: pushed_positions.append(current_position))
    monkeypatch.setattr(app, "get_next_occurrence", lambda: 20)

    app.MainWindow.find_f4_alt(cast(app.MainWindow, cast(object, fake_self)))

    assert pushed_positions == [99]