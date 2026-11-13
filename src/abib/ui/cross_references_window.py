# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Window listing the OpenBible.info cross-references for a Bible verse.

The window shows the source verse, one row per related verse or range (strongest
first), a minimum-votes filter and the OpenBible.info credit. Activating a row
emits :pyattr:`CrossReferencesWindow.referenceActivated` with the first verse
of the chosen reference; the window keeps showing the source verse.

Verse text and reference formatting are supplied as callables so the window has
no dependency on the main window's Bible text globals.
"""


from collections.abc import Callable
from html import escape
from typing import Any

# noinspection PyPackageRequirements
from PySide6.QtCore import Qt, Signal

# noinspection PyPackageRequirements
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from abib.services.cross_references import ATTRIBUTION_URL, CrossReference
from abib.services.settings import SettingsService

MIN_VOTES_SETTING = "crossref_min_votes"
GEOMETRY_KEY = "cross_references_window"
TOOLTIP_VERSE_LIMIT = 10
MIN_VOTES_RANGE = (-1000, 10000)


class CrossReferencesWindow(QWidget):
    """Ranked cross-references for one source verse."""

    referenceActivated = Signal(int)

    def __init__(
        self,
        service: Any,
        verse_text: Callable[[int], str],
        format_range: Callable[[int, int], str],
        parent=None,
        settings_service: SettingsService | None = None,
    ) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Cross References")
        self._service = service
        self._verse_text = verse_text
        self._format_range = format_range
        self._settings_service = settings_service if settings_service is not None else SettingsService()
        self._position: int | None = None
        self._is_dark = False

        try:
            x, y, width, height = self._settings_service.get_window_geometry(GEOMETRY_KEY)
            self.setGeometry(x, y, width, height)
        except (RuntimeError, TypeError, ValueError):
            self.resize(560, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)

        self.heading_label = QLabel(self)
        self.heading_label.setWordWrap(True)
        self.heading_label.setTextFormat(Qt.TextFormat.RichText)
        layout.addWidget(self.heading_label)

        controls = QHBoxLayout()
        min_votes_label = QLabel("Minimum votes:", self)
        controls.addWidget(min_votes_label)
        self.min_votes_spin = QSpinBox(self)
        self.min_votes_spin.setRange(*MIN_VOTES_RANGE)
        self.min_votes_spin.setValue(self._load_min_votes())
        self.min_votes_spin.setToolTip("Hide cross-references with fewer reader votes than this")
        min_votes_label.setBuddy(self.min_votes_spin)
        controls.addWidget(self.min_votes_spin)
        controls.addStretch(1)
        self.count_label = QLabel(self)
        controls.addWidget(self.count_label)
        layout.addLayout(controls)

        self.reference_list = QListWidget(self)
        self.reference_list.setWordWrap(True)
        self.reference_list.itemClicked.connect(self._activate_item)
        self.reference_list.itemActivated.connect(self._activate_item)
        layout.addWidget(self.reference_list, 1)

        self.attribution_label = QLabel(self)
        self.attribution_label.setTextFormat(Qt.TextFormat.RichText)
        self.attribution_label.setOpenExternalLinks(True)
        layout.addWidget(self.attribution_label)

        # Connect after the initial value is set so loading does not re-save it.
        self.min_votes_spin.valueChanged.connect(self._on_min_votes_changed)
        self._render_attribution()

    # --------- Settings ---------
    def _load_min_votes(self) -> int:
        try:
            value = self._settings_service.settings.get(MIN_VOTES_SETTING, 0)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            return 0
        if isinstance(value, bool) or not isinstance(value, int):
            return 0
        return max(MIN_VOTES_RANGE[0], min(value, MIN_VOTES_RANGE[1]))

    def _on_min_votes_changed(self, value: int) -> None:
        try:
            data = self._settings_service.settings
            data[MIN_VOTES_SETTING] = int(value)
            self._settings_service.save(data)
        except (AttributeError, OSError, RuntimeError, TypeError, ValueError):
            pass
        self._refresh()

    # --------- Content ---------
    def set_position(self, position: int) -> None:
        """Show the cross-references for the verse at *position*."""
        self._position = int(position)
        self._refresh()

    def _reference(self, start: int, end: int) -> str:
        try:
            return self._format_range(start, end)
        except (IndexError, KeyError, TypeError, ValueError):
            return f"Verse {start + 1}"

    def _text(self, position: int) -> str:
        try:
            return " ".join(str(self._verse_text(position)).split())
        except (IndexError, KeyError, TypeError, ValueError):
            return ""

    def _refresh(self) -> None:
        self.reference_list.clear()
        position = self._position
        if position is None:
            self.heading_label.setText("")
            self.count_label.setText("")
            return

        source = self._reference(position, position)
        source_text = self._text(position)
        heading = f"<b>{escape(source)}</b>"
        if source_text:
            heading += f" — {escape(source_text)}"
        self.heading_label.setText(heading)
        self.setWindowTitle(f"Cross References — {source}")

        total = int(self._service.count(position))
        references: list[CrossReference] = self._service.lookup(
            position, min_votes=self.min_votes_spin.value()
        )
        if total == 0:
            self.count_label.setText("")
            self._add_message(f"No cross-references for {source}")
            return

        self.count_label.setText(f"Showing {len(references)} of {total}")
        if not references:
            self._add_message("No cross-references meet the minimum vote count.")
            return
        for reference in references:
            self.reference_list.addItem(self._make_item(reference))

    def _add_message(self, message: str) -> None:
        item = QListWidgetItem(message)
        item.setFlags(Qt.ItemFlag.NoItemFlags)
        self.reference_list.addItem(item)

    def _make_item(self, reference: CrossReference) -> QListWidgetItem:
        label = self._reference(reference.to_start, reference.to_end)
        text = self._text(reference.to_start)
        is_range = reference.to_end > reference.to_start
        if is_range and text:
            text += " …"
        votes = f"{reference.votes} vote" + ("" if abs(reference.votes) == 1 else "s")
        item = QListWidgetItem(f"{label}  ({votes})\n{text}" if text else f"{label}  ({votes})")
        item.setData(Qt.ItemDataRole.UserRole, reference.to_start)
        item.setToolTip(self._tooltip(reference, label))
        return item

    def _tooltip(self, reference: CrossReference, label: str) -> str:
        last = min(reference.to_end, reference.to_start + TOOLTIP_VERSE_LIMIT - 1)
        lines = [label]
        for position in range(reference.to_start, last + 1):
            text = self._text(position)
            if text:
                lines.append(f"{self._reference(position, position)}  {text}")
        if reference.to_end > last:
            lines.append("…")
        return "\n".join(lines)

    def _activate_item(self, item: QListWidgetItem) -> None:
        position = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(position, int) and not isinstance(position, bool):
            self.referenceActivated.emit(position)

    # --------- Theme ---------
    def _render_attribution(self) -> None:
        try:
            credit = str(self._service.attribution())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            credit = "Cross-references: OpenBible.info (CC BY)"
        link_color = "#8ab4f8" if self._is_dark else "#1a5fb4"
        self.attribution_label.setText(
            f'<a href="{escape(ATTRIBUTION_URL)}" style="color:{link_color};">{escape(credit)}</a>'
        )

    def apply_theme(self, is_dark: bool) -> None:
        """Update theme-dependent colours (the attribution link)."""
        self._is_dark = bool(is_dark)
        self._render_attribution()

    # --------- Geometry ---------
    def _persist_geometry(self) -> None:
        try:
            geometry = self.geometry()
            self._settings_service.save_window_geometry(
                GEOMETRY_KEY,
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
