# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from PySide6.QtCore import QRunnable, QThreadPool
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QPushButton,
    QSpinBox,
    QSplashScreen,
    QVBoxLayout,
)

from abib.core import shared as sh
from abib.services.settings import SettingsService

if TYPE_CHECKING:
    from abib.Abib import MainWindow

class SettingsDialog(QDialog):
    def __init__(self, parent: MainWindow | None = None, settings_service: SettingsService | None = None):
        super().__init__(parent)
        self.main_window = parent
        self.settings_service: SettingsService = settings_service if settings_service is not None else SettingsService()
        self.settings = self.settings_service.settings

        self.setWindowTitle("Settings")
        self.layout = QVBoxLayout(self)

        # Load window geometry from settings
        try:
            gx, gy, gw, gh = self.settings_service.get_window_geometry("settings_window")
            # If the coordinates are the default (100, 100), center the window instead
            if gx == 100 and gy == 100:
                from abib.utils import ui as ui_utils
                cx, cy = ui_utils.center_on_screen(gw, gh)
                self.setGeometry(cx, cy, gw, gh)
                # Save the centered position immediately so it's remembered as "moveable" from there
                self.settings_service.save_window_geometry("settings_window", cx, cy, gw, gh)
            else:
                self.setGeometry(gx, gy, gw, gh)
        except (RuntimeError, TypeError, ValueError, AttributeError):
            self.resize(400, 500)

        # Track whether the user requested defaults
        self.was_reset_to_defaults = False

        # Create the splash checkbox
        self.splash_checkbox = QCheckBox("Show Splash Screen")
        self.layout.addWidget(self.splash_checkbox)

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
        self.update_now_btn.clicked.connect(self._on_update_now_clicked)
        self.layout.addWidget(self.update_now_btn)

        # Reset to defaults button
        self.reset_defaults_btn = QPushButton("Reset to defaults")
        self.reset_defaults_btn.setToolTip("Apply ALL default settings immediately (overwrites your settings). Window sizes/positions will reset to defaults and may only fully apply after restart.")
        self.reset_defaults_btn.clicked.connect(self._apply_defaults_immediately)
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

        # Create the button box
        button_types = QDialogButtonBox.StandardButton
        buttons = button_types.Ok | button_types.Cancel  # type: ignore
        self.button_box = QDialogButtonBox(buttons)

        # Connect the button box signals
        self.button_box.accepted.connect(self.handle_accept)
        self.button_box.rejected.connect(self.reject)

        # Add the button box to the layout
        self.layout.addWidget(self.button_box)

        self._populate_initial()

    def _populate_initial(self):
        # Populate the settings dialog with current settings
        self.splash_checkbox.setChecked(bool(self.settings.get("show_splash", False)))
        try:
            self.unified_font_size_checkbox.setChecked(bool(self.settings.get("unified_font_size", False)))
        except (AttributeError, RuntimeError):
            pass
        self.theme_combobox.setCurrentText(self.settings.get("theme", "Light"))
        # Gill: Show scripture popups
        try:
            self.gill_show_popups_checkbox.setChecked(bool(self.settings_service.get_gill_show_popups()))
        except (RuntimeError, AttributeError, TypeError, ValueError):
            self.gill_show_popups_checkbox.setChecked(True)
        # Gill popup timing settings
        try:
            self.gill_hover_spin.setValue(int(self.settings_service.get_gill_hover_delay_ms()))
        except (RuntimeError, AttributeError, TypeError, ValueError):
            self.gill_hover_spin.setValue(120)
        try:
            self.gill_hide_spin.setValue(int(self.settings_service.get_gill_hide_delay_ms()))
        except (RuntimeError, AttributeError, TypeError, ValueError):
            self.gill_hide_spin.setValue(160)

    def _apply_defaults_immediately(self) -> None:
        if self.main_window is None:
            return
        # Read the current state to determine splash transition
        prev = bool(self.settings.get("show_splash", False))
        default_settings = self.settings_service.get_default_settings()
        defaults_show_splash = bool(default_settings.get("show_splash", False))

        # Replace entire settings with defaults and persist immediately
        try:
            self.main_window.settings.clear()
            self.main_window.settings.update(default_settings)
        except (AttributeError, TypeError):
            # Fallback: replace the reference if clear/update fails for any reason
            self.main_window.settings = dict(default_settings)  # type: ignore
        self.settings_service.save(self.main_window.settings)  # type: ignore

        # Apply theme across UI right away
        self.main_window.set_theme(self.main_window.settings)

        # Manage splash visibility transitions immediately
        self._update_splash_visibility(prev, defaults_show_splash)

        # Update UI to match defaults
        self._populate_initial()
        self.was_reset_to_defaults = False

    def _on_update_now_clicked(self):
        from abib.core.updater import check_for_updates as _check_for_updates
        from abib.core.updater import perform_update as _perform_update

        class _RunPerformUpdate(QRunnable):
            def __init__(self, version: str, exe_url: str) -> None:
                super().__init__()
                self.version = version
                self.exe_url = exe_url

            def run(self) -> None:
                try:
                    _perform_update(self.version, self.exe_url)
                except (OSError, RuntimeError, ValueError):
                    pass

        try:
            result: Any = _check_for_updates(parent=self)
        except (RuntimeError, TypeError, ValueError):
            result = None

        if not result:
            return

        try:
            update_available, new_version, new_exe_url = result
        except (TypeError, ValueError):
            return

        if not update_available:
            return

        try:
            QThreadPool.globalInstance().start(_RunPerformUpdate(new_version, new_exe_url))
        except (RuntimeError, TypeError):
            try:
                _perform_update(new_version, new_exe_url)
            except (OSError, RuntimeError, ValueError):
                pass

    def handle_accept(self):
        if self.main_window is None:
            self.accept()
            return

        prev_show_splash = bool(self.main_window.settings.get("show_splash", False))

        if self.was_reset_to_defaults:
            defaults = self.settings_service.get_default_settings()
            new_theme = defaults.get("theme", "Light")
            new_show_splash = bool(defaults.get("show_splash", False))
            new_unified_font_size = bool(defaults.get("unified_font_size", False))
            new_gill_show_popups = bool(defaults.get("gill_show_popups", True))
            new_gill_hover = int(defaults.get("gill_hover_delay_ms", 120))
            new_gill_hide = int(defaults.get("gill_hide_delay_ms", 160))
        else:
            new_theme = self.theme_combobox.currentText()
            new_show_splash = self.splash_checkbox.isChecked()
            try:
                new_unified_font_size = bool(self.unified_font_size_checkbox.isChecked())
            except (AttributeError, RuntimeError):
                new_unified_font_size = bool(self.main_window.settings.get("unified_font_size", False))
            try:
                new_gill_show_popups = bool(self.gill_show_popups_checkbox.isChecked())
            except (RuntimeError, AttributeError):
                new_gill_show_popups = self.settings_service.get_gill_show_popups()
            try:
                new_gill_hover = int(self.gill_hover_spin.value())
            except (RuntimeError, AttributeError, TypeError, ValueError):
                new_gill_hover = self.settings_service.get_gill_hover_delay_ms()
            try:
                new_gill_hide = int(self.gill_hide_spin.value())
            except (RuntimeError, AttributeError, TypeError, ValueError):
                new_gill_hide = self.settings_service.get_gill_hide_delay_ms()

        # Update in-memory settings
        self.main_window.settings["theme"] = new_theme
        self.main_window.settings["show_splash"] = new_show_splash
        self.main_window.settings["unified_font_size"] = new_unified_font_size

        # If unified font size was just enabled, sync all font sizes
        if new_unified_font_size:
            bible_size = self.settings_service.get_bible_font_size()
            self.settings_service.update_reader_font_size(bible_size)
            self.settings_service.update_devotional_font_size(bible_size)
            self.settings_service.update_commentary_font_size(bible_size)
            self.main_window.settings["bible_font_size"] = bible_size
            self.main_window.settings["reader_font_size"] = bible_size
            self.main_window.settings["devotional_font_size"] = bible_size
            self.main_window.settings["gill_font_size"] = bible_size

        # Save current position before final settings save
        self._save_current_geometry()

        # Save settings
        self.settings_service.save(self.main_window.settings)

        # Persist Gill settings
        try:
            self.settings_service.set_gill_hover_delay_ms(int(new_gill_hover))
            self.settings_service.set_gill_hide_delay_ms(int(new_gill_hide))
            self.settings_service.set_gill_show_popups(bool(new_gill_show_popups))
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

        # Apply theme
        self.main_window.set_theme(self.main_window.settings)

        # Manage splash visibility
        self._update_splash_visibility(prev_show_splash, new_show_splash)

        # Apply to Gill window if open
        try:
            gill_win = getattr(self.main_window, "_gill_win", None)
            if gill_win is not None:
                if hasattr(gill_win, "set_popup_timing"):
                    gill_win.set_popup_timing(int(new_gill_hover), int(new_gill_hide))
                if hasattr(gill_win, "set_popups_enabled"):
                    gill_win.set_popups_enabled(bool(new_gill_show_popups))
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass

        self.accept()

    @staticmethod
    def _update_splash_visibility(prev_show: bool, new_show: bool) -> None:
        from PySide6.QtWidgets import QWidget

        from abib import Abib
        # Access module-level globals from Abib

        # Turning splash OFF
        if prev_show and not new_show:
            try:
                # Capture and type-hint splash screen instance locally
                splash_obj: Any = getattr(Abib, 'splash', None)
                if splash_obj is not None and isinstance(splash_obj, QSplashScreen):
                    # Local reference is now narrowed to QSplashScreen
                    try:
                        # Capture main window instance locally
                        win_obj: Any = getattr(Abib, 'w', None)
                        if win_obj is not None and isinstance(win_obj, QWidget):
                            # Both splash_obj and win_obj are verified non-None and of correct type
                            splash_obj.finish(win_obj)
                        else:
                            # Fallback if window is not available
                            splash_obj.close()
                    except (RuntimeError, AttributeError, TypeError, AssertionError):
                        try:
                            splash_obj.close()
                        except (RuntimeError, AttributeError):
                            pass
                Abib.splash = None
            except (RuntimeError, AttributeError, ImportError):
                pass

        # Turning splash ON
        if (not prev_show) and new_show:
            try:
                if getattr(Abib, 'splash', None) is None:
                    splash_path = sh.images_dir / "Abib_barley.png"
                    pix = QPixmap(str(splash_path))
                    new_splash = QSplashScreen(pix)
                    new_splash.show()
                    Abib.splash = new_splash
            except (RuntimeError, AttributeError):
                pass

    def _save_current_geometry(self):
        """Helper to capture and persist the current dialog geometry."""
        try:
            geom = self.geometry()
            self.settings_service.save_window_geometry(
                "settings_window",
                geom.x(),
                geom.y(),
                geom.width(),
                geom.height(),
            )
        except (RuntimeError, TypeError, ValueError, AttributeError):
            pass

    def moveEvent(self, event):
        self._save_current_geometry()
        super().moveEvent(event)

    def resizeEvent(self, event):
        self._save_current_geometry()
        super().resizeEvent(event)

    def closeEvent(self, event):
        self._save_current_geometry()
        super().closeEvent(event)
