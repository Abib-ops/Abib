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

from typing import TYPE_CHECKING, Any, ClassVar

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
        # Restyle the coloured pushbuttons for the active theme
        try:
            self.apply_coloured_buttons_theme()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
        # Restyle the coloured comboboxes for the active theme
        try:
            self.apply_coloured_comboboxes_theme()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            pass
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
        if getattr(win, 'strongs_win', None):
            # Use a local reference with a type hint to satisfy the linter
            sw: Any = win.strongs_win
            try:
                sw.apply_theme(win.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            win.theme.apply_widget(sw)

    # Mapping of coloured pushbutton attribute names to their theme colours.
    # Each entry is (light background / base colour, brighter dark-mode text colour).
    _COLOURED_BUTTONS: ClassVar[dict[str, tuple[str, str]]] = {
        'okButton': ('#e6f4e6', '#8cff8c'),   # OK (brighter green)
        'buttonTheme': ('#d6e4ff', '#8cb4ff'),  # Light/Dark (blue)
        'buttonf3': ('#ffe6cc', '#ffb84d'),   # Find (brighter orange)
        'buttonf4': ('#ffe6cc', '#ffb84d'),   # Find Next (brighter orange)
        'buttonf5': ('#b6d7b0', '#8cff8c'),   # Back (brighter green)
        'buttonf6': ('#b6d7b0', '#8cff8c'),   # Forward (brighter green)
        'buttonf7': ('#ffffcc', '#ffff66'),   # Book- (brighter yellow)
        'buttonf8': ('#ffffcc', '#ffff66'),   # Book+ (brighter yellow)
        'buttonf10': ('#ffffcc', '#ffff66'),  # Chapter- (brighter yellow)
        'buttonf11': ('#ffffcc', '#ffff66'),  # Chapter+ (brighter yellow)
        'last_work_btn': ('#ffe6ee', '#ff8cc6'),   # Open Work (brighter pink)
        'search_work_btn': ('#ffe6ee', '#ff8cc6'),  # Search Work (brighter pink)
    }

    @staticmethod
    def _apply_coloured_theme(
        win: MainWindow,
        mapping: dict[str, tuple[str, str]],
        light_style: str,
        dark_style: str,
    ) -> None:
        """Restyle a group of coloured controls for the active theme.

        ``mapping`` pairs each control's attribute name on ``win`` with its
        ``(base_colour, dark_text)`` colours. ``light_style`` and ``dark_style``
        are format strings expecting ``base_colour`` / ``dark_text`` keywords and
        are applied in light and dark mode respectively.
        """
        is_dark = win.theme.state.is_dark_mode
        for name, (base_colour, dark_text) in mapping.items():
            widget = getattr(win, name, None)
            if widget is None:
                continue
            w: Any = widget
            template = dark_style if is_dark else light_style
            style = template.format(base_colour=base_colour, dark_text=dark_text)
            try:
                w.setStyleSheet(style)
            except (RuntimeError, AttributeError, TypeError, ValueError):
                pass

    def apply_coloured_buttons_theme(self) -> None:
        """Restyle the coloured pushbuttons for the active theme.

        In light mode the button uses its base colour as the background with
        black text. In dark mode the background is left to the palette so it
        matches the plain buttons in the right-hand column exactly, and a
        brighter variant of the base colour is used for the text instead.
        """
        # In dark mode do not set a background-color so these buttons inherit the
        # same palette-driven background as the plain buttons on the right.
        self._apply_coloured_theme(
            self._win,
            self._COLOURED_BUTTONS,
            "QPushButton {{ text-align: left; background-color: {base_colour}; color: #000000; }}",
            "QPushButton {{ text-align: left; color: {dark_text}; }}",
        )

    # Mapping of coloured combobox attribute names to their theme colours.
    # Each entry is (light background / base colour, brighter dark-mode text colour).
    _COLOURED_COMBOBOXES: ClassVar[dict[str, tuple[str, str]]] = {
        'comboBox_1': ('#e6f4e6', '#8cff8c'),        # Book (green)
        'comboBox_2': ('#e6f4e6', '#8cff8c'),        # Chapter (green)
        'comboBox_3': ('#e6f4e6', '#8cff8c'),        # Verse (green)
        'other_works_combo': ('#ffe6ee', '#ff8cc6'),  # Other Works (pink)
    }

    def apply_coloured_comboboxes_theme(self) -> None:
        """Restyle the coloured comboboxes for the active theme.

        In light mode the combobox uses its base colour as the background with
        black text. In dark mode the background matches the plain controls
        (a dark grey) and a brighter variant of the base colour is used for
        the text instead.
        """
        self._apply_coloured_theme(
            self._win,
            self._COLOURED_COMBOBOXES,
            "QComboBox {{ background-color: {base_colour}; color: #000000; }}",
            "QComboBox {{ background-color: #2a2a2a; color: {dark_text}; }}",
        )

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
