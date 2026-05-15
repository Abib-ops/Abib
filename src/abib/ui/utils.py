# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations
from PySide6.QtWidgets import QApplication
from typing import cast

def get_screen_size() -> tuple[int, int]:
    """Get the primary screen dimensions."""
    app_instance = QApplication.instance()
    if app_instance is None:
        # If no QApplication exists, create a temporary one
        temp_app = QApplication([])
        size = temp_app.primaryScreen().size()
        width, height = size.width(), size.height()
        temp_app.quit()
        return width, height
    else:
        # Cast to QApplication to access primaryScreen()
        app = cast(QApplication, app_instance)
        size = app.primaryScreen().size()
        return size.width(), size.height()
