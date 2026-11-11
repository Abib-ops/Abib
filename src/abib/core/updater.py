# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Portable update check.

The version check against GitHub runs on every platform. On Windows an
available update is downloaded and installed by ``abib.core.updater_windows``
(imported lazily, only on Windows). On Linux and macOS the Releases page is
opened in the default browser instead; nothing is downloaded or executed.
"""

from typing import Any

import requests

# noinspection PyPackageRequirements
from PySide6.QtCore import QUrl

# noinspection PyPackageRequirements
from PySide6.QtGui import QDesktopServices

# noinspection PyPackageRequirements
from PySide6.QtWidgets import QMessageBox

from abib.core import fcs
from abib.core import shared as sh
from abib.utils import platform as plat

# Use version from shared
# CURRENT_VERSION is accessed via sh.CURRENT_VERSION directly in functions

# Paths and URLs
GITHUB_API_URL = "https://api.github.com/repos/Abib-ops/Abib/releases/latest"
RELEASES_PAGE_URL = "https://github.com/Abib-ops/Abib/releases/latest"


def check_for_updates(parent=None, *, notify_no_update: bool = True) -> tuple[bool, str, str] | None:
    """
    Check for updates on GitHub. Returns a tuple (update_available: bool, version: str, url: str)
    or None on network/format issues. If the user declines the update, returns (False, "", "").

    The URL is the installer download on Windows and the release page elsewhere.
    """
    try:
        response = requests.get(GITHUB_API_URL, timeout=4)
        response.raise_for_status()
        
        try:
            data = response.json()
        except ValueError as e:
            raise ValueError(f"Failed to parse JSON: {e}")

        if not isinstance(data, dict):
            raise TypeError("Response data is not a dictionary")

        latest_version = data.get("tag_name", "")
        if latest_version is None:
            latest_version = ""
        latest_version = str(latest_version).strip()
        
        latest_version = latest_version.removeprefix("v")

        windows = plat.is_windows()
        update_url: str | None = None
        if windows:
            assets = data.get("assets", [])
            if not isinstance(assets, list):
                assets = []

            for asset in assets:
                if not isinstance(asset, dict):
                    continue
                if str(asset.get("name", "")).endswith(".exe"):
                    asset_url = asset.get("browser_download_url")
                    update_url = str(asset_url) if asset_url else None
                    break
        else:
            html_url = data.get("html_url")
            if isinstance(html_url, str) and html_url.strip():
                update_url = html_url.strip()
            else:
                update_url = RELEASES_PAGE_URL

        if latest_version and update_url:
            try:
                # Use sh.CURRENT_VERSION directly to ensure we have the latest value
                output: int = fcs.compare_versions(sh.CURRENT_VERSION, latest_version)
            except (ValueError, TypeError, AttributeError) as e:
                raise ValueError(f"Version comparison failed: {e}")

            if output == -1:
                if windows:
                    prompt = f"A new version ({latest_version}) is available. Do you want to download and install it?\n\n(Current version: {sh.CURRENT_VERSION})"
                else:
                    prompt = f"A new version ({latest_version}) is available. Do you want to open the download page?\n\n(Current version: {sh.CURRENT_VERSION})"
                reply = QMessageBox.question(
                    parent,
                    "Update Available",
                    prompt,
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    return True, latest_version, update_url
                else:
                    return False, "", ""
            elif output >= 0:
                # Already on the latest or newer (dev) version — inform the user
                if notify_no_update:
                    try:
                        QMessageBox.information(
                            parent,
                            "Up to date",
                            f"You are already on the latest version (current: {sh.CURRENT_VERSION}).",
                        )
                    except (RuntimeError, AttributeError, TypeError):
                        # Keep silent if the UI is unavailable or the widget state is invalid
                        pass
                return False, "", ""
            return None
        else:
            QMessageBox.warning(parent, "Update check failed", "Failed to fetch the latest version details or installer link from GitHub.")
            return None
    except requests.exceptions.RequestException as e:
        try:
            QMessageBox.warning(parent, "Update check failed", f"Could not reach the update server: {e}\n\nPlease check your internet connection and try again later.")
        except (RuntimeError, AttributeError, TypeError):
            pass
        return None
    except (ValueError, TypeError, KeyError) as e:
        # Catch all other errors (ValueErrors, etc.)
        try:
            QMessageBox.warning(parent, "Update check failed", f"Received an unexpected response from the update server.\n\nDetails: {e}")
        except (RuntimeError, AttributeError, TypeError):
            pass
        return None


def perform_update(version: str, url: str) -> None:
    """Act on an accepted update.

    Windows: download the installer and run it (see ``updater_windows``).
    Linux/macOS: open the release page in the default browser. This must be
    called on the GUI thread on those platforms.
    """
    if plat.is_windows():
        from abib.core import updater_windows
        updater_windows.perform_update(version, url)
    else:
        QDesktopServices.openUrl(QUrl(url))


def update_abib():
    # print ("Checking for updates...")
    try:
        result = check_for_updates()
        if result is None:
            return
        update_available, version, url = result
    except TypeError:
        return

    if not update_available:
        return
    # Delegate to the shared implementation to avoid duplicated logic
    perform_update(version, url)


def update_abib_if_enabled(parent=None, settings: dict[str, Any] | None = None) -> None:
    """Check for updates at startup when the user has enabled it in Settings."""
    if settings is not None and not bool(settings.get("check_for_updates_on_startup", True)):
        return

    try:
        result = check_for_updates(parent=parent, notify_no_update=False)
        if result is None:
            return
        update_available, version, url = result
    except (RuntimeError, TypeError, ValueError):
        return

    if not update_available:
        return
    perform_update(version, url)
