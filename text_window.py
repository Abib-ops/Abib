# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List, Set

from PySide6.QtCore import Qt, QEvent, QTimer, QPoint, Signal
from PySide6.QtGui import QColor, QFont, QTextCursor, QTextCharFormat, QPalette
from PySide6.QtWidgets import QDialog, QLabel, QVBoxLayout, QPlainTextEdit, QWidget, QTextEdit

import fcs
import scripture
import shared as sh


class TextDocumentWindow(QDialog):
    # Emitted when the user clicks a highlighted scripture reference.
    # Payload is a canonical reference string like "John 3:16" or "Jude 5".
    referenceActivated = Signal(str)
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

        # Load initial window geometry from legacy/global reader_window.
        # Per-file geometry (stored in last_read_positions) will be applied
        # when a file is actually loaded.
        x8, y8, width8, height8 = fcs.get_window_geometry("reader_window")
        self.setGeometry(x8, y8, width8, height8)

        # Load Bible data
        self.bible_data = fcs.load_json_dict("bible_data.json")

        # Layout + editor
        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # One-click: Reset scroll for this text
        try:
            from PySide6.QtWidgets import QPushButton
            self.reset_scroll_btn = QPushButton("Reset scroll for this text")
            self.reset_scroll_btn.setToolTip("Set the saved position for this text to the top (0) and scroll there")
            self.reset_scroll_btn.clicked.connect(self.reset_scroll_for_current_text)
            self.layout.addWidget(self.reset_scroll_btn)
        except (ImportError, AttributeError, RuntimeError, TypeError):
            # If QPushButton is unavailable for any reason, skip the button gracefully
            self.reset_scroll_btn = None

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
        # Whether we are in whole-document parse mode (Option A)
        self._whole_document_mode: bool = False
        # Cancellation token for async scroll restore to avoid stale apply when switching files
        self._restore_token: int = 0
        # Extra selections for QPlainTextEdit highlighting
        self._extra_selections: List[Any] = []
        # Track whether the reference list is sorted by abs_start
        self._refs_sorted: bool = True
        # Trigger quick visible-range highlight on scroll
        self.text_edit.verticalScrollBar().valueChanged.connect(
            lambda _v: (lambda t=self._cancel_token: QTimer.singleShot(
                0, lambda: self._highlight_visible_now() if t == self._cancel_token else None
            ))()
        )

        # Debounced hover handling to avoid heavy work on every mouse move
        self._hover_timer: QTimer = QTimer(self)
        try:
            self._hover_timer.setSingleShot(True)
        except (AttributeError, RuntimeError):
            pass
        self._hover_timer.setInterval(35)
        # Store only a QPoint (copy) from the mouse event to avoid using a deleted QMouseEvent later
        self._pending_hover_pos: QPoint | None = None
        self._hover_timer.timeout.connect(self._do_hover)

        if initial_file_path:
            self.load_text_file(initial_file_path)

        self.canonical_books = scripture.CANONICAL_BOOKS

    # -------- Settings helpers for per-file scroll + geometry --------
    def _ensure_positions_dict(self) -> None:
        try:
            if not isinstance(self.settings.get("last_read_positions"), dict):
                self.settings["last_read_positions"] = {}
        except (AttributeError, TypeError):
            # Ensure the dictionary exists even if settings are malformed
            self.settings["last_read_positions"] = {}

    @staticmethod
    def _safe_geometry_tuple(x: int | None, y: int | None, w: int | None, h: int | None) -> tuple[int, int, int, int] | None:
        try:
            if None in (x, y, w, h):
                return None
            sx, sy = fcs.get_screen_size()
            gx = int(x)
            gy = int(y)
            gw = int(w)
            gh = int(h)
            # Basic sanity clamps similar to fcs.get_window_geometry
            if gx < 0:
                gx = 100
            if gy < 0:
                gy = 100
            if gx + gw > sx:
                gx = max(0, sx - max(640, gw))
                gw = min(gw, sx)
            if gy + gh > sy:
                gy = max(0, sy - max(400, gh))
                gh = min(gh, sy)
            return gx, gy, gw, gh
        except (ValueError, TypeError, AttributeError):
            return None

    def _read_entry_components(self, stem: str) -> tuple[int, tuple[int, int, int, int] | None]:
        """Read per-file entry as (scroll, geometry or None).
        Accepts legacy int (scroll only) or list [scroll, x, y, w, h].
        """
        try:
            positions = self.settings.get("last_read_positions")
            if not isinstance(positions, dict):
                return 0, None
            if stem not in positions:
                return 0, None
            entry = positions.get(stem)
            # Legacy: a single int means scroll only
            if isinstance(entry, int):
                return int(entry), None
            # New format: list/tuple with at least 5 numbers
            if isinstance(entry, (list, tuple)) and len(entry) >= 5:
                scroll = int(entry[0])
                geom = self._safe_geometry_tuple(int(entry[1]), int(entry[2]), int(entry[3]), int(entry[4]))
                return scroll, geom
            # Some partially migrated forms: try to coerce the first value as scroll
            if isinstance(entry, (list, tuple)) and len(entry) >= 1:
                scroll = int(entry[0])
                geom = None
                if len(entry) >= 5:
                    geom = self._safe_geometry_tuple(entry[1], entry[2], entry[3], entry[4])
                return scroll, geom
        except (ValueError, TypeError, AttributeError):
            pass
        return 0, None

    def _write_entry(self, stem: str, scroll: int | None = None, geometry: tuple[int, int, int, int] | None = None) -> None:
        """Persist the per-file entry ensuring format [scroll, x, y, w, h].
        Existing values are preserved if a component is not provided.
        """
        if not stem:
            return
        try:
            self._ensure_positions_dict()
            cur_scroll, cur_geom = self._read_entry_components(stem)
            new_scroll = cur_scroll if scroll is None else int(scroll)
            new_geom = cur_geom if geometry is None else self._safe_geometry_tuple(*geometry)

            # If geometry is still None, fall back to current window geometry
            if new_geom is None:
                g = self.geometry()
                new_geom = (int(g.x()), int(g.y()), int(g.width()), int(g.height()))

            self.settings["last_read_positions"][stem] = [int(new_scroll), int(new_geom[0]), int(new_geom[1]), int(new_geom[2]), int(new_geom[3])]

            # Persist
            if self.settings_path:
                fcs.save_settings_to_file(self.settings, self.settings_path)
            else:
                fcs.save_settings_to_file(self.settings)
        except (ValueError, TypeError, AttributeError, OSError):
            # Non-fatal
            pass

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

            # Rebuild highlights for the visible region so references remain highlighted
            # Some theme operations (palette/stylesheet/char format) can clear visual overlays.
            # Using our existing fast visible-range highlighter guarantees fresh selections
            # and re-applies underline/colour formatting without rescanning the whole file.
            try:
                self._highlight_visible_now()
            except (RuntimeError, AttributeError, TypeError, ValueError):
                # Be resilient: highlighting should never block theming
                pass
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
            # Update only the scroll component; preserve geometry
            self._write_entry(stem, scroll=int(value), geometry=None)
        except (ValueError, TypeError, OSError):
            # Be tolerant: failing to save the scroll should never crash the app
            pass

    def _get_saved_position(self, stem: str) -> int:
        """Return the saved scroll position for the given _stem using the exact key match only.
        No case-insensitive matching, no corrections, and no key changes/migrations.
        Defaults to 0 if the key is not present or settings are malformed.
        """
        try:
            scroll, _geom = self._read_entry_components(stem)
            return int(scroll)
        except (ValueError, TypeError, AttributeError):
            return 0

    def _apply_saved_geometry(self, stem: str) -> None:
        """Apply saved per-file geometry if present; otherwise use the legacy
        reader_window geometry as a fallback.
        """
        try:
            _scroll, geom = self._read_entry_components(stem)
            if geom is None:
                x8, y8, width8, height8 = fcs.get_window_geometry("reader_window")
                self.setGeometry(x8, y8, width8, height8)
            else:
                x, y, w, h = geom
                self.setGeometry(x, y, w, h)
        except (ValueError, TypeError, AttributeError, OSError):
            # Fallback to legacy geometry on any error
            x8, y8, width8, height8 = fcs.get_window_geometry("reader_window")
            self.setGeometry(x8, y8, width8, height8)

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

    def reset_scroll_for_current_text(self) -> None:
        """One-click action: reset the saved scroll for the current text to 0 and scroll to the top.
        Preserves exact key behaviour; does not rename or migrate any settings keys.
        """
        stem = getattr(self, "current_file_stem", None)
        if not stem:
            return
        try:
            # Set scroll to 0, preserve geometry
            self._write_entry(stem, scroll=0, geometry=None)
        except (ValueError, TypeError, OSError):
            # Non-fatal: if persisting fails, still attempt to scroll to the top
            pass
        # Programmatically scroll to the top without triggering a save write-back race
        try:
            self._is_loading = True
            sb = self.text_edit.verticalScrollBar()
            try:
                max_now = int(sb.maximum())
            except (AttributeError, RuntimeError, TypeError, ValueError):
                max_now = 0
            if max_now > 0:
                try:
                    sb.setValue(0)
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    pass
                finally:
                    self._is_loading = False
            else:
                # Use the async restorer to apply 0 once the layout is ready
                self._restore_scroll_position_async(stem, 0)
        except (AttributeError, RuntimeError):
            self._is_loading = False

    def closeEvent(self, event):
        # Save per-file geometry so each text remembers its own window placement
        try:
            stem = getattr(self, "current_file_stem", None)
            if stem:
                g = self.geometry()
                self._write_entry(stem, geometry=(int(g.x()), int(g.y()), int(g.width()), int(g.height())))
        except (ValueError, TypeError, AttributeError, RuntimeError, OSError):
            pass
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
                    # Always capture the current geometry for the previous stem
                    try:
                        gprev = self.geometry()
                        self._write_entry(prev_stem, geometry=(int(gprev.x()), int(gprev.y()), int(gprev.width()), int(gprev.height())))
                    except (ValueError, TypeError, AttributeError, RuntimeError, OSError):
                        pass
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
                # Apply any saved per-file geometry for this stem
                self._apply_saved_geometry(stem)
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

        # Reset state
        self._all_references.clear()
        self._ref_index.clear()
        self._refs_sorted = True
        self._extra_selections = []
        self.text_edit.setExtraSelections(self._extra_selections)

        # Clear any previously applied inline formatting (e.g. from older sessions)
        try:
            c = self.text_edit.textCursor()
            c.beginEditBlock()
            c.select(QTextCursor.SelectionType.Document)
            clear_fmt = QTextCharFormat()
            try:
                clear_fmt.setUnderlineStyle(QTextCharFormat.UnderlineStyle.NoUnderline)
            except AttributeError:
                pass
            clear_fmt.setFontUnderline(False)
            c.mergeCharFormat(clear_fmt)
            c.endEditBlock()
        except (RuntimeError, AttributeError, TypeError):
            pass

        # Still keep line info for viewport math and mapping
        self._lines = content.split('\n')
        self._line_offsets = []
        running = 0
        for ln in self._lines:
            self._line_offsets.append(running)
            running += len(ln) + 1
        self._next_line_index = 0

        # Option A: Parse the entire document so \s can bridge newlines
        self._whole_document_mode = True
        try:
            refs = self.find_scripture_references(content)
        except (RuntimeError, ValueError, TypeError, AttributeError):
            refs = []

        for r in refs:
            start = int(r.get('start', 0))
            length = int(r.get('length', 0))
            key = (start, length)
            if key in self._ref_index:
                continue
            self._ref_index.add(key)
            r_abs = dict(r)
            r_abs['abs_start'] = start
            r_abs['length'] = length
            self._all_references.append(r_abs)
            self._refs_sorted = False

        # No per-line batch processing in whole-document mode
        self._highlight_timer.stop()
        QTimer.singleShot(0, lambda t=token: self._highlight_visible_now() if t == self._cancel_token else None)

    def _apply_highlights_for_refs(self, base: int, refs: List[Dict[str, Any]], *, allow_existing: bool = False) -> None:
        """Collect highlighting ranges for a set of references on a line.
        Deduplicates by (start, length) using self._ref_index.
        Applies ExtraSelections for highlighting.
        """
        selections: List[Any] = []
        for r in refs:
            # Support either relative ('start') or absolute ('abs_start') inputs
            r_start = r.get('start', r.get('abs_start', 0))
            start = base + int(r_start)
            length = int(r.get('length', 0))
            key = (start, length)
            is_new = key not in self._ref_index
            if is_new:
                self._ref_index.add(key)
                # Keep an absolute-position copy for fast hover lookup
                r_abs = dict(r)
                r_abs['abs_start'] = start
                # Ensure length is present (some refs may already include length)
                r_abs['length'] = length
                self._all_references.append(r_abs)
                self._refs_sorted = False
            elif not allow_existing:
                # Skip duplicates during initial accumulation to avoid bloating selections.
                # When rebuilding visible highlights (allow_existing=True), still build selections
                # so formatting is reapplied after operations like theme changes.
                continue
            # Build contiguous selection segments that exclude indentation immediately after line breaks
            text = r.get('text', '')
            if not isinstance(text, str) or not text:
                selections.append({'cursor_start': start, 'length': length})
            else:
                local_i = 0
                seg_abs_start = start
                total_len = len(text)
                while local_i < total_len:
                    ch = text[local_i]
                    if ch == '\r' or ch == '\n':
                        # End the current segment before the newline
                        if seg_abs_start < start + local_i:
                            selections.append({'cursor_start': seg_abs_start, 'length': (start + local_i) - seg_abs_start})
                        # Skip CRLF as a pair
                        local_i += 1
                        if ch == '\r' and local_i < total_len and text[local_i] == '\n':
                            local_i += 1
                        # Skip indentation spaces/tabs at the start of the new line
                        while local_i < total_len and text[local_i] in (' ', '\t'):
                            local_i += 1
                        seg_abs_start = start + local_i
                        continue
                    local_i += 1
                # Tail segment
                if seg_abs_start < start + total_len:
                    selections.append({'cursor_start': seg_abs_start, 'length': (start + total_len) - seg_abs_start})
        # Apply selections
        existing = getattr(self, '_extra_selections', [])
        for extra in selections:
            c = self.text_edit.textCursor()
            c.setPosition(extra['cursor_start'])
            c.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, extra['length'])
            # Add an ExtraSelection for the matching range
            es = self._make_extra_selection(c)
            existing.append(es)
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

    def _move_popup_to_cursor(self, pos: QPoint, y_offset: int = 60) -> None:
        """Position the tooltip popup relative to the mouse cursor within the text edit.
        Extracted from duplicated blocks to avoid code repetition.
        """
        # Compute target position based on cursor rect and editor origin
        cursor = self.text_edit.cursorForPosition(pos)
        cursor_rect = self.text_edit.cursorRect(cursor)
        global_cursor_top_left = self.text_edit.mapToGlobal(cursor_rect.topLeft())
        text_edit_top_left = self.text_edit.mapToGlobal(self.text_edit.rect().topLeft())
        popup_x = text_edit_top_left.x()
        popup_y = global_cursor_top_left.y() + y_offset
        if self.popup_window is not None:
            self.popup_window.move(popup_x, popup_y)

    def _process_highlight_batch(self) -> None:
        # In whole-document mode we don't do per-line batch processing
        if getattr(self, '_whole_document_mode', False):
            self._highlight_timer.stop()
            return
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
            # Finished collecting references; sort once for binary search hover
            # Delegate sorting to the shared helper to avoid duplicate logic
            self._ensure_refs_sorted()

    def _highlight_visible_now(self) -> None:
        # Compute the visible document range in absolute positions
        viewport = self.text_edit.viewport()
        top_pt = QPoint(0, 0)
        bottom_pt = QPoint(viewport.width() - 1, viewport.height() - 1)
        top_cursor = self.text_edit.cursorForPosition(top_pt)
        bot_cursor = self.text_edit.cursorForPosition(bottom_pt)
        top_pos = top_cursor.position()
        bot_pos = bot_cursor.position()

        # If we have no precomputed references (e.g. very first call), trigger parsing
        if not self._all_references:
            text = self.text_edit.toPlainText()
            if text:
                self._start_lazy_highlighting(text)
            return

        # Reset and rebuild only visible selections from precomputed absolute references
        self._extra_selections = []

        # Expand the visible range a bit to avoid edge flicker
        visible_start = max(0, top_pos - 200)
        visible_end = bot_pos + 200

        # Ensure refs sorted once
        self._ensure_refs_sorted()

        refs = self._all_references

        # Binary search to find the first reference near the visible start
        lo, hi = 0, len(refs) - 1
        start_idx = 0
        search_key = max(0, visible_start - 100)
        while lo <= hi:
            mid = (lo + hi) // 2
            s = int(refs[mid].get('abs_start', 0))
            if s < search_key:
                lo = mid + 1
            else:
                start_idx = mid
                hi = mid - 1

        # Iterate forward adding selections within range
        batch: List[Dict[str, Any]] = []
        for i in range(start_idx, len(refs)):
            r = refs[i]
            s = int(r.get('abs_start', 0))
            l = int(r.get('length', 0))
            if s > visible_end:
                break
            e = s + l
            if e < visible_start:
                continue
            batch.append(r)

        if batch:
            # Build selections using absolute positions, allow_existing to refresh formatting
            self._apply_highlights_for_refs(0, batch, allow_existing=True)

        # Apply updated selections for the visible range
        self.text_edit.setExtraSelections(self._extra_selections)

    def _ensure_refs_sorted(self) -> None:
        if not self._refs_sorted and self._all_references:
            try:
                self._all_references.sort(key=lambda r: r.get('abs_start', 0))
            except (TypeError, AttributeError):
                self._all_references = [r for r in self._all_references if 'abs_start' in r]
                self._all_references.sort(key=lambda r: r['abs_start'])
            self._refs_sorted = True

    def _ref_at_position(self, pos: int):
        """Binary search for a reference covering the absolute document position.
        Returns the reference dict with keys including 'abs_start',
        'length', 'book', 'chapter', 'verse' or None.
        """
        refs = self._all_references
        if not refs:
            return None
        self._ensure_refs_sorted()
        lo, hi = 0, len(refs) - 1
        while lo <= hi:
            mid = (lo + hi) // 2
            r = refs[mid]
            start = r.get('abs_start', 0)
            end = start + int(r.get('length', 0))
            if pos < start:
                hi = mid - 1
            elif pos > end:
                lo = mid + 1
            else:
                return r
        return None

    def _do_hover(self):
        if self._pending_hover_pos is None:
            return
        try:
            self.handle_hover(self._pending_hover_pos)
        finally:
            self._pending_hover_pos = None

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Leave:
            # Cancel any pending hover when the cursor leaves the widget
            try:
                self._hover_timer.stop()
            except (RuntimeError, AttributeError):
                pass
            self._pending_hover_pos = None
            self.closePopup()
        elif event.type() == QEvent.Type.MouseButtonPress:
            # Handle clicks on highlighted references to open them in the main Bible window
            try:
                pos = event.position().toPoint()
            except (AttributeError, RuntimeError, TypeError):
                pos = QPoint(0, 0)
            cursor = self.text_edit.cursorForPosition(pos)
            position = cursor.position()
            ref = self._ref_at_position(position)
            if ref is not None:
                # Build a navigation-friendly reference string using the first verse only
                # to ensure compatibility with MainWindow.goto_line parsing.
                book = ref.get('book')
                chapter = ref.get('chapter')
                verse_str = str(ref.get('verse'))
                # Extract the first verse number from possible ranges/lists like "16-18, 21"
                m = re.search(r"\d+", verse_str or "")
                first_verse = m.group(0) if m else verse_str
                # Normalise to canonical book name
                normalized_book = self.normalize_book_input(book) if isinstance(book, str) else book
                book_id = sh.bibledict.get(normalized_book)
                full_book = self.canonical_books.get(book_id, book)
                if book_id and (book_id - 1) in sh.onechapterbooks:
                    nav_ref = f"{full_book} {first_verse}"
                else:
                    nav_ref = f"{full_book} {chapter}:{first_verse}"
                # Emit signal to let the main window navigate to this reference
                try:
                    self.referenceActivated.emit(nav_ref)
                except (RuntimeError, AttributeError, TypeError):
                    pass
                # Close any existing popup after activating
                self.closePopup()
        elif event.type() == QEvent.Type.MouseMove:
            # Copy the QPoint from the event immediately. Qt may delete the event after this method returns.
            pos = event.position().toPoint()
            cursor = self.text_edit.cursorForPosition(pos)
            position = cursor.position()
            # O(log N) lookup using precomputed ranges
            over_reference = self._ref_at_position(position) is not None
            if not over_reference:
                self.closePopup()
            else:
                # Debounce actual hover processing to prevent floods
                self._pending_hover_pos = pos
                if not self._hover_timer.isActive():
                    self._hover_timer.start()
        return super().eventFilter(obj, event)

    def handle_hover(self, pos: QPoint):
        # Convert a stored mouse position to a cursor and document position
        cursor = self.text_edit.cursorForPosition(pos)
        position = cursor.position()
        hovered_reference = self._ref_at_position(position)

        if hovered_reference is None:
            if self.popup_window is not None:
                self.popup_window.close()
                self.popup_window = None
            self.current_reference = None
            return

        same_reference = (
            self.current_reference is not None and
            self.current_reference.get("abs_start") == hovered_reference.get("abs_start") and
            self.current_reference.get("length") == hovered_reference.get("length")
        )

        if same_reference:
            if self.popup_window is None or not self.popup_window.isVisible():
                pass
            else:
                self._move_popup_to_cursor(pos, y_offset=60)
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

        self._move_popup_to_cursor(pos, y_offset=60)

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

        # Use canonical book name for display
        full_book = self.canonical_books.get(book_id, book)

        # Sanitise verse for display: collapse any internal whitespace (incl. CR/LF)
        verse_str = str(verse)
        # Replace any sequence of whitespace (spaces, tabs, CR/LF) with a single space
        verse_clean = re.sub(r"\s+", " ", verse_str).strip()

        # Build a single-line canonical reference string
        if book_id - 1 in sh.onechapterbooks:
            full_reference = f"{full_book} {verse_clean}"
        else:
            full_reference = f"{full_book} {chapter}:{verse_clean}"

        # Final safety: ensure no accidental newlines remain in full_reference
        full_reference = re.sub(r"\s+", " ", full_reference).strip()
        return scripture_text, full_reference

    @staticmethod
    def normalize_book_input(book_input: str) -> str:
        return scripture.normalize_book_input(book_input)

    def lookup_scripture(self, book, chapter, verses):
        return scripture.lookup_scripture(self.bible_data, book, chapter, verses)
