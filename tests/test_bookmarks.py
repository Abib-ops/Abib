# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


from types import SimpleNamespace
from typing import cast

# noinspection PyPackageRequirements
from PySide6.QtWidgets import QPlainTextEdit

from abib import Abib as AbibModule
from abib.core import shared as sh
from abib.services.bookmarks import BookmarkStore
from abib.ui.bookmarks_window import BookmarksWindow


class _MemorySettingsService:
    def __init__(self) -> None:
        self.saved_geometry: tuple[str, tuple[int, ...]] | None = None

    def get_window_geometry(self, _window_name: str) -> tuple[int, int, int, int]:
        return 100, 100, 520, 440

    def save_window_geometry(self, window_name: str, *geometry: int) -> None:
        self.saved_geometry = window_name, geometry


def test_store_round_trip_sorts_updates_and_removes(tmp_path):
    store = BookmarkStore(tmp_path / "bookmarks.json")

    later = store.set(8, "Later verse")
    first = store.set(2, "First note")
    updated = store.set(8, "Updated note")

    assert store.all() == [first, updated]
    assert store.get(8) == updated
    assert updated.created == later.created
    assert store.remove(2)
    assert not store.remove(2)
    assert store.all() == [updated]

    reloaded = BookmarkStore(store.path)
    assert reloaded.all() == [updated]


def test_store_preserves_corrupt_file_and_ignores_out_of_range_records(tmp_path):
    path = tmp_path / "bookmarks.json"
    path.write_text("{broken", encoding="utf-8")
    store = BookmarkStore(path)

    assert store.all() == []
    assert not path.exists()
    assert path.with_name("bookmarks.json.bak").read_text(encoding="utf-8") == "{broken"

    path.write_text(
        '{"bookmarks": ['
        '{"position": -1, "note": "invalid", "created": "now"},'
        '{"position": 31102, "note": "invalid", "created": "now"},'
        '{"position": true, "note": "invalid", "created": "now"},'
        '{"position": 3, "note": "valid", "created": "now"}]}',
        encoding="utf-8",
    )

    assert [(bookmark.position, bookmark.note) for bookmark in store.all()] == [(3, "valid")]


def test_store_rejects_out_of_range_positions(tmp_path):
    store = BookmarkStore(tmp_path / "bookmarks.json")

    for position in (-1, 31102, True):
        try:
            store.set(position, "not valid")
        except ValueError:
            pass
        else:
            raise AssertionError(f"Expected invalid bookmark position: {position!r}")


def test_bookmarks_window_lists_navigates_saves_and_deletes(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(sh, "Info", ((42, 2, 15), (42, 2, 16)))
    monkeypatch.setattr(sh, "onechapterbooks", set())
    store = BookmarkStore(tmp_path / "bookmarks.json")
    store.set(0, "Remember this")
    store.set(1, "Next verse")
    settings_service = _MemorySettingsService()
    window = BookmarksWindow(store, settings_service=settings_service)
    activations: list[int] = []
    window.bookmarkActivated.connect(activations.append)

    assert window.bookmark_list.item(0).text() == "John 3:16 — Remember this"
    window._go_to_selected()
    assert activations == [0]

    window.note_edit.setPlainText("Updated note")
    window._save_note()
    assert store.get(0) is not None and store.get(0).note == "Updated note"

    window._delete_selected()
    assert store.get(0) is None
    assert window.bookmark_list.count() == 1
    assert window.bookmark_list.item(0).text() == "John 3:17 — Next verse"
    window.close()
    assert settings_service.saved_geometry is not None
    assert settings_service.saved_geometry[0] == "bookmarks_window"


def _copy_window(text: str, position: int = 0) -> SimpleNamespace:
    editor = QPlainTextEdit()
    editor.setPlainText(text)
    cursor = editor.textCursor()
    cursor.setPosition(position)
    editor.setTextCursor(cursor)
    window = SimpleNamespace(
        textEditor=editor,
        statusBar=SimpleNamespace(showMessage=lambda _message: None),
        get_line_number=lambda: 0,
        bookmark_store=None,
        bookmarks_window=None,
    )
    window._get_bookmark_store = AbibModule.MainWindow._get_bookmark_store.__get__(window)
    return window


def test_bookmark_current_verse_saves_note_and_refreshes_open_window(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(AbibModule.sh, "user_settings_dir", tmp_path)
    monkeypatch.setattr(AbibModule.sh, "Info", ((42, 2, 15),))
    monkeypatch.setattr(AbibModule.sh, "onechapterbooks", set())
    monkeypatch.setattr(AbibModule, "KJV", ("CHAPTER 3\n", "16 For God so loved\n"))
    monkeypatch.setattr(AbibModule, "Amap_rev", {1: 0})
    monkeypatch.setattr(
        AbibModule.QInputDialog,
        "getMultiLineText",
        lambda _parent, _title, label, initial: ("Prayer note", True)
        if "John 3:16" in label and initial == ""
        else ("", False),
    )
    window = _copy_window("CHAPTER 3\n16 For God so loved", len("CHAPTER 3\n") + 2)
    bookmarks_window = BookmarksWindow(
        BookmarkStore(tmp_path / "bookmarks.json"),
        settings_service=_MemorySettingsService(),
    )
    window.bookmarks_window = bookmarks_window

    AbibModule.MainWindow.bookmark_current_verse(cast(AbibModule.MainWindow, cast(object, window)))

    assert BookmarkStore(tmp_path / "bookmarks.json").get(0) is not None
    assert BookmarkStore(tmp_path / "bookmarks.json").get(0).note == "Prayer note"
    assert bookmarks_window.bookmark_list.count() == 1
    assert bookmarks_window.bookmark_list.item(0).text() == "John 3:16 — Prayer note"
    bookmarks_window.close()


def test_canceling_bookmark_dialog_does_not_save(qapp, tmp_path, monkeypatch):
    monkeypatch.setattr(AbibModule.sh, "user_settings_dir", tmp_path)
    monkeypatch.setattr(AbibModule.sh, "Info", ((42, 2, 15),))
    monkeypatch.setattr(AbibModule.sh, "onechapterbooks", set())
    monkeypatch.setattr(AbibModule, "KJV", ("16 For God so loved\n",))
    monkeypatch.setattr(AbibModule, "Amap_rev", {0: 0})
    monkeypatch.setattr(AbibModule.QInputDialog, "getMultiLineText", lambda *_args: ("", False))
    window = _copy_window("16 For God so loved")

    AbibModule.MainWindow.bookmark_current_verse(cast(AbibModule.MainWindow, cast(object, window)))

    assert not (tmp_path / "bookmarks.json").exists()


def test_bookmark_activation_pushes_current_position_and_displays_target(monkeypatch):
    history: list[tuple[object, int]] = []
    cleared: list[bool] = []
    displayed: list[int] = []
    monkeypatch.setattr(AbibModule, "forward", SimpleNamespace(clear=lambda: cleared.append(True)))
    monkeypatch.setattr(
        AbibModule.history,
        "back_push",
        lambda window, position: history.append((window, position)),
    )
    window = SimpleNamespace(
        get_line_number=lambda: 4,
        display_verse_from_history=displayed.append,
    )

    AbibModule.MainWindow._on_bookmark_activated(
        cast(AbibModule.MainWindow, cast(object, window)), 9,
    )

    assert history == [(window, 4)]
    assert cleared == [True]
    assert displayed == [9]