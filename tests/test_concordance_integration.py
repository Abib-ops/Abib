# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from abib import Abib as AbibModule


def test_concordance_reference_activation_navigates_like_search_result(monkeypatch):
    pushed: list[tuple[object, int]] = []
    displayed: list[int] = []

    monkeypatch.setattr(AbibModule, "forward", SimpleNamespace(clear=lambda: None))
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(AbibModule.history, "back_push", lambda win, line: pushed.append((win, line)))

    window = SimpleNamespace(get_line_number=lambda: 3)
    window.display_verse_from_history = displayed.append

    AbibModule.MainWindow._on_concordance_reference_activated(
        cast(AbibModule.MainWindow, cast(object, window)), 7)

    # The window's own methods now push ``self`` (the live window) to history
    # rather than reaching for a module-level global handle.
    assert pushed == [(window, 3)]
    assert displayed == [7]