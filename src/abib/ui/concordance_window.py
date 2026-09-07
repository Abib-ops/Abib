# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from abib.services.concordance_service import (
    ConcordanceEntry,
    ConcordanceHit,
    ConcordanceService,
)


class ConcordanceWindow(QWidget):
    """Separate top-level window for browsing Bible concordance entries."""

    referenceActivated = Signal(int)

    def __init__(self, service: ConcordanceService, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Concordance")
        self._service = service
        self._entries: tuple[ConcordanceEntry, ...] = ()
        self._current_hits: tuple[ConcordanceHit, ...] = ()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.filter_edit = QLineEdit(self)
        self.filter_edit.setPlaceholderText("Filter words or type a phrase...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        layout.addWidget(splitter)

        self.entry_list = QListWidget(splitter)
        self.entry_list.itemSelectionChanged.connect(self._entry_selection_changed)
        self.entry_list.itemActivated.connect(self._activate_entry)
        splitter.addWidget(self.entry_list)

        right_panel = QWidget(splitter)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(4, 0, 0, 0)

        self.summary_label = QLabel("Select an entry to view references.", right_panel)
        self.summary_label.setWordWrap(True)
        right_layout.addWidget(self.summary_label)

        self.reference_list = QListWidget(right_panel)
        self.reference_list.setWordWrap(True)
        self.reference_list.itemClicked.connect(self._activate_reference)
        self.reference_list.itemActivated.connect(self._activate_reference)
        right_layout.addWidget(self.reference_list)

        splitter.addWidget(right_panel)
        splitter.setSizes([220, 420])

        self.refresh()

    def refresh(self) -> None:
        """Reload entries from the service and apply the current filter."""
        self._entries = self._service.entries()
        self._apply_filter()

    def _apply_filter(self) -> None:
        filter_text = self.filter_edit.text().strip()
        if " " in filter_text:
            phrase_entry = self._service.get_entry(filter_text)
            entries = (phrase_entry,) if phrase_entry is not None else ()
        else:
            entries = self._service.matching_entries(filter_text)

        self.entry_list.clear()
        for entry in entries:
            item = QListWidgetItem(f"{entry.term} ({entry.count})")
            item.setData(Qt.ItemDataRole.UserRole, entry.term)
            item.setToolTip(f"{entry.term}: {entry.count} occurrence(s)")
            self.entry_list.addItem(item)

        if self.entry_list.count():
            self.entry_list.setCurrentRow(0)
        else:
            self._show_entry(None)

    def _entry_selection_changed(self) -> None:
        self._show_entry(self.entry_list.currentItem())

    def _activate_entry(self, item: QListWidgetItem) -> None:
        self._show_entry(item)

    def _show_entry(self, item: QListWidgetItem | None) -> None:
        self.reference_list.clear()
        self._current_hits = ()
        if item is None:
            self.summary_label.setText("No concordance entries match the filter.")
            return

        term = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(term, str):
            self.summary_label.setText("Select an entry to view references.")
            return
        entry = self._service.get_entry(term)
        if entry is None:
            self.summary_label.setText("No references found.")
            return

        self._current_hits = entry.hits
        noun = "occurrence" if entry.count == 1 else "occurrences"
        self.summary_label.setText(f"{entry.term}: {entry.count} {noun}")
        for hit in entry.hits:
            ref_item = QListWidgetItem(f"{hit.reference}  {hit.verse_text}")
            ref_item.setData(Qt.ItemDataRole.UserRole, hit.position)
            ref_item.setToolTip(f"{hit.reference}\n{hit.verse_text}")
            self.reference_list.addItem(ref_item)

    def _activate_reference(self, item: QListWidgetItem) -> None:
        position = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(position, int):
            self.referenceActivated.emit(position)