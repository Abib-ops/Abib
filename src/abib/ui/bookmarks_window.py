# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


# noinspection PyPackageRequirements
from PySide6.QtCore import Qt, Signal

# noinspection PyPackageRequirements
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from abib.core import shared as sh
from abib.services.bookmarks import Bookmark, BookmarkStore
from abib.services.settings import SettingsService
from abib.services.verse_copy import format_reference_range


class BookmarksWindow(QWidget):
    """List and edit personal Bible verse bookmarks and notes."""

    bookmarkActivated = Signal(int)

    def __init__(
        self,
        store: BookmarkStore,
        parent=None,
        settings_service: SettingsService | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Bookmarks and Notes")
        self._store = store
        self._settings_service = settings_service if settings_service is not None else SettingsService()

        try:
            x, y, width, height = self._settings_service.get_window_geometry("bookmarks_window")
            self.setGeometry(x, y, width, height)
        except (RuntimeError, TypeError, ValueError):
            self.resize(520, 440)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(QLabel("Select a bookmark to view or edit its note.", self))

        self.bookmark_list = QListWidget(self)
        self.bookmark_list.itemSelectionChanged.connect(self._selection_changed)
        self.bookmark_list.itemActivated.connect(self._activate_item)
        layout.addWidget(self.bookmark_list)

        layout.addWidget(QLabel("Note", self))
        self.note_edit = QPlainTextEdit(self)
        self.note_edit.setPlaceholderText("Add a personal note for this verse...")
        layout.addWidget(self.note_edit)

        buttons_layout = QHBoxLayout()
        self.go_to_button = QPushButton("Go to", self)
        self.go_to_button.clicked.connect(self._go_to_selected)
        buttons_layout.addWidget(self.go_to_button)
        self.save_note_button = QPushButton("Save Note", self)
        self.save_note_button.clicked.connect(self._save_note)
        buttons_layout.addWidget(self.save_note_button)
        self.delete_button = QPushButton("Delete", self)
        self.delete_button.clicked.connect(self._delete_selected)
        buttons_layout.addWidget(self.delete_button)
        layout.addLayout(buttons_layout)

        self.refresh()

    def refresh(self, selected_position: int | None = None) -> None:
        """Reload bookmarks and keep the requested or current selection."""
        if selected_position is None:
            current = self.bookmark_list.currentItem()
            if current is not None:
                value = current.data(Qt.ItemDataRole.UserRole)
                selected_position = value if isinstance(value, int) else None

        self.bookmark_list.clear()
        for bookmark in self._store.all():
            item = QListWidgetItem(self._item_text(bookmark))
            item.setData(Qt.ItemDataRole.UserRole, bookmark.position)
            item.setToolTip(self._item_tooltip(bookmark))
            self.bookmark_list.addItem(item)
            if bookmark.position == selected_position:
                self.bookmark_list.setCurrentItem(item)

        if self.bookmark_list.currentItem() is None and self.bookmark_list.count():
            self.bookmark_list.setCurrentRow(0)
        self._selection_changed()

    @staticmethod
    def _reference(position: int) -> str:
        try:
            return format_reference_range(position, position, sh.Info, sh.onechapterbooks)
        except (IndexError, TypeError, ValueError):
            return f"Verse {position + 1}"

    @classmethod
    def _item_text(cls, bookmark: Bookmark) -> str:
        preview = " ".join(bookmark.note.split())
        if len(preview) > 80:
            preview = preview[:77] + "..."
        return f"{cls._reference(bookmark.position)} — {preview}" if preview else cls._reference(bookmark.position)

    @classmethod
    def _item_tooltip(cls, bookmark: Bookmark) -> str:
        reference = cls._reference(bookmark.position)
        return f"{reference}\n{bookmark.note}" if bookmark.note else reference

    def _selected_position(self) -> int | None:
        item = self.bookmark_list.currentItem()
        if item is None:
            return None
        position = item.data(Qt.ItemDataRole.UserRole)
        return position if isinstance(position, int) else None

    def _selection_changed(self) -> None:
        position = self._selected_position()
        bookmark = self._store.get(position) if position is not None else None
        self.note_edit.setPlainText(bookmark.note if bookmark is not None else "")
        has_selection = bookmark is not None
        self.go_to_button.setEnabled(has_selection)
        self.save_note_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def _activate_item(self, item: QListWidgetItem) -> None:
        position = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(position, int):
            self.bookmarkActivated.emit(position)

    def _go_to_selected(self) -> None:
        position = self._selected_position()
        if position is not None:
            self.bookmarkActivated.emit(position)

    def _save_note(self) -> None:
        position = self._selected_position()
        if position is None:
            return
        self._store.set(position, self.note_edit.toPlainText())
        self.refresh(position)

    def _delete_selected(self) -> None:
        position = self._selected_position()
        if position is not None:
            self._store.remove(position)
            self.refresh()

    def _persist_geometry(self) -> None:
        try:
            geometry = self.geometry()
            self._settings_service.save_window_geometry(
                "bookmarks_window",
                int(geometry.x()),
                int(geometry.y()),
                int(geometry.width()),
                int(geometry.height()),
            )
        except (RuntimeError, TypeError, ValueError, AttributeError):
            pass

    def moveEvent(self, event):  # type: ignore[override]
        self._persist_geometry()
        try:
            return super().moveEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def resizeEvent(self, event):  # type: ignore[override]
        self._persist_geometry()
        try:
            return super().resizeEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def closeEvent(self, event):  # type: ignore[override]
        self._persist_geometry()
        try:
            return super().closeEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None