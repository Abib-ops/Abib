# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Tests for the OpenBible cross-reference service, window and main-window wiring."""


import sqlite3
from pathlib import Path
from types import SimpleNamespace
from typing import Any, cast

# noinspection PyPackageRequirements
from PySide6.QtCore import Qt

# noinspection PyPackageRequirements
from PySide6.QtWidgets import QPlainTextEdit, QWidget

from abib import Abib as AbibModule
from abib.core import shared as sh
from abib.services.cross_references import (
    DATASET_FILENAME,
    DEFAULT_ATTRIBUTION,
    CrossReference,
    CrossReferenceService,
)
from abib.services.settings import SettingsService
from abib.ui.cross_references_window import CrossReferencesWindow


def _make_db(path: Path, rows: list[tuple[int, int, int, int]], attribution: str | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE crossrefs (
                from_vi  INTEGER NOT NULL,
                to_start INTEGER NOT NULL,
                to_end   INTEGER NOT NULL,
                votes    INTEGER NOT NULL,
                PRIMARY KEY (from_vi, to_start, to_end)
            ) WITHOUT ROWID;
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
            """
        )
        conn.executemany("INSERT INTO crossrefs VALUES (?, ?, ?, ?)", rows)
        if attribution is not None:
            conn.execute("INSERT INTO meta VALUES ('attribution', ?)", (attribution,))
        conn.commit()
    finally:
        conn.close()
    return path


_ROWS = [
    (10, 500, 500, 3),
    (10, 200, 202, 9),
    (10, 100, 100, 9),
    (10, 300, 300, -4),
    (11, 400, 400, 1),
]


def test_lookup_orders_by_votes_then_bible_order(tmp_path):
    service = CrossReferenceService(_make_db(tmp_path / DATASET_FILENAME, _ROWS))

    assert service.is_available()
    assert service.lookup(10) == [
        CrossReference(100, 100, 9),
        CrossReference(200, 202, 9),
        CrossReference(500, 500, 3),
        CrossReference(300, 300, -4),
    ]
    assert service.count(10) == 4
    assert service.count(12) == 0
    assert service.lookup(12) == []


def test_lookup_min_votes_excludes_weaker_rows(tmp_path):
    service = CrossReferenceService(_make_db(tmp_path / DATASET_FILENAME, _ROWS))

    assert [ref.to_start for ref in service.lookup(10, min_votes=0)] == [100, 200, 500]
    assert [ref.to_start for ref in service.lookup(10, min_votes=5)] == [100, 200]
    assert service.count(10) == 4  # count stays unfiltered


def test_attribution_reads_meta_or_falls_back(tmp_path):
    with_meta = CrossReferenceService(
        _make_db(tmp_path / "a" / DATASET_FILENAME, _ROWS, attribution="Credit line")
    )
    without_meta = CrossReferenceService(_make_db(tmp_path / "b" / DATASET_FILENAME, _ROWS))

    assert with_meta.attribution() == "Credit line"
    assert without_meta.attribution() == DEFAULT_ATTRIBUTION
    assert CrossReferenceService(tmp_path / "missing.sqlite").attribution() == DEFAULT_ATTRIBUTION


def test_missing_corrupt_and_wrong_schema_files_degrade(tmp_path):
    missing = CrossReferenceService(tmp_path / "missing.sqlite")
    corrupt_path = tmp_path / "corrupt.sqlite"
    corrupt_path.write_bytes(b"this is not a database")
    corrupt = CrossReferenceService(corrupt_path)
    wrong_path = tmp_path / "wrong.sqlite"
    conn = sqlite3.connect(wrong_path)
    conn.execute("CREATE TABLE other (x INTEGER)")
    conn.commit()
    conn.close()
    wrong = CrossReferenceService(wrong_path)

    for service in (missing, corrupt, wrong):
        assert service.is_available() is False
        assert service.lookup(10) == []
        assert service.count(10) == 0
    assert not (tmp_path / "missing.sqlite").exists()  # read-only open never creates it


def test_invalid_positions_return_nothing(tmp_path):
    service = CrossReferenceService(_make_db(tmp_path / DATASET_FILENAME, _ROWS))

    for position in (None, -1, sh.LAST_VERSE_IN_BIBLE + 1, "10", True):
        assert service.lookup(position) == []  # type: ignore[arg-type]
        assert service.count(position) == 0  # type: ignore[arg-type]


def test_file_can_be_deleted_right_after_lookup(tmp_path):
    path = _make_db(tmp_path / "Cross References" / DATASET_FILENAME, _ROWS)
    service = CrossReferenceService(path)

    assert service.lookup(10)
    assert service.count(10) == 4
    assert service.attribution()
    path.unlink()  # would raise PermissionError on Windows if a handle stayed open

    assert not path.exists()
    assert service.is_available() is False


def test_default_path_uses_user_crossrefs_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(sh, "user_crossrefs_dir", tmp_path / "Cross References")

    assert CrossReferenceService().db_path == tmp_path / "Cross References" / DATASET_FILENAME


def test_real_paths_with_spaces_open(tmp_path):
    path = _make_db(tmp_path / "Folder With Spaces" / "Cross References" / DATASET_FILENAME, _ROWS)

    assert CrossReferenceService(path).count(11) == 1


# --------- Window ---------
class _MemorySettingsService:
    def __init__(self, settings: dict[str, Any] | None = None) -> None:
        self.settings: dict[str, Any] = dict(settings or {})
        self.saves = 0
        self.saved_geometry: tuple[str, tuple[int, ...]] | None = None

    def save(self, data: dict[str, Any]) -> None:
        self.settings = data
        self.saves += 1

    # noinspection PyMethodMayBeStatic
    def get_window_geometry(self, _window_name: str) -> tuple[int, int, int, int]:
        return 120, 120, 560, 520

    def save_window_geometry(self, window_name: str, *geometry: int) -> None:
        self.saved_geometry = window_name, geometry


def _verse_text(position: int) -> str:
    return f"text {position}"


def _format_range(start: int, end: int) -> str:
    return f"V{start}" if start == end else f"V{start}-{end}"


def _window(tmp_path, settings: dict[str, Any] | None = None, rows=None):
    service = CrossReferenceService(
        _make_db(tmp_path / DATASET_FILENAME, _ROWS if rows is None else rows, attribution="Credit")
    )
    settings_service = _MemorySettingsService(settings)
    window = CrossReferencesWindow(
        service,
        _verse_text,
        _format_range,
        settings_service=cast(SettingsService, cast(object, settings_service)),
    )
    return window, settings_service


def _row_texts(window: CrossReferencesWindow) -> list[str]:
    return [window.reference_list.item(i).text() for i in range(window.reference_list.count())]


def test_window_shows_heading_rows_count_and_attribution(qapp, tmp_path):
    window, _settings = _window(tmp_path)

    window.set_position(10)

    assert "V10" in window.heading_label.text()
    assert "text 10" in window.heading_label.text()
    assert _row_texts(window) == [
        "V100  (9 votes)\ntext 100",
        "V200-202  (9 votes)\ntext 200 …",
        "V500  (3 votes)\ntext 500",
    ]
    assert window.count_label.text() == "Showing 3 of 4"
    assert "Credit" in window.attribution_label.text()
    assert "openbible.info" in window.attribution_label.text()
    tooltip = window.reference_list.item(1).toolTip()
    assert tooltip.splitlines() == ["V200-202", "V200  text 200", "V201  text 201", "V202  text 202"]
    window.close()


def test_window_tooltip_caps_long_ranges(qapp, tmp_path):
    window, _settings = _window(tmp_path, rows=[(10, 100, 130, 5)])

    window.set_position(10)

    lines = window.reference_list.item(0).toolTip().splitlines()
    assert lines[0] == "V100-130"
    assert len(lines) == 1 + 10 + 1
    assert lines[-1] == "…"
    window.close()


def test_min_votes_filter_refilters_and_is_saved(qapp, tmp_path):
    window, settings = _window(tmp_path, settings={"crossref_min_votes": -10})

    window.set_position(10)
    assert window.min_votes_spin.value() == -10
    assert window.count_label.text() == "Showing 4 of 4"
    assert settings.saves == 0

    window.min_votes_spin.setValue(5)

    assert window.count_label.text() == "Showing 2 of 4"
    assert settings.settings["crossref_min_votes"] == 5

    window.min_votes_spin.setValue(50)
    assert window.count_label.text() == "Showing 0 of 4"
    assert _row_texts(window) == ["No cross-references meet the minimum vote count."]
    window.close()


def test_window_reports_verse_without_cross_references(qapp, tmp_path):
    window, _settings = _window(tmp_path)

    window.set_position(12)

    assert _row_texts(window) == ["No cross-references for V12"]
    assert window.count_label.text() == ""
    assert window.reference_list.item(0).flags() == Qt.ItemFlag.NoItemFlags
    window.close()


def test_activating_row_emits_first_verse_and_keeps_source(qapp, tmp_path):
    window, settings = _window(tmp_path)
    activated: list[int] = []
    window.referenceActivated.connect(activated.append)
    window.set_position(10)

    window._activate_item(window.reference_list.item(1))

    assert activated == [200]
    assert "V10" in window.heading_label.text()
    window.close()
    assert settings.saved_geometry is not None
    assert settings.saved_geometry[0] == "cross_references_window"


def test_apply_theme_changes_link_colour(qapp, tmp_path):
    window, _settings = _window(tmp_path)
    light = window.attribution_label.text()

    window.apply_theme(True)

    assert window.attribution_label.text() != light
    window.close()


# --------- Main window ---------
class _Host(QWidget):
    """Minimal stand-in for MainWindow (a real QWidget, so it can parent the window)."""

    def __init__(self, service: CrossReferenceService, editor_text: str, cursor_position: int) -> None:
        super().__init__()
        self.textEditor = QPlainTextEdit()
        self.textEditor.setPlainText(editor_text)
        cursor = self.textEditor.textCursor()
        cursor.setPosition(cursor_position)
        self.textEditor.setTextCursor(cursor)
        self.cross_reference_service = service
        self.cross_references_window: Any = None
        self.settings_service = _MemorySettingsService()
        self.messages: list[str] = []
        self.statusBar = SimpleNamespace(showMessage=self.messages.append)
        self.theme = SimpleNamespace(
            state=SimpleNamespace(is_dark_mode=False), apply_widget=lambda _widget: None
        )
        self.update_calls = 0
        self.activated: list[int] = []

    # noinspection PyMethodMayBeStatic
    def get_line_number(self) -> int:
        return 0

    def update_other_works(self) -> None:
        self.update_calls += 1

    def _on_cross_reference_activated(self, position: int) -> None:
        self.activated.append(position)


def _patch_bible(monkeypatch) -> None:
    monkeypatch.setattr(AbibModule.sh, "Info", ((42, 2, 15), (42, 2, 16), (0, 0, 0)))
    monkeypatch.setattr(AbibModule.sh, "onechapterbooks", set())
    monkeypatch.setattr(
        AbibModule, "KJV", ("16 For God so loved\n", "17 For God sent not\n", "In the beginning\n")
    )
    monkeypatch.setattr(AbibModule, "Amap", (0, 1, 2))
    monkeypatch.setattr(AbibModule, "Amap_rev", {0: 0, 1: 1, 2: 2})


def _open(host: _Host) -> None:
    AbibModule.MainWindow.open_cross_references(cast(AbibModule.MainWindow, cast(object, host)))


def test_open_cross_references_shows_current_verse(qapp, tmp_path, monkeypatch):
    _patch_bible(monkeypatch)
    service = CrossReferenceService(
        _make_db(tmp_path / DATASET_FILENAME, [(1, 0, 0, 7), (1, 2, 2, 3)])
    )
    text = "16 For God so loved\n17 For God sent not\nIn the beginning"
    host = _Host(service, text, len("16 For God so loved\n") + 3)

    _open(host)

    window = host.cross_references_window
    assert isinstance(window, CrossReferencesWindow)
    assert "John 3:17" in window.heading_label.text()
    assert "For God sent not" in window.heading_label.text()
    assert _row_texts(window) == [
        "John 3:16  (7 votes)\nFor God so loved",
        "Genesis 1:1  (3 votes)\nIn the beginning",
    ]
    window._activate_item(window.reference_list.item(0))
    assert host.activated == [0]

    # Invoking the action again shows the then-current verse in the same window.
    cursor = host.textEditor.textCursor()
    cursor.setPosition(0)
    host.textEditor.setTextCursor(cursor)
    _open(host)
    assert host.cross_references_window is window
    assert "John 3:16" in window.heading_label.text()
    assert _row_texts(window) == ["No cross-references for John 3:16"]
    window.close()


def test_missing_dataset_offers_update_other_works(qapp, tmp_path, monkeypatch):
    _patch_bible(monkeypatch)
    questions: list[str] = []
    answers = [AbibModule.QMessageBox.StandardButton.No, AbibModule.QMessageBox.StandardButton.Yes]

    def fake_question(_parent, _title, text, *_args):
        questions.append(text)
        return answers.pop(0)

    monkeypatch.setattr(AbibModule.QMessageBox, "question", fake_question)
    host = _Host(CrossReferenceService(tmp_path / "missing.sqlite"), "16 For God so loved", 0)

    _open(host)
    assert host.update_calls == 0
    _open(host)

    assert host.update_calls == 1
    assert len(questions) == 2
    assert "Open Update Other Works now?" in questions[0]
    assert host.cross_references_window is None


def test_cross_reference_activation_records_history(navigation_recorder):
    AbibModule.MainWindow._on_cross_reference_activated(navigation_recorder.window, 9)

    navigation_recorder.assert_navigated_to(9)
