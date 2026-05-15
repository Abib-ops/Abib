# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import Any
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat

class SyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter."""

    def __init__(self, parent) -> None:
        """Initialise highlighter."""
        super(SyntaxHighlighter, self).__init__(parent)
        self._highlight_lines: dict[int, QTextCharFormat] = {}
        self.lineinc = 0
        self.keyinc = 0
        self.position = 0
        self.length = 1
        self.fmt: QTextCharFormat | None = None
        self.clear = False

    def highlight_line(self, line_num, fmt) -> None:
        """Highlight lines."""

        if isinstance(line_num, int) and \
                (line_num >= 0) and (isinstance(fmt, QTextCharFormat)):
            self._highlight_lines[line_num] = fmt
            block = self.document().findBlockByLineNumber(line_num)
            self.rehighlightBlock(block)

    def clear_highlight(self) -> None:
        """Clear highlight."""

        if self.clear:
            self._highlight_lines = {}
            self.rehighlight()

    def highlightBlock(self, text: str) -> None:
        """Highlight a block."""
        from abib import Abib
        w = Abib.w

        # 1. Create a local reference with a type hint to satisfy the linter
        assert w is not None
        win: Any = w

        # Do not apply search/verse highlighting when viewing non-Bible files
        try:
            if getattr(win, 'otherFileFlag', False):
                return
        except (AttributeError, RuntimeError):
            # If the state is unavailable, fall through and rely on existing guards
            pass

        # Ensure _highlight_lines is populated
        if not self._highlight_lines:
            # print ("Skipping highlight: _highlight_lines not populated yet.")
            return

        blockNumber = self.currentBlock().blockNumber()
        self.fmt = self._highlight_lines.get(blockNumber)
        if self.fmt is not None:
            # noinspection PyTypeChecker
            self.position = win.y + self.lineinc
            if win.dlg is not None:
                if win.dlg.checks[2] != 6:
                    self.length = len(win.key) + self.keyinc
                else:
                    self.length += self.keyinc
            else:
                self.length = len(win.key) + self.keyinc
            self.setFormat(self.position, self.length, self.fmt)
            # print(f'Block {blockNumber} {KJV[blockNumber]}')
