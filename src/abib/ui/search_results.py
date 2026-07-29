# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from typing import Iterable, Sequence

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout, QWidget

from abib.utils.text import create_pattern, split_strip


@dataclass(frozen=True)
class SearchResult:
    """A single verse shown in the search results panel."""

    position: int
    reference: str
    text: str
    html_text: str


def format_reference(
        position: int,
        info: Sequence[Sequence[int]],
        book_names: Sequence[str],
        one_chapter_books: Iterable[int]) -> str:
    """Format a verse reference from the global verse position."""
    book_id = info[position][0]
    chapter = info[position][1] + 1
    verse = info[position][2] + 1
    book_name = book_names[book_id]
    if book_id in one_chapter_books:
        return f"{book_name} {verse}"
    return f"{book_name} {chapter}:{verse}"


def highlight_result_text(text: str, search_text: str, search_mode: int, case_sensitive: bool) -> str:
    """Return escaped HTML for a verse with search terms highlighted."""
    ranges = find_highlight_ranges(text, search_text, search_mode, case_sensitive)
    if not ranges:
        return html.escape(text)

    parts: list[str] = []
    current = 0
    for start, end in ranges:
        if start < current:
            continue
        parts.append(html.escape(text[current:start]))
        highlighted = html.escape(text[start:end])
        parts.append(f'<span style="background-color: #fff59d; color: #000000;">{highlighted}</span>')
        current = end
    parts.append(html.escape(text[current:]))
    return ''.join(parts)


def result_verse_text(position: int, kjv: Sequence[str], amap: Sequence[int | str]) -> str:
    """Return the display verse text for a compact search-result position."""
    line_number = int(amap[position])
    return str(kjv[line_number])


def find_highlight_ranges(text: str, search_text: str, search_mode: int, case_sensitive: bool) -> list[tuple[int, int]]:
    """Find non-overlapping match ranges for result-snippet highlighting."""
    flags = 0 if case_sensitive else re.IGNORECASE
    patterns: list[str] = []

    if search_mode in (3, 4):
        _, stripped = split_strip(search_text)
        terms = list(dict.fromkeys(term for term in stripped.split(' ') if term))
        patterns = [create_pattern(re.escape(term)) for term in terms]
    elif search_mode == 2:
        _, stripped = split_strip(search_text)
        if stripped:
            patterns = [create_pattern(re.escape(stripped))]
    elif search_text.strip():
        patterns = [re.escape(search_text.strip())]

    ranges: list[tuple[int, int]] = []
    for pattern in patterns:
        try:
            ranges.extend((m.start(), m.end()) for m in re.finditer(pattern, text, flags))
        except re.error:
            continue

    ranges.sort(key=lambda item: (item[0], -(item[1] - item[0])))
    merged: list[tuple[int, int]] = []
    for start, end in ranges:
        if not merged or start >= merged[-1][1]:
            merged.append((start, end))
        elif end > merged[-1][1]:
            merged[-1] = (merged[-1][0], end)
    return merged


class SearchResultsWindow(QWidget):
    """Separate top-level window listing clickable search results."""

    resultActivated = Signal(int)

    def __init__(self, parent=None, settings_service=None) -> None:
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Search Results")
        self._results: list[SearchResult] = []
        self._settings_service = settings_service

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        self.filter_edit = QLineEdit(self)
        self.filter_edit.setPlaceholderText("Filter results...")
        self.filter_edit.textChanged.connect(self._apply_filter)
        layout.addWidget(self.filter_edit)

        self.list_widget = QListWidget(self)
        self.list_widget.setWordWrap(True)
        self.list_widget.itemClicked.connect(self._activate_item)
        self.list_widget.itemActivated.connect(self._activate_item)
        layout.addWidget(self.list_widget)

    def set_results(self, results: list[SearchResult], search_text: str) -> None:
        """Replace the displayed results."""
        self._results = results
        count = len(results)
        noun = "verse" if count == 1 else "verses"
        title = f"Search Results: {count} {noun}"
        if search_text:
            title = f'{title} for "{search_text}"'
        self.setWindowTitle(title)
        self._apply_filter()

    def clear_results(self) -> None:
        """Clear the displayed results."""
        self._results = []
        self.setWindowTitle("Search Results")
        self.list_widget.clear()

    def _apply_filter(self) -> None:
        filter_text = self.filter_edit.text().casefold()
        self.list_widget.clear()
        for result in self._results:
            searchable = f"{result.reference} {result.text}".casefold()
            if filter_text and filter_text not in searchable:
                continue
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, result.position)
            item.setToolTip(f"{result.reference}\n{result.text}")

            label = QLabel(self.list_widget)
            label.setTextFormat(Qt.TextFormat.RichText)
            label.setWordWrap(True)
            label.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            label.setText(f"<b>{html.escape(result.reference)}</b>&nbsp;&nbsp;{result.html_text}")
            item.setSizeHint(label.sizeHint())
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, label)

    def _activate_item(self, item: QListWidgetItem) -> None:
        position = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(position, int):
            self.resultActivated.emit(position)

    def save_width(self) -> None:
        """Persist the current panel width to settings."""
        if self._settings_service is None:
            return
        try:
            self._settings_service.update_search_results_width(self.width())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            pass

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.isVisible():
            self.save_width()