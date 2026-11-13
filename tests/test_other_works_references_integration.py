# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


from types import SimpleNamespace

# noinspection PyPackageRequirements
from PySide6.QtWidgets import QPlainTextEdit

from abib import Abib as AbibModule
from abib.services.other_works_reference_index import OtherWorksReferenceIndex


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


def test_commentary_result_opens_gill_at_selected_reference(monkeypatch, tmp_path):
    db_path = tmp_path / "gill.cmt.sqlite"
    db_path.touch()
    monkeypatch.setattr(AbibModule.sh, "str_cwd", str(tmp_path))
    opened: list[tuple[str, int, int, int]] = []
    monkeypatch.setattr(
        AbibModule.MainWindow,
        "_show_gill_reference",
        lambda _window, path, book, chapter, verse: opened.append((str(path), book, chapter, verse)),
    )
    window = SimpleNamespace()

    # noinspection PyTypeChecker
    AbibModule.MainWindow._on_commentary_reference_activated(window, 43, 3, 16)

    assert opened == [(str(db_path), 43, 3, 16)]


def test_open_mhcc_for_current_verse_jumps_to_matching_passage(qapp, tmp_path):
    text = "__________\n\nGenesis\n\nChapter 1\n\nVerses 1-3\nCreation passage.\n"
    work_path = tmp_path / "MHCC.txt"
    work_path.write_text(text, encoding="utf-8")
    opened: list[str] = []
    jumped: list[tuple[int, int]] = []
    status_messages: list[str] = []
    reader = SimpleNamespace(jump_to_reference_offset=lambda start, length: jumped.append((start, length)))
    window = SimpleNamespace(
        get_line_number=lambda: 0,
        other_works_map={"MHCC": str(work_path)},
        statusBar=SimpleNamespace(showMessage=status_messages.append),
        open_text_file_in_window=opened.append,
        text_edit_window=reader,
    )
    window._on_other_work_reference_activated = (
        lambda path, start, length: AbibModule.MainWindow._on_other_work_reference_activated(
            window, path, start, length,
        )
    )

    # noinspection PyTypeChecker
    AbibModule.MainWindow.open_mhcc_for_current_verse(window)

    assert opened == [str(work_path)]
    assert jumped == [(text.index("Verses 1-3"), len("Verses 1-3"))]
    assert status_messages and "Genesis 1:1" in status_messages[0]


def test_open_mhcc_warns_when_text_is_not_available(qapp, monkeypatch):
    warnings: list[tuple[str, str]] = []
    monkeypatch.setattr(AbibModule.QMessageBox, "warning", lambda _parent, title, text: warnings.append((title, text)))
    monkeypatch.setattr(AbibModule.sh, "other_works_dirs", list)
    window = SimpleNamespace(
        get_line_number=lambda: 0,
        other_works_map={},
        statusBar=SimpleNamespace(showMessage=lambda _message: None),
    )

    # noinspection PyTypeChecker
    AbibModule.MainWindow.open_mhcc_for_current_verse(window)

    assert warnings
    assert "MHCC.txt is not available" in warnings[0][1]


def test_open_other_works_text_search_includes_every_present_work(qapp, tmp_path):
    first = tmp_path / "First.txt"
    first.write_text("mercy", encoding="utf-8")
    second = tmp_path / "Second.txt"
    second.write_text("mercy", encoding="utf-8")
    window = SimpleNamespace(
        settings={},
        other_works_map={"First": str(first), "Second": str(second)},
        other_works_text_search_service=None,
        other_works_text_search_window=None,
        _on_other_work_text_search_activated=lambda *_args: None,
    )

    # noinspection PyTypeChecker
    AbibModule.MainWindow.open_other_works_text_search(window)

    results = window.other_works_text_search_service.search("mercy")

    assert [occ.work_stem for occ in results.occurrences] == ["First", "Second"]


def test_open_other_works_text_search_clears_previous_search(qapp, tmp_path):
    work = tmp_path / "First.txt"
    work.write_text("mercy and mercy", encoding="utf-8")
    window = SimpleNamespace(
        settings={},
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
        settings={},
        other_works_map={"First": str(work)},
        other_works_reference_index=None,
        other_works_references_window=None,
        _on_other_work_reference_activated=lambda *_args: None,
        _on_commentary_reference_activated=lambda *_args: None,
    )

    # noinspection PyTypeChecker
    AbibModule.MainWindow.open_other_works_references(window)
    window.other_works_references_window.set_reference("John 3:16")

    # noinspection PyTypeChecker
    AbibModule.MainWindow.open_other_works_references(window)

    assert window.other_works_references_window.reference_edit.text() == ""
    assert window.other_works_references_window.results_tree.topLevelItemCount() == 0
    assert window.other_works_references_window.summary_label.text() == "Enter a reference to search enabled Other Works."


def test_study_current_verse_searches_canonical_reference_and_citing_work(qapp, tmp_path, monkeypatch):
    work_path = tmp_path / "Example.txt"
    monkeypatch.setattr(AbibModule.sh, "str_cwd", str(tmp_path))
    cases = (
        (42, 2, 15, "John 3:16"),
        (64, 0, 2, "Jude 1:3"),
        (18, 22, 0, "Psalms 23:1"),
    )

    for book_index, chapter_index, verse_index, reference in cases:
        work_path.write_text(f"A reference to {reference}.", encoding="utf-8")
        monkeypatch.setattr(AbibModule, "KJV", ("Verse text\n",))
        monkeypatch.setattr(AbibModule, "Amap_rev", {0: 0})
        monkeypatch.setattr(AbibModule.sh, "Info", ((book_index, chapter_index, verse_index),))
        monkeypatch.setattr(AbibModule.sh, "onechapterbooks", {64})
        editor = QPlainTextEdit("Verse text")
        status_messages: list[str] = []
        window = SimpleNamespace(
            textEditor=editor,
            get_line_number=lambda: 0,
            statusBar=SimpleNamespace(showMessage=status_messages.append),
            settings={},
            other_works_map={"Example": str(work_path)},
            other_works_reference_index=None,
            other_works_references_window=None,
            _on_other_work_reference_activated=lambda *_args: None,
            _on_commentary_reference_activated=lambda *_args: None,
        )
        window.open_other_works_references = (
            lambda target=window: AbibModule.MainWindow.open_other_works_references(target)
        )

        # noinspection PyTypeChecker
        AbibModule.MainWindow.study_current_verse(window)

        references_window = window.other_works_references_window
        assert references_window.reference_edit.text() == reference
        assert references_window.results_tree.topLevelItemCount() == 1
        assert references_window.results_tree.topLevelItem(0).text(0) == "Example (1)"
        assert OtherWorksReferenceIndex.key_for_reference(reference) == (
            book_index + 1,
            chapter_index + 1,
            verse_index + 1,
        )
        assert status_messages[-1] == f"Study results for {reference}."
        references_window.close()