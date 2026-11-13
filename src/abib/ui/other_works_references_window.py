# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

# noinspection PyPackageRequirements
from PySide6.QtCore import Qt, Signal

# noinspection PyPackageRequirements
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from abib.services.commentary_lookup import CommentaryEntry, CommentaryLookup
from abib.services.other_works_reference_index import (
    OtherWorkReferenceOccurrence,
    OtherWorksReferenceIndex,
    reference_label_from_key,
)
from abib.services.settings import SettingsService
from abib.ui.other_works_results_view import populate_results_tree


class OtherWorksReferencesWindow(QWidget):
    """Browse Other Works that mention a Bible reference."""

    occurrenceActivated = Signal(str, int, int)
    commentaryActivated = Signal(int, int, int)

    def __init__(
        self,
        service: OtherWorksReferenceIndex,
        parent=None,
        settings_service: SettingsService | None = None,
        commentary: CommentaryLookup | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Other Works Scripture reference search")
        self.setMinimumSize(520, 360)
        self._service = service
        self._commentary_service = commentary
        self._settings_service = settings_service if settings_service is not None else SettingsService()
        self._occurrences: tuple[OtherWorkReferenceOccurrence, ...] = ()
        self._commentaries: tuple[CommentaryEntry, ...] = ()

        try:
            gx, gy, gw, gh = self._settings_service.get_window_geometry("other_works_references_window")
            self.setGeometry(gx, gy, gw, gh)
        except (RuntimeError, TypeError, ValueError):
            self.resize(520, 360)

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
        self._commentaries = ()
        self.summary_label.setText("Enter a reference to search enabled Other Works.")

    def refresh_index(self) -> None:
        self._service.rebuild()
        if self.reference_edit.text().strip():
            self.search()

    def search(self) -> None:
        reference = self.reference_edit.text().strip()
        self.results_tree.clear()
        self._occurrences = ()
        self._commentaries = ()
        if not reference:
            self.summary_label.setText("Enter a reference to search enabled Other Works.")
            return

        group = self._service.lookup(reference)
        key = self._service.key_for_reference(reference)
        commentaries = self._commentary_service.lookup(key) if key is not None and self._commentary_service else ()
        if group is None and not commentaries:
            self.summary_label.setText(f"No enabled Other Works contain {reference}.")
            return

        self._commentaries = commentaries
        if group is not None:
            self._occurrences = group.occurrences
        if group is not None:
            reference_label = group.reference_label
        elif key is not None:
            reference_label = reference_label_from_key(key)
        else:
            reference_label = reference

        if commentaries:
            names = ", ".join(entry.label for entry in commentaries)
            parent = QTreeWidgetItem([f"Commentaries on {reference_label} ({len(commentaries)})", "", ""])
            parent.setFirstColumnSpanned(True)
            self.results_tree.addTopLevelItem(parent)
            for entry in commentaries:
                item = QTreeWidgetItem([entry.label, reference_label, entry.snippet])
                item.setData(0, Qt.ItemDataRole.UserRole, entry)
                parent.addChild(item)
            parent.setExpanded(True)

        if self._occurrences:
            populate_results_tree(
                self.results_tree,
                self.summary_label,
                self._occurrences,
                reference_label,
                lambda occurrence: [occurrence.matched_text, occurrence.reference_label, occurrence.snippet],
            )
        elif commentaries:
            self.summary_label.setText(f"Commentaries for {reference_label}: {names}.")
        if commentaries and self._occurrences:
            noun = "occurrence" if len(self._occurrences) == 1 else "occurrences"
            self.summary_label.setText(
                f"Commentaries for {reference_label}: {names}; "
                f"{len(self._occurrences)} Other Works {noun} found."
            )

    def _clear_if_empty(self) -> None:
        if not self.reference_edit.text().strip():
            self.results_tree.clear()
            self._occurrences = ()
            self._commentaries = ()
            self.summary_label.setText("Enter a reference to search enabled Other Works.")

    def _activate_item(self, item: QTreeWidgetItem) -> None:
        occurrence = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(occurrence, CommentaryEntry):
            if occurrence.source == "gill":
                self.commentaryActivated.emit(occurrence.book, occurrence.chapter, occurrence.verse)
            elif occurrence.work_path is not None and occurrence.abs_start is not None and occurrence.length is not None:
                self.occurrenceActivated.emit(occurrence.work_path, occurrence.abs_start, occurrence.length)
            return
        if isinstance(occurrence, OtherWorkReferenceOccurrence):
            self.occurrenceActivated.emit(occurrence.work_path, occurrence.abs_start, occurrence.length)

    def _persist_geometry(self) -> None:
        try:
            geom = self.geometry()
            self._settings_service.save_window_geometry(
                "other_works_references_window", int(geom.x()), int(geom.y()), int(geom.width()), int(geom.height())
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