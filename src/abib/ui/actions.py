# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from PySide6.QtGui import QAction, QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QToolBar
from PySide6.QtCore import QSize

from abib.core import shared as sh


@dataclass
class ActionsBundle:
    file_toolbar: Optional[QToolBar]
    edit_toolbar: Optional[QToolBar]
    actions: List[QAction]


@dataclass
class ShortcutsBundle:
    shortcuts: List[QShortcut]


def setup_shortcuts(window) -> ShortcutsBundle:
    """Create keyboard shortcuts and attach them to the given window.

    Returns a bundle to keep references alive for the lifetime of the window.
    """
    shortcuts: List[QShortcut] = []

    # Ctrl++
    sc_inc1 = QShortcut(QKeySequence("Ctrl++"), window)
    sc_inc1.activated.connect(window.increase_font_size)
    shortcuts.append(sc_inc1)

    # Ctrl+= (many keyboards)
    sc_inc2 = QShortcut(QKeySequence("Ctrl+="), window)
    sc_inc2.activated.connect(window.increase_font_size)
    shortcuts.append(sc_inc2)

    # Ctrl+-
    sc_dec = QShortcut(QKeySequence("Ctrl+-"), window)
    sc_dec.activated.connect(window.decrease_font_size)
    shortcuts.append(sc_dec)

    return ShortcutsBundle(shortcuts=shortcuts)


def setup_menus_and_toolbars(window) -> ActionsBundle:
    """Create menus, toolbars, and actions on the provided main window.

    Mirrors the previous inline setup in Abib.MainWindow.initui, wiring the same
    icons, labels, status tips, and signal handlers.
    """
    # Get the menu bar; QMainWindow.menuBar() ensures one exists
    mb = window.menuBar()

    # File toolbar/menu
    file_toolbar = QToolBar("File")
    file_toolbar.setIconSize(QSize(14, 14))
    window.addToolBar(file_toolbar)
    file_menu = mb.addMenu("&File")

    # GitHub Releases
    github_icon_path = sh.images_dir / 'github.png'
    github_action = QAction(QIcon(str(github_icon_path)), "GitHub Releases", window)
    github_action.setStatusTip("Open GitHub releases page")
    github_action.triggered.connect(window.open_github_releases)
    file_menu.addAction(github_action)
    file_menu.addSeparator()

    # Open file
    icon1_path = sh.images_dir / 'blue-folder-open-document.png'
    open_file_action = QAction(QIcon(str(icon1_path)), "Open file...", window)
    open_file_action.setStatusTip("Open file")
    open_file_action.triggered.connect(window.file_open)
    file_menu.addAction(open_file_action)
    file_toolbar.addAction(open_file_action)

    # Print
    icon2_path = sh.images_dir / 'printer.png'
    print_action = QAction(QIcon(str(icon2_path)), "Print...", window)
    print_action.setStatusTip("Print current page")
    print_action.triggered.connect(window.file_print)
    file_menu.addAction(print_action)
    file_toolbar.addAction(print_action)

    # Exit
    icon3_path = sh.images_dir / 'exit.png'
    exit_action = QAction(QIcon(str(icon3_path)), "Exit", window)
    exit_action.setStatusTip("Exit the program")
    exit_action.triggered.connect(window.close)
    file_menu.addAction(exit_action)

    # Edit toolbar/menu
    edit_toolbar = QToolBar("Edit")
    # Use a fixed, small icon size consistent with the File toolbar
    edit_toolbar.setIconSize(QSize(14, 14))
    window.addToolBar(edit_toolbar)
    edit_menu = window.menuBar().addMenu("&Edit")

    # Copy
    icon4_path = sh.images_dir / 'document-copy.png'
    copy_action = QAction(QIcon(str(icon4_path)), "Copy", window)
    copy_action.setStatusTip("Copy selected text")
    copy_action.triggered.connect(window.textEditor.copy)
    edit_toolbar.addAction(copy_action)
    edit_menu.addAction(copy_action)

    # Select All
    icon5_path = sh.images_dir / 'selection-input.png'
    select_action = QAction(QIcon(str(icon5_path)), "Select all", window)
    select_action.setStatusTip("Select all text")
    select_action.triggered.connect(window.textEditor.selectAll)
    edit_menu.addAction(select_action)

    # Help menu items
    help_menu = window.menuBar().addMenu("&Help")

    icon6_path = sh.images_dir / 'license.png'
    copyright_action = QAction(QIcon(str(icon6_path)), "LICENSE", window)
    copyright_action.setStatusTip("License")
    copyright_action.triggered.connect(window.copyright)
    help_menu.addAction(copyright_action)

    help_menu.addSeparator()
    icon7_path = sh.images_dir / 'question.png'
    help_action = QAction(QIcon(str(icon7_path)), "Abib Help", window)
    help_action.setStatusTip("Help file")
    help_action.triggered.connect(window.helper)
    help_menu.addAction(help_action)

    help_menu.addSeparator()
    icon8_path = sh.images_dir / 'details.png'
    readme_action = QAction(QIcon(str(icon8_path)), "Readme", window)
    readme_action.setStatusTip("Readme file")
    readme_action.triggered.connect(window.readme)
    help_menu.addAction(readme_action)

    help_menu.addSeparator()
    icon9_path = sh.images_dir / 'about.png'
    about_action = QAction(QIcon(str(icon9_path)), "About", window)
    about_action.setStatusTip("About Abib")
    about_action.triggered.connect(window.show_about_dialog)
    help_menu.addAction(about_action)

    help_menu.addSeparator()
    icon10_path = sh.images_dir / 'settings.png'
    # Create a Settings submenu under Help
    settings_menu = help_menu.addMenu(QIcon(str(icon10_path)), "Settings")
    # First item: open the full Settings dialog
    settings_action = QAction("Open Settings...", window)
    settings_action.setStatusTip("Open Settings dialog")
    settings_action.triggered.connect(window.open_settings_dialog)
    settings_menu.addAction(settings_action)
    # Build a tickable list of Other Works under the Settings submenu
    # Prefer a public helper on the window; fall back to a private one if present
    try:
        builder = getattr(window, "build_show_works_menu", None)
        if not callable(builder):
            # Backward-compatible fallback: use a private method if available
            builder = getattr(window, "_build_show_works_menu", None)
        if callable(builder):
            builder(settings_menu)
    except (AttributeError, RuntimeError, TypeError, ValueError):
        # If dynamic building fails, ignore to keep the app functional
        pass

    # Note: Gill auto-follow setting has been moved to the main Settings dialog.

    actions = [
        github_action, open_file_action, print_action, exit_action,
        copy_action, select_action,
        copyright_action, help_action, readme_action, about_action, settings_action,
    ]

    return ActionsBundle(
        file_toolbar=file_toolbar,
        edit_toolbar=edit_toolbar,
        actions=actions,
    )
