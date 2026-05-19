# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import TYPE_CHECKING, Any
from abib.core import shared as sh

if TYPE_CHECKING:
    from abib.Abib import MainWindow

class NavigationCore:
    """Core logic for Bible navigation."""
    
    def __init__(self, main_window: 'MainWindow') -> None:
        self.w = main_window

    def get_current_bcv(self) -> tuple[int, int, int]:
        """Return (book, chapter, verse) 1-based from the current context position."""
        try:
            pos = int(self.w.last_context_position) if hasattr(self.w, "last_context_position") else int(self.w.get_line_number())
        except (TypeError, ValueError, AttributeError):
            pos = 0
        try:
            entry = sh.Info[pos]
            # Info stores [book(0..65), chapter(0..), verse(0..)]
            b = int(entry[0]) + 1
            c = int(entry[1]) + 1
            v = int(entry[2]) + 1
            return b, c, v
        except (IndexError, TypeError, ValueError):
            return 1, 1, 1

    def resolve_reference(self, bits: Any) -> Any:
        """Resolves a scripture reference into (book_num, chapter, verse)."""
        from abib.domain.scripture_refs import resolve_reference
        return resolve_reference(bits)

    def get_status_message(self, index: int) -> str:
        """Constructs a status bar message for a given Bible index."""
        if index < 0 or index > sh.LAST_VERSE_IN_BIBLE:
            return ""
            
        info = sh.Info[index]
        book_id = info[0]
        chapter = info[1] + 1
        verse = info[2] + 1
        book_name = self.w.nwin[book_id]
        
        # Occurrence info if currently searching
        occ_msg = ""
        if hasattr(self.w, 'keym') and self.w.keym:
             occ_msg = f'Occurrence {self.w.occurrence}/{self.w.occurring} of "{self.w.keym}"  -  '

        end_msg = "..." if getattr(self.w, 'occurrence', 0) != getattr(self.w, 'occurring', 0) else "."
        
        if getattr(self.w, 'occurrence', 0) == getattr(self.w, 'occurring', 0):
             setattr(self.w, 'no_f3_yet', 0)

        if book_id in sh.onechapterbooks:
            return f'{occ_msg}{book_name} {verse} KJV{end_msg}'
        else:
            return f'{occ_msg}{book_name} {chapter}:{verse} KJV{end_msg}'

    @staticmethod
    def calculate_line(book: int, chapter: int, verse: int, current_line: int = 0) -> int:
        """Resolves (B, C, V) to a global 0-based verse index."""
        from abib.domain.scripture_refs import calculate_book_line
        result = calculate_book_line(book, chapter, verse, current_line)
        if result is None:
             raise ValueError("Invalid scripture reference")
        return result
