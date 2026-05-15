# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations
from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QDialog,
    QWidget,
    QLabel,
    QVBoxLayout,
    QScrollArea,
)
import abib.utils as utils

def get_screen_size() -> tuple[int, int]:
    return utils.get_screen_size()

def _center_on_screen(width: int, height: int) -> tuple[int, int]:
    return utils.center_on_screen(width, height)

def _fit_to_screen(width: int, height: int) -> tuple[int, int]:
    return utils.fit_to_screen(width, height)

class NoZoomPlainTextEdit(QPlainTextEdit):
    def wheelEvent(self, event):
        # Block zoom when Ctrl is pressed
        if Qt.KeyboardModifier.ControlModifier in event.modifiers():
            event.ignore()
            return
        # Allow normal scrolling
        super().wheelEvent(event)


def center_on_screen(width: int, height: int) -> tuple[int, int]:
    """Return top-left coordinates to centre a window of (width,height) on the primary screen."""
    return _center_on_screen(width, height)


def fit_to_screen(window_width: int, window_height: int) -> tuple[int, int]:
    """Shrink window size to fit within the current screen with a small margin."""
    return _fit_to_screen(window_width, window_height)


class NoZoomDialog(QDialog):
    def eventFilter(self, obj, event):
        # Block Ctrl+Wheel events on any child widget
        if event.type() == QEvent.Type.Wheel:
            if Qt.KeyboardModifier.ControlModifier in event.modifiers():
                event.ignore()
                return True
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        # Install event filter on all child widgets when a dialog is shown
        super().showEvent(event)
        for child in self.findChildren(QWidget):
            child.installEventFilter(self)


class SimpleScripturePopup:
    """Lightweight scrollable tooltip popup used by both Other Works and Gill windows.

    Provides identical look and behaviour:
    - ToolTip window with a blue border
    - QScrollArea to handle long content without screen overflow
    - QLabel with word wrap, width matched to the host editor's width
    - Positioning near the text cursor for a given mouse position
    - No mouse interaction (transparent to the pointer)
    """

    def __init__(self) -> None:
        self._widget: QWidget | None = None
        self._text: QLabel | None = None
        self._scroll: QScrollArea | None = None
        self._is_dark: bool | None = None

    def ensure_created(self) -> None:
        if self._widget is None:
            # Use ToolTip + Frameless to avoid native frame double-borders
            self._widget = QWidget(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
            assert self._widget is not None
            self._widget.setObjectName("ScripturePopup")
            # Default stylesheet (will be updated by apply_theme)
            self._widget.setStyleSheet("#ScripturePopup { background-color: #ffffff; border: 2px solid #2160FF; }")
            try:
                self._widget.setContentsMargins(0, 0, 0, 0)
            except (RuntimeError, AttributeError):
                pass
            lay = QVBoxLayout(self._widget)
            lay.setContentsMargins(0, 0, 0, 0)

            # Scroll area for long references
            self._scroll = QScrollArea(self._widget)
            assert self._scroll is not None
            self._scroll.setWidgetResizable(True)
            self._scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            # Ensure the scroll area doesn't have its own background/border
            self._scroll.setStyleSheet("background: transparent; border: none;")

            # Use a QLabel (non-interactive) for the text
            self._text = QLabel()
            assert self._text is not None
            try:
                self._text.setWordWrap(True)
                self._text.setContentsMargins(6, 4, 6, 4)
                # Ensure the text is readable; will be updated by apply_theme
                self._text.setStyleSheet("color: #000000; background: transparent; border: none;")
                try:
                    self._widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                except (RuntimeError, AttributeError):
                    pass
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass
            
            self._scroll.setWidget(self._text)
            lay.addWidget(self._scroll)

    def apply_theme(self, is_dark: bool) -> None:
        """Update the popup colours to match the theme (dark or light)."""
        self.ensure_created()
        if self._is_dark == is_dark:
            return
        self._is_dark = is_dark
        
        if is_dark:
            # Match ThemeManager dark palette: Window/Base #121212, WindowText/Text #f0f0f0, Highlight #2a5adf
            bg = "#121212"
            fg = "#f0f0f0"
            border = "#2a5adf"
        else:
            # Match ThemeManager light palette: Window #ffffff, Text #000000, Highlight #cce8ff
            bg = "#ffffff"
            fg = "#000000"
            border = "#2160FF" # Keep the distinctive blue for light mode

        try:
            if self._widget:
                self._widget.setStyleSheet(f"""
                    #ScripturePopup {{
                        background-color: {bg};
                        border: 2px solid {border};
                    }}
                """)
            if self._text:
                self._text.setStyleSheet(f"color: {fg}; background: transparent; border: none;")
        except (RuntimeError, AttributeError):
            pass

    def show(self, host_editor: QWidget, text: str, pos: QPoint, font, is_dark: bool | None = None) -> None:
        self.ensure_created()
        assert self._widget is not None and self._text is not None and self._scroll is not None
        
        # Determine theme if not provided
        if is_dark is None:
            try:
                # Heuristic: check if the text colour is lighter than the background
                pal = host_editor.palette()
                bg = pal.color(host_editor.backgroundRole())
                is_dark = bg.lightness() < 128
            except (RuntimeError, AttributeError):
                is_dark = False
        
        self.apply_theme(is_dark)

        # Only update text if it changed to avoid layout churn
        try:
            if self._text.text() != text:
                self._text.setText(text)
        except (RuntimeError, AttributeError):
            pass

        try:
            self._text.setFont(font)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

        # Match the width of the host editor
        try:
            w = host_editor.width()
            self._widget.setFixedWidth(w)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            w = 400  # Default fallback width
            
        # Limit height to avoid covering too much screen (max 60% of screen height)
        try:
            screen_w, screen_h = get_screen_size()
            max_h = int(screen_h * 0.6)
        except (RuntimeError, AttributeError):
            max_h = 600

        # Determine target height based on content
        try:
            # Use heightForWidth to get the required height for the given width.
            # The inner width available for content is w - 4 (due to 2px borders).
            hfw = self._text.heightForWidth(w - 4)
            if hfw < 0:
                # Fallback to sizeHint if heightForWidth is not supported (though QLabel supports it)
                hfw = self._text.sizeHint().height()

            # Account for 2px border on top and bottom (total 4px)
            needed_h = hfw + 4
            
            if needed_h > max_h:
                self._widget.setFixedHeight(max_h)
            else:
                # Set to the exact necessary height
                self._widget.setFixedHeight(needed_h)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            # Fallback to previous behaviour if calculation fails
            try:
                self._widget.adjustSize()
                if self._widget.height() > max_h:
                    self._widget.setFixedHeight(max_h)
            except (RuntimeError, AttributeError):
                pass

        # Position after final sizing so flip/clamp uses the final height
        self.move_to(host_editor, pos)
        try:
            self._widget.show()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    @staticmethod
    def _calculate_position(host_editor: QWidget, pos: QPoint, popup_h: int, y_offset: int = 60) -> tuple[int, int]:
        """Shared logic to calculate (x, y) coordinates for the popup."""
        try:
            # host_editor is a QTextEdit/QPlainTextEdit
            cursor = getattr(host_editor, 'cursorForPosition')(pos)
            rect = getattr(host_editor, 'cursorRect')(cursor)
            global_tl = host_editor.mapToGlobal(rect.topLeft())
            editor_tl = host_editor.mapToGlobal(host_editor.rect().topLeft())
            editor_br = host_editor.mapToGlobal(host_editor.rect().bottomRight())

            popup_x = editor_tl.x()
            popup_y = global_tl.y() + y_offset

            if (editor_br.y() - popup_y - popup_h) < 0:
                popup_y = global_tl.y() - y_offset - popup_h

            min_y = int(editor_tl.y())
            max_y = int(editor_br.y()) - popup_h
            if max_y < min_y:
                max_y = min_y
            popup_y = max(min_y, min(popup_y, max_y))

            return int(popup_x), int(popup_y)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            # Fallback
            try:
                editor_tl = host_editor.mapToGlobal(host_editor.rect().topLeft())
                return editor_tl.x(), editor_tl.y()
            except (RuntimeError, AttributeError, TypeError, ValueError):
                return 0, 0

    def predict_geometry(self, host_editor: QWidget, text: str, pos: QPoint, font) -> tuple[int, int, int, int]:
        """Calculate where the popup would be positioned and its size without showing it."""
        self.ensure_created()
        
        # 1. Calculate width matched to the editor
        try:
            w = host_editor.width()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            w = 400
            
        # 2. Calculate height based on content
        try:
            screen_w, screen_h = get_screen_size()
            max_h = int(screen_h * 0.6)
            
            # Temporarily set text/font to measure
            if self._text:
                old_text = self._text.text()
                old_font = self._text.font()
                self._text.setText(text)
                self._text.setFont(font)
                hfw = self._text.heightForWidth(w - 4)
                if hfw < 0:
                    hfw = self._text.sizeHint().height()
                popup_h = min(hfw + 4, max_h)
                # Restore
                self._text.setText(old_text)
                self._text.setFont(old_font)
            else:
                popup_h = 200
        except (RuntimeError, AttributeError, TypeError, ValueError):
            popup_h = 200
            
        # 3. Calculate position
        popup_x, popup_y = SimpleScripturePopup._calculate_position(host_editor, pos, popup_h)
        return popup_x, popup_y, w, popup_h

    def scroll_by(self, delta_y: int) -> None:
        """Scroll the internal area by a pixel delta (forwarded from host)."""
        if self._scroll is not None:
            try:
                bar = self._scroll.verticalScrollBar()
                if bar and bar.isVisible():
                    bar.setValue(bar.value() - delta_y)
            except (RuntimeError, AttributeError):
                pass

    def move_to(self, host_editor: QWidget, pos: QPoint, y_offset: int = 60) -> None:
        if self._widget is None:
            return
        # Compute target position based on cursor rect and editor origin
        try:
            # Measure popup height safely
            try:
                popup_h = int(self._widget.height())
            except (RuntimeError, AttributeError, TypeError, ValueError):
                popup_h = 0

            popup_x, popup_y = SimpleScripturePopup._calculate_position(host_editor, pos, popup_h, y_offset)
            self._widget.move(popup_x, popup_y)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    def hide(self) -> None:
        if self._widget is not None:
            try:
                self._widget.hide()
            except (RuntimeError, AttributeError):
                pass
            # Do not delete this; reuse across hovers
            
    def is_visible(self) -> bool:
        """Return True if the popup widget exists and is currently visible."""
        try:
            return bool(self._widget is not None and self._widget.isVisible())
        except (RuntimeError, AttributeError):
            return False
