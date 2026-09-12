# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from types import SimpleNamespace

from abib import Abib as AbibModule


def _make_jump_window() -> tuple[SimpleNamespace, list[str], list[tuple[int, int]]]:
    opened: list[str] = []
    jumped: list[tuple[int, int]] = []
    reader = SimpleNamespace(jump_to_reference_offset=lambda start, length: jumped.append((start, length)))
    window = SimpleNamespace(text_edit_window=reader)
    window.open_text_file_in_window = opened.append
    return window, opened, jumped


def test_other_work_reference_activation_opens_reader_and_jumps(qapp):
    window, opened, jumped = _make_jump_window()

    # noinspection PyTypeChecker
    AbibModule.MainWindow._on_other_work_reference_activated(window, "C:\\Works\\Example.txt", 42, 9)

    assert opened == ["C:\\Works\\Example.txt"]
    assert jumped == [(42, 9)]


def test_other_work_reference_activation_queues_jump_for_loading_reader(qapp):
    opened: list[str] = []
    jumped: list[tuple[int, int]] = []

    def jump_to_reference_offset(start, length):
        jumped.append((start, length))
        return True

    reader = SimpleNamespace(
        _is_loading_file=True,
        jump_to_reference_offset=jump_to_reference_offset,
    )
    window = SimpleNamespace(text_edit_window=reader)
    window.open_text_file_in_window = opened.append

    # noinspection PyTypeChecker
    AbibModule.MainWindow._on_other_work_reference_activated(window, "C:\\Works\\Example.txt", 42, 9)

    assert opened == ["C:\\Works\\Example.txt"]
    assert reader._pending_reference_offset == (42, 9)
    assert reader._pending_jump_char == 42
    assert jumped == [(42, 9)]


def test_other_work_text_search_activation_uses_reference_jump_path(qapp):
    window, opened, jumped = _make_jump_window()

    # noinspection PyTypeChecker
    AbibModule.MainWindow._on_other_work_text_search_activated(window, "C:\\Works\\Example.txt", 12, 5)

    assert opened == ["C:\\Works\\Example.txt"]
    assert jumped == [(12, 5)]


def test_open_other_works_text_search_uses_current_show_work_settings(qapp, tmp_path):
    first = tmp_path / "First.txt"
    first.write_text("mercy", encoding="utf-8")
    hidden = tmp_path / "Hidden.txt"
    hidden.write_text("mercy", encoding="utf-8")
    window = SimpleNamespace(
        settings={"show_work": {"First": True, "Hidden": False}},
        other_works_map={"First": str(first), "Hidden": str(hidden)},
        other_works_text_search_service=None,
        other_works_text_search_window=None,
        _on_other_work_text_search_activated=lambda *_args: None,
    )

    # noinspection PyTypeChecker
    AbibModule.MainWindow.open_other_works_text_search(window)

    results = window.other_works_text_search_service.search("mercy")

    assert [occ.work_stem for occ in results.occurrences] == ["First"]


def test_open_other_works_text_search_clears_previous_search(qapp, tmp_path):
    work = tmp_path / "First.txt"
    work.write_text("mercy and mercy", encoding="utf-8")
    window = SimpleNamespace(
        settings={"show_work": {"First": True}},
        other_works_map={"First": str(work)},
        other_works_text_search_service=None,
        other_works_text_search_window=None,
        _on_other_work_text_search_activated=lambda *_args: None,
    )

    # noinspection PyTypeChecker
    AbibModule.MainWindow.open_other_works_text_search(window)
    window.other_works_text_search_window.set_query("mercy")

    # noinspection PyTypeChecker
    AbibModule.MainWindow.open_other_works_text_search(window)

    assert window.other_works_text_search_window.query_edit.text() == ""
    assert window.other_works_text_search_window.results_tree.topLevelItemCount() == 0
    assert window.other_works_text_search_window.summary_label.text() == "Enter text to search enabled Other Works."


def test_open_other_works_references_clears_previous_search(qapp, tmp_path):
    work = tmp_path / "First.txt"
    work.write_text("First has John 3:16 here.", encoding="utf-8")
    window = SimpleNamespace(
        settings={"show_work": {"First": True}},
        other_works_map={"First": str(work)},
        other_works_reference_index=None,
        other_works_references_window=None,
        _on_other_work_reference_activated=lambda *_args: None,
    )

    # noinspection PyTypeChecker
    AbibModule.MainWindow.open_other_works_references(window)
    window.other_works_references_window.set_reference("John 3:16")

    # noinspection PyTypeChecker
    AbibModule.MainWindow.open_other_works_references(window)

    assert window.other_works_references_window.reference_edit.text() == ""
    assert window.other_works_references_window.results_tree.topLevelItemCount() == 0
    assert window.other_works_references_window.summary_label.text() == "Enter a reference to search enabled Other Works."