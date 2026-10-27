# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Search controller extracted from ``MainWindow``.

Holds the Find-dialog lifecycle (F3) and the find-next orchestration (F4):
launching/showing/closing the Find window, deciding which search strategy to
run (``find_next``), driving a ranged search (``find_in_range``) and stepping
through subsequent matches for the raw and whole-word strategies
(``find_f4`` / ``find_f4_alt``), plus the F3/F4 key entry points
(``search_current_word`` / ``repeat_find_forward``).

``MainWindow`` keeps thin delegating methods, so the F-key shortcuts, the Find
button and the Find dialog callbacks that are wired to ``self.<name>`` remain
unchanged. The controller operates on the owning window via ``self._win`` and
reuses the module-level history stacks, the ``get_next_occurrence`` helper and
the ``book_bounds`` table defined in ``abib.Abib`` (imported lazily to avoid an
import cycle). Pure matching/iteration continues to live in
``abib.services.search_service`` via the window's existing thin delegators.
"""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Any

from abib.core import shared as sh
from abib.services import search_service

if TYPE_CHECKING:
    from abib.Abib import MainWindow


class SearchController:
    """Encapsulate the Find behaviour of ``MainWindow``."""

    def __init__(self, window: MainWindow) -> None:
        self._win = window

    # ENTRY POINT FOR F3 FIND.
    def on_find_button_clicked(self) -> None:
        """Launch the Find dialog box."""
        win = self._win
        win.reload()  # Reload KJB_PCE.txt if another file loaded.

        if win.dlg is None:
            from abib.ui.find_dialog import FindDialog  # deferred import
            win.dlg = FindDialog(win, settings_service=win.settings_service)
            # Apply the theme palette to the Find dialog (apply_widget is internally safe)
            win.theme.apply_widget(win.dlg)
            win.dlg.exec()
        else:
            self.show_find_window()

    def show_find_window(self) -> None:
        """Show the Find window."""
        win = self._win
        if win.dlg is None:
            from abib.ui.find_dialog import FindDialog  # deferred import
            win.dlg = FindDialog(win, settings_service=win.settings_service)
            # Apply the theme palette to the Find dialog (apply_widget is internally safe)
            win.theme.apply_widget(win.dlg)
            win.dlg.show()
        else:
            # Ensure the theme is applied before showing
            win.theme.apply_widget(win.dlg)
            win.dlg.show()

    def close_find_window(self) -> None:
        """Close the Find window."""
        self._win.dlg.hide()

    # ENTRY POINT FOR F4 FIND NEXT.
    def find_next(self) -> None:
        """Spaghetti Junction."""
        win = self._win
        win.display_verse_input.setFocus()

        if win.dlg.checks[0] != 1 or win.dlg.checks[2] == 6:
            self.find_f4_alt()
        elif win.dlg.checks[0] == 1:
            if win.gent is None:
                win.search_current_word()
            else:
                self.find_f4()

    def find_in_range(self, x_start: int, x_end: int) -> None:
        """Find function."""
        from abib.Abib import book_bounds, get_next_occurrence

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self._win

        #win.display_verse_input.setFocus()
        current_position = win.get_line_number()
        savedx = current_position
        error_flag = False

        win.prepare_key_for_find()
        try:
            x1 = int(book_bounds[x_start])
        except (IndexError, TypeError, ValueError):
            x1 = 0
        try:
            x2 = int(book_bounds[x_end + 1]) - 1
        except (IndexError, TypeError, ValueError):
            x2 = sh.LAST_VERSE_IN_BIBLE
        current_position = x1

        win.no_f3_yet = 1

        win.keym = win.key
        if win.key == '' or win.key == ' ':
            win.y = -1
            win.no_f3_yet = 0
            win.occurring = 0
            win.statusBar.clearMessage()
            win.statusBar.repaint()
        else:
            win.statusBar.showMessage('Finding...')
            win.statusBar.repaint()
            keylow = win.key.lower()
            win.y = 0
            win.occurring = 0

            if win.dlg.checks[2] == 6:
                win.iterate_regex(search_service.get_search_data().Rnew, x1, x2)
                if win.occurring != 0:
                    win.y = win.occur[0][0][0]
                    win.occurrence = 0
                    win.verse = 0
                    win.finding = -1
                    current_position = get_next_occurrence()
                    if win.message:
                        win.statusBar.showMessage(win.message)
                    win.statusBar.repaint()
            else:
                tv = win.dlg.checks[0] == 1   # Raw
                if not tv:
                    current_position = win.find_whole_word(x1, x2)
                elif tv:
                    # Raw.
                    current_position = win.find_raw(current_position, x1, x2, keylow)

        if win.occurring == 0:
            current_position = savedx
            win.on_error('Not found...', 2000, True)
            error_flag = True

        if win.key in ('q', 'Q'):
            win.display_verse_input.clear()
            sys.exit()
        if not error_flag:
            win.goto_line_find(current_position)
        win.update_search_results_panel()

    def find_f4(self) -> None:
        """Repeat find frontend for raw search."""
        from abib.Abib import back, forward, history

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self._win

        if win.occurrence < win.occurring:
            current_position = win.get_line_number()

            if forward:
                history.back_push(win, current_position)
                while forward:
                    b_ = forward.pop()
                    back.append(b_)
            else:
                forward.clear()
                history.back_push(win, current_position)

            # Ensure win.gent is a valid generator
            gent = win.gent
            if gent is None:
                raise ValueError(
                    "self.gent has not been initialized. It must be assigned a valid generator before calling find_f4.")

            try:
                current_position, win.y, win.occurrence = next(gent)
            except StopIteration:
                # Handle generator exhaustion if needed
                win.statusBar.showMessage("Search completed: no more matches.")
                return

            # Set the status bar message and other UI updates.
            win.statusBar.showMessage(win.nav.get_status_message(current_position))
            if win.message:
                win.statusBar.showMessage(win.message)
            win.statusBar.repaint()
            win.goto_line_find(current_position)

    def find_f4_alt(self) -> None:
        """Repeat find frontend for Whole words."""
        from abib.Abib import back, forward, get_next_occurrence, history

        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self._win

        if len(win.occurs) > 0 and win.occurrence < win.occurring:
            current_position = win.get_line_number()
            if forward:
                history.back_push(win, current_position)
                while forward:
                    b_ = forward.pop()
                    back.append(b_)
            else:
                forward.clear()
                history.back_push(win, current_position)

            if win.dlg.checks[0] in (3, 4):
                win.verse += 1
                current_position = win.occurs[win.verse]
                win.finding = -1
            if win.dlg.checks[0] in (2, 3, 4) or win.dlg.checks[2] == 6:
                current_position = get_next_occurrence()

            if win.message:
                win.statusBar.showMessage(win.message)
            win.statusBar.repaint()
            win.goto_line_find(current_position)

    def search_current_word(self) -> None:
        """F3 key for find key entry."""
        from abib.Abib import forward, history

        win = self._win
        win.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = win.get_line_number()
        forward.clear()
        history.back_push(win, current_position)
        self.on_find_button_clicked()

    def repeat_find_forward(self) -> None:
        """Find the next key F4."""
        # 1. Create a local reference with a type hint to satisfy the linter
        win: Any = self._win

        win.reload()  # Reload KJB_PCE.txt if another file loaded.
        if win.key == ' ' or win.no_f3_yet == 0:
            pass
        else:
            win.textEditor.setFocus()
            self.find_next()
