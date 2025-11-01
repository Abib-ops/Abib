# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtCore import Qt, QEvent
from PySide6.QtWidgets import QPlainTextEdit, QDialog, QWidget
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
