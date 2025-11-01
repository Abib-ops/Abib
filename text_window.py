# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set

from PySide6.QtCore import Qt, QEvent, QTimer, QPoint
from PySide6.QtGui import QColor, QFont, QTextCursor, QTextCharFormat
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QTextEdit, QWidget

import fcs
import scripture
import shared as sh


class TextDocumentWindow(QDialog):
    def __init__(self, initial_file_path: str | None = None,
                 settings: Dict[str, Any] | None = None,
                 settings_path: str | None = None) -> None:
        super().__init__()

        # Externalised settings (instead of relying on globals)
        self.settings: Dict[str, Any] = settings if isinstance(settings, dict) else {}
        self.settings_path: str | None = settings_path

        self.current_reference = None
        self.current_file_stem = None
        self.setWindowTitle("Text Reader")

        # Load window geometry from settings
        x8, y8, width8, height8 = fcs.get_window_geometry("pilgrims_progress_window")
        self.setGeometry(x8, y8, width8, height8)

        # Load Bible data
        self.bible_data = fcs.load_json_dict("bible_data.json")

        # Layout + editor
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Cascadia Mono", 12))
        self.text_edit.setReadOnly(True)
        self.layout.addWidget(self.text_edit)

        # Save scroll position per file
        self.text_edit.verticalScrollBar().valueChanged.connect(self.save_scroll_position)

        # Hover tracking
        self.text_edit.viewport().setMouseTracking(True)
        self.text_edit.viewport().installEventFilter(self)
        self.text_edit.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self.popup_window = None

        # Lazy highlighting state
        self._all_references: List[Dict[str, Any]] = []
        self._ref_index: Set[tuple] = set()
        self._lines: List[str] = []
        self._line_offsets: List[int] = []
        self._next_line_index: int = 0
        self._highlight_timer: QTimer = QTimer(self)
        self._highlight_timer.setInterval(25)
        self._highlight_timer.timeout.connect(self._process_highlight_batch)
        self._cancel_token: int = 0
        # Trigger quick visible-range highlight on scroll
        self.text_edit.verticalScrollBar().valueChanged.connect(
            lambda _v: (lambda t=self._cancel_token: QTimer.singleShot(
                0, lambda: self._highlight_visible_now() if t == self._cancel_token else None
            ))()
        )

        if initial_file_path:
            self.load_text_file(initial_file_path)

        self.canonical_books = scripture.CANONICAL_BOOKS

    def save_scroll_position(self, value: Any) -> None:
        stem = self.current_file_stem
        # Ensure the dictionary for per-file positions exists
        if "last_read_positions" not in self.settings:
            self.settings["last_read_positions"] = {}
        if stem:
            self.settings["last_read_positions"][stem] = int(value)
        else:
            # Fallback: keep previous single-position behaviour
            self.settings["last_read_position"] = int(value)
        # Persist the settings to disk
        if self.settings_path:
            fcs.save_settings_to_file(self.settings, self.settings_path)
        else:
            fcs.save_settings_to_file(self.settings)

    def closeEvent(self, event):
        geometry = self.geometry()
        fcs.save_window_geometry("pilgrims_progress_window",
                                 geometry.x(), geometry.y(),
                                 geometry.width(), geometry.height())
        event.accept()

    def load_text_file(self, file_path1):
        try:
            if not file_path1:
                return
            p = Path(file_path1)
            stem = p.stem
            self.current_file_stem = stem

            # Determine the last position: prefer a per-file map, fallback to legacy single value
            positions = self.settings.get("last_read_positions", {}) or {}
            last_position = int(positions.get(stem, self.settings.get("last_read_position", 0)))

            with open(file_path1, 'r', encoding='utf-8') as file1:
                content = file1.read()
                self.text_edit.setText(content)
                self.setWindowTitle(stem)
                self._start_lazy_highlighting(content)
                QTimer.singleShot(100, lambda: self.text_edit.verticalScrollBar().setValue(last_position))

                if hasattr(self, 'file_selector'):
                    idx = self.file_selector.findText(stem)
                    if 0 <= idx != self.file_selector.currentIndex():
                        self.file_selector.blockSignals(True)
                        self.file_selector.setCurrentIndex(idx)
                        self.file_selector.blockSignals(False)
        except FileNotFoundError:
            self.text_edit.setText("Error: File not found.")
        except (OSError, UnicodeDecodeError, ValueError) as e1:
            self.text_edit.setText(f"Error loading file: {e1}")

    def highlight_references(self):
        text = self.text_edit.toPlainText()
        self._start_lazy_highlighting(text)

    def _start_lazy_highlighting(self, content: str) -> None:
        self._cancel_token += 1
        token = self._cancel_token

        self._all_references.clear()
        self._ref_index.clear()
        self._lines = content.split('\n')
        self._line_offsets = []
        running = 0
        for ln in self._lines:
            self._line_offsets.append(running)
            running += len(ln) + 1
        self._next_line_index = 0

        cursor = self.text_edit.textCursor()
        cursor.select(QTextCursor.SelectionType.Document)
        cursor.setCharFormat(QTextCharFormat())

        self._highlight_timer.stop()
        QTimer.singleShot(0, lambda t=token: self._highlight_visible_now() if t == self._cancel_token else None)
        self._highlight_timer.start()

    def _apply_highlights_for_refs(self, base: int, refs: List[Dict[str, Any]], cursor: QTextCursor, fmt: QTextCharFormat) -> None:
        """Apply highlighting for a set of references on a line.
        Deduplicates by (start, length) using self._ref_index.
        """
        for r in refs:
            start = base + r['start']
            length = r['length']
            key = (start, length)
            if key in self._ref_index:
                continue
            self._ref_index.add(key)
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, length)
            cursor.setCharFormat(fmt)

    def _move_popup_to_cursor(self, event, y_offset: int = 60) -> None:
        """Position the tooltip popup relative to the mouse cursor within the text edit.
        Extracted from duplicated blocks to avoid code repetition.
        """
        # Compute target position based on cursor rect and editor origin
        cursor = self.text_edit.cursorForPosition(event.position().toPoint())
        cursor_rect = self.text_edit.cursorRect(cursor)
        global_cursor_top_left = self.text_edit.mapToGlobal(cursor_rect.topLeft())
        text_edit_top_left = self.text_edit.mapToGlobal(self.text_edit.rect().topLeft())
        popup_x = text_edit_top_left.x()
        popup_y = global_cursor_top_left.y() + y_offset
        if self.popup_window is not None:
            self.popup_window.move(popup_x, popup_y)

    def _process_highlight_batch(self) -> None:
        if not self._lines:
            self._highlight_timer.stop()
            return
        token = self._cancel_token
        batch_size = 200
        end_index = min(self._next_line_index + batch_size, len(self._lines))
        if self._next_line_index >= end_index:
            self._highlight_timer.stop()
            return

        fmt = QTextCharFormat()
        fmt.setForeground(QColor("blue"))
        fmt.setFontUnderline(True)

        cursor = self.text_edit.textCursor()
        for i in range(self._next_line_index, end_index):
            if token != self._cancel_token:
                return
            line = self._lines[i]
            if not line:
                continue
            base = self._line_offsets[i]
            refs = self.find_scripture_references(line)
            if not refs:
                continue
            self._apply_highlights_for_refs(base, refs, cursor, fmt)
        self._next_line_index = end_index
        if self._next_line_index >= len(self._lines):
            self._highlight_timer.stop()

    def _highlight_visible_now(self) -> None:
        if not self._lines:
            text = self.text_edit.toPlainText()
            if not text:
                return
            if len(text) < 20000:
                self._start_lazy_highlighting(text)
            return

        viewport = self.text_edit.viewport()
        top_pt = QPoint(0, 0)
        bottom_pt = QPoint(viewport.width() - 1, viewport.height() - 1)
        top_cursor = self.text_edit.cursorForPosition(top_pt)
        bot_cursor = self.text_edit.cursorForPosition(bottom_pt)
        top_pos = top_cursor.position()
        bot_pos = bot_cursor.position()

        def pos_to_line(pos: int) -> int:
            lo, hi = 0, len(self._line_offsets) - 1
            ans = 0
            while lo <= hi:
                mid = (lo + hi) // 2
                if self._line_offsets[mid] <= pos:
                    ans = mid
                    lo = mid + 1
                else:
                    hi = mid - 1
            return ans

        i1 = pos_to_line(max(0, top_pos - 200))
        i2 = pos_to_line(min(bot_pos + 200, self._line_offsets[-1] + len(self._lines[-1])))

        fmt = QTextCharFormat()
        fmt.setForeground(QColor("blue"))
        fmt.setFontUnderline(True)
        cursor = self.text_edit.textCursor()

        for i in range(i1, min(i2 + 1, len(self._lines))):
            line = self._lines[i]
            if not line:
                continue
            base = self._line_offsets[i]
            refs = self.find_scripture_references(line)
            self._apply_highlights_for_refs(base, refs, cursor, fmt)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Leave:
            self.closePopup()
        elif event.type() == QEvent.Type.MouseMove:
            cursor = self.text_edit.cursorForPosition(event.position().toPoint())
            position = cursor.position()
            text = self.text_edit.toPlainText()
            references = self.find_scripture_references(text)
            over_reference = any(ref['start'] <= position <= ref['start'] + ref['length'] for ref in references)
            if not over_reference:
                self.closePopup()
            else:
                self.handle_hover(event)
        return super().eventFilter(obj, event)

    def handle_hover(self, event):
        cursor = self.text_edit.cursorForPosition(event.position().toPoint())
        position = cursor.position()
        text = self.text_edit.toPlainText()
        references = self.find_scripture_references(text)

        hovered_reference = None
        for ref in references:
            if ref["start"] <= position <= ref["start"] + ref["length"]:
                hovered_reference = ref
                break

        if hovered_reference is None:
            if self.popup_window is not None:
                self.popup_window.close()
                self.popup_window = None
            self.current_reference = None
            return

        same_reference = (
            self.current_reference is not None and
            self.current_reference["start"] == hovered_reference["start"] and
            self.current_reference["length"] == hovered_reference["length"]
        )

        if same_reference:
            if self.popup_window is None or not self.popup_window.isVisible():
                pass
            else:
                self._move_popup_to_cursor(event, y_offset=60)
                return
        else:
            if self.popup_window is not None:
                self.popup_window.close()
                self.popup_window = None
            self.current_reference = hovered_reference

        self.popup_window = QWidget()
        self.popup_window.setWindowFlags(Qt.WindowType.ToolTip)
        self.popup_window.setStyleSheet("border: 2px solid blue;")

        scriptures, canonical = self.get_scripture(hovered_reference)
        scriptur = scriptures + "\n" + canonical + " KJV"

        label = QLabel(scriptur, self.popup_window)
        label.setFont(self.text_edit.font())
        label.setWordWrap(True)
        label.setFixedWidth(self.text_edit.width())
        label.adjustSize()

        layout = QVBoxLayout(self.popup_window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        self.popup_window.adjustSize()

        self._move_popup_to_cursor(event, y_offset=60)

        self.popup_window.show()

    def closePopup(self):
        if self.popup_window and self.popup_window.isVisible():
            self.popup_window.close()
            self.popup_window = None

    @staticmethod
    def find_scripture_references(text):
        return scripture.find_scripture_references(text)

    def get_scripture(self, reference):
        book = reference['book']
        chapter = reference['chapter']
        verse = reference['verse']
        scripture_text = self.lookup_scripture(book, chapter, verse)

        normalized_book = self.normalize_book_input(book)
        book_id = sh.bibledict.get(normalized_book)
        if not book_id:
            return "Scripture not found.", ""

        full_book = self.canonical_books.get(book_id, book)
        if book_id - 1 in sh.onechapterbooks:
            full_reference = f"{full_book} {verse}"
        else:
            full_reference = f"{full_book} {chapter}:{verse}"
        return scripture_text, full_reference

    @staticmethod
    def normalize_book_input(book_input: str) -> str:
        return scripture.normalize_book_input(book_input)

    def lookup_scripture(self, book, chapter, verses):
        return scripture.lookup_scripture(self.bible_data, book, chapter, verses)
