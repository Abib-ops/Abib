# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import Callable, Any

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
from ui_helpers import NoZoomDialog


class SecondaryWindow(NoZoomDialog):
    def __init__(
        self,
        text: str,
        navigate_left_cb: Callable[[], None] | None = None,
        navigate_right_cb: Callable[[], None] | None = None,
        settings_service: Any | None = None,
    ):
        """
        Initialise the secondary window to display text.
        :param text: The text to display in the window.
        :param navigate_left_cb: Callback invoked when the left arrow is clicked.
        :param navigate_right_cb: Callback invoked when the right arrow is clicked.
        :param settings_service: Optional SettingsService for persistence.
        """
        super().__init__()

        if not isinstance(text, str):
            raise ValueError(f"Expected a string for 'text', but got {type(text).__name__}")

        self.settings_service = settings_service
        # Load window geometry from settings
        if self.settings_service:
            ss: Any = self.settings_service
            x7, y7, width7, height7 = ss.get_window_geometry("devotional_window")
        else:
            x7, y7, width7, height7 = fcs.get_window_geometry("devotional_window")

        # Window setup
        self.setWindowTitle("C H Spurgeon's Morning and Evening Readings")
        self.setGeometry(x7, y7, width7, height7)

        self.text = text
        self._navigate_left_cb = navigate_left_cb
        self._navigate_right_cb = navigate_right_cb

        # Load font size from settings
        try:
            if self.settings_service:
                ss: Any = self.settings_service
                self.fontsize = ss.get_devotional_font_size()
            else:
                self.fontsize = fcs.get_devotional_font_size()
        except (TypeError, ValueError, OSError, AttributeError) as e7:
            print(f"Failed to load font size: {e7}")
            self.fontsize = 14  # fallback default

        # Text display
        self.text_display = QPlainTextEdit()
        self.text_display.setPlainText(text)
        self.text_display.setReadOnly(True)

        # Keep references to QShortcut instances to satisfy Qt and linters
        self._shortcuts = []

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
        # Ensure we keep references to shortcuts to prevent GC
        # Ctrl++ to increase font size
        increase_shortcut = QKeySequence("Ctrl++")
        self._shortcuts.append(self._make_shortcut(increase_shortcut, self.increase_font_size))

        # Ctrl+= alternative
        increase_alt = QKeySequence("Ctrl+=")
        self._shortcuts.append(self._make_shortcut(increase_alt, self.increase_font_size))

        # Ctrl+- to decrease font size
        decrease_shortcut = QKeySequence("Ctrl+-")
        self._shortcuts.append(self._make_shortcut(decrease_shortcut, self.decrease_font_size))

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
        try:
            if self.text_display.font().pointSize() == self.fontsize:
                return
        except (AttributeError, RuntimeError):
            pass

        font: QFont = QFont("Cascadia Mono", self.fontsize, QFont.Weight.Medium)
        self.text_display.setFont(font)

        # Save font size to settings
        try:
            if self.settings_service:
                ss: Any = self.settings_service
                ss.update_devotional_font_size(self.fontsize)
            else:
                fcs.update_devotional_font_size(self.fontsize)

            # Unified font size support: notify the main window
            from PySide6.QtWidgets import QApplication
            for widget in QApplication.topLevelWidgets():
                # Check for MainWindow by class name to avoid circular imports
                if widget.__class__.__name__ == "MainWindow":
                    try:
                        if bool(getattr(widget, "settings", {}).get("unified_font_size", False)):
                            ws = getattr(widget, "settings_service", None)
                            if ws:
                                win_service: Any = ws
                                if win_service.get_bible_font_size() != self.fontsize:
                                    win_service.update_bible_font_size(self.fontsize)
                                    af = getattr(widget, "apply_font_size", None)
                                    if af:
                                        af()
                    except (AttributeError, RuntimeError):
                        pass
                    break
        except (PermissionError, OSError, ValueError, TypeError) as e5:
            print(f"Failed to save font size: {e5}")

    def _save_current_geometry(self):
        """Persist current geometry to settings"""
        try:
            geometry = self.geometry()
            if self.settings_service:
                ss: Any = self.settings_service
                ss.save_window_geometry(
                    "devotional_window",
                    geometry.x(),
                    geometry.y(),
                    geometry.width(),
                    geometry.height(),
                )
            else:
                fcs.save_window_geometry(
                    "devotional_window",
                    geometry.x(),
                    geometry.y(),
                    geometry.width(),
                    geometry.height(),
                )
        except (RuntimeError, TypeError, ValueError):
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
        """Handle window close event - save geometry"""
        self._save_current_geometry()
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
    def __init__(self, version_text: str, settings_service: Any | None = None):
        super().__init__()
        self.setWindowTitle(version_text)
        self.settings_service = settings_service

        # Default size
        winwidth: int = 480
        winheight: int = 500

        # Load window geometry from settings
        try:
            if self.settings_service:
                ss: Any = self.settings_service
                gx, gy, gw, gh = ss.get_window_geometry("about_window")
            else:
                gx, gy, gw, gh = fcs.get_window_geometry("about_window")
            # If the stored geometry is too large, use the new defaults
            if gh == 810 or gw > 600:
                gh = winheight
                gw = winwidth
            self.setGeometry(gx, gy, gw, gh)
        except (RuntimeError, TypeError, ValueError):
            self.resize(winwidth, winheight)

        # Load About.txt and Licence content
        main_content, license_notice = AboutWindow.about()

        # Create the main content label
        label_main = QLabel(self)
        label_main.setWordWrap(True)
        label_main.setText(main_content)
        label_main.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        fontsize_main = 14
        font_main = QFont("Cascadia Mono", fontsize_main, QFont.Weight.Bold)
        label_main.setFont(font_main)

        # Create the licence notice label
        label_license = QLabel(self)
        label_license.setWordWrap(True)
        label_license.setText(license_notice)
        label_license.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        fontsize_license = 9
        font_license = QFont("Segoe UI", fontsize_license) # Using a standard UI font for the smaller notice
        label_license.setFont(font_license)

        # Set the QLabel as the central widget
        from PySide6.QtWidgets import QWidget
        container = QWidget(self)
        layout = QVBoxLayout(container)
        layout.addWidget(label_main)
        
        # Add a separator line or space if desired? 
        # The current code has \n\n---\n\n in license_notice.
        
        layout.addWidget(label_license)
        self.setCentralWidget(container)

    @staticmethod
    def about() -> tuple[str, str]:
        """Load the 'About' content from ABOUT.txt and return it along with the licence notice."""
        content: str = ""
        try:
            with open("ABOUT.txt", "r", encoding="utf-8") as file_about:
                content = file_about.read()
        except FileNotFoundError:
            content = "ABOUT.txt file not found."
        except UnicodeDecodeError:
            content = "Error: Unable to decode ABOUT.txt. Please make sure the file encoding is UTF-8."
        
        license_notice = (
            "---\n\n"
            "Abib Bible Reader\n"
            "Copyright © 2003–2026 The Abib Contributors\n\n"
            "This program is free software: you can redistribute it and/or modify "
            "it under the terms of the GNU General Public License as published by "
            "the Free Software Foundation, either version 3 of the License, or "
            "(at your option) any later version.\n\n"
            "This program is distributed in the hope that it will be useful, "
            "but WITHOUT ANY WARRANTY; without even the implied warranty of "
            "MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the "
            "GNU General Public License for more details.\n\n"
            "You should have received a copy of the GNU General Public License "
            "along with this program.  If not, see <https://www.gnu.org/licenses/>."
        )
        return content.strip(), license_notice

    def _save_current_geometry(self):
        """Persist current geometry to settings"""
        try:
            geometry = self.geometry()
            if self.settings_service:
                ss: Any = self.settings_service
                ss.save_window_geometry(
                    "about_window",
                    geometry.x(),
                    geometry.y(),
                    geometry.width(),
                    geometry.height(),
                )
            else:
                fcs.save_window_geometry(
                    "about_window",
                    geometry.x(),
                    geometry.y(),
                    geometry.width(),
                    geometry.height(),
                )
        except (RuntimeError, TypeError, ValueError):
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
        """Handle window close event - save geometry"""
        self._save_current_geometry()
        event.accept()
