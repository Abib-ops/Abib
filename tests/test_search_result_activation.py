# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from types import SimpleNamespace

from abib import Abib as AbibModule
from abib.ui.search_results import SearchResult


def _activate_result(
        navigation_recorder, result: SearchResult
) -> tuple[list[tuple[int, tuple[tuple[int, int], ...]]], list[int]]:
    """Activate *result* on the stub window and record which highlight path ran."""
    window = navigation_recorder.window
    highlights: list[tuple[int, tuple[tuple[int, int], ...]]] = []
    state_syncs: list[int] = []
    window.search_results_window = SimpleNamespace(result_for_position=lambda _position: result)
    window._apply_tagged_highlights = lambda position, ranges: highlights.append((position, ranges))
    window._sync_search_state_for_result = state_syncs.append

    AbibModule.MainWindow.on_search_result_activated(window, result.position)
    return highlights, state_syncs


def test_strongs_result_activation_applies_tagged_highlights(navigation_recorder):
    result = SearchResult(7, "Genesis 1:8", "verse", "verse", ((4, 8),))

    highlights, state_syncs = _activate_result(navigation_recorder, result)

    assert navigation_recorder.displayed == [7]
    assert highlights == [(7, ((4, 8),))]
    assert state_syncs == []


def test_regular_result_activation_keeps_existing_search_state_path(navigation_recorder):
    result = SearchResult(7, "Genesis 1:8", "verse", "verse")

    highlights, state_syncs = _activate_result(navigation_recorder, result)

    assert navigation_recorder.displayed == [7]
    assert highlights == []
    assert state_syncs == [7]
