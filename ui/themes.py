from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

try:
    # Import only the minimal Qt classes we need to type the editor and widgets
    from PySide6.QtWidgets import QPlainTextEdit, QApplication, QWidget
    from PySide6.QtGui import QPalette, QColor
except ImportError:  # pragma: no cover - allows importing this module without Qt
    QPlainTextEdit = object  # type: ignore
    QApplication = object  # type: ignore
    QWidget = object  # type: ignore
    QPalette = object  # type: ignore
    QColor = object  # type: ignore


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

    def __init__(self, state: Optional[ThemeState] = None) -> None:
        self.state = state or ThemeState()

    # ---- State ----
    def toggle(self) -> bool:
        """Toggle dark mode and return the new state."""
        self.state.is_dark_mode = not self.state.is_dark_mode
        return self.state.is_dark_mode

    # ---- Palettes ----
    def _build_dark_palette(self) -> QPalette:
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

    def _build_light_palette(self) -> QPalette:
        pal = QPalette()
        pal.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
        pal.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        pal.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        pal.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        pal.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        pal.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
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
        except Exception:
            app = None
        if not app:
            return
        pal = self._build_dark_palette() if self.state.is_dark_mode else self._build_light_palette()
        app.setPalette(pal)
        # ToolTip styling (Qt ignores palette for tooltip background sometimes)
        if self.state.is_dark_mode:
            app.setStyleSheet(
                """
                QToolTip { color: #f0f0f0; background-color: #282828; border: 1px solid #3a3a3a; }
                QMenu { background-color: #222222; color: #f0f0f0; border: 1px solid #3a3a3a; }
                QMenu::item:selected { background-color: #2a2a2a; color: #ffffff; }
                QMenu::separator { height: 1px; background: #3a3a3a; margin: 4px 8px; }
                QComboBox { background-color: #2a2a2a; color: #f0f0f0; border: 1px solid #3a3a3a; }
                QComboBox QAbstractItemView { background-color: #222222; color: #f0f0f0; selection-background-color: #2a2a2a; selection-color: #ffffff; }
                QLineEdit { background-color: #1e1e1e; color: #f0f0f0; border: 1px solid #3a3a3a; }
                """
            )
        else:
            app.setStyleSheet("")

    # ---- Apply helpers ----
    def apply_to_editor(self, editor: Optional[EditorWithStyleSheet]) -> None:
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

    def apply_widget(self, widget: Optional[QWidget]) -> None:
        """Apply current palette to a specific widget (useful for dialogs)."""
        if widget is None:
            return
        pal = self._build_dark_palette() if self.state.is_dark_mode else self._build_light_palette()
        try:
            widget.setPalette(pal)
        except Exception:
            pass

    def apply_to_secondary(self, secondary_window: Optional[ThemeApplier]) -> None:
        if secondary_window is None:
            return
        try:
            secondary_window.apply_theme(self.state.is_dark_mode)
        except (AttributeError, RuntimeError):
            # Be tolerant: the secondary window might not be fully initialised or already deleted.
            pass
