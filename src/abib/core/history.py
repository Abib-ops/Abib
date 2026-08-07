# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from copy import deepcopy
from typing import Any


class History:
    """Encapsulates navigation history (back/forward) for the MainWindow.

    Stores full state tuples identical to the previous global implementation,
    so popping restores the same attributes on the window instance.
    """

    def __init__(self) -> None:
        self.back: list[tuple[Any, ...]] = []
        self.forward: list[tuple[Any, ...]] = []

    @staticmethod
    def _snapshot(win) -> tuple[Any, ...]:
        return (
            win.current_position if hasattr(win, "current_position") else 0,
            win.y,
            win.yend,
            win.hiLita.lineinc,
            win.hiLita.keyinc,
            win.hiLita.fmt,
            win.hiLita.length,
            win.no_f3_yet,
            win.occurring,
            win.occurrence,
            win.verse,
            win.finding,
            win.key,
            win.keym,
            win.store,
            deepcopy(win.occurs),
            deepcopy(win.occur),
            deepcopy(win.count),
            getattr(win, "dlg", None),
        )

    # ---- Internal helpers to remove duplication ----
    @staticmethod
    def _build_saving(win, current_position: int) -> tuple[Any, ...]:
        """Create a snapshot tuple using an explicit current_position.

        We do not rely on win.current_position here to keep behaviour identical
        to existing call sites that pass the intended position explicitly.
        """
        return (
            current_position,
            win.y,
            win.yend,
            win.hiLita.lineinc,
            win.hiLita.keyinc,
            win.hiLita.fmt,
            win.hiLita.length,
            win.no_f3_yet,
            win.occurring,
            win.occurrence,
            win.verse,
            win.finding,
            win.key,
            win.keym,
            win.store,
            deepcopy(win.occurs),
            deepcopy(win.occur),
            deepcopy(win.count),
            getattr(win, "dlg", None),
        )

    @staticmethod
    def _restore_from_saving(win, saving: tuple[Any, ...]) -> int:
        """Restore a window state from a snapshot tuple and return position."""
        current_position = saving[0]
        win.y = saving[1]
        if len(saving) == 12:
            win.hiLita.lineinc = saving[2]
            win.hiLita.keyinc = saving[3]
            win.hiLita.fmt = saving[4]
            win.hiLita.length = saving[5]
            win.no_f3_yet = saving[6]
            win.occurring = saving[7]
            win.occurrence = saving[8]
            win.key = saving[9]
            win.keym = saving[10]
            win.dlg = saving[11]
            return current_position
        win.yend = saving[2]
        win.hiLita.lineinc = saving[3]
        win.hiLita.keyinc = saving[4]
        win.hiLita.fmt = saving[5]
        win.hiLita.length = saving[6]
        win.no_f3_yet = saving[7]
        win.occurring = saving[8]
        win.occurrence = saving[9]
        win.verse = saving[10]
        win.finding = saving[11]
        win.key = saving[12]
        win.keym = saving[13]
        win.store = saving[14]
        win.occurs = deepcopy(saving[15])
        win.occur = deepcopy(saving[16])
        win.count = deepcopy(saving[17])
        win.dlg = saving[18]
        return current_position

    def _push(self, stack: list[tuple[Any, ...]], win, current_position: int) -> None:
        """Generic push with deduplication on (position, y)."""
        saving = self._build_saving(win, current_position)
        if not stack:
            stack.append(saving)
            return
        last = stack[-1]
        if not (last[0] == current_position and last[1] == win.y):
            stack.append(saving)

    def _pop(self, stack: list[tuple[Any, ...]], win) -> int:
        """Generic pop that restores state and returns the position, or 0 if empty."""
        if not stack:
            return 0
        saving = stack.pop()
        return self._restore_from_saving(win, saving)

    def back_push(self, win, current_position: int) -> None:
        self._push(self.back, win, current_position)

    def back_pop(self, win) -> int:
        return self._pop(self.back, win)

    def forward_push(self, win, current_position: int) -> None:
        self._push(self.forward, win, current_position)

    def forward_pop(self, win) -> int:
        return self._pop(self.forward, win)
