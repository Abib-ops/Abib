# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


from types import SimpleNamespace
from typing import cast

# noinspection PyPackageRequirements
from PySide6.QtGui import QTextCursor

# noinspection PyPackageRequirements
from PySide6.QtWidgets import QApplication, QPlainTextEdit

from abib import Abib as AbibModule
from abib.services.verse_copy import (
    clean_verse_text,
    format_citation,
    format_reference_range,
)


def test_clean_verse_text_removes_markers_and_normalizes_italics():
    assert clean_verse_text("¶ 12 𝐺𝑜𝑑 𝒽 𝟙") == "God h 1"
    assert clean_verse_text("16 ¶ 𝐺𝑜𝑑 𝒽 𝟙") == "God h 1"
    assert clean_verse_text("¶ For God", strip_verse_number=False) == "For God"


def test_clean_verse_text_preserves_leading_number_for_partial_selection():
    assert clean_verse_text("5 things endure", strip_verse_number=False) == "5 things endure"


def test_format_reference_range_within_chapter():
    info = ((42, 2, 15), (42, 2, 16))

    assert format_reference_range(0, 0, info, set()) == "John 3:16"
    assert format_reference_range(0, 1, info, set()) == "John 3:16-17"


def test_format_reference_range_across_chapters_and_books():
    info = ((42, 2, 15), (42, 3, 1), (43, 0, 0))

    assert format_reference_range(0, 1, info, set()) == "John 3:16-4:2"
    assert format_reference_range(1, 2, info, set()) == "John 4:2-Acts 1:1"


def test_format_reference_range_for_one_chapter_books_and_psalms():
    info = ((64, 0, 2), (64, 0, 3), (18, 0, 0))

    assert format_reference_range(0, 0, info, {64}) == "Jude 3"
    assert format_reference_range(0, 1, info, {64}) == "Jude 3-4"
    assert format_reference_range(2, 2, info, set()) == "Psalm 1:1"


def test_format_citation_quotes_text_and_reference():
    assert format_citation("Let there be light", "Genesis 1:3") == '"Let there be light" (Genesis 1:3)'


def _copy_window(text: str) -> SimpleNamespace:
    editor = QPlainTextEdit()
    editor.setPlainText(text)
    messages: list[str] = []
    return SimpleNamespace(
        textEditor=editor,
        statusBar=SimpleNamespace(showMessage=messages.append),
        messages=messages,
    )


def test_copy_current_verse_and_selected_verses(qapp, monkeypatch):
    lines = ("CHAPTER 3\n", "16 ¶ For God so loved\n", "17 ¶ that he gave\n")
    monkeypatch.setattr(AbibModule, "KJV", lines)
    monkeypatch.setattr(AbibModule, "Amap_rev", {1: 0, 2: 1})
    monkeypatch.setattr(AbibModule.sh, "Info", ((42, 2, 15), (42, 2, 16)))
    monkeypatch.setattr(AbibModule.sh, "onechapterbooks", set())
    window = _copy_window("".join(lines))

    cursor = window.textEditor.textCursor()
    cursor.setPosition(len(lines[0]) + 4)
    window.textEditor.setTextCursor(cursor)
    AbibModule.MainWindow.copy_verse_with_reference(cast(AbibModule.MainWindow, cast(object, window)))
    assert QApplication.clipboard().text() == '"For God so loved" (John 3:16)'

    cursor = window.textEditor.textCursor()
    cursor.setPosition(0)
    cursor.setPosition(len(window.textEditor.toPlainText()), QTextCursor.MoveMode.KeepAnchor)
    window.textEditor.setTextCursor(cursor)
    AbibModule.MainWindow.copy_verse_with_reference(cast(AbibModule.MainWindow, cast(object, window)))
    assert QApplication.clipboard().text() == '"For God so loved that he gave" (John 3:16-17)'


def test_copy_partial_selection_preserves_leading_content_number(qapp, monkeypatch):
    line = "1 5 things endure"
    monkeypatch.setattr(AbibModule, "KJV", (line,))
    monkeypatch.setattr(AbibModule, "Amap_rev", {0: 0})
    monkeypatch.setattr(AbibModule.sh, "Info", ((42, 2, 15),))
    monkeypatch.setattr(AbibModule.sh, "onechapterbooks", set())
    window = _copy_window(line)
    cursor = window.textEditor.textCursor()
    cursor.setPosition(2)
    cursor.setPosition(len(line), QTextCursor.MoveMode.KeepAnchor)
    window.textEditor.setTextCursor(cursor)

    AbibModule.MainWindow.copy_verse_with_reference(cast(AbibModule.MainWindow, cast(object, window)))

    assert QApplication.clipboard().text() == '"5 things endure" (John 3:16)'


def test_copy_skips_non_bible_text_without_changing_clipboard(qapp, monkeypatch):
    monkeypatch.setattr(AbibModule, "KJV", ("1 Bible verse",))
    monkeypatch.setattr(AbibModule, "Amap_rev", {0: 0})
    monkeypatch.setattr(AbibModule.sh, "Info", ((42, 2, 15),))
    monkeypatch.setattr(AbibModule.sh, "onechapterbooks", set())
    window = _copy_window("Text from another file")
    QApplication.clipboard().setText("previous clipboard")

    AbibModule.MainWindow.copy_verse_with_reference(cast(AbibModule.MainWindow, cast(object, window)))

    assert QApplication.clipboard().text() == "previous clipboard"
    assert window.messages[-1] == "No Bible verse text to copy."