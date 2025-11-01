# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QSpacerItem,
    QSizePolicy,
    QPushButton,
)

import fcs
from ui_helpers import NoZoomDialog, center_on_screen, fit_to_screen


class SecondaryWindow(NoZoomDialog):
    def __init__(
        self,
        text: str,
        navigate_left_cb: Callable[[], None] | None = None,
        navigate_right_cb: Callable[[], None] | None = None,
    ):
        """
        Initialise the secondary window to display text.
        :param text: The text to display in the window.
        :param navigate_left_cb: Callback invoked when the left arrow is clicked.
        :param navigate_right_cb: Callback invoked when the right arrow is clicked.
        """
        super().__init__()

        if not isinstance(text, str):
            raise ValueError(f"Expected a string for 'text', but got {type(text).__name__}")

        # Load window geometry from settings
        x7, y7, width7, height7 = fcs.get_window_geometry("devotional_window")

        # Window setup
        self.setWindowTitle("C H Spurgeon's Morning and Evening Readings")
        self.setGeometry(x7, y7, width7, height7)

        self.text = text
        self._navigate_left_cb = navigate_left_cb
        self._navigate_right_cb = navigate_right_cb

        # Load font size from settings
        try:
            self.fontsize = fcs.get_devotional_font_size()
        except (TypeError, ValueError, OSError) as e7:
            print(f"Failed to load font size: {e7}")
            self.fontsize = 14  # fallback default

        # Text display
        self.text_display = QPlainTextEdit()
        self.text_display.setPlainText(text)
        self.text_display.setReadOnly(True)

        # Create keyboard shortcuts for font size changes
        self.create_font_shortcuts()

        # Set an initial font
        self.update_font()

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.text_display)

        # Create a container for buttons
        button_layout = QHBoxLayout()

        # Add a spacer to push buttons to the right
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        button_layout.addSpacerItem(spacer)

        # Left navigation button
        self.left_button: QPushButton = QPushButton("←", self)
        self.left_button.setFixedSize(30, 30)
        if self._navigate_left_cb:
            self.left_button.clicked.connect(self._navigate_left_cb)
        button_layout.addWidget(self.left_button)

        # Right navigation button
        self.right_button: QPushButton = QPushButton("→", self)
        self.right_button.setFixedSize(30, 30)
        if self._navigate_right_cb:
            self.right_button.clicked.connect(self._navigate_right_cb)
        button_layout.addWidget(self.right_button)

        # Add the button layout to the main layout
        layout.addLayout(button_layout)
        self.setLayout(layout)

    def create_font_shortcuts(self):
        """Create keyboard shortcuts for font size changes"""
        # Ctrl++ to increase font size
        increase_shortcut = QKeySequence("Ctrl++")
        self.addAction(self._make_shortcut(increase_shortcut, self.increase_font_size))

        # Ctrl+= alternative
        increase_alt = QKeySequence("Ctrl+=")
        self.addAction(self._make_shortcut(increase_alt, self.increase_font_size))

        # Ctrl+- to decrease font size
        decrease_shortcut = QKeySequence("Ctrl+-")
        self.addAction(self._make_shortcut(decrease_shortcut, self.decrease_font_size))

    def _make_shortcut(self, seq: QKeySequence, slot):
        from PySide6.QtGui import QShortcut
        sc = QShortcut(seq, self)
        sc.activated.connect(slot)
        return sc

    def increase_font_size(self):
        """Increase font size"""
        self.fontsize = min(72, self.fontsize + 1)
        self.update_font()

    def decrease_font_size(self):
        """Decrease font size"""
        self.fontsize = max(6, self.fontsize - 1)
        self.update_font()

    def update_font(self):
        """Update the text widget font and immediately save to settings"""
        font: QFont = QFont("Cascadia Mono", self.fontsize, QFont.Weight.Medium)
        self.text_display.setFont(font)

        # Save font size to settings
        try:
            fcs.update_devotional_font_size(self.fontsize)
        except (PermissionError, OSError, ValueError, TypeError) as e5:
            print(f"Failed to save font size: {e5}")

    def closeEvent(self, event):
        """Handle window close event - save geometry"""
        geometry = self.geometry()
        fcs.save_window_geometry(
            "devotional_window",
            geometry.x(),
            geometry.y(),
            geometry.width(),
            geometry.height(),
        )
        event.accept()

    def update_content(self, new_text: str) -> None:
        """Updates the displayed content of the secondary window."""
        self.text_display.setPlainText(new_text)

    def apply_theme(self, is_dark_mode: bool):
        """Apply light or dark theme to the text_display widget."""
        if is_dark_mode:
            self.text_display.setStyleSheet(
                """
                QPlainTextEdit {
                    background-color: #121212;
                    color: #ffffff;
                }
                """
            )
        else:
            self.text_display.setStyleSheet(
                """
                QPlainTextEdit {
                    background-color: #ffffff;
                    color: #000000;
                }
                """
            )


class AboutWindow(QMainWindow):
    def __init__(self, version_text: str):
        super().__init__()
        self.setWindowTitle(version_text)

        self.resize(480, 810)
        self.content = None

        # Create a QLabel widget
        label = QLabel(self)
        self.label = label

        # Load About.txt content
        self.content = self.about()

        # Set the contents of the QLabel
        label.setText(self.content)

        # Center align content
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        fontsize = 14
        fixedfont: QFont = QFont("Cascadia Mono", fontsize, QFont.Weight.Bold)
        label.setFont(fixedfont)

        # Set the QLabel as the central widget
        from PySide6.QtWidgets import QWidget
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.addWidget(label)
        self.setCentralWidget(container)

    def about(self) -> str:
        """Load the 'About' content from ABOUT.txt and set geometry."""
        content: str = ""
        try:
            with open("ABOUT.txt", "r", encoding="utf-8") as file_about:
                content = file_about.read()
        except FileNotFoundError:
            content = "ABOUT.txt file not found."
        except UnicodeDecodeError:
            content = "Error: Unable to decode ABOUT.txt. Please make sure the file encoding is UTF-8."

        winwidth: int = 480
        winheight: int = 810

        # Fit and center for small screens
        winheight, winwidth = fit_to_screen(winheight, winwidth)
        w_origin, h_origin = center_on_screen(winwidth, winheight)
        self.setGeometry(w_origin, h_origin, winwidth, winheight)

        return content
