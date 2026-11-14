# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


from types import SimpleNamespace
from typing import cast

from abib import Abib as AbibModule
from abib.services import search_service
from abib.services.data_loader import DataLoader


def test_concordance_reference_activation_navigates_like_search_result(monkeypatch):
    pushed: list[tuple[object, int]] = []
    displayed: list[int] = []

    monkeypatch.setattr(AbibModule, "forward", SimpleNamespace(clear=lambda: None))
    # noinspection PyUnresolvedReferences
    monkeypatch.setattr(AbibModule.history, "back_push", lambda win, line: pushed.append((win, line)))

    window = SimpleNamespace(get_line_number=lambda: 3)
    window.display_verse_from_history = displayed.append

    AbibModule.MainWindow._on_concordance_reference_activated(
        cast(AbibModule.MainWindow, cast(object, window)), 7, "light")

    # The window's own methods now push ``self`` (the live window) to history
    # rather than reaching for a module-level global handle.
    assert pushed == [(window, 3)]
    assert displayed == [7]


def test_concordance_reference_activation_syncs_highlight_state():
    search_service.set_search_data(DataLoader().load_search())

    class DummyWindow:
        def __init__(self):
            self.key = ""
            self.keym = ""
            self.store = ""
            self.occurs = []
            self.occur = []
            self.verse = -1
            self.finding = -1
            self.occurrence = -1
            self.occurring = 0
            self.y = -1
            self.yend = -1
            self.dlg = None

    win = DummyWindow()
    # Test verse position 2 (Gen 1:3), term 'light'
    AbibModule.MainWindow._sync_concordance_state_for_result(
        cast(AbibModule.MainWindow, cast(object, win)), 2, "light")

    assert win.key == "light"
    assert win.occurs == [2]
    assert len(win.occur[0]) == 2
    assert win.y == win.occur[0][0][0]
    assert win.yend == win.occur[0][0][1]
    assert win.dlg is not None
    assert win.dlg.checks[0] == 3