# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


# noinspection PyPackageRequirements
from PySide6.QtWidgets import QMainWindow, QMenu, QTextEdit

from abib.ui.actions import setup_menus_and_toolbars


class DummyMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.textEditor = QTextEdit()

    def open_github_releases(self) -> None:
        pass

    def file_open(self) -> None:
        pass

    def file_print(self) -> None:
        pass

    def open_concordance(self) -> None:
        pass

    def open_other_works_references(self) -> None:
        pass

    def open_other_works_text_search(self) -> None:
        pass

    def open_mhcc_for_current_verse(self) -> None:
        pass

    def study_current_verse(self) -> None:
        pass

    def open_cross_references(self) -> None:
        pass

    def bookmark_current_verse(self) -> None:
        pass

    def open_bookmarks(self) -> None:
        pass

    def copy_verse_with_reference(self) -> None:
        pass

    def update_other_works(self) -> None:
        pass

    def copyright(self) -> None:
        pass

    def helper(self) -> None:
        pass

    def readme(self) -> None:
        pass

    def show_about_dialog(self) -> None:
        pass

    def open_settings_dialog(self) -> None:
        pass


def test_study_menu_matches_default_dropdown_style(qapp):
    window = DummyMainWindow()

    setup_menus_and_toolbars(window)

    study_menu = next(menu for menu in window.menuBar().findChildren(QMenu) if menu.title() == "&Study")
    assert study_menu.minimumWidth() == 0
    assert study_menu.styleSheet() == ""
    assert any(action.text().strip() == "Matthew Henry on This Verse" for action in study_menu.actions())
    bookmark_action = next(action for action in study_menu.actions() if action.text() == "Bookmark This Verse…")
    bookmarks_action = next(action for action in study_menu.actions() if action.text() == "Bookmarks and Notes")
    study_action = next(action for action in study_menu.actions() if action.text() == "Study This Verse")
    assert bookmark_action.shortcut().toString() == "Ctrl+D"
    assert bookmarks_action.shortcut().toString() == "Ctrl+Shift+B"
    assert study_action.shortcut().toString() == "Ctrl+Alt+S"
    cross_references_action = next(
        action for action in study_menu.actions() if action.text() == "Cross References"
    )
    assert cross_references_action.shortcut().toString() == "Ctrl+Shift+X"
    shortcuts = [
        action.shortcut().toString()
        for menu in window.menuBar().findChildren(QMenu)
        for action in menu.actions()
        if not action.shortcut().isEmpty()
    ]
    assert shortcuts.count("Ctrl+Shift+X") == 1

    edit_menu = next(menu for menu in window.menuBar().findChildren(QMenu) if menu.title() == "&Edit")
    assert any(action.text() == "Copy Verse with Reference" for action in edit_menu.actions())