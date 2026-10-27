# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Verse-navigation controller extracted from ``MainWindow``.

Holds the logic for moving the reader around the Bible text: the
``display_verse`` entry point (F2), the book/chapter/verse combo-box handlers,
reference-string resolution, the earlier/later book and chapter steppers and the
history back/forward navigation.

``MainWindow`` keeps thin delegating methods, so the combo-box signals, toolbar
buttons and F-key shortcuts that are wired to ``self.<name>`` remain unchanged.
The controller operates on the owning window via ``self._win`` and reuses the
module-level history stacks and ``reset_attributes`` helper defined in
``abib.Abib`` (imported lazily to avoid an import cycle).
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from abib.core import fcs
from abib.core import shared as sh

if TYPE_CHECKING:
    from abib.Abib import MainWindow


class NavigationController:
    """Encapsulate the verse-navigation behaviour of ``MainWindow``."""

    def __init__(self, window: MainWindow) -> None:
        self._win = window

    def _begin_navigation(self) -> Any:
        """Run the common navigation preamble and return the window handle.

        Reloads the Bible file if another was loaded, records the current
        position in history, clears the forward stack and resets display
        attributes. Shared by the ``goto_*`` navigation entry points.
        """
        from abib.Abib import forward, history, reset_attributes

        win: Any = self._win
        win.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = win.get_line_number()
        forward.clear()
        history.back_push(win, current_position)
        reset_attributes()
        return win

    # ENTRY POINT FOR F2 DISPLAY VERSE.
    def goto_line(self, ref: str = '') -> None:
        """Move the display to the line requested."""
        win = self._begin_navigation()
        if not ref:
            ref = win.display_verse_input.text()
        ref = fcs.remove_junk(ref)
        if ref in ('q', 'Q'):
            win.display_verse_input.clear()
            sys.exit()

        current_position = self.reference_to_line_number(ref)
        if current_position == -1:
            win.display_verse_input.clear()
        else:
            current_position = max(current_position, 0)
            current_position = min(current_position, sh.LAST_VERSE_IN_BIBLE)
            win.display_verse(current_position)

    def goto_book(self, _index: int) -> None:
        """Move the display to the line requested by comboBox_1."""
        win = self._begin_navigation()
        book: int = win.comboBox_1.currentIndex()
        # book is an index 0-65
        if book == sh.BOOKS_IN_THE_BIBLE - 1:
            b = 22  # Number of chapters in Revelation
        else:
            a: int = sh.Info.index((book + 1, 0, 0))
            b: int = sh.Info[a - 1][1] + 1  # No. of chapters in the book.
        win.nchapters = []
        for _ in range(1, b + 1):
            win.nchapters.append(str(_))
        win.comboBox_2.clear()
        win.comboBox_2.addItems(win.nchapters)
        win.comboBox_3.clear()
        win.nverses = ['1']
        win.comboBox_3.addItems(win.nverses)
        ref = win.nwin[book]
        ref = ref.replace(' ', '')
        current_position = self.reference_to_line_number(ref, book)
        current_position = max(current_position, 0)
        current_position = min(current_position, sh.LAST_VERSE_IN_BIBLE)
        win.display_verse(current_position)
        self.goto_chapter(_index)

    def goto_chapter(self, _index: int) -> None:
        """Move the display to the line requested by comboBox_2."""
        win = self._begin_navigation()
        book: int = win.comboBox_1.currentIndex()
        chapter: int = win.comboBox_2.currentIndex()
        if chapter == int(win.nchapters[-1]) - 1:
            # No. of verses in the chapter.
            if book == sh.BOOKS_IN_THE_BIBLE - 1:
                d = 21
            else:
                c: int = sh.Info.index((book + 1, 0, 0)) - 1
                d: int = sh.Info[c][2] + 1
        else:
            try:
                c = sh.Info.index((book, chapter + 1, 0)) - 1
            except ValueError:
                c = sh.Info.index((book + 1, 0, 0)) - 1
            d = sh.Info[c][2] + 1
        win.nverses = []
        for _ in range(1, d + 1):
            win.nverses.append(str(_))
        win.comboBox_3.clear()
        win.comboBox_3.addItems(win.nverses)

        ref = win.nwin[book]
        ref = ref.replace(' ', '')
        ref = f"{ref} {chapter + 1!s}"

        current_position = self.reference_to_line_number(ref, book, chapter)
        current_position = max(current_position, 0)
        current_position = min(current_position, sh.LAST_VERSE_IN_BIBLE)
        win.display_verse(current_position)

    def goto_verse(self, _index: int) -> None:
        """Move the display to the line requested by comboBox_3."""
        win = self._begin_navigation()
        book: int = win.comboBox_1.currentIndex()
        chapter: int = win.comboBox_2.currentIndex()
        verse: int = win.comboBox_3.currentIndex()

        ref = win.nwin[book]
        ref = ref.replace(' ', '')
        ref = f"{ref} {chapter + 1!s}.{verse + 1}"
        current_position = self.reference_to_line_number(ref, book, chapter)
        current_position = max(current_position, 0)
        current_position = min(current_position, sh.LAST_VERSE_IN_BIBLE)
        win.display_verse(current_position)

    def reference_to_line_number(self, reference_text: str, book: int = 0, chapter: int = 0) -> int:
        """Convert reference text to a line number in the Bible."""
        from abib.domain.scripture_refs import normalize_reference

        win = self._win
        current_line = win.get_line_number()
        normalized = normalize_reference(reference_text, book, chapter)

        if not normalized:
            win.on_error("Invalid format. Please enter a valid reference.", 750, True)
            return -1

        # Handle numeric-only (verse in current chapter)
        if normalized.isdigit():
            verse = int(normalized) - 1
            return win.calculate_position(current_line, verse)

        # Handle floating point-style (e.g. "23.7" -> current book)
        if fcs.is_float_re(normalized):
            normalized = fcs.attach_book_name(normalized, current_line)

        bits = fcs.split_reference(normalized)
        book_num, chapter, verse = win.nav.resolve_reference(bits)

        if not book_num:
            win.error_invalid_book()

        if book_num is None or chapter is None or verse is None:
            return -1

        try:
            position = win.nav.calculate_line(book_num, chapter, verse, current_line)
            if position is not None:
                return position
        except ValueError:
            win.error_invalid_verse_or_position()

        return -1

    def history_back(self) -> None:
        """Back key."""
        from abib.Abib import back, history

        win = self._win
        win.reload()  # Reload KJB_PCE.txt if another file loaded.
        # If we have just returned from an auxiliary file (README/COPYING/HELP),
        # skip one Back action to keep the restored verse position, rather than
        # popping history to an unrelated location (often Genesis 1:1).
        if getattr(win, "_just_restored_from_aux", False):
            win._just_restored_from_aux = False
            return
        win.message = ''
        if len(back) > 0:
            current_position: int = win.get_line_number()
            history.forward_push(win, current_position)
            current_position = history.back_pop(win)
            win.display_verse_from_history(current_position)

    def history_forward(self) -> None:
        """Forward key."""
        from abib.Abib import forward, history

        win = self._win
        win.reload()  # Reload KJB_PCE.txt if another file loaded.
        if len(forward) > 0:
            current_position: int = win.get_line_number()
            history.back_push(win, current_position)
            current_position = history.forward_pop(win)
            win.display_verse_from_history(current_position)

    def earlier_book(self) -> None:
        """Move to the earlier book."""
        from abib.Abib import forward, history, reset_attributes

        win = self._win
        win.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = win.get_line_number()
        book: int = sh.Info[current_position][0]
        newbook: int = book - 1
        if newbook < 0:
            win.on_error('No earlier book!', 3000, True)
        else:
            forward.clear()
            history.back_push(win, current_position)
            reset_attributes()
            current_position = sh.Info.index((newbook, 0, 0))
            win.display_verse(current_position)

    def later_book(self) -> None:
        """Move to the later book."""
        from abib.Abib import forward, history, reset_attributes

        win = self._win
        win.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = win.get_line_number()
        book: int = sh.Info[current_position][0]
        newbook: int = book + 1
        if newbook > sh.BOOKS_IN_THE_BIBLE - 1:
            win.on_error('No later book!', 3000, True)
        else:
            forward.clear()
            history.back_push(win, current_position)
            reset_attributes()
            current_position = sh.Info.index((newbook, 0, 0))
            win.display_verse(current_position)

    def earlier_chapter(self) -> None:
        """Move to the earlier chapter."""
        from abib.Abib import forward, history, reset_attributes

        win = self._win
        win.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = win.get_line_number()
        old_position = current_position
        book: int = sh.Info[current_position][0]
        chapter: int = sh.Info[current_position][1]
        newchapter: int = chapter - 1
        if newchapter < 0:
            newbook: int = book - 1
            if newbook < 0:
                win.on_error('No earlier chapter!', 3000, True)
                return
            while True:
                if sh.Info[current_position][0] == book:
                    current_position -= 1
                else:
                    break
            newchapter = sh.Info[current_position][1]
            book = newbook
        current_position = sh.Info.index((book, newchapter, 0))
        forward.clear()
        history.back_push(win, old_position)
        reset_attributes()
        win.display_verse(current_position)

    def later_chapter(self) -> None:
        """Move to the later chapter."""
        from abib.Abib import forward, history, reset_attributes

        win = self._win
        win.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = win.get_line_number()
        old_position = current_position
        book: int = sh.Info[current_position][0]
        chapter: int = sh.Info[current_position][1]
        newchapter: int = chapter + 1
        try:
            current_position = sh.Info.index((book, newchapter, 0))
        except ValueError:
            newbook: int = book + 1
            if newbook > sh.BOOKS_IN_THE_BIBLE - 1:
                win.on_error('No later chapter!', 3000, True)
                return
            while True:
                if sh.Info[current_position][0] == book:
                    current_position += 1
                else:
                    break
            newchapter = sh.Info[current_position][1]
            book = newbook
        current_position = sh.Info.index((book, newchapter, 0))
        forward.clear()
        history.back_push(win, old_position)
        reset_attributes()
        win.display_verse(current_position)
