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

from abib.services.other_works_reference_index import (
    OtherWorkReferenceOccurrence,
    OtherWorksReferenceIndex,
)
from abib.ui.other_works_results_view import populate_results_tree


class OtherWorksReferencesWindow(QWidget):
    """Browse Other Works that mention a Bible reference."""

    occurrenceActivated = Signal(str, int, int)

    def __init__(self, service: OtherWorksReferenceIndex, parent=None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Other Works Scripture reference search")
        self.setMinimumSize(520, 360)
        self.resize(520, 360)
        self._service = service
        self._occurrences: tuple[OtherWorkReferenceOccurrence, ...] = ()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.reference_edit = QLineEdit(self)
        self.reference_edit.setPlaceholderText("Enter a Bible reference, e.g. John 3:16")
        self.reference_edit.returnPressed.connect(self.search)
        self.reference_edit.textChanged.connect(self._clear_if_empty)
        layout.addWidget(self.reference_edit)

        self.summary_label = QLabel("Enter a reference to search enabled Other Works.", self)
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.results_tree = QTreeWidget(self)
        self.results_tree.setHeaderLabels(["Work / occurrence", "Reference", "Snippet"])
        self.results_tree.itemActivated.connect(self._activate_item)
        self.results_tree.itemClicked.connect(self._activate_item)
        layout.addWidget(self.results_tree)

    def set_reference(self, reference: str) -> None:
        self.reference_edit.setText(reference)
        self.search()

    def clear_search(self) -> None:
        self.reference_edit.clear()
        self.results_tree.clear()
        self._occurrences = ()
        self.summary_label.setText("Enter a reference to search enabled Other Works.")

    def refresh_index(self) -> None:
        self._service.rebuild()
        if self.reference_edit.text().strip():
            self.search()

    def search(self) -> None:
        reference = self.reference_edit.text().strip()
        self.results_tree.clear()
        self._occurrences = ()
        if not reference:
            self.summary_label.setText("Enter a reference to search enabled Other Works.")
            return

        group = self._service.lookup(reference)
        if group is None:
            self.summary_label.setText(f"No enabled Other Works contain {reference}.")
            return

        self._occurrences = group.occurrences
        populate_results_tree(
            self.results_tree,
            self.summary_label,
            group.occurrences,
            group.reference_label,
            lambda occurrence: [occurrence.matched_text, occurrence.reference_label, occurrence.snippet],
        )

    def _clear_if_empty(self) -> None:
        if not self.reference_edit.text().strip():
            self.results_tree.clear()
            self.summary_label.setText("Enter a reference to search enabled Other Works.")

    def _activate_item(self, item: QTreeWidgetItem) -> None:
        occurrence = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(occurrence, OtherWorkReferenceOccurrence):
            self.occurrenceActivated.emit(occurrence.work_path, occurrence.abs_start, occurrence.length)