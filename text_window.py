# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Set

from PySide6.QtCore import Qt, QEvent, QTimer, QPoint
from PySide6.QtGui import QColor, QFont, QTextCursor, QTextCharFormat, QPalette
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QPlainTextEdit, QWidget, QTextEdit

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
        x8, y8, width8, height8 = fcs.get_window_geometry("reader_window")
        self.setGeometry(x8, y8, width8, height8)

        # Load Bible data
        self.bible_data = fcs.load_json_dict("bible_data.json")

        # Layout + editor
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        self.text_edit = QPlainTextEdit()
        self.text_edit.setFont(QFont("Cascadia Mono", 12))
        self.text_edit.setReadOnly(True)
        # Ensure readable colours regardless of global theme settings
        is_dark = self.settings.get("theme", "Light") == "Dark"
        if is_dark:
            self.text_edit.setStyleSheet("QPlainTextEdit { background-color: #121212; color: #ffffff; }")
            pal = self.text_edit.palette()
            pal.setColor(QPalette.ColorRole.Base, QColor("#121212"))
            pal.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
            pal.setColor(QPalette.ColorRole.Highlight, QColor("#2a5adf"))
            pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            self.text_edit.setPalette(pal)
        else:
            self.text_edit.setStyleSheet("QPlainTextEdit { background-color: #ffffff; color: #000000; }")
            pal = self.text_edit.palette()
            pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
            pal.setColor(QPalette.ColorRole.Text, QColor("#000000"))
            pal.setColor(QPalette.ColorRole.Highlight, QColor("#cce8ff"))
            pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
            self.text_edit.setPalette(pal)
        self.layout.addWidget(self.text_edit)

        # Save scroll position per file
        self._is_loading: bool = False
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
        # Cancellation token for async scroll restore to avoid stale apply when switching files
        self._restore_token: int = 0
        # Extra selections for QPlainTextEdit highlighting
        self._extra_selections: List[Any] = []
        # Trigger quick visible-range highlight on scroll
        self.text_edit.verticalScrollBar().valueChanged.connect(
            lambda _v: (lambda t=self._cancel_token: QTimer.singleShot(
                0, lambda: self._highlight_visible_now() if t == self._cancel_token else None
            ))()
        )

        if initial_file_path:
            self.load_text_file(initial_file_path)

        self.canonical_books = scripture.CANONICAL_BOOKS

    def apply_theme(self, is_dark: bool) -> None:
        """Apply a light/dark theme explicitly to the plain-text editor.
        Safe to call at any time; keeps text readable regardless of OS palette.
        Also ensures the document text colour updates immediately without needing reload.
        Scroll position is preserved and not saved while theming is applied.
        """
        # Preserve scroll and suppress saving while applying theme formatting
        sb = self.text_edit.verticalScrollBar()
        try:
            saved_scroll = int(sb.value())
            saved_max = int(sb.maximum())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            saved_scroll, saved_max = 0, 0
        prev_loading = getattr(self, "_is_loading", False)
        self._is_loading = True

        if is_dark:
            self.text_edit.setStyleSheet("QPlainTextEdit { background-color: #121212; color: #ffffff; }")
            pal = self.text_edit.palette()
            pal.setColor(QPalette.ColorRole.Base, QColor("#121212"))
            pal.setColor(QPalette.ColorRole.Text, QColor("#ffffff"))
            pal.setColor(QPalette.ColorRole.Highlight, QColor("#2a5adf"))
            pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#ffffff"))
            self.text_edit.setPalette(pal)
        else:
            self.text_edit.setStyleSheet("QPlainTextEdit { background-color: #ffffff; color: #000000; }")
            pal = self.text_edit.palette()
            pal.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
            pal.setColor(QPalette.ColorRole.Text, QColor("#000000"))
            pal.setColor(QPalette.ColorRole.Highlight, QColor("#cce8ff"))
            pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
            self.text_edit.setPalette(pal)

        # Ensure the document text colour follows the theme immediately.
        # Previously, the load routine applied an explicit foreground colour to the whole document,
        # which prevented palette/stylesheet changes from taking effect until reload.
        try:
            cursor = self.text_edit.textCursor()
            # Preserve caret/selection
            orig_pos = int(cursor.position())
            orig_anchor = int(cursor.anchor())

            cursor.beginEditBlock()
            cursor.select(QTextCursor.SelectionType.Document)
            # Explicitly set the whole document's foreground to match the theme
            fmt = QTextCharFormat()
            fmt.setForeground(QColor("#ffffff" if is_dark else "#000000"))
            cursor.setCharFormat(fmt)
            cursor.endEditBlock()
            # Force immediate repaint to ensure a colour change is visible without delay
            try:
                self.text_edit.viewport().update()
            except (AttributeError, RuntimeError):
                pass

            # Restore caret/selection
            c2 = self.text_edit.textCursor()
            c2.setPosition(orig_anchor)
            if orig_anchor != orig_pos:
                c2.setPosition(orig_pos, QTextCursor.MoveMode.KeepAnchor)
            else:
                c2.setPosition(orig_pos, QTextCursor.MoveMode.MoveAnchor)
            self.text_edit.setTextCursor(c2)

            # Reapply highlight formats for scripture references to keep them visible
            fmt_hl = TextDocumentWindow._make_highlight_format()
            for sel in getattr(self, "_extra_selections", []):
                try:
                    c = self.text_edit.textCursor()
                    start = sel.cursor.selectionStart()
                    end = sel.cursor.selectionEnd()
                    c.setPosition(start)
                    c.setPosition(end, QTextCursor.MoveMode.KeepAnchor)
                    c.setCharFormat(fmt_hl)
                except (AttributeError, RuntimeError):
                    # Ignore cases where underlying Qt objects are already deleted or missing attributes
                    pass
            # Re-apply the ExtraSelections overlay too
            self.text_edit.setExtraSelections(getattr(self, "_extra_selections", []))
        except (RuntimeError, AttributeError):
            # Be tolerant: theme changes should not crash the app and ignore deleted Qt objects or missing attributes
            pass
        finally:
            # Restore the previous scroll position without triggering a save
            try:
                max_now = int(sb.maximum())
            except (AttributeError, RuntimeError, TypeError, ValueError):
                max_now = saved_max
            try:
                target = 0 if max_now == 0 else max(0, min(saved_scroll, max_now))
                sb.setValue(target)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass
            # Release the guard but keep the previous state intact
            self._is_loading = prev_loading

    def _save_scroll_for(self, stem: Any, value: Any) -> None:
        """Persist the scroll position for a given file _stem, safely.
        Creates the per-file map if needed and writes to settings.json.
        """
        try:
            if not stem:
                return
            # Ensure the dictionary for per-file positions exists and is a dict
            if not isinstance(self.settings.get("last_read_positions"), dict):
                self.settings["last_read_positions"] = {}
            self.settings["last_read_positions"][stem] = int(value)
            # Persist the settings to disk
            if self.settings_path:
                fcs.save_settings_to_file(self.settings, self.settings_path)
            else:
                fcs.save_settings_to_file(self.settings)
        except (ValueError, TypeError, OSError):
            # Be tolerant: failing to save the scroll should never crash the app
            pass

    def _get_saved_position(self, stem: str) -> int:
        """Return the saved scroll position for the given _stem using the exact key match only.
        No case-insensitive matching, no corrections, and no key changes/migrations.
        Defaults to 0 if the key is not present or settings are malformed.
        """
        try:
            positions = self.settings.get("last_read_positions")
            if not isinstance(positions, dict):
                return 0
            if stem in positions:
                return int(positions.get(stem, 0))
        except (ValueError, TypeError, AttributeError):
            pass
        return 0

    def _restore_scroll_position_async(self, _stem: str, desired: int, timeout_ms: int = 6000, interval_ms: int = 50) -> None:
        """Restore the scroll position after the document is laid out.
        Waits until the scrollbar exposes a non-zero range before applying the saved value.
        Keeps _is_loading True until applied to suppress saves.
        Uses a cancellation token so that stale timers from a previous file cannot override the
        current document's scroll position.
        """
        try:
            desired = int(desired) if desired is not None else 0
        except (ValueError, TypeError):
            desired = 0

        # New restore cycle: increment token and capture it locally
        self._restore_token += 1
        token = self._restore_token

        # Use a countdown of attempts to avoid infinite retries
        attempts = max(int(timeout_ms // max(1, interval_ms)), 1)
        scrollbar = self.text_edit.verticalScrollBar()

        def try_apply():
            nonlocal attempts
            # Abort if a newer restore has started
            if token != getattr(self, "_restore_token", token):
                return
            try:
                # If the editor is gone, stop (and only clear the flag if still current)
                if self.text_edit is None or scrollbar is None:
                    if token == getattr(self, "_restore_token", token):
                        self._is_loading = False
                    return
            except (AttributeError, RuntimeError):
                if token == getattr(self, "_restore_token", token):
                    self._is_loading = False
                return

            attempts -= 1
            try:
                maximum = int(scrollbar.maximum())
            except (AttributeError, RuntimeError, TypeError, ValueError):
                maximum = 0

            # Consider layout ready only when the scrollbar has a non-zero range
            ready = (maximum > 0)

            if ready:
                try:
                    target = 0 if maximum == 0 else max(0, min(desired, maximum))
                    scrollbar.setValue(target)
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    pass
                finally:
                    # Done with programmatic changes
                    if token == getattr(self, "_restore_token", token):
                        self._is_loading = False
                return

            if attempts <= 0:
                # Give up gracefully; ensure the flag is cleared for the current token only
                if token == getattr(self, "_restore_token", token):
                    self._is_loading = False
                return

            # Retry shortly
            QTimer.singleShot(interval_ms, try_apply)

        # Kick off the first attempt soon to allow initial layout
        QTimer.singleShot(interval_ms, try_apply)

    def save_scroll_position(self, value: Any) -> None:
        """Slot for scrollbar valueChanged: save only during user-driven scrolls.
        Suppressed while a document is programmatically loading/restoring.
        """
        if getattr(self, "_is_loading", False):
            return
        stem = self.current_file_stem
        self._save_scroll_for(stem, value)

    def closeEvent(self, event):
        geometry = self.geometry()
        fcs.save_window_geometry("reader_window",
                                 geometry.x(), geometry.y(),
                                 geometry.width(), geometry.height())
        event.accept()

    def load_text_file(self, file_path1):
        try:
            if not file_path1:
                return
            # Before switching to a new text, record the current text's scroll position
            try:
                prev_stem = getattr(self, "current_file_stem", None)
                if prev_stem:
                    sb_prev = self.text_edit.verticalScrollBar()
                    try:
                        prev_value = int(sb_prev.value())
                        prev_max = int(sb_prev.maximum())
                    except (AttributeError, RuntimeError, TypeError, ValueError):
                        prev_value, prev_max = 0, 0
                    if prev_max > 0:
                        # Avoid overwriting a good non-zero with an early zero
                        existing = self._get_saved_position(prev_stem)
                        if (prev_value != 0) or (existing == 0):
                            self._save_scroll_for(prev_stem, prev_value)
            except (ValueError, TypeError, OSError, AttributeError, RuntimeError):
                # Non-fatal: failure to save the previous scroll should not block loading
                pass

            p = Path(file_path1)
            stem = p.stem

            # Set the loading guard to suppress save events during programmatic changes
            self._is_loading = True
            self.current_file_stem = stem

            # Determine the last position from the per-file map; default to 0 if missing
            last_position = self._get_saved_position(stem)

            with open(file_path1, 'r', encoding='utf-8') as file1:
                content = file1.read()
                self.text_edit.setPlainText(content)
                self.setWindowTitle(stem)
                self._start_lazy_highlighting(content)
                # Restore the saved scroll position once the document layout is ready.
                # _restore_scroll_position_async will clear _is_loading when done.
                self._restore_scroll_position_async(stem, last_position)

                if hasattr(self, 'file_selector'):
                    idx = self.file_selector.findText(stem)
                    if 0 <= idx != self.file_selector.currentIndex():
                        self.file_selector.blockSignals(True)
                        self.file_selector.setCurrentIndex(idx)
                        self.file_selector.blockSignals(False)
        except FileNotFoundError:
            self.text_edit.setPlainText("Error: File not found.")
        except (OSError, UnicodeDecodeError, ValueError) as e1:
            self.text_edit.setPlainText(f"Error loading file: {e1}")

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


        self._highlight_timer.stop()
        QTimer.singleShot(0, lambda t=token: self._highlight_visible_now() if t == self._cancel_token else None)
        self._highlight_timer.start()
        # Apply any collected selections now
        self.text_edit.setExtraSelections(getattr(self, '_extra_selections', []))

    def _apply_highlights_for_refs(self, base: int, refs: List[Dict[str, Any]]) -> None:
        """Collect highlighting ranges for a set of references on a line.
        Deduplicates by (start, length) using self._ref_index.
        Applies both ExtraSelections and direct char formatting for robustness.
        """
        selections: List[Any] = []
        for r in refs:
            start = base + r['start']
            length = r['length']
            key = (start, length)
            if key in self._ref_index:
                continue
            self._ref_index.add(key)
            selections.append({'cursor_start': start, 'length': length})
        # Apply selections
        existing = getattr(self, '_extra_selections', [])
        # Prepare a reusable format for direct application
        fmt = TextDocumentWindow._make_highlight_format()
        for extra in selections:
            c = self.text_edit.textCursor()
            c.setPosition(extra['cursor_start'])
            c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, extra['length'])
            # 1) Add an ExtraSelection (helps on some platforms)
            es = self._make_extra_selection(c)
            existing.append(es)
            # 2) Also directly apply the char format to ensure visibility everywhere
            c.setCharFormat(fmt)
        self._extra_selections = existing

    @staticmethod
    def _make_highlight_format() -> QTextCharFormat:
        """Create the standard format used to highlight scripture references."""
        fmt = QTextCharFormat()
        # Explicit, high-contrast formatting for visibility across themes
        blue = QColor(33, 96, 255)  # slightly lighter blue for contrast
        fmt.setForeground(blue)
        # Set both underline style and flag for maximum compatibility
        try:
            fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SingleUnderline)
        except AttributeError:
            pass
        fmt.setFontUnderline(True)
        try:
            fmt.setUnderlineColor(blue)
        except AttributeError:
            # Older Qt bindings may not support underline colour; ignore
            pass
        return fmt

    @staticmethod
    def _make_extra_selection(cursor: QTextCursor):
        sel = QTextEdit.ExtraSelection()
        sel.cursor = cursor
        fmt = TextDocumentWindow._make_highlight_format()
        sel.format = fmt
        return sel

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

        # Do not reset _extra_selections here; accumulate batches so visible highlights are preserved
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
            self._apply_highlights_for_refs(base, refs)
        self._next_line_index = end_index
        # Apply the current batch of selections
        self.text_edit.setExtraSelections(self._extra_selections)
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

        # Reset and rebuild only visible selections
        self._extra_selections = []

        for i in range(i1, min(i2 + 1, len(self._lines))):
            line = self._lines[i]
            if not line:
                continue
            base = self._line_offsets[i]
            refs = self.find_scripture_references(line)
            self._apply_highlights_for_refs(base, refs)
        # Apply updated selections for the visible range
        self.text_edit.setExtraSelections(self._extra_selections)

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
