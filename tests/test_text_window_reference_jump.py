# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-
import time

from abib.services.settings import SettingsService
from abib.ui.text_window import TextDocumentWindow


def make_reader() -> TextDocumentWindow:
    service = SettingsService("test_reader_reference_jump_settings.json")
    window = TextDocumentWindow(settings_service=service)
    window.text_edit.setPlainText("Alpha John 3:16 Omega")
    return window


def test_jump_to_reference_offset_selects_range(qapp):
    window = make_reader()
    try:
        assert window.jump_to_reference_offset(6, 9) is True
        assert window.text_edit.textCursor().selectedText() == "John 3:16"
    finally:
        window.close()
        window.deleteLater()


def test_jump_to_reference_offset_rejects_invalid_range(qapp):
    window = make_reader()
    try:
        original_position = window.text_edit.textCursor().position()
        assert window.jump_to_reference_offset(-1, 9) is False
        assert window.jump_to_reference_offset(6, 0) is False
        assert window.jump_to_reference_offset(1000, 9) is False
        assert window.text_edit.textCursor().position() == original_position
    finally:
        window.close()
        window.deleteLater()


def test_pending_reference_offset_is_applied_after_file_load(qapp, tmp_path):
    path = tmp_path / "Example.txt"
    path.write_text("Alpha John 3:16 Omega", encoding="utf-8")
    service = SettingsService("test_reader_reference_jump_settings.json")
    window = TextDocumentWindow(settings_service=service)
    try:
        window.load_text_file(str(path))
        assert window.jump_to_reference_offset(6, 9) is True

        deadline = time.monotonic() + 2
        while getattr(window, "_is_loading_file", False) and time.monotonic() < deadline:
            qapp.processEvents()

        assert getattr(window, "_is_loading_file", False) is False
        assert window.text_edit.textCursor().selectedText() == "John 3:16"
        assert window._pending_reference_offset is None
        assert window._pending_jump_char is None
    finally:
        window.close()
        window.deleteLater()