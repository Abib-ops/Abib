# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

# noinspection PyPep8Naming
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

    def highlight_line(self, line_num, _fmt) -> None:
        self.lines.append(line_num)


def _setup_multi_word_search_window(monkeypatch, occurs):
    """Build the shared window/highlighter fixture for multi-word search tests."""
    window = SimpleNamespace()
    highlighter = FakeHighlighter()
    window.dlg = SimpleNamespace(checks=[3, 0, 5])
    window.hiLita = highlighter
    window.key = "passing"
    window.store = "passing"
    window.y = 5
    window.occur = [[(5, 12), (20, 24)]]
    window.occurs = occurs
    window.verse = 0

    monkeypatch.setattr(app, "w", window)
    monkeypatch.setattr(app, "KJV", ["", "And Saul took him that day."])
    monkeypatch.setattr(app, "Amap_rev", {1: 0})
    monkeypatch.setattr(app, "linehighlightcolor", "#fff59d")
    monkeypatch.setattr(app, "linetextcolor", "#000000")
    window.adjust_highlighting = lambda ln, current_position: None

    return window, highlighter


def test_normal_verse_navigation_does_not_reuse_previous_multi_word_search_highlights(monkeypatch):
    window, highlighter = _setup_multi_word_search_window(monkeypatch, [2])

    app.MainWindow.on_text_changed(cast(app.MainWindow, cast(object, window)), 1)

    assert highlighter.ranges == []
    assert highlighter.lines == []


def test_active_multi_word_search_result_still_highlights(monkeypatch):
    window, highlighter = _setup_multi_word_search_window(monkeypatch, [0])

    app.MainWindow.on_text_changed(cast(app.MainWindow, cast(object, window)), 1)

    assert highlighter.ranges == [(1, 5, 7), (1, 20, 4)]
    assert highlighter.lines == [1]


def test_raw_result_click_recomputes_highlight_offsets(monkeypatch):
    """Reaching a Raw-search result verse must recompute lineinc/keyinc.

    Regression for "cedars of Lebanon": the first match (Judges 9:15) sits
    after several Unicode-italic characters, so the initial find sets a
    non-zero lineinc. Clicking another result (Isaiah 2:13) previously reused
    that stale offset and highlighted the wrong character.
    """
    window = SimpleNamespace()
    # Raw search, match case.
    window.dlg = SimpleNamespace(checks=[1, 1, 5])
    window.hiLita = FakeHighlighter()
    # Stale offset left over from highlighting the first match.
    window.hiLita.lineinc = 7
    window.hiLita.keyinc = 0
    window.key = "cedars of Lebanon"
    window.keym = "cedars of Lebanon"
    window.store = "cedars of Lebanon"
    window.occurs = [0, 1]
    window.occur = [[(184, 201)], [(20, 37)]]
    window.verse = 0
    window.occurrence = 0
    window.finding = 0
    window.message = ""
    # win.y already points at the clicked verse's match start (set by _sync).
    window.y = 20

    monkeypatch.setattr(app, "w", window)
    monkeypatch.setattr(app, "Amap", [100, 200])
    monkeypatch.setattr(app, "starts_with_italics", [])
    monkeypatch.setattr(app, "make_offset", lambda ln: ln)

    class FakeCursor:
        class MoveOperation:
            End = 0

        def __init__(self, _block=None) -> None:
            pass

    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(app, "QTextCursor", FakeCursor)

    calls: list[tuple[int, int]] = []

    block = SimpleNamespace()
    document = SimpleNamespace(findBlockByLineNumber=lambda ln: block)
    text_editor = SimpleNamespace(
        setLineWrapMode=lambda mode: None,
        document=lambda: document,
        moveCursor=lambda op: None,
        setTextCursor=lambda cursor: None,
    )

    fake_self = SimpleNamespace(
        dlg=window.dlg,
        textEditor=text_editor,
        adjust_highlighting=lambda ln, current_position: calls.append((ln, current_position)),
        on_text_changed=lambda ln: None,
        ref_to_statusbar=lambda current_position: None,
    )

    app.MainWindow.display_verse_from_history(cast(app.MainWindow, cast(object, fake_self)), 1)

    # adjust_highlighting must be invoked for the clicked verse (ln=200).
    assert calls == [(200, 1)]


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
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(app.history, "back_push", lambda win, current_position: pushed_positions.append(current_position))
    monkeypatch.setattr(app, "get_next_occurrence", lambda: 20)

    app.MainWindow.find_f4_alt(cast(app.MainWindow, cast(object, fake_self)))

    assert pushed_positions == [99]