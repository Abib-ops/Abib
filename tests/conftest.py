# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


import os

import pytest

# Run Qt headlessly so widget tests work without a display.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session", autouse=True)
def qapp():
    """Provide a session-wide QApplication for tests that touch Qt objects."""
    # noinspection PyPackageRequirements
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    yield app

    # Deterministic teardown so PySide6/Qt objects are destroyed while the
    # interpreter is still alive, avoiding a segfault at shutdown.
    for widget in QApplication.topLevelWidgets():
        widget.close()
        widget.deleteLater()
    app.processEvents()
    app.quit()
