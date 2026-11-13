# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


# noinspection PyPackageRequirements
from PySide6.QtCore import Qt

# noinspection PyPackageRequirements
from PySide6.QtTest import QTest

# noinspection PyPackageRequirements
from PySide6.QtWidgets import QMainWindow

from abib.core import shared as sh
from abib.services.settings import SettingsService
from abib.ui.find_dialog import FindDialog


def _settings_service(tmp_path, monkeypatch) -> SettingsService:
    monkeypatch.setattr(sh, "user_settings_dir", tmp_path)
    return SettingsService("search_history_settings.json")


def _find_dialog(settings_service: SettingsService) -> tuple[QMainWindow, FindDialog, list]:
    parent = QMainWindow()
    parent.nwin = []
    searches: list[tuple[str, int, int]] = []
    parent.find_in_range = lambda start, end: searches.append((parent.key, start, end))
    parent.close_find_window = lambda: None
    return parent, FindDialog(parent, settings_service), searches


def test_search_history_deduplicates_caps_skips_blanks_and_persists(tmp_path, monkeypatch):
    service = _settings_service(tmp_path, monkeypatch)
    service.add_search_history("alpha")
    service.add_search_history("Beta")
    service.add_search_history("alpha")
    service.add_search_history("Alpha")
    service.add_search_history("   ")

    assert service.get_search_history() == ["Alpha", "alpha", "Beta"]

    for number in range(25):
        service.add_search_history(f"search {number}")

    expected = [f"search {number}" for number in range(24, 4, -1)]
    assert service.get_search_history() == expected
    assert SettingsService("search_history_settings.json").get_search_history() == expected


def test_search_history_ignores_malformed_stored_values_and_clears(tmp_path, monkeypatch):
    service = _settings_service(tmp_path, monkeypatch)
    service.save({"search_history": [None, "valid", 3, "", "  "]})

    assert service.get_search_history() == ["valid"]

    service.save({"search_history": {"unexpected": "value"}})
    assert service.get_search_history() == []

    service.add_search_history("recent")
    service.clear_search_history()
    assert service.get_search_history() == []
    assert SettingsService("search_history_settings.json").get_search_history() == []


def test_find_getter_records_nonblank_term_and_runs_search(qapp, tmp_path, monkeypatch):
    service = _settings_service(tmp_path, monkeypatch)
    parent, dialog, searches = _find_dialog(service)
    assert dialog.ui.lineEdit_1 is not None
    dialog.ui.lineEdit_1.setText("  Psalm 23  ")

    dialog.getter()

    assert service.get_search_history() == ["  Psalm 23  "]
    assert searches == [("  Psalm 23  ", -1, -1)]
    dialog.close()
    parent.close()


def test_find_history_menu_selects_search_and_clears_history(qapp, tmp_path, monkeypatch):
    service = _settings_service(tmp_path, monkeypatch)
    service.add_search_history("older")
    service.add_search_history("recent")
    parent, dialog, searches = _find_dialog(service)

    dialog.show_history_menu()

    menu = dialog._history_menu
    actions = menu.actions()
    assert [action.text() for action in actions[:2]] == ["recent", "older"]
    assert actions[-2].isSeparator()
    assert actions[-1].text() == "Clear History"
    assert dialog.history_button.isEnabled()
    menu.actions()[1].trigger()
    assert dialog.ui.lineEdit_1.text() == "older"
    assert searches == []

    menu.actions()[-1].trigger()
    assert service.get_search_history() == []
    assert not dialog.history_button.isEnabled()
    dialog.close()
    parent.close()


def test_down_arrow_opens_find_history_menu(qapp, tmp_path, monkeypatch):
    service = _settings_service(tmp_path, monkeypatch)
    service.add_search_history("recent")
    parent, dialog, _searches = _find_dialog(service)
    assert dialog.ui.lineEdit_1 is not None

    QTest.keyClick(dialog.ui.lineEdit_1, Qt.Key.Key_Down)

    assert dialog._history_menu.isVisible()
    dialog._history_menu.hide()
    dialog.close()
    parent.close()