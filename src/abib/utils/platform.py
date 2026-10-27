# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Small platform abstraction.

Historically, the codebase scattered bare ``sys.platform`` string checks across
the UI and service layers. Centralising them here keeps the operating-system
branches in one tested place, makes the intent of each call site explicit
(``is_windows()`` reads better than ``sys.platform == 'win32'``) and gives the
rest of the application a single, portable seam to reason about cross-platform
behaviour.
"""

import platform as _platform
import sys


def is_windows() -> bool:
    """Return True when running on any Windows build."""
    return sys.platform.startswith("win")


def is_macos() -> bool:
    """Return True when running on macOS (Darwin)."""
    return sys.platform == "darwin"


def is_linux() -> bool:
    """Return True when running on Linux."""
    return sys.platform.startswith("linux")


def is_windows_10() -> bool:
    """Return True only on Windows 10 (and earlier 10-era builds).

    Windows 11 reports a build number of 22000 or greater, so the heuristic is
    "Windows and build < 22000". Both ``platform.version()`` and the Win32
    ``sys.getwindowsversion()`` API are consulted, so a failure of one still
    yields a sensible answer. On non-Windows systems this is always False.
    """
    if not is_windows():
        return False

    try:
        build = int(_platform.version().split(".")[-1])
    except (ValueError, AttributeError, IndexError, TypeError):
        build = 0
    if build and build < 22000:
        return True

    try:
        winver = sys.getwindowsversion()  # type: ignore[attr-defined]
    except (AttributeError, RuntimeError):
        return False
    return getattr(winver, "major", 0) == 10 and getattr(winver, "build", 0) < 22000
