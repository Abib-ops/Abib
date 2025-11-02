from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Protocol

try:
    # Import only the minimal Qt class we need to type the editor
    from PySide6.QtWidgets import QPlainTextEdit
except ImportError:  # pragma: no cover - allows importing this module without Qt
    QPlainTextEdit = object  # type: ignore


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

    def apply_to_secondary(self, secondary_window: Optional[ThemeApplier]) -> None:
        if secondary_window is None:
            return
        try:
            secondary_window.apply_theme(self.state.is_dark_mode)
        except (AttributeError, RuntimeError):
            # Be tolerant: the secondary window might not be fully initialised or already deleted.
            pass
