# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path

from abib.services.other_works_reference_index import OtherWorksReferenceIndex
from abib.ui.other_works_references_window import OtherWorksReferencesWindow


def make_window(tmp_path: Path) -> OtherWorksReferencesWindow:
    first = tmp_path / "First.txt"
    first.write_text("First has John 3:16 here.", encoding="utf-8")
    second = tmp_path / "Second.txt"
    second.write_text("Second has Jn. 3:16 here and Jude 5 there.", encoding="utf-8")
    service = OtherWorksReferenceIndex(
        {"First": str(first), "Second": str(second)},
        {"First": True, "Second": True},
        tmp_path / "companions",
    )
    return OtherWorksReferencesWindow(service)


def test_window_searches_and_groups_results(qapp, tmp_path):
    window = make_window(tmp_path)

    window.set_reference("John 3:16")

    assert "2 occurrences" in window.summary_label.text()
    assert window.results_tree.topLevelItemCount() == 2
    assert window.results_tree.topLevelItem(0).text(0) == "First (1)"
    assert window.results_tree.topLevelItem(1).text(0) == "Second (1)"
    assert "John 3:16" in window.results_tree.topLevelItem(0).child(0).text(2)


def test_window_title_and_default_size_are_readable(qapp, tmp_path):
    window = make_window(tmp_path)

    assert window.windowTitle() == "Other Works Scripture reference search"
    assert window.minimumWidth() >= 520
    assert window.minimumHeight() >= 360


def test_window_shows_empty_state(qapp, tmp_path):
    window = make_window(tmp_path)

    window.set_reference("Romans 8:28")

    assert window.results_tree.topLevelItemCount() == 0
    assert "No enabled Other Works contain Romans 8:28" in window.summary_label.text()


def test_window_clear_search_removes_previous_reference_and_results(qapp, tmp_path):
    window = make_window(tmp_path)
    window.set_reference("John 3:16")

    window.clear_search()

    assert window.reference_edit.text() == ""
    assert window.results_tree.topLevelItemCount() == 0
    assert window.summary_label.text() == "Enter a reference to search enabled Other Works."


def test_window_emits_occurrence_payload(qapp, tmp_path):
    window = make_window(tmp_path)
    activations: list[tuple[str, int, int]] = []
    window.occurrenceActivated.connect(lambda path, start, length: activations.append((path, start, length)))

    window.set_reference("Jude 5")
    item = window.results_tree.topLevelItem(0).child(0)
    window._activate_item(item)

    assert activations == [(str(tmp_path / "Second.txt"), 29, 6)]