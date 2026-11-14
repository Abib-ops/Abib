# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


import os
from types import SimpleNamespace

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


class NavigationRecorder:
    """Records what a main-window jump does to Abib's history and display."""

    def __init__(self) -> None:
        self.history: list[tuple[object, int]] = []
        self.cleared: list[bool] = []
        self.displayed: list[int] = []
        self.window = SimpleNamespace(
            get_line_number=lambda: 4,
            display_verse_from_history=self.displayed.append,
        )

    def assert_navigated_to(self, position: int) -> None:
        assert self.history == [(self.window, 4)]
        assert self.cleared == [True]
        assert self.displayed == [position]


@pytest.fixture
def navigation_recorder(monkeypatch) -> NavigationRecorder:
    """Replace Abib's back/forward history with recorders and provide a fake window at verse 4."""
    from abib import Abib as AbibModule

    recorder = NavigationRecorder()
    monkeypatch.setattr(
        AbibModule, "forward", SimpleNamespace(clear=lambda: recorder.cleared.append(True))
    )
    monkeypatch.setattr(
        AbibModule,
        "history",
        SimpleNamespace(
            back_push=lambda owner, position: recorder.history.append((owner, position))
        ),
    )
    return recorder
