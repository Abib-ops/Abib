# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from types import SimpleNamespace

from abib import Abib as AbibModule


def make_window_open_env(monkeypatch, tmp_path) -> SimpleNamespace:
    """Set up the shared-state monkeypatches and a base fake window.

    Both the Strong's and Gill commentary window-opening tests rely on the
    same environment: a working directory, verse metadata, a light theme and
    the current/last position bookkeeping. Callers add the window-specific
    attributes (e.g. ``strongs_win`` / ``gill_win`` / ``nav``) afterwards.
    """
    monkeypatch.setattr(AbibModule.sh, "str_cwd", str(tmp_path))
    monkeypatch.setattr(AbibModule.sh, "LAST_VERSE_IN_BIBLE", 2)
    monkeypatch.setattr(AbibModule.sh, "Info", [[0, 0, 0], [8, 0, 0], [9, 1, 2]])

    window = SimpleNamespace()
    window.settings_service = SimpleNamespace()
    window.theme = SimpleNamespace(
        state=SimpleNamespace(is_dark_mode=False),
        apply_widget=lambda widget: None,
    )
    window._last_bible_position = 1
    window._last_context_position = 1
    window.get_line_number = lambda: 2
    return window
