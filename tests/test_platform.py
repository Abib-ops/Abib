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


def test_configure_qt_logging_suppresses_wayland_textinput(monkeypatch):
    import os

    from abib.app import _configure_qt_logging

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("QT_LOGGING_RULES", raising=False)
    _configure_qt_logging()
    assert "qt.qpa.wayland.textinput*=false" in os.environ.get("QT_LOGGING_RULES", "")


def test_configure_qt_platform_defaults_to_xcb_wayland_on_linux(monkeypatch):
    import os

    from abib.app import _configure_qt_platform

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    _configure_qt_platform()
    assert os.environ.get("QT_QPA_PLATFORM") == "xcb;wayland"


def test_configure_qt_platform_preserves_existing_env(monkeypatch):
    import os

    from abib.app import _configure_qt_platform

    monkeypatch.setattr(sys, "platform", "linux")
    monkeypatch.setenv("QT_QPA_PLATFORM", "offscreen")
    _configure_qt_platform()
    assert os.environ.get("QT_QPA_PLATFORM") == "offscreen"


def test_configure_qt_platform_no_op_on_non_linux(monkeypatch):
    import os

    from abib.app import _configure_qt_logging, _configure_qt_platform

    monkeypatch.setattr(sys, "platform", "win32")
    monkeypatch.delenv("QT_QPA_PLATFORM", raising=False)
    monkeypatch.delenv("QT_LOGGING_RULES", raising=False)
    _configure_qt_platform()
    _configure_qt_logging()
    assert "QT_QPA_PLATFORM" not in os.environ
    assert "QT_LOGGING_RULES" not in os.environ


def test_configure_linux_font_fallback_adds_stylesheet_and_substitutions(monkeypatch):
    from abib import app as app_module

    class _App:
        stylesheet = "QWidget { color: red; }"

        def styleSheet(self):
            return self.stylesheet

        def setStyleSheet(self, stylesheet):
            self.stylesheet = stylesheet

    monkeypatch.setattr(sys, "platform", "linux")
    substitutions = []
    registered = []
    monkeypatch.setattr(
        app_module.QFont,
        "insertSubstitutions",
        lambda family, fallback: substitutions.append((family, fallback)),
    )
    monkeypatch.setattr(
        app_module.QFontDatabase,
        "addApplicationFont",
        lambda path: registered.append(path) or 0,
    )
    app = _App()

    app_module._configure_linux_font_fallback(app)
    app_module._configure_linux_font_fallback(app)

    assert app.stylesheet.startswith("QWidget { color: red; }")
    assert app.stylesheet.count("QLabel, QTextEdit, QPlainTextEdit") == 1
    assert (
        "'Cascadia Mono', 'Abib Italic h', 'Noto Sans Math', 'DejaVu Sans', sans-serif"
        in app.stylesheet
    )
    fallback = ["Abib Italic h", "Noto Sans Math", "DejaVu Sans"]
    assert substitutions == [("Cascadia Mono", fallback), ("Cascadia Mono", fallback)]
    assert registered[:2] == [
        str(app_module.sh.italic_h_font_path),
        str(app_module.sh.math_font_path),
    ]


def test_configure_linux_font_fallback_is_no_op_on_windows(monkeypatch):
    from abib import app as app_module

    class _App:
        stylesheet = "QWidget { color: red; }"

        def styleSheet(self):
            return self.stylesheet

        def setStyleSheet(self, stylesheet):
            self.stylesheet = stylesheet

    monkeypatch.setattr(sys, "platform", "win32")
    app = _App()

    app_module._configure_linux_font_fallback(app)

    assert app.stylesheet == "QWidget { color: red; }"


def test_bundled_italic_h_font_draws_the_kjb_italic_h():
    # noinspection PyPackageRequirements
    from PySide6.QtGui import QFontDatabase, QRawFont

    from abib.core import shared as sh

    font_id = QFontDatabase.addApplicationFont(str(sh.italic_h_font_path))
    assert "Abib Italic h" in QFontDatabase.applicationFontFamilies(font_id)
    italic_h = QRawFont(str(sh.italic_h_font_path), 12)
    math = QRawFont(str(sh.math_font_path), 12)
    assert italic_h.supportsCharacter(0x1D4BD)
    # The script h is drawn with Noto Sans Math's italic h (U+210E) outline.
    assert (
        italic_h.pathForGlyph(italic_h.glyphIndexesForString("\U0001D4BD")[0]).boundingRect()
        == math.pathForGlyph(math.glyphIndexesForString("\u210e")[0]).boundingRect()
    )


def test_kjb_text_uses_one_italic_h():
    from abib.core import shared as sh

    for name in ("KJB_PCE.txt", "KJB_PCE_stripped.txt"):
        assert "\U0001D629" not in (sh.package_directory / "data" / name).read_text(encoding="utf-8")
