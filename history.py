# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Any, List, Tuple


class History:
    """Encapsulates navigation history (back/forward) for MainWindow.

    Stores full state tuples identical to the previous global implementation so
    popping restores the same attributes on the window instance.
    """

    def __init__(self) -> None:
        self.back: List[Tuple[Any, ...]] = []
        self.forward: List[Tuple[Any, ...]] = []

    def _snapshot(self, win) -> Tuple[Any, ...]:
        return (
            win.current_position if hasattr(win, "current_position") else 0,
            win.y,
            win.hiLita.lineinc,
            win.hiLita.keyinc,
            win.hiLita.fmt,
            win.hiLita.length,
            win.no_f3_yet,
            win.occurring,
            win.key,
            getattr(win, "dlg", None),
        )

    def back_push(self, win, current_position: int) -> None:
        if len(self.back) == 0:
            saving = (
                current_position,
                win.y,
                win.hiLita.lineinc,
                win.hiLita.keyinc,
                win.hiLita.fmt,
                win.hiLita.length,
                win.no_f3_yet,
                win.occurring,
                win.key,
                getattr(win, "dlg", None),
            )
            self.back.append(saving)
        else:
            last_item = self.back[-1]
            if not (last_item[0] == current_position and last_item[1] == win.y):
                saving = (
                    current_position,
                    win.y,
                    win.hiLita.lineinc,
                    win.hiLita.keyinc,
                    win.hiLita.fmt,
                    win.hiLita.length,
                    win.no_f3_yet,
                    win.occurring,
                    win.key,
                    getattr(win, "dlg", None),
                )
                self.back.append(saving)

    def back_pop(self, win) -> int:
        current_position = 0
        if self.back:
            saving = self.back.pop()
            current_position = saving[0]
            win.y = saving[1]
            win.hiLita.lineinc = saving[2]
            win.hiLita.keyinc = saving[3]
            win.hiLita.fmt = saving[4]
            win.hiLita.length = saving[5]
            win.no_f3_yet = saving[6]
            win.occurring = saving[7]
            win.key = saving[8]
            win.dlg = saving[9]
        return current_position

    def forward_push(self, win, current_position: int) -> None:
        if len(self.forward) == 0:
            saving = (
                current_position,
                win.y,
                win.hiLita.lineinc,
                win.hiLita.keyinc,
                win.hiLita.fmt,
                win.hiLita.length,
                win.no_f3_yet,
                win.occurring,
                win.key,
                getattr(win, "dlg", None),
            )
            self.forward.append(saving)
        else:
            last_item = self.forward[-1]
            if not (last_item[0] == current_position and last_item[1] == win.y):
                saving = (
                    current_position,
                    win.y,
                    win.hiLita.lineinc,
                    win.hiLita.keyinc,
                    win.hiLita.fmt,
                    win.hiLita.length,
                    win.no_f3_yet,
                    win.occurring,
                    win.key,
                    getattr(win, "dlg", None),
                )
                self.forward.append(saving)

    def forward_pop(self, win) -> int:
        current_position = 0
        if self.forward:
            saving = self.forward.pop()
            current_position = saving[0]
            win.y = saving[1]
            win.hiLita.lineinc = saving[2]
            win.hiLita.keyinc = saving[3]
            win.hiLita.fmt = saving[4]
            win.hiLita.length = saving[5]
            win.no_f3_yet = saving[6]
            win.occurring = saving[7]
            win.key = saving[8]
            win.dlg = saving[9]
        return current_position
