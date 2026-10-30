# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol, cast

from abib.utils import platform as plat

if TYPE_CHECKING:
    # noinspection PyPackageRequirements
    from PySide6.QtGui import QColor, QPalette

    # noinspection PyPackageRequirements
    from PySide6.QtWidgets import QApplication, QWidget
    QPaletteT = QPalette
    QColorT = QColor
else:
    try:
        # noinspection PyPackageRequirements
        from PySide6.QtGui import QColor, QPalette

        # noinspection PyPackageRequirements
        from PySide6.QtWidgets import QApplication, QPlainTextEdit, QWidget
    except ImportError:
        QPlainTextEdit = object  # type: ignore
        QApplication = object  # type: ignore
        QWidget = object  # type: ignore
        QPalette = object  # type: ignore
        QColor = object  # type: ignore
    QPaletteT = Any
    QColorT = Any


@dataclass
class ThemeState:
    is_dark_mode: bool = False


class EditorWithStyleSheet(Protocol):
    def setStyleSheet(self, style: str) -> None: ...


class ThemeApplier(Protocol):
    def apply_theme(self, is_dark: bool) -> None: ...


class ThemeManager:
    """Encapsulates dark/light theme state and application helpers.

    This module centralises the styling logic so the rest of the app avoids
    manipulating global state directly and keeps UI code thin.
    """

    def __init__(self, state: ThemeState | None = None) -> None:
        self.state = state or ThemeState()
        # Track style switching to Fusion on Windows 10 dark mode
        self._original_style_name: str | None = None
        self._using_fusion: bool = False

    # ---- State ----
    def toggle(self) -> bool:
        """Toggle dark mode and return the new state."""
        self.state.is_dark_mode = not self.state.is_dark_mode
        return self.state.is_dark_mode

    # ---- Palettes ----
    @staticmethod
    def _build_dark_palette() -> QPaletteT:
        pal = QPalette()
        # Window background and text
        pal.setColor(QPalette.ColorRole.Window, QColor(18, 18, 18))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(240, 240, 240))
        # Text areas
        pal.setColor(QPalette.ColorRole.Base, QColor(18, 18, 18))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor(28, 28, 28))
        pal.setColor(QPalette.ColorRole.Text, QColor(240, 240, 240))
        # Buttons
        pal.setColor(QPalette.ColorRole.Button, QColor(28, 28, 28))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor(240, 240, 240))
        # Links/selection
        pal.setColor(QPalette.ColorRole.Link, QColor(100, 149, 237))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(42, 90, 223))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        # Tooltips
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(40, 40, 40))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor(240, 240, 240))
        return pal

    @staticmethod
    def _build_light_palette() -> QPaletteT:
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        # Slightly darken control backgrounds in light mode for better contrast
        pal.setColor(QPalette.ColorRole.Base, QColor(250, 250, 250))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor(238, 238, 238))
        pal.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        pal.setColor(QPalette.ColorRole.Button, QColor(232, 232, 232))
        pal.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        pal.setColor(QPalette.ColorRole.Link, QColor(0, 102, 204))
        pal.setColor(QPalette.ColorRole.Highlight, QColor(204, 232, 255))
        pal.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
        pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        pal.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        return pal

    def apply_app_palette(self) -> None:
        """Apply the current theme's palette to the QApplication (if available)."""
        try:
            app = QApplication.instance()
        except (RuntimeError, AttributeError, TypeError):
            app = None
        if not app:
            return
        # On Windows 10 in dark mode, force Fusion style so button stylesheets take effect
        # (the Windows-version heuristic now lives in the shared platform helper).
        try:
            if self.state.is_dark_mode and plat.is_windows_10():
                if not self._original_style_name:
                    try:
                        self._original_style_name = cast("QApplication", app).style().objectName()
                    except (AttributeError, RuntimeError, TypeError):
                        self._original_style_name = None
                if not self._using_fusion:
                    try:
                        QApplication.setStyle("Fusion")
                        self._using_fusion = True
                    except (RuntimeError, ValueError, TypeError):
                        self._using_fusion = False
            else:
                if self._using_fusion:
                    try:
                        if self._original_style_name:
                            QApplication.setStyle(self._original_style_name)
                        else:
                            QApplication.setStyle("WindowsVista")
                    except (RuntimeError, ValueError, TypeError, AttributeError):
                        pass
                    self._using_fusion = False
        except (RuntimeError, AttributeError, TypeError, ValueError):
            # Never fail theming due to style switching errors
            self._using_fusion = False

        pal = self._build_dark_palette() if self.state.is_dark_mode else self._build_light_palette()
        QApplication.setPalette(pal)
        # ToolTip styling (Qt ignores palette for a tooltip background sometimes)
        if self.state.is_dark_mode:
            # Base dark stylesheet applied to all platforms
            dark_base_styles = (
            """
            QToolTip { color: #f0f0f0; background-color: #282828; border: 1px solid #3a3a3a; }
            QMenuBar { background-color: #222222; color: #f0f0f0; border-bottom: 1px solid #3a3a3a; }
            QMenuBar::item { background-color: transparent; }
            QMenuBar::item:selected { background-color: #3a3a3a; color: #ffffff; }
            QMenu { background-color: #222222; color: #f0f0f0; border: 1px solid #3a3a3a; }
            QMenu::item:selected { background-color: #2a2a2a; color: #ffffff; }
            QMenu::separator { height: 1px; background: #3a3a3a; margin: 4px 8px; }
            /* Unify control shade in dark mode */
            QComboBox, QSpinBox, QLineEdit { background-color: #2a2a2a; color: #f0f0f0; border: 1px solid #3a3a3a; }
            QComboBox QAbstractItemView { background-color: #222222; color: #f0f0f0; selection-background-color: #2a2a2a; selection-color: #ffffff; }
            /* Ensure visibility of radio buttons and checkboxes in dark mode */
            QRadioButton, QCheckBox { color: #f0f0f0; }
            QRadioButton:disabled, QCheckBox:disabled { color: #8a8a8a; }
            /* Indicator styling (some platforms ignore palette for these) */
            /* Make radio buttons clearly circular and 14px with a small dot when checked */
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
                background-color: #2a2a2a;
                border: 1px solid #5a5a5a;
                border-radius: 7px; /* 14px circle */
            }
            /* Make checkboxes square (not circular) at 14px, with a small inner dot when checked */
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                background-color: #2a2a2a;
                border: 1px solid #5a5a5a;
                /* square shape: no border-radius */
            }
            QRadioButton::indicator:hover, QCheckBox::indicator:hover {
                border-color: #6a6a6a;
            }
            /* Radio: show a smaller inner dot when checked */
            QRadioButton::indicator:checked {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5,
                    stop:0 #2a5adf, stop:0.45 #2a5adf, stop:0.46 transparent, stop:1 transparent);
                border-color: #2a5adf;
            }
            /* Checkbox: show a smaller inner dot when checked */
            QCheckBox::indicator:checked {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5,
                    stop:0 #2a5adf, stop:0.45 #2a5adf, stop:0.46 transparent, stop:1 transparent);
                border-color: #2a5adf;
            }
            QRadioButton::indicator:disabled, QCheckBox::indicator:disabled {
                background-color: #2a2a2a;
                border-color: #2f2f2f;
            }
            /* Disabled checked states */
            QRadioButton::indicator:checked:disabled {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5,
                    stop:0 #555555, stop:0.45 #555555, stop:0.46 transparent, stop:1 transparent);
                border-color: #555555;
            }
            QCheckBox::indicator:checked:disabled {
                background: qradialgradient(cx:0.5, cy:0.5, radius:0.5,
                    fx:0.5, fy:0.5,
                    stop:0 #555555, stop:0.45 #555555, stop:0.46 transparent, stop:1 transparent);
                border-color: #555555;
            }
            """
        )

            # Button styles applied on every platform in dark mode. In light mode
            # the equivalent QPushButton rules (border + padding) are applied on
            # all platforms, so they must be here too. Any button that carries its
            # own per-widget stylesheet (e.g. the main-window buttons which set
            # "text-align: left; padding-left: 6px") switches to Qt's CSS box model
            # and loses its native frame metrics; without these global rules those
            # buttons would render with no border/vertical padding in dark mode on
            # Linux/macOS, making them a different height and misaligning their
            # text compared with light mode.
            button_styles = (
                """
                QPushButton, QDialogButtonBox QPushButton, QToolButton {
                    background: #2a2a2a;
                    background-color: #2a2a2a;
                    color: #f0f0f0;
                    border: 1px solid #3a3a3a;
                    border-radius: 3px;
                    padding: 4px 8px;
                }
                QPushButton:hover, QDialogButtonBox QPushButton:hover, QToolButton:hover { background-color: #333333; }
                QPushButton:pressed, QDialogButtonBox QPushButton:pressed, QToolButton:pressed { background-color: #1f1f1f; }
                QPushButton:disabled, QDialogButtonBox QPushButton:disabled, QToolButton:disabled { background-color: #2a2a2a; color: #8a8a8a; border-color: #2f2f2f; }
                """
            )

            # Apply the button stylesheet on all platforms so that dark mode matches
            # light mode: native widgets can render grey buttons and ignore the
            # palette (notably on Windows), and on Linux/macOS the main-window
            # buttons with their own stylesheet need these border/padding rules to
            # keep the same height and text alignment as in light mode.
            styles = dark_base_styles + button_styles
            cast("QApplication", app).setStyleSheet(styles)
        else:
            # Light mode: ensure consistent darker-than-default shade for buttons, combos, and line edits
            light_base_styles = (
                """
                /* Unify control shade in light mode */
                QMenuBar { background-color: #f0f0f0; color: #000000; border-bottom: 1px solid #d6d6d6; }
                QMenuBar::item { background-color: transparent; }
                QMenuBar::item:selected { background-color: #e6f0ff; color: #000000; }
                QMenu { background-color: #ffffff; color: #000000; border: 1px solid #d6d6d6; }
                QMenu::item:selected { background-color: #e6f0ff; color: #000000; }
                QMenu::separator { height: 1px; background: #d6d6d6; margin: 4px 8px; }
                QPushButton, QDialogButtonBox QPushButton, QToolButton {
                    /* Darker neutral to improve readability in light mode */
                    background: #e9e9e9;
                    background-color: #e9e9e9;
                    color: #000000;
                    border: 1px solid #b5b5b5;
                    border-radius: 3px;
                    padding: 4px 8px;
                }
                QPushButton:hover, QDialogButtonBox QPushButton:hover, QToolButton:hover { background-color: #e2e2e2; }
                QPushButton:pressed, QDialogButtonBox QPushButton:pressed, QToolButton:pressed { background-color: #d9d9d9; }
                QPushButton:disabled, QDialogButtonBox QPushButton:disabled, QToolButton:disabled { background-color: #ececec; color: #8a8a8a; border-color: #d6d6d6; }

                QComboBox, QSpinBox, QLineEdit { background-color: #e9e9e9; color: #000000; border: 1px solid #b5b5b5; }
                QComboBox QAbstractItemView { background-color: #ffffff; color: #000000; selection-background-color: #e6f0ff; selection-color: #000000; }
                """
            )
            cast("QApplication", app).setStyleSheet(light_base_styles)

    # ---- Apply helpers ----
    def apply_to_editor(self, editor: EditorWithStyleSheet | None) -> None:
        if editor is None:
            return
        if self.state.is_dark_mode:
            editor.setStyleSheet(
                """
                QPlainTextEdit {
                    background-color: #121212;  /* Dark background */
                    color: #ffffff;              /* White text */
                }
                """
            )
        else:
            editor.setStyleSheet(
                """
                QPlainTextEdit {
                    background-color: #ffffff;  /* Light background */
                    color: #000000;             /* Black text */
                }
                """
            )

    def apply_widget(self, widget: QWidget | None) -> None:
        """Apply the current palette to a specific widget (useful for dialogs)."""
        if widget is None:
            return
        pal = self._build_dark_palette() if self.state.is_dark_mode else self._build_light_palette()
        try:
            widget.setPalette(pal)
        except (AttributeError, RuntimeError, TypeError, ValueError):
            # Be tolerant of the Qt object lifecycle and type issues but avoid swallowing all exceptions
            pass

    def apply_to_secondary(self, secondary_window: ThemeApplier | None) -> None:
        if secondary_window is None:
            return
        try:
            secondary_window.apply_theme(self.state.is_dark_mode)
        except (AttributeError, RuntimeError):
            # Be tolerant: the secondary window might not be fully initialised or already deleted.
            pass
