# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

# noinspection PyPackageRequirements
from PySide6.QtCore import Qt, Signal

# noinspection PyPackageRequirements
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
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
from abib.services.settings import SettingsService
from abib.ui.other_works_results_view import populate_results_tree


class OtherWorksTextSearchWindow(QWidget):
    """Search enabled Other Works for literal text."""

    occurrenceActivated = Signal(str, int, int)

    def __init__(
        self,
        service: OtherWorksTextSearchService,
        parent=None,
        settings_service: SettingsService | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Other Works Text Search")
        self.setMinimumSize(520, 360)
        self._service = service
        self._settings_service = settings_service if settings_service is not None else SettingsService()
        self._occurrences: tuple[OtherWorkTextSearchOccurrence, ...] = ()

        try:
            gx, gy, gw, gh = self._settings_service.get_window_geometry("other_works_text_search_window")
            self.setGeometry(gx, gy, gw, gh)
        except (RuntimeError, TypeError, ValueError):
            self.resize(520, 360)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.query_edit = QLineEdit(self)
        self.query_edit.setPlaceholderText("Enter a word or phrase to search enabled Other Works")
        self.query_edit.returnPressed.connect(self.search)
        self.query_edit.textChanged.connect(self._clear_if_empty)
        layout.addWidget(self.query_edit)

        options_layout = QHBoxLayout()
        options_layout.setContentsMargins(0, 0, 0, 0)
        self.whole_words_checkbox = QCheckBox("Whole words only", self)
        self.whole_words_checkbox.toggled.connect(self._on_options_changed)
        options_layout.addWidget(self.whole_words_checkbox)
        self.case_sensitive_checkbox = QCheckBox("Case sensitive", self)
        self.case_sensitive_checkbox.toggled.connect(self._on_options_changed)
        options_layout.addWidget(self.case_sensitive_checkbox)
        options_layout.addStretch(1)
        layout.addLayout(options_layout)

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

        results = self._service.search(
            query,
            whole_words=self.whole_words_checkbox.isChecked(),
            case_sensitive=self.case_sensitive_checkbox.isChecked(),
        )
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

    def _on_options_changed(self) -> None:
        if self.query_edit.text().strip():
            self.search()

    def _clear_if_empty(self) -> None:
        if not self.query_edit.text().strip():
            self.results_tree.clear()
            self.summary_label.setText("Enter text to search enabled Other Works.")

    def _activate_item(self, item: QTreeWidgetItem) -> None:
        occurrence = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(occurrence, OtherWorkTextSearchOccurrence):
            self.occurrenceActivated.emit(occurrence.work_path, occurrence.abs_start, occurrence.length)

    def _persist_geometry(self) -> None:
        try:
            geom = self.geometry()
            self._settings_service.save_window_geometry(
                "other_works_text_search_window", int(geom.x()), int(geom.y()), int(geom.width()), int(geom.height())
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