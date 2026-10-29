# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

# noinspection PyPackageRequirements
from PySide6.QtWidgets import QMessageBox

from abib.core import updater


class _Response:
    def raise_for_status(self) -> None:
        pass

    # noinspection PyMethodMayBeStatic
    def json(self) -> dict[str, object]:
        return {
            "tag_name": "417.49",
            "assets": [
                {
                    "name": "Abib_setup_417.49_win.exe",
                    "browser_download_url": "https://example.test/Abib_setup_417.49_win.exe",
                }
            ],
        }


def test_automatic_update_check_does_not_show_up_to_date_message(monkeypatch):
    information = MagicMock()
    monkeypatch.setattr("abib.core.updater.requests.get", MagicMock(return_value=_Response()))
    monkeypatch.setattr(updater.fcs, "compare_versions", MagicMock(return_value=0))
    monkeypatch.setattr(QMessageBox, "information", information)

    result = updater.check_for_updates(notify_no_update=False)

    assert result == (False, "", "")
    information.assert_not_called()


def test_startup_update_check_respects_disabled_setting(monkeypatch):
    check_for_updates = MagicMock()
    perform_update = MagicMock()
    monkeypatch.setattr(updater, "check_for_updates", check_for_updates)
    monkeypatch.setattr(updater, "perform_update", perform_update)

    updater.update_abib_if_enabled(settings={"check_for_updates_on_startup": False})

    check_for_updates.assert_not_called()
    perform_update.assert_not_called()