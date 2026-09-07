# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from abib.services.other_works_text_search import (
    OtherWorksTextSearchService,
    OtherWorkTextSearchOccurrence,
)
from abib.ui.other_works_results_view import populate_results_tree


class OtherWorksTextSearchWindow(QWidget):
    """Search enabled Other Works for literal text."""

    occurrenceActivated = Signal(str, int, int)

    def __init__(self, service: OtherWorksTextSearchService, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Other Works Text Search")
        self.setMinimumSize(520, 360)
        self.resize(520, 360)
        self._service = service
        self._occurrences: tuple[OtherWorkTextSearchOccurrence, ...] = ()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.query_edit = QLineEdit(self)
        self.query_edit.setPlaceholderText("Enter a word or phrase to search enabled Other Works")
        self.query_edit.returnPressed.connect(self.search)
        self.query_edit.textChanged.connect(self._clear_if_empty)
        layout.addWidget(self.query_edit)

        self.summary_label = QLabel("Enter text to search enabled Other Works.", self)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.results_tree = QTreeWidget(self)
        self.results_tree.setHeaderLabels(["Work / occurrence", "Match", "Snippet"])
        self.results_tree.itemActivated.connect(self._activate_item)
        self.results_tree.itemClicked.connect(self._activate_item)
        layout.addWidget(self.results_tree)

    def set_query(self, query: str) -> None:
        self.query_edit.setText(query)
        self.search()

    def clear_search(self) -> None:
        self.query_edit.clear()
        self.results_tree.clear()
        self._occurrences = ()
        self.summary_label.setText("Enter text to search enabled Other Works.")

    def refresh_index(self) -> None:
        self._service.rebuild()
        if self.query_edit.text().strip():
            self.search()

    def search(self) -> None:
        query = self.query_edit.text().strip()
        self.results_tree.clear()
        self._occurrences = ()
        if not query:
            self.summary_label.setText("Enter text to search enabled Other Works.")
            return

        results = self._service.search(query)
        if not results.occurrences:
            self.summary_label.setText(f"No enabled Other Works contain {query}.")
            return

        self._occurrences = results.occurrences
        populate_results_tree(
            self.results_tree,
            self.summary_label,
            results.occurrences,
            results.query,
            lambda occurrence: [occurrence.matched_text, occurrence.matched_text, occurrence.snippet],
        )

    def _clear_if_empty(self) -> None:
        if not self.query_edit.text().strip():
            self.results_tree.clear()
            self.summary_label.setText("Enter text to search enabled Other Works.")

    def _activate_item(self, item: QTreeWidgetItem) -> None:
        occurrence = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(occurrence, OtherWorkTextSearchOccurrence):
            self.occurrenceActivated.emit(occurrence.work_path, occurrence.abs_start, occurrence.length)