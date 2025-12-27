# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QPushButton,
    QLabel,
    QSpinBox,
)
import fcs


class SettingsDialog(QDialog):
    def __init__(self, parent=None, settings_service: Any | None = None):
        super().__init__(parent)
        self.settings_service = settings_service

        self.setWindowTitle("Settings")
        self.layout = QVBoxLayout(self)

        # Load window geometry from settings
        try:
            if self.settings_service:
                gx, gy, gw, gh = self.settings_service.get_window_geometry("settings_window")
            else:
                gx, gy, gw, gh = fcs.get_window_geometry("settings_window")
            self.setGeometry(gx, gy, gw, gh)
        except (RuntimeError, TypeError, ValueError):
            self.resize(400, 500)

        # Track whether the user requested defaults
        self.was_reset_to_defaults = False

        # Create the splash checkbox
        self.splash_checkbox = QCheckBox("Show Splash Screen")
        self.layout.addWidget(self.splash_checkbox)

        # Check for updates on startup (runs asynchronously)
        self.update_checkbox = QCheckBox("Check for updates on startup (runs in background)")
        self.update_checkbox.setToolTip("If enabled, Abib will check for updates in the background when it starts.")
        self.layout.addWidget(self.update_checkbox)

        # Unified font size option
        self.unified_font_size_checkbox = QCheckBox("Use the same font size for all windows")
        self.unified_font_size_checkbox.setToolTip("If enabled, changing the font size in one window will change it in all windows.")
        self.layout.addWidget(self.unified_font_size_checkbox)

        # Create theme combobox
        self.theme_combobox = QComboBox()
        self.theme_combobox.addItems(["Light", "Dark"])
        self.layout.addWidget(self.theme_combobox)

        # Check for updates now (manual trigger)
        self.update_now_btn = QPushButton("Check for updates now")
        self.update_now_btn.setToolTip("Run the updater once now without waiting for next startup.")
        self.layout.addWidget(self.update_now_btn)

        # Reset to defaults button
        self.reset_defaults_btn = QPushButton("Reset to defaults")
        self.reset_defaults_btn.setToolTip("Apply ALL default settings immediately (overwrites your settings). Window sizes/positions will reset to defaults and may only fully apply after restart.")
        self.reset_defaults_btn.clicked.connect(self.reset_to_defaults)
        self.layout.addWidget(self.reset_defaults_btn)

        # Gill: Show scripture popups
        self.gill_show_popups_checkbox = QCheckBox("Gill: Show scripture popups")
        self.gill_show_popups_checkbox.setToolTip("If disabled, scripture popups in the Gill window will never be shown.")
        self.layout.addWidget(self.gill_show_popups_checkbox)

        # --- Gill settings ---
        # Hover delay (ms)
        self.gill_hover_label = QLabel("Gill: Popup hover delay (ms)")
        self.layout.addWidget(self.gill_hover_label)
        self.gill_hover_spin = QSpinBox()
        self.gill_hover_spin.setRange(0, 5000)
        self.gill_hover_spin.setSingleStep(10)
        self.gill_hover_spin.setToolTip("Delay before showing the scripture popup when hovering a link in Gill.")
        self.layout.addWidget(self.gill_hover_spin)
        # Hide delay (ms)
        self.gill_hide_label = QLabel("Gill: Popup hide delay (ms)")
        self.layout.addWidget(self.gill_hide_label)
        self.gill_hide_spin = QSpinBox()
        self.gill_hide_spin.setRange(0, 5000)
        self.gill_hide_spin.setSingleStep(10)
        self.gill_hide_spin.setToolTip("Delay before hiding the scripture popup after moving off the link in Gill.")
        self.layout.addWidget(self.gill_hide_spin)

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
            self.update_checkbox.setChecked(bool(defaults.get("check_updates_on_startup", False)))
            self.unified_font_size_checkbox.setChecked(bool(defaults.get("unified_font_size", False)))
            self.theme_combobox.setCurrentText(defaults.get("theme", "Light"))
            self.gill_show_popups_checkbox.setChecked(bool(defaults.get("gill_show_popups", True)))
            # Gill timing defaults
            self.gill_hover_spin.setValue(int(defaults.get("gill_hover_delay_ms", 120)))
            self.gill_hide_spin.setValue(int(defaults.get("gill_hide_delay_ms", 160)))
            # Mark that the user requested defaults so the caller can persist them on OK
            self.was_reset_to_defaults = True
        except (RuntimeError, AttributeError, TypeError):
            # Ignore typical Qt/attribute/type issues without masking unrelated errors
            pass

    def closeEvent(self, event):
        """Handle window close event - save geometry"""
        try:
            geometry = self.geometry()
            if self.settings_service:
                self.settings_service.save_window_geometry(
                    "settings_window",
                    geometry.x(),
                    geometry.y(),
                    geometry.width(),
                    geometry.height(),
                )
            else:
                fcs.save_window_geometry(
                    "settings_window",
                    geometry.x(),
                    geometry.y(),
                    geometry.width(),
                    geometry.height(),
                )
        except (RuntimeError, TypeError, ValueError):
            pass
        super().closeEvent(event)
