# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QComboBox, QDialogButtonBox


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.layout = QVBoxLayout(self)

        # Create the splash checkbox
        self.splash_checkbox = QCheckBox("Show Splash Screen")
        self.layout.addWidget(self.splash_checkbox)

        # Create theme combobox
        self.theme_combobox = QComboBox()
        self.theme_combobox.addItems(["Light", "Dark"])
        self.layout.addWidget(self.theme_combobox)

        # Create the button box with correct typing
        button_types = QDialogButtonBox.StandardButton
        buttons = button_types.Ok | button_types.Cancel  # type: ignore
        self.button_box = QDialogButtonBox(buttons)

        # Connect the button box signals
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Add the button box to the layout
        self.layout.addWidget(self.button_box)
