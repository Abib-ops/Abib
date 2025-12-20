# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtCore import Qt, QEvent, QPoint
from PySide6.QtWidgets import QPlainTextEdit, QDialog, QWidget, QLabel, QVBoxLayout
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
        self._label: QLabel | None = None

    def ensure_created(self) -> None:
        if self._widget is None:
            self._widget = QWidget(None, Qt.WindowType.ToolTip)
            try:
                self._widget.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass
            self._widget.setStyleSheet("border: 2px solid blue;")
            lay = QVBoxLayout(self._widget)
            lay.setContentsMargins(0, 0, 0, 0)
            self._label = QLabel(self._widget)
            self._label.setWordWrap(True)
            lay.addWidget(self._label)

    def show(self, host_editor: QWidget, text: str, pos: QPoint, font) -> None:
        self.ensure_created()
        assert self._widget is not None and self._label is not None
        try:
            self._label.setFont(font)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        self._label.setText(text)
        # Match the width of the host editor for readability
        try:
            self._label.setFixedWidth(host_editor.width())
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        try:
            self._widget.adjustSize()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
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
            popup_x = editor_tl.x()
            popup_y = global_tl.y() + y_offset
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
