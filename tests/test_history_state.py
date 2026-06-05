# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from types import SimpleNamespace

from abib.core.history import History


def _window_with_highlight_state(position: int, occurs: list[int], occur: list[list[tuple[int, int]]]):
    return SimpleNamespace(
        current_position=position,
        y=5,
        yend=12,
        hiLita=SimpleNamespace(lineinc=1, keyinc=2, fmt="fmt", length=7),
        no_f3_yet=1,
        occurring=sum(len(item) for item in occur),
        occurrence=1,
        verse=0,
        finding=0,
        key="light",
        keym="light",
        store="light",
        occurs=occurs,
        occur=occur,
        count=[len(item) for item in occur],
        dlg=SimpleNamespace(checks=[3, 0, 5]),
    )


def test_history_restores_exact_highlight_state_without_reusing_current_search_state():
    history = History()
    original_occurs = [10]
    original_occur = [[(5, 12)]]
    window = _window_with_highlight_state(10, original_occurs, original_occur)

    history.back_push(window, 10)

    window.occurs = [20]
    window.occur = [[(1, 4), (9, 13)]]
    window.count = [2]
    window.verse = 0
    window.y = 1

    restored_position = history.back_pop(window)

    assert restored_position == 10
    assert window.occurs == [10]
    assert window.occur == [[(5, 12)]]
    assert window.count == [1]
    assert window.y == 5
    assert window.yend == 12


def test_history_snapshot_deep_copies_highlight_lists():
    history = History()
    window = _window_with_highlight_state(10, [10], [[(5, 12)]])

    history.back_push(window, 10)
    window.occurs.append(20)
    window.occur[0].append((15, 18))
    window.count.append(1)

    history.back_pop(window)

    assert window.occurs == [10]
    assert window.occur == [[(5, 12)]]
    assert window.count == [1]