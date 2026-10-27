# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Unit tests for the small platform abstraction (``abib.utils.platform``).

These centralise the previously-scattered ``sys.platform`` checks, so the
helpers are tested here by monkeypatching ``sys.platform`` (and, for the
Windows-10 heuristic, the version APIs) to each operating system.
"""

import sys

from abib.utils import platform as plat


def test_exactly_one_os_matches_on_real_platform():
    # On whatever OS the suite runs on, exactly one of the three should be true.
    assert sum([plat.is_windows(), plat.is_macos(), plat.is_linux()]) == 1


def test_is_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    assert plat.is_windows() is True
    assert plat.is_macos() is False
    assert plat.is_linux() is False


def test_is_macos(monkeypatch):
    monkeypatch.setattr(sys, "platform", "darwin")
    assert plat.is_macos() is True
    assert plat.is_windows() is False
    assert plat.is_linux() is False


def test_is_linux(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert plat.is_linux() is True
    assert plat.is_windows() is False
    assert plat.is_macos() is False


def test_is_windows_10_false_off_windows(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    assert plat.is_windows_10() is False


def test_is_windows_10_true_for_old_build(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(plat._platform, "version", lambda: "10.0.19045")
    assert plat.is_windows_10() is True


def test_is_windows_10_false_for_windows_11_build(monkeypatch):
    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.setattr(plat._platform, "version", lambda: "10.0.22631")

    # The build-number branch returns False; the getwindowsversion() fallback
    # must also report a Windows-11-era build to keep the overall result False.
    class _WinVer:
        major = 10
        build = 22631

    monkeypatch.setattr(sys, "getwindowsversion", lambda: _WinVer(), raising=False)
    assert plat.is_windows_10() is False
