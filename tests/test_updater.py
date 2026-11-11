# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

import importlib
import sys
from types import SimpleNamespace
from unittest.mock import MagicMock

# noinspection PyPackageRequirements
from PySide6.QtCore import QUrl

# noinspection PyPackageRequirements
from PySide6.QtWidgets import QMessageBox

from abib.core import updater


class _Response:
    def raise_for_status(self) -> None:
        pass

    # noinspection PyMethodMayBeStatic
    def json(self) -> dict[str, object]:
        return {
            "tag_name": "417.51",
            "assets": [
                {
                    "name": "Abib_setup_417.51_win.exe",
                    "browser_download_url": "https://example.test/Abib_setup_417.51_win.exe",
                }
            ],
        }


class _ReleaseResponse:
    def __init__(self, data: dict[str, object]) -> None:
        self._data = data

    def raise_for_status(self) -> None:
        pass

    def json(self) -> dict[str, object]:
        return self._data


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


def test_non_windows_check_uses_release_page_without_exe_asset(monkeypatch):
    release_url = "https://github.com/Abib-ops/Abib/releases/tag/v417.52"
    monkeypatch.setattr(
        updater,
        "plat",
        SimpleNamespace(is_windows=lambda: False),
        raising=False,
    )
    monkeypatch.setattr(
        updater.requests,
        "get",
        MagicMock(return_value=_ReleaseResponse({"tag_name": "v417.52", "html_url": release_url})),
    )
    monkeypatch.setattr(updater.fcs, "compare_versions", MagicMock(return_value=-1))
    question = MagicMock(return_value=QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "question", question)

    result = updater.check_for_updates()

    assert result == (True, "417.52", release_url)
    assert "open the download page" in question.call_args.args[2].lower()


def test_non_windows_check_falls_back_to_releases_page(monkeypatch):
    monkeypatch.setattr(
        updater,
        "plat",
        SimpleNamespace(is_windows=lambda: False),
        raising=False,
    )
    monkeypatch.setattr(
        updater.requests,
        "get",
        MagicMock(return_value=_ReleaseResponse({"tag_name": "417.52"})),
    )
    monkeypatch.setattr(updater.fcs, "compare_versions", MagicMock(return_value=-1))
    monkeypatch.setattr(QMessageBox, "question", MagicMock(return_value=QMessageBox.StandardButton.Yes))

    assert updater.check_for_updates() == (
        True,
        "417.52",
        "https://github.com/Abib-ops/Abib/releases/latest",
    )


def test_non_windows_perform_update_opens_browser_without_downloading(monkeypatch):
    monkeypatch.setattr(
        updater,
        "plat",
        SimpleNamespace(is_windows=lambda: False),
        raising=False,
    )
    browser = MagicMock()
    monkeypatch.setattr(updater, "QDesktopServices", browser, raising=False)
    download = MagicMock(return_value=False)
    monkeypatch.setattr(updater, "download_upgrade", download, raising=False)

    updater.perform_update("417.52", "https://example.test/releases/417.52")

    browser.openUrl.assert_called_once()
    opened_url = browser.openUrl.call_args.args[0]
    assert isinstance(opened_url, QUrl)
    assert opened_url.toString() == "https://example.test/releases/417.52"
    download.assert_not_called()


def test_updater_module_imports_with_non_windows_platform(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")

    reloaded = importlib.reload(updater)

    assert reloaded.RELEASES_PAGE_URL == "https://github.com/Abib-ops/Abib/releases/latest"
    assert not hasattr(reloaded, "ctypes")
    assert not hasattr(reloaded, "subprocess")


def test_windows_check_returns_installer_url(monkeypatch):
    monkeypatch.setattr(updater, "plat", SimpleNamespace(is_windows=lambda: True))
    monkeypatch.setattr(updater.requests, "get", MagicMock(return_value=_Response()))
    monkeypatch.setattr(updater.fcs, "compare_versions", MagicMock(return_value=-1))
    question = MagicMock(return_value=QMessageBox.StandardButton.Yes)
    monkeypatch.setattr(QMessageBox, "question", question)

    result = updater.check_for_updates()

    assert result == (True, "417.51", "https://example.test/Abib_setup_417.51_win.exe")
    assert "download and install" in question.call_args.args[2]


def test_windows_check_warns_when_release_has_no_exe(monkeypatch):
    monkeypatch.setattr(updater, "plat", SimpleNamespace(is_windows=lambda: True))
    monkeypatch.setattr(
        updater.requests,
        "get",
        MagicMock(return_value=_ReleaseResponse({"tag_name": "417.52", "html_url": "https://example.test"})),
    )
    warning = MagicMock()
    monkeypatch.setattr(QMessageBox, "warning", warning)

    assert updater.check_for_updates() is None
    warning.assert_called_once()


def test_windows_perform_update_dispatches_to_windows_module(monkeypatch):
    fake_windows = SimpleNamespace(perform_update=MagicMock())
    monkeypatch.setattr(updater, "plat", SimpleNamespace(is_windows=lambda: True))
    monkeypatch.setitem(sys.modules, "abib.core.updater_windows", fake_windows)
    monkeypatch.setattr("abib.core.updater_windows", fake_windows, raising=False)
    browser = MagicMock()
    monkeypatch.setattr(updater, "QDesktopServices", browser)

    updater.perform_update("417.52", "https://example.test/setup.exe")

    fake_windows.perform_update.assert_called_once_with("417.52", "https://example.test/setup.exe")
    browser.openUrl.assert_not_called()


def test_non_windows_declined_prompt_returns_no_update(monkeypatch):
    monkeypatch.setattr(updater, "plat", SimpleNamespace(is_windows=lambda: False))
    monkeypatch.setattr(
        updater.requests,
        "get",
        MagicMock(return_value=_ReleaseResponse({"tag_name": "417.52"})),
    )
    monkeypatch.setattr(updater.fcs, "compare_versions", MagicMock(return_value=-1))
    monkeypatch.setattr(QMessageBox, "question", MagicMock(return_value=QMessageBox.StandardButton.No))

    assert updater.check_for_updates() == (False, "", "")