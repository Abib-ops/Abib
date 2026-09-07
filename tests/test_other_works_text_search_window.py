# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from abib.services.other_works_text_search import OtherWorksTextSearchService
from abib.ui.other_works_text_search_window import OtherWorksTextSearchWindow


def make_window(tmp_path: Path) -> OtherWorksTextSearchWindow:
    first = tmp_path / "First.txt"
    first.write_text("First has mercy here and Mercy there.", encoding="utf-8")
    second = tmp_path / "Second.txt"
    second.write_text("Second has tender mercy here.", encoding="utf-8")
    service = OtherWorksTextSearchService(
        {"First": str(first), "Second": str(second)},
        {"First": True, "Second": True},
    )
    return OtherWorksTextSearchWindow(service)


def test_window_searches_and_groups_results(qapp, tmp_path):
    window = make_window(tmp_path)

    window.set_query("mercy")

    assert "3 occurrences" in window.summary_label.text()
    assert window.results_tree.topLevelItemCount() == 2
    assert window.results_tree.topLevelItem(0).text(0) == "First (2)"
    assert window.results_tree.topLevelItem(1).text(0) == "Second (1)"
    assert "mercy" in window.results_tree.topLevelItem(0).child(0).text(2)


def test_window_shows_empty_state(qapp, tmp_path):
    window = make_window(tmp_path)

    window.set_query("   ")

    assert window.results_tree.topLevelItemCount() == 0
    assert window.summary_label.text() == "Enter text to search enabled Other Works."


def test_window_clear_search_removes_previous_query_and_results(qapp, tmp_path):
    window = make_window(tmp_path)
    window.set_query("mercy")

    window.clear_search()

    assert window.query_edit.text() == ""
    assert window.results_tree.topLevelItemCount() == 0
    assert window.summary_label.text() == "Enter text to search enabled Other Works."


def test_window_shows_no_result_state(qapp, tmp_path):
    window = make_window(tmp_path)

    window.set_query("faith")

    assert window.results_tree.topLevelItemCount() == 0
    assert "No enabled Other Works contain faith" in window.summary_label.text()


def test_window_emits_occurrence_payload(qapp, tmp_path):
    window = make_window(tmp_path)
    activations: list[tuple[str, int, int]] = []
    window.occurrenceActivated.connect(lambda path, start, length: activations.append((path, start, length)))

    window.set_query("tender mercy")
    item = window.results_tree.topLevelItem(0).child(0)
    window._activate_item(item)

    assert activations == [(str(tmp_path / "Second.txt"), 11, 12)]