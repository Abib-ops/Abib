# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtWidgets import (
    QPlainTextEdit,
    QDialog,
    QWidget,
    QLabel,
    QVBoxLayout,
    QTextEdit,
)
from PySide6.QtGui import QGuiApplication
import math
import fcs


class NoZoomPlainTextEdit(QPlainTextEdit):
    def wheelEvent(self, event):
        # Block zoom when Ctrl is pressed
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            event.ignore()
            return
        # Allow normal scrolling
        super().wheelEvent(event)


def center_on_screen(width: int, height: int) -> tuple[int, int]:
    """Return top-left coordinates to centre a window of (width,height) on the primary screen."""
    screen_w, screen_h = fcs.get_screen_size()
    w_origin = max(0, int((screen_w - width) / 2))
    h_origin = max(0, int((screen_h - height) / 2))
    return w_origin, h_origin


def fit_to_screen(window_height: int, window_width: int) -> tuple[int, int]:
    """Shrink window size to fit within the current screen with a small margin."""
    screen_w, screen_h = fcs.get_screen_size()
    if window_height > screen_h:
        window_height = int(screen_h * 0.95)
    if window_width > screen_w:
        window_width = int(screen_w * 0.95)
    return window_height, window_width


class NoZoomDialog(QDialog):
    def eventFilter(self, obj, event):
        # Block Ctrl+Wheel events on any child widget
        if event.type() == QEvent.Type.Wheel:
            if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
                event.ignore()
                return True
        return super().eventFilter(obj, event)

    def showEvent(self, event):
        # Install event filter on all child widgets when a dialog is shown
        super().showEvent(event)
        for child in self.findChildren(QWidget):
            child.installEventFilter(self)


class SimpleScripturePopup:
    """Lightweight tooltip-like popup used by both Other Works and Gill windows.

    Provides identical look and behavior:
    - ToolTip window with blue border
    - QLabel with word wrap, width matched to the host editor's width
    - Positioning near the text cursor for a given mouse position
    - No mouse interaction (transparent to the pointer)
    """

    def __init__(self) -> None:
        self._widget: QWidget | None = None
        self._text: QLabel | None = None

    def ensure_created(self) -> None:
        if self._widget is None:
            # Use a standard ToolTip window (with native frame)
            self._widget = QWidget(None, Qt.WindowType.ToolTip)
            # Keep a simple stylesheet border; native frame may result in a double outline as before
            self._widget.setStyleSheet("border: 2px solid #2160FF;")
            try:
                self._widget.setContentsMargins(0, 0, 0, 0)
            except Exception:
                pass
            lay = QVBoxLayout(self._widget)
            lay.setContentsMargins(0, 0, 0, 0)
            # Use a QLabel (non-interactive) as in the pre-selection state
            self._text = QLabel(self._widget)
            try:
                self._text.setWordWrap(True)
                try:
                    self._text.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                except Exception:
                    pass
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass
            lay.addWidget(self._text)

    def show(self, host_editor: QWidget, text: str, pos: QPoint, font) -> None:
        self.ensure_created()
        assert self._widget is not None and self._text is not None
        try:
            self._text.setFont(font)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            self._text.setText(text)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        # Match the width of the host editor and let QLabel compute its own height
        try:
            self._text.setFixedWidth(host_editor.width())
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            self._widget.adjustSize()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        # Position after final sizing so flip/clamp uses the final height
        self.move_to(host_editor, pos)
        try:
            self._widget.show()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

    def move_to(self, host_editor: QWidget, pos: QPoint, y_offset: int = 60) -> None:
        if self._widget is None:
            return
        # Compute target position based on cursor rect and editor origin
        try:
            # host_editor is a QTextEdit/QPlainTextEdit; both implement cursorForPosition/cursorRect
            cursor = getattr(host_editor, 'cursorForPosition')(pos)
            rect = getattr(host_editor, 'cursorRect')(cursor)
            global_tl = host_editor.mapToGlobal(rect.topLeft())
            editor_tl = host_editor.mapToGlobal(host_editor.rect().topLeft())
            editor_br = host_editor.mapToGlobal(host_editor.rect().bottomRight())
            popup_x = editor_tl.x()

            # Measure popup height safely
            try:
                popup_h = int(self._widget.height())
            except (RuntimeError, AttributeError, TypeError, ValueError):
                popup_h = 0

            # Default: position below the cursor
            popup_y = global_tl.y() + y_offset

            # If there isn't enough space below, flip above the cursor
            try:
                space_below = int(editor_br.y()) - int(popup_y) - int(popup_h)
            except (RuntimeError, AttributeError, TypeError, ValueError):
                space_below = 0
            if space_below < 0:
                # Place above the cursor using the same offset distance
                popup_y = global_tl.y() - y_offset - popup_h

            # Clamp Y within the visible editor bounds so the popup never renders off-screen
            min_y = int(editor_tl.y())
            max_y = int(editor_br.y()) - popup_h
            if max_y < min_y:
                # Degenerate case: ensure at least min_y
                max_y = min_y
            popup_y = max(min_y, min(popup_y, max_y))

            self._widget.move(popup_x, popup_y)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            # Fallback: place at editor's top-left
            try:
                editor_tl = host_editor.mapToGlobal(host_editor.rect().topLeft())
                self._widget.move(editor_tl)
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
