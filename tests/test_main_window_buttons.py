# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from typing import cast

# noinspection PyPackageRequirements
from PySide6.QtCore import Qt

# noinspection PyPackageRequirements
from PySide6.QtGui import QShortcut

# noinspection PyPackageRequirements
from PySide6.QtWidgets import QComboBox, QGridLayout, QLineEdit, QPushButton, QWidget

from abib.Abib import MainWindow


class _MainWindowButtonHarness(QWidget):
    def __init__(self):
        super().__init__()
        self.comboBox_1 = QComboBox(self)
        self.comboBox_2 = QComboBox(self)
        self.comboBox_3 = QComboBox(self)
        self.display_verse_input = QLineEdit(self)
        self.calls = []

        for name in (
            "goto_book",
            "goto_chapter",
            "goto_verse",
            "goto_line",
            "toggle_dark_mode",
            "search_current_word",
            "repeat_find_forward",
            "history_back",
            "history_forward",
            "earlier_book",
            "later_book",
            "earlier_chapter",
            "later_chapter",
            "open_commentary_window_shortcut",
            "show_devotional",
            "open_commentary_window",
            "copy_verse_with_reference",
        ):
            setattr(self, name, lambda *_args: None)

    def open_mhcc_for_current_verse(self):
        self.calls.append("mhcc")

    def open_strongs_window(self):
        self.calls.append("strongs")

    def _normalize_control_heights(self):
        pass


def _button_at(grid: QGridLayout, row: int, column: int) -> QPushButton:
    item = grid.itemAtPosition(row, column)
    assert item is not None
    button = item.widget()
    assert isinstance(button, QPushButton)
    return button


def test_study_and_strongs_buttons_occupy_bottom_right_cells(qapp):
    window = _MainWindowButtonHarness()
    grid = QGridLayout()

    MainWindow._layout_widgets(cast(MainWindow, cast(QWidget, window)), grid)

    mhcc_button = _button_at(grid, 4, 4)
    strongs_button = _button_at(grid, 5, 4)
    assert mhcc_button.text() == "Matthew Henry"
    assert strongs_button.text() == "Strong's Lookup"
    assert mhcc_button.focusPolicy() == Qt.FocusPolicy.NoFocus
    assert strongs_button.focusPolicy() == Qt.FocusPolicy.NoFocus

    mhcc_button.click()
    strongs_button.click()
    assert window.calls == ["mhcc", "strongs"]

    shortcuts = {shortcut.key().toString() for shortcut in window.findChildren(QShortcut)}
    assert "Ctrl+Shift+M" in shortcuts
    assert "Ctrl+Shift+S" in shortcuts