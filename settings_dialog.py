# -*- coding: utf-8 -*-
from __future__ import annotations

from PySide6.QtWidgets import QDialog, QVBoxLayout, QCheckBox, QComboBox, QDialogButtonBox, QPushButton
import fcs


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.layout = QVBoxLayout(self)

        # Track whether the user requested defaults
        self.was_reset_to_defaults = False

        # Create the splash checkbox
        self.splash_checkbox = QCheckBox("Show Splash Screen")
        self.layout.addWidget(self.splash_checkbox)

        # Create theme combobox
        self.theme_combobox = QComboBox()
        self.theme_combobox.addItems(["Light", "Dark"])
        self.layout.addWidget(self.theme_combobox)

        # Reset to defaults button
        self.reset_defaults_btn = QPushButton("Reset to defaults")
        self.reset_defaults_btn.setToolTip("Apply ALL default settings immediately (overwrites your settings). Window sizes/positions will reset to defaults and may only fully apply after restart.")
        self.reset_defaults_btn.clicked.connect(self.reset_to_defaults)
        self.layout.addWidget(self.reset_defaults_btn)

        # Create the button box with correct typing
        button_types = QDialogButtonBox.StandardButton
        buttons = button_types.Ok | button_types.Cancel  # type: ignore
        self.button_box = QDialogButtonBox(buttons)

        # Connect the button box signals
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Add the button box to the layout
        self.layout.addWidget(self.button_box)

    def reset_to_defaults(self) -> None:
        """Reset the dialog controls to Abib's default settings.
        Does not persist automatically; user must click OK to save.
        """
        try:
            defaults = fcs.get_default_settings()
            # Apply defaults to controls based on the central defaults
            self.splash_checkbox.setChecked(bool(defaults.get("show_splash", False)))
            self.theme_combobox.setCurrentText(defaults.get("theme", "Light"))
            # Mark that the user requested defaults so the caller can persist them on OK
            self.was_reset_to_defaults = True
        except (RuntimeError, AttributeError, TypeError):
            # Ignore typical Qt/attribute/type issues without masking unrelated errors
            pass
