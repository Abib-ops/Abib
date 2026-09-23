"""Regression test: an open Strong's window follows the theme when it changes.

Previously ``ThemeController.refresh_theme_across_ui`` re-themed the dialog,
about, text-edit and Gill commentary windows but not the Strong's Lookup
window, so its background stayed dark/black after a light/dark toggle.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from abib.Abib import MainWindow
from abib.ui.theme_controller import ThemeController


class _FakeStrongsWin:
    def __init__(self) -> None:
        self.applied_theme: bool | None = None
        self.palette_applied: bool = False

    def apply_theme(self, is_dark: bool) -> None:
        self.applied_theme = is_dark


def _make_window(strongs_win: Any) -> SimpleNamespace:
    palette_targets: list[Any] = []

    theme = SimpleNamespace(
        state=SimpleNamespace(is_dark_mode=True),
        apply_app_palette=lambda: None,
        apply_to_editor=lambda editor: None,
        apply_widget=lambda widget: palette_targets.append(widget),
    )

    win = SimpleNamespace(
        theme=theme,
        textEditor=None,
        update_text_display_theme=lambda: None,
        display_verse_input=SimpleNamespace(setStyleSheet=lambda style: None),
        okButton=None,
        dlg=None,
        about_window=None,
        text_edit_window=None,
        gill_win=None,
        strongs_win=strongs_win,
        _palette_targets=palette_targets,
    )
    return win


def test_refresh_theme_reapplies_to_open_strongs_window():
    strongs_win = _FakeStrongsWin()
    win = _make_window(strongs_win)

    ThemeController(cast(MainWindow, cast(object, win))).refresh_theme_across_ui()

    # The window's stored theme is re-applied (background follows the theme)...
    assert strongs_win.applied_theme is True
    # ...and its palette is refreshed via apply_widget.
    assert strongs_win in win._palette_targets


def test_refresh_theme_skips_when_no_strongs_window():
    win = _make_window(None)

    # Must not raise when the Strong's window has never been opened.
    ThemeController(cast(MainWindow, cast(object, win))).refresh_theme_across_ui()

    assert win._palette_targets == []
