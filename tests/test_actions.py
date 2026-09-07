# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

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