# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Theming controller extracted from ``MainWindow``.

Holds all light/dark theme logic (palette application, control-height
normalisation, persistence and refresh of open dialogs/windows). ``MainWindow``
keeps thin delegators so external callers (settings dialog, theme toggle button)
are unaffected.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from abib.Abib import MainWindow


class ThemeController:
    """Encapsulate the theming behaviour previously living on ``MainWindow``."""

    def __init__(self, window: MainWindow) -> None:
        self._win = window

    def refresh_theme_across_ui(self) -> None:
        """Apply the app palette, style the main editor, update secondary windows, and
        re-theme any open dialogs/windows.
         Centralised to avoid duplication."""
        win = self._win
        # Apply application-wide palette first so dialogs/menus follow suit
        win.theme.apply_app_palette()
        # Apply to the main editor and secondary window
        win.theme.apply_to_editor(win.textEditor)
        win.update_text_display_theme()
        # Per user request: the verse input / search box should always have a white background and black text
        # in both themes to distinguish it from other dark controls.
        if win.theme.state.is_dark_mode:
            win.display_verse_input.setStyleSheet(
                "QLineEdit { background-color: #ffffff; color: #000000; border: 1px solid #3a3a3a; }"
            )
        else:
            win.display_verse_input.setStyleSheet(
                "QLineEdit { background-color: #ffffff; color: #000000; border: 1px solid #b5b5b5; }"
            )
        # Keep control heights consistent with the active style/theme
        try:
            self.normalize_control_heights()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        # Also refresh any currently open dialogs/windows
        if getattr(win, 'dlg', None):
            win.theme.apply_widget(win.dlg)
        if getattr(win, 'about_window', None):
            win.theme.apply_widget(win.about_window)
        if getattr(win, 'text_edit_window', None):
            try:
                win.text_edit_window.apply_theme(win.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            win.theme.apply_widget(win.text_edit_window)
        if getattr(win, 'gill_win', None):
            # Use a local reference with a type hint to satisfy the linter
            gw: Any = win.gill_win
            try:
                gw.apply_theme(win.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            win.theme.apply_widget(gw)

    def normalize_control_heights(self) -> None:
        """Make QComboBox controls the same height as pushbuttons.

        Uses the current style's sizeHint for a reference QPushButton (OK)
        to compute a DPI- and theme-aware height, then applies it to the
        main comboboxes.
        Called after UI setup and whenever the theme changes.
        """
        win = self._win
        try:
            ref_btn = getattr(win, 'okButton', None)
            if not ref_btn:
                return
            # Use a local reference with a type hint to satisfy the linter
            r: Any = ref_btn
            ref_h = int(r.sizeHint().height())
        except (RuntimeError, AttributeError, TypeError, ValueError):
            ref_h = 0
        if not ref_h:
            return
        # Controls to normalise to the same height as pushbuttons
        for ctrl_name in (
            'comboBox_1',
            'comboBox_2',
            'comboBox_3',
            'other_works_combo',
            'display_verse_input',  # F2 text entry box
        ):
            ctrl = getattr(win, ctrl_name, None)
            if ctrl is None:
                continue
            # Use a local reference with a type hint to satisfy the linter
            c: Any = ctrl
            try:
                c.setFixedHeight(ref_h)
            except (RuntimeError, AttributeError, TypeError, ValueError):
                # Be tolerant of lifecycle/style changes
                pass

    def set_theme(self, the_settings) -> None:
        """Apply the theme from settings using ThemeManager without legacy globals."""
        win = self._win
        theme_key = 'theme'
        current_theme = the_settings.get(theme_key, 'Light')

        # Set ThemeManager state explicitly to match settings
        win.theme.state.is_dark_mode = (current_theme == 'Dark')

        # Apply the palette and refresh all open UI elements
        self.refresh_theme_across_ui()

        # Ensure settings reflect what's applied and persist
        win.settings[theme_key] = 'Dark' if win.theme.state.is_dark_mode else 'Light'
        win.settings_service.save(win.settings)

    def toggle_dark_mode(self) -> None:
        """Toggle dark mode using ThemeManager and persist to settings."""
        win = self._win
        # Toggle via ThemeManager
        is_dark = win.theme.toggle()

        # Persist selection in settings
        win.settings["theme"] = "Dark" if is_dark else "Light"
        win.settings_service.save(win.settings)

        # Apply the palette and refresh all open UI elements
        self.refresh_theme_across_ui()

    def update_text_display_theme(self) -> None:
        """Update the text display theme using ThemeManager."""
        win = self._win
        # Apply to the secondary window if available
        if win.secondary_window and getattr(win.secondary_window, 'text_display', None):
            win.theme.apply_to_secondary(win.secondary_window)
            return
        # If the secondary window (or its text display) does not exist yet, exit quietly.
        # This method can be called during startup/theme changes before the window is created.
        return
