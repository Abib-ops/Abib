# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import re
from typing import Any, Dict, List, Set, Optional

from PySide6.QtCore import Qt, QEvent, QTimer, QPoint, Signal, QCoreApplication
from PySide6.QtGui import (
    QColor,
    QFont,
    QTextCursor,
    QTextCharFormat,
    QPalette,
    QKeySequence,
    QTextDocument,
    QShortcut,
    QMouseEvent,
    QWheelEvent,
)
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QVBoxLayout,
    QPlainTextEdit,
    QWidget,
    QTextEdit,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QHBoxLayout,
    QProgressBar,
)

import fcs
import scripture
import shared as sh
from ui_helpers import SimpleScripturePopup


# Helper: Safely resolve QTextDocument find flags in a way that keeps static analysers happy
# Some PySide6 versions expose flags as QTextDocument.FindCaseSensitively while others
# only expose them under QTextDocument.FindFlag.FindCaseSensitively.
# This helper returns an int-compatible bit value or 0 if the flag cannot be resolved.
def _qdoc_find_flag(name: str) -> int:
    try:
        val = getattr(QTextDocument, name, None)
        if val is None:
            findflag = getattr(QTextDocument, "FindFlag", None)
            if findflag is not None:
                val = getattr(findflag, name, None)
        if val is None:
            return 0
        try:
            return int(val)  # PySide enum/QFlags are int-convertible
        except (ValueError, TypeError):
            # Fallback: try a common attribute
            v2 = getattr(val, "value", None)
            return int(v2) if v2 is not None else 0
    except (AttributeError, TypeError):
        return 0


class TextDocumentWindow(QDialog):
    # Emitted when the user clicks a highlighted scripture reference.
    # Payload is a canonical reference string like "John 3:16" or "Jude 5".
    referenceActivated = Signal(str)
    # Emitted when this window becomes shown/hidden, so the main window can toggle buttons
    displayedChanged = Signal(bool)
    def __init__(self, initial_file_path: str | None = None,
                 settings: Dict[str, Any] | None = None,
                 settings_path: str | None = None,
                 settings_service: Any | None = None) -> None:
        super().__init__()

        # Externalised settings (instead of relying on globals)
        self.settings_service: Any | None = settings_service
        self.settings: Dict[str, Any] = settings if isinstance(settings, dict) else {}
        self.settings_path: str | None = settings_path
        
        # If a service is provided, prefer its managed settings and path
        if self.settings_service is not None:
            try:
                self.settings = self.settings_service.settings
                self.settings_path = str(self.settings_service.user_settings_path)
            except (AttributeError, RuntimeError, TypeError):
                pass

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
            self.reset_scroll_btn = QPushButton("Reset scroll for this text")
            self.reset_scroll_btn.setToolTip("Set the saved position for this text to the top (0) and scroll there")
            self.reset_scroll_btn.clicked.connect(self.reset_scroll_for_current_text)
            self.layout.addWidget(self.reset_scroll_btn)
        except (ImportError, AttributeError, RuntimeError, TypeError):
            # If QPushButton is unavailable for any reason, skip the button gracefully
            self.reset_scroll_btn = None

        self.text_edit = QPlainTextEdit()
        # Reader font size (persisted in settings.json)
        try:
            self.reader_fontsize: int = int(self.settings.get("reader_font_size", 12))
        except (TypeError, ValueError):
            self.reader_fontsize = 12
        self.text_edit.setFont(QFont("Cascadia Mono", int(self.reader_fontsize)))
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

        # Keep references to QShortcut instances
        self._shortcuts: list[QShortcut] = []
        try:
            self._shortcuts.append(self._make_shortcut(QKeySequence("Ctrl++"), self.increase_reader_font_size))
            self._shortcuts.append(self._make_shortcut(QKeySequence("Ctrl+="), self.increase_reader_font_size))
            self._shortcuts.append(self._make_shortcut(QKeySequence("Ctrl+-"), self.decrease_reader_font_size))
        except (RuntimeError, AttributeError, TypeError, ValueError):
            # Shortcuts are optional; do not fail window creation
            pass

        # Save scroll position per file
        self._is_loading: bool = False
        self.text_edit.verticalScrollBar().valueChanged.connect(self.save_scroll_position)
        # Debounced saving to avoid rapid writes and possible external side effects.
        try:
            self._save_debounce: QTimer = QTimer(self)
            self._save_debounce.setSingleShot(True)
            self._save_debounce.setInterval(150)
            self._pending_save_stem: Optional[str] = None
            self._pending_save_value: Optional[int] = None
            self._save_debounce.timeout.connect(self._flush_pending_save)
        except (RuntimeError, AttributeError, TypeError):
            self._save_debounce = None  # type: ignore
            self._pending_save_stem = None  # type: ignore
            self._pending_save_value = None  # type: ignore

        # --- Progress bar footer (hidden by default) ---
        try:
            self._progress_container = QWidget(self)
            ph = QHBoxLayout(self._progress_container)
            ph.setContentsMargins(8, 4, 8, 6)
            ph.setSpacing(8)
            self._progress_label = QLabel("")
            small_font = self._progress_label.font()
            try:
                small_font.setPointSize(8)
            except (AttributeError, TypeError, RuntimeError):
                pass
            self._progress_label.setFont(small_font)
            self._progress_bar = QProgressBar()
            self._progress_bar.setMinimum(0)
            self._progress_bar.setMaximum(100)
            self._progress_bar.setValue(0)
            self._progress_bar.setTextVisible(False)
            ph.addWidget(self._progress_label)
            ph.addWidget(self._progress_bar, 1)
            self._progress_container.setVisible(False)
            self.layout.addWidget(self._progress_container)
            # Animated pulse for the message (cycles dots …)
            # Optional because the fail-safe path below may set it to None
            self._progress_pulse: Optional[QTimer] = QTimer(self)
            try:
                self._progress_pulse.setInterval(250)
            except (AttributeError, TypeError, RuntimeError):
                pass
            # Guarded connect to satisfy static analysers that type QTimer.timeout (Signal)
            # may not expose .connect in stubs, while at runtime it does.
            try:
                sig = getattr(self._progress_pulse, "timeout", None)
                cn = getattr(sig, "connect", None)
                if callable(cn):
                    cn(self._tick_progress_pulse)
            except (AttributeError, TypeError, RuntimeError):
                pass
            self._progress_indeterminate: bool = False
            self._progress_msg_base: str = ""
            self._progress_msg_static: str = ""
            self._progress_dots: int = 0
            # Cap the IO phase so the bar does not reach 100% until all heavy
            # finalisation's (decode, layout, highlighting) have completed.
            self._io_progress_cap: int = 95
        except (RuntimeError, AttributeError, TypeError):
            # Fail-safe: if any widget creation fails, keep attributes None
            self._progress_container = None
            self._progress_label = None
            self._progress_bar = None
            self._progress_pulse = None
            self._progress_indeterminate = False
            self._progress_msg_base = ""
            self._progress_msg_static = ""
            self._progress_dots = 0
            self._io_progress_cap = 95

        # Hover tracking
        self.text_edit.viewport().setMouseTracking(True)
        self.text_edit.viewport().installEventFilter(self)
        self.text_edit.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self.popup_window = None
        # Initialise the popup helper so static analysers know this attribute exists
        # (actual instance may be created lazily where needed)
        self._popup_helper: SimpleScripturePopup | None = None

        # Lazy highlighting state
        self._all_references: List[Dict[str, Any]] = []
        self._ref_index: Set[tuple] = set()
        self._lines: List[str] = []
        self._line_offsets: List[int] = []
        self._next_line_index: int = 0
        # Has the current document been scanned for references yet?
        # Prevents repeated whole-document rescans when none are present.
        self._refs_scanned: bool = False
        self._highlight_timer: QTimer = QTimer(self)
        self._highlight_timer.setInterval(25)
        self._highlight_timer.timeout.connect(self._process_highlight_batch)
        self._cancel_token: int = 0
        # Whether we are in whole-document parse mode (Option A)
        self._whole_document_mode: bool = False
        # Cancellation token for async scroll restore to avoid stale apply when switching files
        self._restore_token: int = 0
        # Pending restore guard: while a restore is in progress for a given stem
        # and the desired value is not yet reachable, suppress saving partial
        # scroll values to settings.json.
        self._pending_restore_stem: Optional[str] = None
        self._pending_restore_value: int = 0
        # Extra selections for QPlainTextEdit highlighting
        self._extra_selections: List[Any] = []
        # Track whether the reference list is sorted by abs_start
        self._refs_sorted: bool = True
        # Trigger quick visible-range highlight on scroll
        # Debounced highlight-on-scroll to avoid repaint storms; suppressed while loading/restoring
        try:
            self._highlight_debounce: QTimer = QTimer(self)
            self._highlight_debounce.setSingleShot(True)
            self._highlight_debounce.setInterval(75)
            # Token-based guard to avoid cross-file stray triggers
            self._highlight_debounce_token: int = 0
            self._highlight_debounce.timeout.connect(self._fire_highlight_debounced)
        except (RuntimeError, AttributeError, TypeError):
            # Fallback timer placeholder
            self._highlight_debounce = None  # type: ignore
        self.text_edit.verticalScrollBar().valueChanged.connect(self._on_scrollbar_value_changed)
        
        # Auto-scrolling state for scripture popups
        self._auto_scroll_timer = QTimer(self)
        self._auto_scroll_timer.setInterval(20) # ~50 FPS
        self._auto_scroll_timer.timeout.connect(self._do_auto_scroll)
        
        self._auto_scroll_delay_timer = QTimer(self)
        self._auto_scroll_delay_timer.setSingleShot(True)
        self._auto_scroll_delay_timer.setInterval(600) 
        self._auto_scroll_delay_timer.timeout.connect(self._start_auto_scroll)
        
        self._scrolling_reference = None
        self._last_mouse_char_pos = -1

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

        # Async file loading state
        self._load_timer: Optional[QTimer] = None
        self._load_fp = None
        self._load_total: int = 0
        self._load_read: int = 0
        self._load_chunks: list[bytes] = []
        self._load_token: int = 0
        # Track the currently connected timeout slot so we can disconnect safely
        self._load_timeout_slot: Optional[object] = None
        # Idempotency/reentrancy guards for loading
        self._is_loading_file: bool = False
        self._loaded_file_path: Optional[str] = None

        if initial_file_path:
            self.load_text_file(initial_file_path)

        self.canonical_books = scripture.CANONICAL_BOOKS

        # Pending jump-to-anchor patterns to be applied after a file finishes loading
        self._pending_jump_patterns: Optional[list[str]] = None
        # Pending jump-to-character offset to be applied after a file finishes loading
        self._pending_jump_char: Optional[int] = None

        # ---- Lightweight Find dialog state and shortcuts ----
        # Use the concrete dialog type so static analysers know about `.edit`, `.build_flags`, etc.
        self._find_dlg: Optional["TextDocumentWindow._ReaderFindDialog"] = None
        try:
            # Keyboard shortcuts within the reader window
            sc_find = QShortcut(QKeySequence.StandardKey.Find, self)
            sc_find.setContext(Qt.ShortcutContext.WindowShortcut)
            sc_find.activated.connect(self.show_find_dialog)

            sc_next = QShortcut(QKeySequence.StandardKey.FindNext, self)
            sc_next.setContext(Qt.ShortcutContext.WindowShortcut)
            sc_next.activated.connect(self.find_next)

            sc_prev = QShortcut(QKeySequence.StandardKey.FindPrevious, self)
            sc_prev.setContext(Qt.ShortcutContext.WindowShortcut)
            sc_prev.activated.connect(self.find_prev)

            # Use the proper PySide6 enum path to satisfy static analysers
            sc_esc = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
            sc_esc.setContext(Qt.ShortcutContext.WindowShortcut)
            sc_esc.activated.connect(self._maybe_close_find_dialog)
        except (RuntimeError, AttributeError, TypeError):
            # Shortcuts are optional; ignore failures gracefully
            pass

    # -------- Reader font size controls (shortcuts + persistence) --------
    def _make_shortcut(self, seq: QKeySequence, slot):
        """Create a QShortcut and keep a reference to avoid GC."""
        sc = QShortcut(seq, self)
        try:
            sc.setContext(Qt.ShortcutContext.WindowShortcut)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            sc.activated.connect(slot)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        return sc

    def _persist_reader_font_size(self) -> None:
        try:
            val = int(getattr(self, "reader_fontsize", 12))
            if self.settings_service:
                self.settings_service.update_reader_font_size(val)
            else:
                path = str(self.settings_path) if self.settings_path else "settings.json"
                fcs.update_reader_font_size(val, path)
                # Also update local self.settings if available to avoid stale saves later
                if isinstance(self.settings, dict):
                    self.settings["reader_font_size"] = val
        except (ValueError, TypeError, OSError):
            pass

    def apply_font_size(self, size: int) -> None:
        try:
            size_int = int(size)
        except (TypeError, ValueError):
            size_int = 12
        # Update widget font
        try:
            f = self.text_edit.font()
            if f.pointSize() == size_int:
                return
            f.setPointSize(size_int)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            f = QFont("Cascadia Mono", size_int)
        self.text_edit.setFont(f)
        # Save and persist
        self.reader_fontsize = size_int
        self._persist_reader_font_size()

        # Unified font size support: notify the main window
        try:
            from PySide6.QtWidgets import QApplication
            for widget in QApplication.topLevelWidgets():
                if widget.__class__.__name__ == "MainWindow":
                    if bool(getattr(widget, "settings", {}).get("unified_font_size", False)):
                        ws = getattr(widget, "settings_service", None)
                        if ws and ws.get_bible_font_size() != size_int:
                            ws.update_bible_font_size(size_int)
                            af = getattr(widget, "apply_font_size", None)
                            if af:
                                af()
                    break
        except (AttributeError, RuntimeError):
            pass

    def increase_reader_font_size(self) -> None:
        try:
            cur = int(getattr(self, "reader_fontsize", 12))
        except (TypeError, ValueError):
            cur = 12
        self.apply_font_size(min(cur + 1, 72))

    def decrease_reader_font_size(self) -> None:
        try:
            cur = int(getattr(self, "reader_fontsize", 12))
        except (TypeError, ValueError):
            cur = 12
        self.apply_font_size(max(cur - 1, 6))

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

            # Use relaxed multi-monitor aware clamping similar to fcs.get_window_geometry
            VIRTUAL_LIMIT = 10000

            gx, gy, gw, gh = int(x), int(y), int(w), int(h)

            if not (-VIRTUAL_LIMIT < gx < VIRTUAL_LIMIT):
                gx = 100
            if not (-VIRTUAL_LIMIT < gy < VIRTUAL_LIMIT):
                gy = 100
            if gw <= 0 or gw > VIRTUAL_LIMIT:
                gw = 736
            if gh <= 0 or gh > VIRTUAL_LIMIT:
                gh = 599

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

    def _write_entry(
        self,
        stem: str,
        scroll: int | None = None,
        geometry: tuple[int, int, int, int] | None = None,
    ) -> None:
        """Persist the per-file entry using only legacy fields: [scroll, x, y, w, h]."""
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

            payload = [
                int(new_scroll),
                int(new_geom[0]),
                int(new_geom[1]),
                int(new_geom[2]),
                int(new_geom[3]),
            ]

            self.settings["last_read_positions"][stem] = payload
            # Also ensure this work is recorded as the last one read
            try:
                self.settings["last_other_work"] = stem
            except (TypeError, KeyError):
                pass

            # Persist
            if self.settings_service:
                try:
                    self.settings_service.save(self.settings)
                except (RuntimeError, AttributeError, TypeError, ValueError, OSError):
                    pass
            elif self.settings_path:
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
        
        # Ensure the popup helper matches the new theme if it exists
        if hasattr(self, '_popup_helper') and isinstance(self._popup_helper, SimpleScripturePopup):
            try:
                self._popup_helper.apply_theme(is_dark)
            except (RuntimeError, AttributeError):
                pass

    def _save_scroll_for(self, stem: Any, value: Any) -> None:
        """Persist the reading position for a given file stem.
        Stores a single positive integer representing the current scrollbar value
        (pixel scroll position).
        Negative content-anchored encoding is no longer used for persistence;
        it remains supported for reading/backward compatibility.
        """
        try:
            if not stem:
                return
            try:
                sb = self.text_edit.verticalScrollBar()
                cur_val = int(sb.value())
            except (AttributeError, RuntimeError, TypeError, ValueError):
                cur_val = int(value) if isinstance(value, int) else 0
            self._write_entry(stem, scroll=int(cur_val), geometry=None)
        except (ValueError, TypeError, OSError):
            # Be tolerant: failing to save should never crash the app
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

    def _restore_scroll_position_async(
        self,
        stem: str,
        saved: int,
        timeout_ms: int = 45000,
        interval_ms: int = 50,
        on_done: Any | None = None,
    ) -> None:
        """Content-anchored restore of the reading position.
        If ``saved`` is negative, it encodes the absolute character offset of the
        desired top-of-viewport block: ``target_char = -saved - 1`` (backward compatibility).
        Positive values are treated as pixel scrollbar positions and approximated
        as pixel scrollbar positions and restored using a stabilised scrollbar-maximum
        strategy to avoid early-partial maxima causing incorrect placement.
        After a successful restore, any legacy negative values are rewritten
        to the current positive scrollbar value, so settings.json no longer contains
        large negative numbers.

        Keeps _is_loading True until finalising; uses a cancellation token.
        Calls ``on_done()`` after successful or terminal finalising (once).
        """
        # New restore cycle
        self._restore_token += 1
        token = self._restore_token

        # Determine target character offset
        try:
            saved_int = int(saved) if saved is not None else 0
        except (ValueError, TypeError):
            saved_int = 0

        doc: QTextDocument = self.text_edit.document()
        try:
            total_chars = int(doc.characterCount())
        except (AttributeError, RuntimeError, TypeError, ValueError):
            total_chars = 0

        # Approximate mapping for legacy positive pixel scroll values
        def _legacy_to_char(px: int) -> int:
            try:
                sb = self.text_edit.verticalScrollBar()
                maximum = int(sb.maximum()) if sb is not None else 0
            except (AttributeError, RuntimeError, TypeError, ValueError):
                maximum = 0
            try:
                # Use ratio of current known maximum; will be refined by geometry retries
                ratio = 0.0 if maximum <= 0 else max(0.0, min(1.0, float(px) / float(maximum)))
            except (ValueError, TypeError):
                ratio = 0.0
            # characterCount includes a terminating position; clamp to range
            end_char = max(0, total_chars - 1)
            return int(ratio * end_char)

        is_legacy = saved_int >= 0
        target_char = (-saved_int - 1) if saved_int < 0 else _legacy_to_char(saved_int)
        # Clamp to available range
        if total_chars <= 0:
            target_char = 0
        else:
            if target_char < 0:
                target_char = 0
            elif target_char >= total_chars:
                target_char = max(0, total_chars - 1)

        attempts = max(int(timeout_ms // max(1, interval_ms)), 1)
        done_emitted = False

        # Note: Previously we disabled viewport updates during restore to reduce flicker,
        # but this could leave the UI appearing blank on slower layouts until finalising.
        # Keep updates enabled throughout restore so content is visible while we retry.
        try:
            _ = bool(self.text_edit.updatesEnabled())
        except (AttributeError, RuntimeError, TypeError):
            pass

        def finalize_upgrade_and_done():
            nonlocal done_emitted
            if done_emitted:
                return
            done_emitted = True
            # Clear guards
            self._is_loading = False
            self._pending_restore_stem = None
            self._pending_restore_value = 0
            # Rewrite any legacy negative saved positions to positive scrollbar values
            try:
                if not is_legacy:
                    sb2 = self.text_edit.verticalScrollBar()
                    new_val = int(sb2.value()) if sb2 is not None else 0
                    self._write_entry(stem, scroll=new_val, geometry=None)
            except (AttributeError, RuntimeError, TypeError, ValueError, OSError):
                pass
            # Ensure updates are enabled and repaint to show the final state
            try:
                self.text_edit.setUpdatesEnabled(True)
                # If they were previously disabled, force a viewport refresh
                self.text_edit.viewport().update()
            except (AttributeError, RuntimeError, TypeError):
                pass
            # Callback
            try:
                if callable(on_done):
                    on_done()
            except (RuntimeError, AttributeError, TypeError, ValueError):
                # Do not allow callback errors to propagate; handle common runtime/callback issues
                pass

        # If the saved value is a positive pixel scrollbar position, use a stabilised
        # pixel-based restore to avoid flicker and wrong placement from early maxima.
        if is_legacy:
            sb_px = self.text_edit.verticalScrollBar()
            # Guard: if no scrollbar, just finalise
            if sb_px is None:
                finalize_upgrade_and_done()
                return

            # Stabilisation state
            last_max = -1
            stable_ticks = 0

            def try_place_px():
                # Abort if a newer restore has started
                if token != getattr(self, "_restore_token", token):
                    return
                nonlocal attempts, last_max, stable_ticks
                attempts -= 1
                # Validate scrollbar each tick
                try:
                    maximum = int(sb_px.maximum())
                    cur_val = int(sb_px.value())
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    finalize_upgrade_and_done()
                    return

                # If maximum is zero (The layout is not ready), keep waiting
                if maximum <= 0:
                    if attempts <= 0:
                        finalize_upgrade_and_done()
                        return
                    QTimer.singleShot(interval_ms, try_place_px)
                    return

                # Track stabilisation of maximum
                if maximum != last_max:
                    last_max = maximum
                    stable_ticks = 0
                else:
                    stable_ticks += 1

                # Compute target for current knowledge and apply only if changed materially
                target_px = max(0, min(saved_int, maximum))
                if abs(cur_val - target_px) > 2:
                    try:
                        sb_px.setValue(target_px)
                    except (AttributeError, RuntimeError, TypeError, ValueError):
                        pass

                # Finalise when the domain can accommodate the desired value, or when stabilised
                # for several ticks, or when timeout expires
                if maximum >= saved_int or stable_ticks >= 10 or attempts <= 0:
                    finalize_upgrade_and_done()
                    return

                QTimer.singleShot(interval_ms, try_place_px)

            QTimer.singleShot(interval_ms, try_place_px)
            return

        def try_place():
            # Abort if a newer restore has started
            if token != getattr(self, "_restore_token", token):
                return
            # If editor/doc are unavailable, bail out gracefully
            try:
                if self.text_edit is None or doc is None:
                    finalize_upgrade_and_done()
                    return
            except (AttributeError, RuntimeError):
                finalize_upgrade_and_done()
                return

            nonlocal attempts
            attempts -= 1

            # Locate the block containing the target character
            try:
                blk = doc.findBlock(int(target_char))
            except (ValueError, TypeError):
                blk = doc.firstBlock()
            if not getattr(blk, 'isValid', lambda: True)():
                # Give up if 'doc' has no valid blocks
                if attempts <= 0:
                    finalize_upgrade_and_done()
                else:
                    QTimer.singleShot(interval_ms, try_place)
                return

            # Compute the Y position of the block's top within the content
            try:
                geom = self.text_edit.blockBoundingGeometry(blk)
                offset = self.text_edit.contentOffset()
                rect = geom.translated(offset)
                top_y = int(rect.top())
                height = float(rect.height())
            except (AttributeError, RuntimeError, TypeError, ValueError):
                top_y = 0
                height = 0.0

            # If the block hasn't been laid out yet (height ~ 0 and target not the very first block), retry
            try:
                blk_pos = int(blk.position())
            except (ValueError, TypeError):
                blk_pos = 0

            if height <= 0.1 and blk_pos > 0 and attempts > 0:
                QTimer.singleShot(interval_ms, try_place)
                return

            # Apply the placement using the computed content Y (only if it changed materially)
            try:
                sb = self.text_edit.verticalScrollBar()
                if sb is not None:
                    target_val = max(0, top_y)
                    try:
                        cur_val = int(sb.value())
                    except (AttributeError, RuntimeError, TypeError, ValueError):
                        cur_val = -1
                    # Only set if the delta is meaningful to avoid repaint storms
                    if abs(cur_val - target_val) > 2:
                        sb.setValue(target_val)
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass

            # Verify: if we are close enough (same block at top), finalise; otherwise
            # retry a limited number of times to avoid long flicker on slow layouts.
            # Maintain a small counter on the function object to limit post-checks.
            try:
                _ = try_place._post_checks  # type: ignore[attr-defined]
            except AttributeError:
                try_place._post_checks = 10  # type: ignore[attr-defined]

            try:
                fb = self.text_edit.firstVisibleBlock()
                if fb.isValid() and int(fb.position()) <= blk_pos <= int(fb.position()) + 1:
                    finalize_upgrade_and_done()
                    return
            except (AttributeError, RuntimeError, TypeError, ValueError):
                # If verification fails, still try to finalise after timeout
                pass

            # If we exhausted attempts or our limited post-checks, finalise to prevent loops
            try:
                try_place._post_checks -= 1  # type: ignore[attr-defined]
            except (AttributeError, TypeError):
                # If the attribute doesn't exist or isn't numeric, ignore safely
                pass

            if attempts <= 0 or getattr(try_place, "_post_checks", 0) <= 0:  # type: ignore[attr-defined]
                finalize_upgrade_and_done()
            else:
                QTimer.singleShot(interval_ms, try_place)

        # Begin attempts shortly to allow initial layout
        QTimer.singleShot(interval_ms, try_place)

    def _on_scrollbar_value_changed(self, _value: Any) -> None:
        """Handle user-driven scrollbar changes.
        Suppress heavy work while loading/restoring; debounce highlight updates to reduce flicker.
        """
        # Never react during programmatic changes
        if getattr(self, "_is_loading", False):
            return
        try:
            if self._pending_restore_stem and self.current_file_stem == self._pending_restore_stem:
                return
        except (AttributeError, RuntimeError):
            # If attributes are missing, proceed cautiously
            pass

        # Debounce highlight updates for the visible region
        try:
            if getattr(self, "_highlight_debounce", None) is not None:
                # Bump a token so any stale timer run is ignored across file switches
                try:
                    self._highlight_debounce_token += 1
                    self._highlight_debounce_scheduled = self._highlight_debounce_token  # type: ignore
                except (AttributeError, TypeError):
                    pass
                try:
                    # Restart debounce timer
                    self._highlight_debounce.stop()
                except (RuntimeError, AttributeError):
                    pass
                try:
                    self._highlight_debounce.start()
                except (RuntimeError, AttributeError):
                    # If the timer fails, fall back to immediate update
                    self._highlight_visible_now()
            else:
                # No debounce available; update immediately
                self._highlight_visible_now()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            # Be resilient and avoid throwing from UI callbacks
            pass

    def _fire_highlight_debounced(self) -> None:
        """Timer slot to perform a coalesced visible-range highlight update."""
        # If we are loading/restoring, skip to avoid repaint storms
        if getattr(self, "_is_loading", False):
            return
        try:
            if self._pending_restore_stem and self.current_file_stem == self._pending_restore_stem:
                return
        except (AttributeError, RuntimeError):
            pass

        # Ensure this fire corresponds to the latest scheduled token
        try:
            scheduled = getattr(self, "_highlight_debounce_scheduled", None)
            if scheduled is not None and scheduled != getattr(self, "_highlight_debounce_token", 0):
                return
        except (AttributeError, RuntimeError):
            pass

        try:
            self._highlight_visible_now()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    def save_scroll_position(self, value: Any) -> None:
        """Slot for scrollbar valueChanged: save only during user-driven scrolls.
        Suppressed while a document is programmatically loading/restoring.
        """
        if getattr(self, "_is_loading", False):
            return
        stem = self.current_file_stem
        # If a restore is pending for this stem, suppress saves entirely until it finalises.
        try:
            if self._pending_restore_stem and stem == self._pending_restore_stem:
                return
        except (AttributeError, RuntimeError):
            pass
        # Debounce the save to avoid rapid disk writes and potential reload side effects.
        try:
            ivalue = int(value) if not isinstance(value, int) else value
        except (ValueError, TypeError):
            ivalue = 0
        try:
            self._pending_save_stem = stem
            self._pending_save_value = ivalue
            if getattr(self, "_save_debounce", None) is not None:
                try:
                    self._save_debounce.stop()
                except (RuntimeError, AttributeError):
                    pass
                try:
                    self._save_debounce.start()
                except (RuntimeError, AttributeError):
                    # Fallback: if the timer fails, write immediately
                    self._save_scroll_for(stem, ivalue)
            else:
                self._save_scroll_for(stem, ivalue)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            # As a last resort, try immediate save
            self._save_scroll_for(stem, ivalue)

    def _flush_pending_save(self) -> None:
        """Write the pending debounced scroll save if any."""
        try:
            if getattr(self, "_is_loading", False):
                return
            if self._pending_restore_stem and self.current_file_stem == self._pending_restore_stem:
                return
        except (AttributeError, RuntimeError):
            pass
        try:
            stem = getattr(self, "_pending_save_stem", None)
            value = getattr(self, "_pending_save_value", None)
            if stem is None or value is None:
                return
            self._save_scroll_for(stem, int(value))
        except (ValueError, TypeError, AttributeError):
            pass
        finally:
            try:
                self._pending_save_stem = None
                self._pending_save_value = None
            except (AttributeError, TypeError):
                pass

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
                    # Also move the caret to the start
                    try:
                        c = self.text_edit.textCursor()
                        c.setPosition(0)
                        self.text_edit.setTextCursor(c)
                    except (AttributeError, RuntimeError, TypeError):
                        pass
                except (AttributeError, RuntimeError, TypeError, ValueError):
                    pass
                finally:
                    self._is_loading = False
            else:
                # Use the async restorer to apply 0 once the layout is ready
                self._restore_scroll_position_async(stem, 0)
        except (AttributeError, RuntimeError):
            self._is_loading = False

    def _save_current_geometry(self):
        # Save geometry
        try:
            g = self.geometry()
            # 1. Update the global/default reader window position in the settings dict
            if isinstance(self.settings, dict):
                if "reader_window" not in self.settings:
                    self.settings["reader_window"] = {}
                self.settings["reader_window"].update({
                    "x": int(g.x()),
                    "y": int(g.y()),
                    "width": int(g.width()),
                    "height": int(g.height())
                })

            # 2. Save per-file geometry if a work is loaded
            stem = getattr(self, "current_file_stem", None)
            if stem:
                # _write_entry also persists in the whole settings dict, including our "reader_window" update
                self._write_entry(stem, geometry=(int(g.x()), int(g.y()), int(g.width()), int(g.height())))
            else:
                # No work loaded, just persist global settings (theme, reader_window, etc.)
                if self.settings_service:
                    self.settings_service.save(self.settings)
                elif self.settings_path:
                    fcs.save_settings_to_file(self.settings, self.settings_path)
                else:
                    fcs.save_settings_to_file(self.settings)
        except (ValueError, TypeError, AttributeError, RuntimeError, OSError):
            pass

    def moveEvent(self, event):
        self._save_current_geometry()
        try:
            return super().moveEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def resizeEvent(self, event):
        self._save_current_geometry()
        try:
            return super().resizeEvent(event)
        except (RuntimeError, AttributeError, TypeError):
            return None

    def closeEvent(self, event):
        self._save_current_geometry()

        # Explicitly close the modeless find dialog if it exists
        if getattr(self, "_find_dlg", None):
            try:
                self._find_dlg.close()
            except (RuntimeError, AttributeError):
                pass

        # Notify listeners that this window is no longer displayed
        try:
            self.displayedChanged.emit(False)
        except (RuntimeError, AttributeError, TypeError):
            pass
        event.accept()

    def showEvent(self, event):
        try:
            self.displayedChanged.emit(True)
        except (RuntimeError, AttributeError, TypeError):
            pass
        super().showEvent(event)

    def hideEvent(self, event):
        try:
            self.displayedChanged.emit(False)
        except (RuntimeError, AttributeError, TypeError):
            pass
        super().hideEvent(event)

    def _show_progress(self, message: str, total_bytes: int | None = None) -> None:
        try:
            if self._progress_container is None:
                return
            # Show determinate progress if the total size is known; otherwise fallback to indeterminate marquee
            try:
                known_total = (total_bytes is not None) and (int(total_bytes) > 0)
            except (TypeError, ValueError):
                known_total = False
            if known_total:
                self._progress_bar.setRange(0, 100)
                self._progress_bar.setValue(0)
                self._progress_indeterminate = False
            else:
                self._progress_bar.setRange(0, 0)
                self._progress_indeterminate = True
            self._progress_msg_base = message
            self._progress_msg_static = message
            self._progress_dots = 0
            self._progress_label.setText(message)
            self._progress_container.setVisible(True)
            # Start a subtle pulse on the label to reinforce activity even on styles
            # that don’t animate the marquee conspicuously
            if self._progress_pulse is not None:
                try:
                    self._progress_pulse.start()
                except (RuntimeError, AttributeError):
                    pass
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    def _update_progress(self, read_bytes: int, total_bytes: int) -> None:
        try:
            if self._progress_bar is None:
                return
            # Keep the progress bar in indeterminate mode for visible animation
            if getattr(self, "_progress_indeterminate", False):
                return
            pct = 0 if total_bytes <= 0 else int((read_bytes / total_bytes) * 100)
            if pct < 0:
                pct = 0
            if pct > 100:
                pct = 100
            # During the IO phase, clamp to a cap so the bar doesn't hit 100% before
            # decode/layout/highlighting complete.
            try:
                cap = int(getattr(self, "_io_progress_cap", 95))
                if cap > 0:
                    pct = min(pct, cap)
            except (AttributeError, TypeError, ValueError):
                pass
            # Ensure determinate mode
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(pct)
            # Update the message to include percentage while retaining pulsing dots
            try:
                base_static = getattr(self, "_progress_msg_static", "") or getattr(self, "_progress_msg_base", "")
                self._progress_msg_base = f"{base_static} {pct}%"
                if self._progress_label is not None:
                    # Show immediate text; pulse timer will append dots on the next tick
                    self._progress_label.setText(f"{self._progress_msg_base}{'.' * getattr(self, '_progress_dots', 0)}")
            except (AttributeError, TypeError, ValueError):
                pass
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    def _set_progress_percent(self, pct: int) -> None:
        """Force-set the progress bar to a specific percentage (0-100) and
        update the label accordingly, regardless of IO cap.
        Used during the finalisation phase to reflect progress up to 100%.
        """
        try:
            if self._progress_bar is None:
                return
            if pct < 0:
                pct = 0
            if pct > 100:
                pct = 100
            # Ensure determinate mode
            self._progress_bar.setRange(0, 100)
            self._progress_bar.setValue(int(pct))
            # Update the message to include percentage while retaining pulsing dots
            try:
                base_static = getattr(self, "_progress_msg_static", "") or getattr(self, "_progress_msg_base", "")
                self._progress_msg_base = f"{base_static} {int(pct)}%"
                if self._progress_label is not None:
                    self._progress_label.setText(f"{self._progress_msg_base}{'.' * getattr(self, '_progress_dots', 0)}")
            except (AttributeError, TypeError, ValueError):
                pass
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    def _hide_progress(self) -> None:
        try:
            if self._progress_container is not None:
                self._progress_container.setVisible(False)
            # Stop pulse and reset state
            if self._progress_pulse is not None:
                try:
                    self._progress_pulse.stop()
                except (RuntimeError, AttributeError):
                    pass
            self._progress_indeterminate = False
            self._progress_msg_base = ""
            self._progress_msg_static = ""
            self._progress_dots = 0
        except (RuntimeError, AttributeError, TypeError):
            pass

    def _tick_progress_pulse(self) -> None:
        try:
            if self._progress_label is None:
                return
            base = getattr(self, "_progress_msg_base", "")
            self._progress_dots = (getattr(self, "_progress_dots", 0) + 1) % 4
            dots = "." * self._progress_dots
            self._progress_label.setText(f"{base}{dots}")
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    def _cancel_active_loader(self) -> None:
        # Stop any ongoing timer and close the file handle
        try:
            self._load_token += 1
            if self._load_timer is not None:
                try:
                    self._load_timer.stop()
                except (RuntimeError, AttributeError):
                    pass
                # Safely disconnect the last connected slot, if any
                try:
                    if getattr(self, "_load_timeout_slot", None) is not None:
                        self._load_timer.timeout.disconnect(self._load_timeout_slot)
                except (RuntimeError, TypeError):
                    pass
                self._load_timeout_slot = None
                self._load_timer = None
            if self._load_fp is not None:
                try:
                    self._load_fp.close()
                except (OSError, ValueError):
                    pass
                self._load_fp = None
            self._load_total = 0
            self._load_read = 0
            self._load_chunks = []
            self._hide_progress()
            # Clear the loading state so a new load can begin cleanly
            self._is_loading_file = False
        except (RuntimeError, AttributeError, OSError, TypeError, ValueError):
            pass

    def load_text_file(self, file_path1):
        try:
            if not file_path1:
                return
            # Normalise the incoming path to an absolute string for comparison (Windows-safe)
            try:
                abs_path = str(Path(file_path1).resolve())
            except (OSError, RuntimeError, ValueError, TypeError):
                # Fall back to raw string if resolve fails
                abs_path = str(file_path1)

            # Derive stem early for idempotency checks that don't require cancelling the current load
            try:
                early_stem = Path(abs_path).stem
            except (OSError, RuntimeError, ValueError, TypeError):
                early_stem = None

            # If we are already loading this exact file, ignore duplicate requests
            if getattr(self, "_is_loading_file", False) and self._loaded_file_path == abs_path:
                return
            # If we are already loading a file with the same stem, ignore (prevents reload loops)
            try:
                if getattr(self, "_is_loading_file", False) and early_stem and getattr(self, "current_file_stem", None) == early_stem:
                    return
            except (AttributeError, RuntimeError, TypeError, ValueError, OSError):
                # If any attribute/path resolution issues occur, fall through to the normal load
                pass
            # If the same file is already loaded and no load in progress, no-op to avoid flicker
            if (not getattr(self, "_is_loading_file", False)) and self._loaded_file_path == abs_path:
                return
            # If the same stem is already loaded (path string may differ), no-op
            try:
                if (
                        not getattr(self, "_is_loading_file", False)
                        and early_stem
                        and getattr(self, "current_file_stem", None) == early_stem
                ):
                    return
            except (AttributeError, RuntimeError, TypeError, ValueError, OSError):
                # If state inspection fails, proceed with the load rather than crashing
                pass
            # Cancel any prior asynchronous load in progress
            self._cancel_active_loader()
            # NEW: Invalidate any pending scroll restore from a previous file
            self._restore_token += 1
            # Clear any pending restore guard from the previous file
            self._pending_restore_stem = None
            self._pending_restore_value = 0
            # New file: reset reference-scan flag so we can scan or load companions once
            self._refs_scanned = False
            # Mark the loading state and remember the target path
            self._is_loading_file = True
            self._loaded_file_path = abs_path

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

            p = Path(abs_path)
            stem = p.stem

            # Set the loading guard to suppress save events during programmatic changes
            self._is_loading = True
            self.current_file_stem = stem
            try:
                self.settings["last_other_work"] = stem
            except (TypeError, KeyError):
                pass

            # Determine the last position from the per-file map; default to 0 if missing
            last_position = self._get_saved_position(stem)

            # OPTIONAL: for legacy positive saved values, reflect the target scroll while loading
            try:
                if isinstance(last_position, int) and last_position >= 0:
                    sb_now = self.text_edit.verticalScrollBar()
                    sb_now.setValue(int(last_position))
            except (AttributeError, RuntimeError, TypeError, ValueError):
                pass

            # Prepare async an incremental file load to keep the UI responsive
            from os import path as _ospath
            try:
                # Use the resolved absolute path for a reliable file size
                total = int(_ospath.getsize(abs_path))
            except (OSError, TypeError):
                total = 0

            # Show a progress footer with a neat message
            msg = f"Loading {stem}"
            self._show_progress(msg, total)

            # Open the file in binary and iterate in chunks via QTimer
            fp = open(abs_path, 'rb')
            self._load_fp = fp
            self._load_total = total
            self._load_read = 0
            self._load_chunks = []
            self._load_token += 1
            token = self._load_token

            # Apply per-file geometry early so the window positions correctly while loading
            self._apply_saved_geometry(stem)

            if self._load_timer is None:
                self._load_timer = QTimer(self)
            # Read approx 512KB per tick to balance responsiveness and speed
            chunk_size = 512 * 1024

            def _step():
                # If a new load started, abort this one
                if token != self._load_token:
                    try:
                        self._load_timer.stop()
                    except (RuntimeError, AttributeError):
                        pass
                    return
                try:
                    chunk = fp.read(chunk_size)
                except (OSError, ValueError) as _e:
                    # On read error, abort and show a message
                    try:
                        self._load_timer.stop()
                    except (RuntimeError, AttributeError):
                        pass
                    # Invalidate this load to prevent further reads on a handle that
                    # may already be closed and clear our reference.
                    try:
                        self._load_token += 1
                    except (AttributeError, TypeError):
                        pass
                    try:
                        fp.close()
                    except (OSError, ValueError):
                        pass
                    self._load_fp = None
                    self._hide_progress()
                    self.text_edit.setPlainText(f"Error loading file: {_e}")
                    # Clear loading state on error
                    self._is_loading_file = False
                    return

                if not chunk:
                    # Done. Assemble and display
                    try:
                        fp.close()
                    except (OSError, ValueError):
                        pass
                    # Prevent any further timer ticks from attempting to read this
                    # (now closed) file handle.
                    # Invalidate this load cycle and stop the timer immediately to
                    # avoid "read of closed file" errors.
                    try:
                        # Invalidate current token so any stray queued callbacks no-op
                        self._load_token += 1
                    except (AttributeError, TypeError):
                        pass
                    try:
                        if self._load_timer is not None:
                            self._load_timer.stop()
                            # Safely disconnect the connected timeout slot, if any
                            try:
                                if getattr(self, "_load_timeout_slot", None) is not None:
                                    self._load_timer.timeout.disconnect(self._load_timeout_slot)
                            except (RuntimeError, TypeError):
                                pass
                            self._load_timeout_slot = None
                    except (RuntimeError, AttributeError):
                        pass
                    # Null out the handle to signal EOF/closed state
                    self._load_fp = None
                    # Before heavy finalisation work begins (decode, setPlainText, highlighting),
                    # show the IO cap percentage and flush events so the UI reflects that loading
                    # is not yet complete.
                    try:
                        if getattr(self, "_load_total", 0) > 0:
                            self._set_progress_percent(getattr(self, "_io_progress_cap", 95))
                            try:
                                QCoreApplication.processEvents()
                            except (RuntimeError, AttributeError):
                                pass
                    except (RuntimeError, AttributeError, TypeError, ValueError):
                        pass
                    try:
                        content = b''.join(self._load_chunks).decode('utf-8', errors='replace')
                        # Normalise newlines so character offsets used for highlighting
                        # match Qt's internal document representation.
                        # Qt treats line breaks as a single character; binary decode preserves CRLF, so
                        # convert CRLF/CR to LF to avoid shifted highlights.
                        try:
                            content = content.replace('\r\n', '\n').replace('\r', '\n')
                        except (AttributeError, TypeError):
                            pass
                    except (ValueError, TypeError, AttributeError, MemoryError):
                        content = ''
                    self.text_edit.setPlainText(content)
                    self.setWindowTitle(stem)
                    # The content is now visible; complete and hide the progress UI immediately
                    try:
                        if getattr(self, "_load_total", 0) > 0:
                            self._set_progress_percent(100)
                    except (RuntimeError, AttributeError, TypeError, ValueError):
                        pass
                    self._hide_progress()

                    # Mark that we are restoring and suppress saves until finalising
                    self._pending_restore_stem = stem
                    self._pending_restore_value = int(last_position)

                    def _after_restore():
                        # After the content-anchored restore finalises, begin highlighting
                        try:
                            # If a precise char jump was requested during a load, apply it first
                            try:
                                pending_char = getattr(self, "_pending_jump_char", None)
                            except AttributeError:
                                pending_char = None
                            if isinstance(pending_char, int) and pending_char >= 0:
                                self._jump_to_char_now(int(pending_char))
                                self._pending_jump_char = None
                        
                            # Then attempt to load precomputed refs or fall back to live scan
                            if not self._try_load_precomputed_refs(p, content):
                                # Use the editor's text to guarantee offsets exactly match Qt's document
                                self._start_lazy_highlighting(self.text_edit.toPlainText())
                        except (RuntimeError, AttributeError, TypeError, ValueError):
                            pass
                        # If a jump to anchors was requested during a load, apply it now
                        try:
                            if isinstance(self._pending_jump_patterns, list) and self._pending_jump_patterns:
                                self._jump_to_anchors_now(self._pending_jump_patterns)
                                self._pending_jump_patterns = None
                        except (RuntimeError, AttributeError, TypeError, ValueError):
                            self._pending_jump_patterns = None
                        # Progress was already hidden when content became visible; keep as a safeguard
                        try:
                            if getattr(self, "_load_total", 0) > 0:
                                self._set_progress_percent(100)
                                try:
                                    QCoreApplication.processEvents()
                                except (RuntimeError, AttributeError):
                                    pass
                        except (RuntimeError, AttributeError, TypeError, ValueError):
                            pass
                        self._hide_progress()
                        try:
                            self._load_timer.stop()
                        except (RuntimeError, AttributeError):
                            pass
                        # Ensure the loading state is cleared after successful restore/finalise
                        self._is_loading_file = False

                    # Perform content-anchored restore first, then highlight via callback
                    self._restore_scroll_position_async(stem, last_position, on_done=_after_restore)
                    return

                # Accumulate and update progress
                self._load_chunks.append(chunk)
                self._load_read += len(chunk)
                if self._load_total > 0:
                    self._update_progress(self._load_read, self._load_total)

            # Disconnect any previously connected slot to avoid duplicates and warnings
            try:
                prev_slot = getattr(self, "_load_timeout_slot", None)
                if prev_slot is not None:
                    self._load_timer.timeout.disconnect(prev_slot)
            except (RuntimeError, TypeError):
                pass
            self._load_timeout_slot = None
            self._load_timer.setInterval(10)
            self._load_timer.timeout.connect(_step)
            # Remember the connected slot so we can disconnect it explicitly next time
            self._load_timeout_slot = _step
            self._load_timer.start()

            if hasattr(self, 'file_selector'):
                idx = self.file_selector.findText(stem)
                if 0 <= idx != self.file_selector.currentIndex():
                    self.file_selector.blockSignals(True)
                    self.file_selector.setCurrentIndex(idx)
                    self.file_selector.blockSignals(False)
        except FileNotFoundError:
            self.text_edit.setPlainText("Error: File not found.")
            self._hide_progress()
            self._is_loading_file = False
        except (OSError, UnicodeDecodeError, ValueError) as e1:
            self.text_edit.setPlainText(f"Error loading file: {e1}")
            self._hide_progress()
            self._is_loading_file = False

    # ---- Jump to text anchors (used by the Commentary button) ----
    def goto_text_anchors(self, anchors: list[str]) -> None:
        """Jump to the first occurrence of the given anchor strings.
        If a file is currently loading, queue the request and apply it after a load completes.
        Anchors are matched case-insensitively against the loaded text.
        """
        try:
            # If a load is in progress, queue the anchors to apply after restore/highlighting
            if getattr(self, "_is_loading_file", False):
                # Store a shallow copy to avoid external mutation
                try:
                    self._pending_jump_patterns = list(anchors) if isinstance(anchors, list) else []
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    self._pending_jump_patterns = []
                return
            # Otherwise, apply immediately
            self._jump_to_anchors_now(anchors)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    def _jump_to_anchors_now(self, anchors: list[str]) -> bool:
        """Internal helper to perform the jump immediately.
        Returns True if an anchor was found.
        Priority respects the order of anchors provided: the first anchor that matches anywhere
        in the document is used.
        This avoids accidentally jumping to an earlier generic heading
        (e.g. the first "Chapter 1" of a different book) when a more specific anchor appears later.
        """
        try:
            if not isinstance(anchors, list) or not anchors:
                return False
            text = self.text_edit.toPlainText()
            if not text:
                return False
            # Case-insensitive search; precompute a lowered copy
            low_text = text.lower()
            best_idx = -1
            for a in anchors:
                try:
                    if not a:
                        continue
                    idx = low_text.find(str(a).lower())
                    if idx != -1:
                        best_idx = idx
                        break
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    continue
            if best_idx == -1:
                return False
            # Move the cursor to the found index and make it visible
            try:
                cursor = self.text_edit.textCursor()
                cursor.setPosition(int(best_idx))
                self.text_edit.setTextCursor(cursor)
                self.text_edit.ensureCursorVisible()
                # Nudge the view a little up so the anchor is not the last line
                # by moving the cursor to the start of the block
                try:
                    block = self.text_edit.document().findBlock(int(best_idx))
                    if block and block.isValid():
                        c2 = self.text_edit.textCursor()
                        c2.setPosition(block.position())
                        self.text_edit.setTextCursor(c2)
                        self.text_edit.ensureCursorVisible()
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    pass
                return True
            except (RuntimeError, AttributeError, TypeError, ValueError):
                return False
        except (RuntimeError, AttributeError, TypeError, ValueError):
            return False

    # ---- Jump to a specific character offset (used by precise commentary index) ----
    def goto_char_offset(self, char_index: int) -> None:
        """Jump to a specific character index in the loaded document.
        If a file is loading, queue the request and apply it after a load completes.
        """
        try:
            if not isinstance(char_index, int) or char_index < 0:
                return
            if getattr(self, "_is_loading_file", False):
                self._pending_jump_char = int(char_index)
                return
            self._jump_to_char_now(int(char_index))
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    def _jump_to_char_now(self, char_index: int) -> bool:
        try:
            doc = self.text_edit.document()
            if doc is None:
                return False
            # Clamp to valid range
            try:
                total_chars = int(doc.characterCount())
            except (AttributeError, TypeError, ValueError):
                total_chars = 0
            if total_chars <= 0:
                return False
            pos = max(0, min(int(char_index), max(0, total_chars - 1)))
            c = self.text_edit.textCursor()
            c.setPosition(pos)
            self.text_edit.setTextCursor(c)
            # Scroll to make it visible
            self.text_edit.ensureCursorVisible()
            # Optional: align to the start of the block so the heading is visible
            try:
                blk = doc.findBlock(pos)
                if blk and blk.isValid():
                    c2 = self.text_edit.textCursor()
                    c2.setPosition(blk.position())
                    self.text_edit.setTextCursor(c2)
                    self.text_edit.ensureCursorVisible()
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass
            return True
        except (RuntimeError, AttributeError, TypeError, ValueError):
            return False

    def _try_load_precomputed_refs(self, text_path: Path, content: str) -> bool:
        """Attempt to load precomputed reference indices for the given text.
        Returns True if successfully loaded and applied; otherwise False to fall back to live scan.
        Validation ensures the companion matches the exact normalised content displayed.
        """
        # Compute hash of the exact normalised content (UTF-8 + LF) we just set
        try:
            import hashlib
            content_hash = hashlib.sha256(content.encode("utf-8", errors="replace")).hexdigest()
        except (ValueError, TypeError, AttributeError):
            return False

        # Candidate companion locations: alongside the text, then central folder
        try:
            base_name = text_path.name  # e.g. "Works of Jonathan Edwards Vol II.txt"
            same_dir_gz = text_path.parent / f"{base_name}.refs.json.gz"
            same_dir_json = text_path.parent / f"{base_name}.refs.json"
            central_dir = Path(sh.str_cwd) / "Other Works companions"
            central_gz = central_dir / f"{base_name}.refs.json.gz"
            central_json = central_dir / f"{base_name}.refs.json"
            candidates = [same_dir_gz, same_dir_json, central_gz, central_json]
        except (AttributeError, TypeError):
            return False

        path = None
        for c in candidates:
            try:
                if c.exists():
                    path = c
                    break
            except (OSError, ValueError):
                continue
        if path is None:
            return False

        # Ensure gzip/json are available
        try:
            import gzip  # type: ignore
            import json  # type: ignore
        except (ImportError, ModuleNotFoundError):
            return False

        # Load JSON (gzipped or plain)
        try:
            if str(path).lower().endswith(".gz"):
                with gzip.open(path, "rt", encoding="utf-8") as f:
                    data = json.load(f)
            else:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
        except (OSError, ValueError, AttributeError, json.JSONDecodeError):
            return False

        # Basic schema validation
        try:
            fmt_ok = int(data.get("format", 0)) == 1
        except (ValueError, TypeError, AttributeError):
            fmt_ok = False
        if not fmt_ok:
            return False
        try:
            if data.get("content_sha256") != content_hash:
                return False
        except (AttributeError, TypeError):
            return False

        refs = data.get("refs")
        if not isinstance(refs, list):
            return False

        # Cancel any currently scheduled highlighting work
        try:
            self._cancel_token += 1
            self._highlight_timer.stop()
        except (AttributeError, RuntimeError):
            pass
        self._whole_document_mode = False

        # Seed references and auxiliary structures
        self._all_references = []
        self._ref_index = set()
        self._extra_selections = []
        try:
            self.text_edit.setExtraSelections(self._extra_selections)
        except (AttributeError, RuntimeError):
            pass

        for r in refs:
            try:
                s = int(r.get("abs_start", 0))
                l = int(r.get("length", 0))
            except (ValueError, TypeError, AttributeError):
                continue
            self._all_references.append(
                {
                    "abs_start": s,
                    "length": l,
                    "book": r.get("book"),
                    "chapter": r.get("chapter"),
                    "verse": r.get("verse"),
                    "text": r.get("text", ""),
                }
            )
            self._ref_index.add((s, l))

        # Sort once for fast binary searches on hover/visible-range rebuild
        try:
            self._all_references.sort(key=lambda x: int(x.get("abs_start", 0)))
            self._refs_sorted = True
        except (ValueError, TypeError, AttributeError):
            self._refs_sorted = False
            self._ensure_refs_sorted()

        # Prepare line metrics for viewport computations
        self._lines = content.split("\n")
        self._line_offsets = []
        running = 0
        for ln in self._lines:
            self._line_offsets.append(running)
            running += len(ln) + 1

        # Build visible highlights immediately
        try:
            # Mark that references are available (even if none) so we don't rescan
            self._refs_scanned = True
            self._highlight_visible_now()
        except (RuntimeError, AttributeError, TypeError):
            return False
        return True

    def highlight_references(self):
        text = self.text_edit.toPlainText()
        self._start_lazy_highlighting(text)

    # ----------------------- Find dialog implementation -----------------------
    class _ReaderFindDialog(QDialog):
        def __init__(self, parent: "TextDocumentWindow") -> None:
            super().__init__(parent)
            self.setWindowTitle("Search")
            self.setModal(False)
            self._parent = parent
            self._last_term: str = ""

            lay = QHBoxLayout(self)
            self.edit = QLineEdit(self)
            self.edit.setPlaceholderText("Find in page…")
            self.edit.returnPressed.connect(parent.find_next)

            self.case_box = QCheckBox("Aa", self)
            self.case_box.setToolTip("Case sensitive")

            self.whole_box = QCheckBox("Whole", self)
            self.whole_box.setToolTip("Whole word only")

            self.prev_btn = QPushButton("Prev", self)
            self.prev_btn.clicked.connect(parent.find_prev)
            self.next_btn = QPushButton("Next", self)
            self.next_btn.clicked.connect(parent.find_next)

            lay.addWidget(self.edit)
            lay.addWidget(self.case_box)
            lay.addWidget(self.whole_box)
            lay.addWidget(self.prev_btn)
            lay.addWidget(self.next_btn)

            # Inherit the palette so it matches the dark/light theme
            try:
                self.setPalette(parent.text_edit.palette())
            except (AttributeError, RuntimeError, TypeError):
                pass

            # Make the text entry box twice as wide (initially) without hard-coding pixels.
            # Use the size hint as a baseline so it adapts to DPI and fonts.
            try:
                base_w = int(self.edit.sizeHint().width())
                # Ensure a reasonable lower bound in case the sizeHint is tiny
                min_w = max(300, base_w * 2)
                self.edit.setMinimumWidth(min_w)
            except (AttributeError, TypeError, ValueError, RuntimeError):
                # Fallback to a sensible minimum width
                self.edit.setMinimumWidth(360)

            # Ensure the line edit takes available extra space when the dialog is resized
            try:
                # Give the line edit stretch so it grows, keep others at default
                lay.setStretch(0, 1)
            except (AttributeError, TypeError, RuntimeError):
                pass

            # Load window geometry from settings
            try:
                ss = getattr(parent, "settings_service", None)
                if ss:
                    gx, gy, gw, gh = ss.get_window_geometry("reader_find_window")
                else:
                    gx, gy, gw, gh = fcs.get_window_geometry("reader_find_window")
                self.setGeometry(gx, gy, gw, gh)
            except (RuntimeError, TypeError, ValueError):
                pass

        def closeEvent(self, event):
            """Handle window close event - save geometry"""
            try:
                geometry = self.geometry()
                ss = getattr(self._parent, "settings_service", None)
                if ss:
                    ss.save_window_geometry(
                        "reader_find_window",
                        geometry.x(),
                        geometry.y(),
                        geometry.width(),
                        geometry.height(),
                    )
                else:
                    fcs.save_window_geometry(
                        "reader_find_window",
                        geometry.x(),
                        geometry.y(),
                        geometry.width(),
                        geometry.height(),
                    )
            except (RuntimeError, TypeError, ValueError):
                pass
            super().closeEvent(event)

        # Build proper QTextDocument find flags for QPlainTextEdit.find
        # Some PySide6 builds require QFlags<QTextDocument::FindFlag> rather than plain ints.
        def build_flags(self):
            try:
                # Start with a zero-value FindFlag if available; fall back to 0
                base = getattr(QTextDocument, "FindFlag", None)
                flags = base(0) if base is not None else 0
                if self.case_box.isChecked():
                    flags |= getattr(QTextDocument.FindFlag, "FindCaseSensitively", 0)
                if self.whole_box.isChecked():
                    flags |= getattr(QTextDocument.FindFlag, "FindWholeWords", 0)
                return flags
            except (AttributeError, TypeError, RuntimeError, ValueError):
                # Fallback to integer flags using helper if enums are unavailable
                f = 0
                try:
                    if self.case_box.isChecked():
                        f |= _qdoc_find_flag("FindCaseSensitively")
                    if self.whole_box.isChecked():
                        f |= _qdoc_find_flag("FindWholeWords")
                except (AttributeError, TypeError, RuntimeError, ValueError):
                    pass
                return f

    def _ensure_find_dialog(self) -> None:
        if getattr(self, "_find_dlg", None) is None:
            try:
                self._find_dlg = TextDocumentWindow._ReaderFindDialog(self)
            except (RuntimeError, TypeError):
                self._find_dlg = None

    def show_find_dialog(self) -> None:
        self._ensure_find_dialog()
        dlg = self._find_dlg
        if not dlg:
            return
        try:
            dlg.show()
            dlg.raise_()
            dlg.activateWindow()
            dlg.edit.setFocus()
            dlg.edit.selectAll()
        except (RuntimeError, AttributeError):
            pass

    def _maybe_close_find_dialog(self) -> None:
        dlg = getattr(self, "_find_dlg", None)
        if dlg and dlg.isVisible():
            try:
                dlg.hide()
                self.text_edit.setFocus()
            except (RuntimeError, AttributeError):
                pass

    def _do_find(self, forward: bool = True) -> None:
        dlg = self._find_dlg
        if not dlg:
            return
        try:
            term = dlg.edit.text()
        except (RuntimeError, AttributeError):
            term = ""
        if not term:
            return

        flags = dlg.build_flags()
        if not forward:
            try:
                flags |= getattr(QTextDocument.FindFlag, "FindBackward", _qdoc_find_flag("FindBackward"))
            except (AttributeError, TypeError, RuntimeError, ValueError):
                # Keep whatever we have
                pass

        # If term changed, restart from beginning/end
        last_term = getattr(dlg, "_last_term", "")
        if term != last_term:
            try:
                dlg._last_term = term
                cursor = self.text_edit.textCursor()
                if forward:
                    cursor.setPosition(0)
                else:
                    doc = self.text_edit.document()
                    cursor.setPosition(doc.characterCount() - 1)
                self.text_edit.setTextCursor(cursor)
            except (RuntimeError, AttributeError):
                pass

        # Try to find; if not found (or an error occurs), wrap once and try again
        try:
            # Pass proper flags to find(); avoid casting to Any to keep types compatible
            if not self.text_edit.find(term, flags):
                cursor = self.text_edit.textCursor()
                if forward:
                    cursor.setPosition(0)
                else:
                    doc = self.text_edit.document()
                    cursor.setPosition(doc.characterCount() - 1)
                self.text_edit.setTextCursor(cursor)
                self.text_edit.find(term, flags)
        except (RuntimeError, AttributeError, TypeError):
            # Silently ignore lifecycle/type errors from Qt objects
            pass
        try:
            self.text_edit.ensureCursorVisible()
        except (RuntimeError, AttributeError):
            pass

    def find_next(self) -> None:
        self._do_find(True)

    def find_prev(self) -> None:
        self._do_find(False)

    def _start_lazy_highlighting(self, content: str) -> None:
        self._cancel_token += 1
        token = self._cancel_token

        # Reset state
        self._all_references.clear()
        self._ref_index.clear()
        self._refs_sorted = True
        self._extra_selections = []
        self.text_edit.setExtraSelections(self._extra_selections)
        # We're about to (re)scan the whole document: mark as scanned to avoid re-entry
        # If no refs are found, we keep this True so we don't rescan endlessly.
        self._refs_scanned = True

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

        # Mark scanning complete, even if no references were found
        self._refs_scanned = True
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
        if hasattr(self, '_popup_helper') and isinstance(self._popup_helper, SimpleScripturePopup):
            try:
                self._popup_helper.move_to(self.text_edit, pos, y_offset=y_offset)
                return
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass
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
            # Only kick off a whole-document scan once per document
            if not getattr(self, "_refs_scanned", False):
                text = self.text_edit.toPlainText()
                if text:
                    self._start_lazy_highlighting(text)
            return

        # Reset and rebuild only visible selections from precomputed absolute references
        self._extra_selections = []

        # Expand the visible range a bit to avoid edge flicker
        visible_start = max(0, top_pos)
        visible_end = bot_pos

        # Ensure refs sorted once
        self._ensure_refs_sorted()

        refs = self._all_references

        # Binary search to find the first reference near the visible start
        lo, hi = 0, len(refs) - 1
        start_idx = 0
        # Use a larger buffer (100 chars) to ensure references that start off-screen
        # but span into the viewport are caught.
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
            elif pos >= end:
                lo = mid + 1
            else:
                return r
        return None

    def _get_ref_vertical_range(self, ref: Dict[str, Any]) -> tuple[int, int]:
        """Return the (top, bottom) global Y coordinates of the reference."""
        start = ref.get('abs_start', 0)
        length = ref.get('length', 0)
        
        cursor = QTextCursor(self.text_edit.document())
        cursor.setPosition(start)
        rect_start = self.text_edit.cursorRect(cursor)
        cursor.setPosition(start + length)
        rect_end = self.text_edit.cursorRect(cursor)
        
        viewport = self.text_edit.viewport()
        top = viewport.mapToGlobal(rect_start.topLeft()).y()
        bottom = viewport.mapToGlobal(rect_end.bottomLeft()).y()
        return min(top, bottom), max(top, bottom)

    def _check_popup_overlap(self, ref: Dict[str, Any], pos: QPoint, text: str) -> bool:
        """Check if the popup at current position would overlap the reference."""
        # Check if the feature is disabled in settings
        if not self.settings.get("reader_auto_scroll_popups", True):
            return False

        if not hasattr(self, '_popup_helper') or not self._popup_helper:
            # Lazily initialise if needed for prediction
            from ui_helpers import SimpleScripturePopup
            self._popup_helper = SimpleScripturePopup()
            
        px, py, pw, ph = self._popup_helper.predict_geometry(
            self.text_edit, text, pos, self.text_edit.font()
        )
        ref_top, ref_bottom = self._get_ref_vertical_range(ref)
        
        # Check the vertical intersection between popup range [py, py+ph] and ref range [ref_top, ref_bottom]
        return max(py, ref_top) < min(py + ph, ref_bottom)

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
            self._stop_auto_scroll()
            self._pending_hover_pos = None
            self.closePopup()
        elif event.type() == QEvent.Type.MouseButtonPress:
            self._stop_auto_scroll()
            # Handle clicks on highlighted references to open them in the main Bible window
            try:
                if isinstance(event, QMouseEvent):
                    pos = event.position().toPoint()
                else:
                    pos = QPoint(0, 0)
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
            if isinstance(event, QMouseEvent):
                pos = event.position().toPoint()
            else:
                return super().eventFilter(obj, event)
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
        elif event.type() == QEvent.Type.Wheel:
            # If the popup helper is showing a long reference, scroll it instead of the document
            if hasattr(self, '_popup_helper') and isinstance(self._popup_helper, SimpleScripturePopup):
                try:
                    if self._popup_helper.is_visible() and isinstance(event, QWheelEvent):
                        # Forward the vertical delta
                        self._popup_helper.scroll_by(event.angleDelta().y())
                        return True
                except (RuntimeError, AttributeError):
                    pass
        return super().eventFilter(obj, event)

    def handle_hover(self, pos: QPoint):
        # Convert a stored mouse position to a cursor and document position
        cursor = self.text_edit.cursorForPosition(pos)
        position = cursor.position()
        hovered_reference = self._ref_at_position(position)

        if hovered_reference is None:
            self._stop_auto_scroll()
            self.closePopup()
            self.current_reference = None
            return

        same_reference = (
            self.current_reference is not None and
            self.current_reference.get("abs_start") == hovered_reference.get("abs_start") and
            self.current_reference.get("length") == hovered_reference.get("length")
        )

        # If over a valid reference, check for overlap before showing
        scriptures, canonical = self.get_scripture(hovered_reference)
        scriptur = scriptures + "\n" + canonical + " KJV"
        
        if self._check_popup_overlap(hovered_reference, pos, scriptur):
            if not self._auto_scroll_timer.isActive() and not self._auto_scroll_delay_timer.isActive():
                self._scrolling_reference = hovered_reference
                # Store character position under the mouse to allow "sticking"
                self._last_mouse_char_pos = self.text_edit.cursorForPosition(pos).position()
                self._auto_scroll_delay_timer.start()
            return

        # No overlap: stop any scrolling and show popup normally
        self._stop_auto_scroll()

        # Check if the helper or legacy is already visible for this reference
        if same_reference:
            is_any_visible = False
            if hasattr(self, '_popup_helper') and self._popup_helper:
                try:
                    is_any_visible = self._popup_helper.is_visible()
                except (RuntimeError, AttributeError):
                    pass
            
            if not is_any_visible and self.popup_window and self.popup_window.isVisible():
                is_any_visible = True
                
            if is_any_visible:
                self._move_popup_to_cursor(pos, y_offset=60)
                return

        # New reference or popup hidden: update and show
        self.current_reference = hovered_reference
        scriptures, canonical = self.get_scripture(hovered_reference)
        scriptur = scriptures + "\n" + canonical + " KJV"

        # Use the shared popup helper for consistent behaviour and look
        if not hasattr(self, '_popup_helper') or not isinstance(self._popup_helper, SimpleScripturePopup):
            self._popup_helper = SimpleScripturePopup()
        
        # Ensure the legacy popup is closed before showing the helper to avoid "double blue box"
        if self.popup_window:
            try:
                self.popup_window.close()
                self.popup_window = None
            except (RuntimeError, AttributeError):
                pass

        try:
            is_dark = self.settings.get("theme", "Light") == "Dark"
            self._popup_helper.show(self.text_edit, scriptur, pos, self.text_edit.font(), is_dark=is_dark)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            # Fallback to the legacy widget path if helper fails
            is_dark = self.settings.get("theme", "Light") == "Dark"
            self.popup_window = QWidget()
            self.popup_window.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
            bg = "#121212" if is_dark else "#ffffff"
            border = "#2a5adf" if is_dark else "#2160FF"
            fg = "#f0f0f0" if is_dark else "#000000"
            self.popup_window.setStyleSheet(f"background-color: {bg}; border: 2px solid {border};")
            label = QLabel(scriptur, self.popup_window)
            label.setFont(self.text_edit.font())
            label.setWordWrap(True)
            label.setFixedWidth(self.text_edit.width())
            label.setStyleSheet(f"color: {fg}; border: none;")
            label.adjustSize()
            layout = QVBoxLayout(self.popup_window)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(label)
            self.popup_window.adjustSize()
            self._move_popup_to_cursor(pos, y_offset=60)
            self.popup_window.show()

    def closePopup(self):
        # Prefer the shared helper
        if hasattr(self, '_popup_helper') and isinstance(self._popup_helper, SimpleScripturePopup):
            try:
                self._popup_helper.hide()
            except (RuntimeError, AttributeError):
                pass
        if self.popup_window and self.popup_window.isVisible():
            self.popup_window.close()
            self.popup_window = None

    def _start_auto_scroll(self):
        self._auto_scroll_timer.start()

    def _do_auto_scroll(self):
        from PySide6.QtGui import QCursor
        if not self._scrolling_reference:
            self._stop_auto_scroll()
            return
            
        vbar = self.text_edit.verticalScrollBar()
        old_val = vbar.value()
        # Scroll text UP (increase scroll value) to bring reference to the top
        vbar.setValue(old_val + 2)
        
        if vbar.value() == old_val: # Reached end
            self._stop_auto_scroll()
            return

        # Make the mouse "stick" to the reference text
        if self._last_mouse_char_pos >= 0:
            cursor = QTextCursor(self.text_edit.document())
            cursor.setPosition(self._last_mouse_char_pos)
            new_rect = self.text_edit.cursorRect(cursor)
            new_global_pos = self.text_edit.viewport().mapToGlobal(new_rect.center())
            QCursor.setPos(new_global_pos)
            
            # Check if the popup can now be shown
            pos_viewport = self.text_edit.viewport().mapFromGlobal(new_global_pos)
            scriptures, canonical = self.get_scripture(self._scrolling_reference)
            if not self._check_popup_overlap(self._scrolling_reference, pos_viewport, scriptures + "\n" + canonical + " KJV"):
                self._stop_auto_scroll()
                self.handle_hover(pos_viewport)

    def _stop_auto_scroll(self):
        self._auto_scroll_timer.stop()
        self._auto_scroll_delay_timer.stop()
        self._scrolling_reference = None

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
