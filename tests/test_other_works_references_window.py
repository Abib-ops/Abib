# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


from pathlib import Path
from typing import cast

# noinspection PyPackageRequirements
from PySide6.QtWidgets import QTreeWidgetItem

from abib.services.commentary_lookup import CommentaryEntry, CommentaryLookup
from abib.services.other_works_reference_index import (
    OtherWorkReferenceGroup,
    OtherWorkReferenceOccurrence,
    OtherWorksReferenceIndex,
)
from abib.ui.other_works_references_window import OtherWorksReferencesWindow


def make_window(tmp_path: Path) -> OtherWorksReferencesWindow:
    first = tmp_path / "First.txt"
    first.write_text("First has John 3:16 here.", encoding="utf-8")
    second = tmp_path / "Second.txt"
    second.write_text("Second has Jn. 3:16 here and Jude 5 there.", encoding="utf-8")
    service = OtherWorksReferenceIndex(
        {"First": str(first), "Second": str(second)},
        tmp_path / "companions",
    )
    return OtherWorksReferencesWindow(service)


def _top(window: OtherWorksReferencesWindow, index: int) -> QTreeWidgetItem:
    item = window.results_tree.topLevelItem(index)
    assert item is not None
    return item


def _child(window: OtherWorksReferencesWindow, index: int, child: int) -> QTreeWidgetItem:
    item = _top(window, index).child(child)
    assert item is not None
    return item


def test_window_searches_and_groups_results(qapp, tmp_path):
    window = make_window(tmp_path)

    window.set_reference("John 3:16")

    assert "2 occurrences" in window.summary_label.text()
    assert window.results_tree.topLevelItemCount() == 2
    assert _top(window, 0).text(0) == "First (1)"
    assert _top(window, 1).text(0) == "Second (1)"
    assert "John 3:16" in _child(window, 0, 0).text(2)


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
    window._activate_item(_child(window, 0, 0))

    assert activations == [(str(tmp_path / "Second.txt"), 29, 6)]


class _ReferenceService:
    def __init__(self, group: OtherWorkReferenceGroup | None) -> None:
        self.group = group

    def lookup(self, _reference: str) -> OtherWorkReferenceGroup | None:
        return self.group

    @staticmethod
    def key_for_reference(_reference: str) -> tuple[int, int, int]:
        return 43, 3, 16


class _CommentaryService:
    def __init__(self, entries: tuple[CommentaryEntry, ...]) -> None:
        self.entries = entries

    def lookup(self, _key) -> tuple[CommentaryEntry, ...]:
        return self.entries


def _commentary_entries(tmp_path: Path) -> tuple[CommentaryEntry, CommentaryEntry]:
    mhcc_path = tmp_path / "MHCC.txt"
    return (
        CommentaryEntry("Gill", "gill", "Gill", "Gill snippet", 43, 3, 16),
        CommentaryEntry("MHCC", "mhcc", "Matthew Henry", "Henry snippet", 43, 3, 16, str(mhcc_path), 25, 12),
    )


def _commentary_window(
    group: OtherWorkReferenceGroup | None, entries: tuple[CommentaryEntry, ...],
) -> OtherWorksReferencesWindow:
    """Build the window around the stand-in services, typed as the real ones for the checker."""
    return OtherWorksReferencesWindow(
        cast(OtherWorksReferenceIndex, cast(object, _ReferenceService(group))),
        commentary=cast(CommentaryLookup, cast(object, _CommentaryService(entries))),
    )


def test_window_places_commentaries_before_other_works(qapp, tmp_path):
    occurrence = OtherWorkReferenceOccurrence(
        "Ordinary", str(tmp_path / "Ordinary.txt"), (43, 3, 16), "John 3:16", "John 3:16", 0, 10, "work snippet",
    )
    group = OtherWorkReferenceGroup("John 3:16", (occurrence,))
    window = _commentary_window(group, _commentary_entries(tmp_path))

    window.set_reference("John 3:16")

    assert window.results_tree.topLevelItemCount() == 2
    assert _top(window, 0).text(0) == "Commentaries on John 3:16 (2)"
    assert _top(window, 1).text(0) == "Ordinary (1)"
    assert "Gill, Matthew Henry" in window.summary_label.text()


def test_window_shows_commentaries_without_other_work_mentions(qapp, tmp_path):
    window = _commentary_window(None, _commentary_entries(tmp_path))

    window.set_reference("John 3:16")

    assert window.results_tree.topLevelItemCount() == 1
    assert _top(window, 0).text(0) == "Commentaries on John 3:16 (2)"
    assert "Gill, Matthew Henry" in window.summary_label.text()


def test_window_activates_gill_reference(qapp, tmp_path):
    window = _commentary_window(None, _commentary_entries(tmp_path))
    activations: list[tuple[int, int, int]] = []
    window.commentaryActivated.connect(lambda book, chapter, verse: activations.append((book, chapter, verse)))
    window.set_reference("John 3:16")

    window._activate_item(_child(window, 0, 0))

    assert activations == [(43, 3, 16)]


def test_window_activates_mhcc_reader_offset(qapp, tmp_path):
    window = _commentary_window(None, _commentary_entries(tmp_path))
    activations: list[tuple[str, int, int]] = []
    window.occurrenceActivated.connect(lambda path, start, length: activations.append((path, start, length)))
    window.set_reference("John 3:16")

    window._activate_item(_child(window, 0, 1))

    assert activations == [(str(tmp_path / "MHCC.txt"), 25, 12)]