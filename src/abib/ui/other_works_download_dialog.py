# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Dialog letting the user choose which optional "Other Works" to download.

Driven by the remote manifest (see :func:`abib.core.content_sync.list_available`),
it shows one tickable row per available book. Already-downloaded (or previously
subscribed) titles start ticked. The chosen set of file *stems* is returned via
:meth:`OtherWorksDownloadDialog.selected_stems` and threaded into the content
sync so only those books are fetched/kept.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)


class OtherWorksDownloadDialog(QDialog):
    """Checklist of available Other Works for the user to select for download."""

    def __init__(
        self,
        parent: Any = None,
        available: Sequence[dict[str, Any]] | None = None,
        preselected: Iterable[str] | None = None,
    ) -> None:
        super().__init__(parent)
        self._available: list[dict[str, Any]] = list(available or [])
        # ``None`` means "no saved subscription" -> default installed books to
        # ticked. A concrete (possibly empty) set is an explicit selection.
        preselect_downloaded = preselected is None
        preselected_set = {str(s) for s in (preselected or [])}

        self.setWindowTitle("Download Other Works")
        self.resize(460, 520)

        layout = QVBoxLayout(self)

        intro = QLabel(
            "Choose which books to download. Ticked books are kept up to date; "
            "unticking a book removes its local copy on the next update."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        # Select all / Deselect all controls.
        controls = QHBoxLayout()
        select_all_btn = QPushButton("Select all")
        deselect_all_btn = QPushButton("Deselect all")
        select_all_btn.clicked.connect(lambda: self._set_all(True))
        deselect_all_btn.clicked.connect(lambda: self._set_all(False))
        controls.addWidget(select_all_btn)
        controls.addWidget(deselect_all_btn)
        controls.addStretch(1)
        layout.addLayout(controls)

        # Scrollable list of checkboxes.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        self._list_layout = QVBoxLayout(container)
        self._list_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._checkboxes: dict[str, QCheckBox] = {}
        if self._available:
            for book in self._available:
                stem = str(book.get("stem", ""))
                if not stem:
                    continue
                title = str(book.get("title") or stem)
                downloaded = bool(book.get("downloaded"))
                label = f"{title} (installed)" if downloaded else title
                checkbox = QCheckBox(label)
                checkbox.setChecked(stem in preselected_set or (downloaded and preselect_downloaded))
                self._checkboxes[stem] = checkbox
                self._list_layout.addWidget(checkbox)
        else:
            self._list_layout.addWidget(QLabel("No optional books are currently available."))

        scroll.setWidget(container)
        layout.addWidget(scroll, 1)

        button_types = QDialogButtonBox.StandardButton
        buttons = button_types.Ok | button_types.Cancel  # type: ignore[operator]
        self.button_box = QDialogButtonBox(buttons)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _set_all(self, checked: bool) -> None:
        for checkbox in self._checkboxes.values():
            checkbox.setChecked(checked)

    def selected_stems(self) -> set[str]:
        """Return the set of file stems the user ticked."""
        return {stem for stem, cb in self._checkboxes.items() if cb.isChecked()}
