# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path
import ctypes
import subprocess
from typing import Any, cast

import requests
from PySide6.QtWidgets import QMessageBox

import fcs
import shared as sh

# Use version from shared
CURRENT_VERSION = sh.CURRENT_VERSION

# Paths and URLs
uninstaller_path = r"C:\Program Files\Abib\unins000.exe"
GITHUB_API_URL = "https://api.github.com/repos/Abib-ops/Abib/releases/latest"


def check_for_updates(parent=None):
    """
    Check for updates on GitHub. Returns a tuple (update_available: bool, version: str, exe_url: str)
    or None on network/format issues. If the user declines the update, returns (False, "", "").
    """
    try:
        response = requests.get(GITHUB_API_URL, timeout=4)
        response.raise_for_status()
        data = response.json()

        latest_version = data.get("tag_name", "").strip()
        assets = data.get("assets", [])
        exe_url = None
        for asset in assets:
            if asset.get("name", "").endswith(".exe"):
                exe_url = asset.get("browser_download_url")
                break

        if latest_version and exe_url:
            output: int = fcs.compare_versions(CURRENT_VERSION, latest_version)
            if output == -1:
                reply = QMessageBox.question(
                    parent,
                    "Update Available",
                    f"A new version ({latest_version}) is available. Do you want to download and install it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if reply == QMessageBox.StandardButton.Yes:
                    return True, latest_version, exe_url
                else:
                    return False, "", ""
            elif output >= 0:
                return False, "", ""
            return None
        else:
            QMessageBox.warning(parent, "Error", "Failed to fetch the latest version details.")
            return None
    except requests.exceptions.RequestException:
        return None
    except ValueError:
        return None


def download_upgrade(version: str, exe_url: str) -> bool:
    """Download the installer to the user's Downloads folder."""
    try:
        print(f"Downloading the upgrade (version: {version}) from {exe_url}...")
        response = requests.get(exe_url, stream=True)
        if response.status_code == 200:
            download_path = Path.home() / "Downloads" / f"Abib_setup_{version}_win.exe"
            with open(download_path, "wb") as download_file:
                for chunk in response.iter_content(chunk_size=1024):
                    download_file.write(chunk)
            print(f"Download complete. Installer saved to {download_path}")
            return True
        else:
            print(f"Download failed. Status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as ee:
        print(f"An error occurred while downloading the upgrade: {str(ee)}")
        return False


def run_uninstaller() -> bool:
    print("Running Abib uninstaller...")
    uninstall_process = subprocess.Popen([uninstaller_path, "/SILENT", "/VERYSILENT"])  # nosec B603
    uninstall_process.wait()
    if uninstall_process.returncode == 0:
        print("Uninstalled successfully.")
        return True
    else:
        print(f"Uninstallation failed with return code {uninstall_process.returncode}")
        return False


def run_installer(installer_path: str) -> bool:
    """
    Run the installer with elevated privileges using ShellExecute.
    """
    try:
        # Help static analysis: cast windll to Any so ShellExecuteW is recognised on Windows
        shell32 = cast(Any, ctypes.windll).shell32
        # Use standard Inno Setup switches separated by spaces (commas are not required)
        params = "/SILENT /VERYSILENT /NORESTART /SUPPRESSMSGBOXES"
        result = shell32.ShellExecuteW(
            None,
            "runas",
            installer_path,
            params,
            None,
            0,
        )
        if result <= 32:
            print(f"Failed to run the installer. Error code: {result}")
            return False
        print("Installer is running...")
        return True
    except (AttributeError, OSError, ctypes.ArgumentError) as ee:
        print(f"An error occurred while running the installer: {ee}")
        return False


def update_abib():
    # print("Checking for updates...")
    try:
        result = check_for_updates()
        if result is None:
            return
        update_available, version, exe_url = result
    except TypeError:
        return

    if not update_available:
        return

    path_to_setup_exe = str(Path.home() / "Downloads" / f"Abib_setup_{version}_win.exe")
    print("Update process started...")
    if not download_upgrade(version, exe_url):
        print("Update aborted: Could not download upgrade.")
        return
    if not run_uninstaller():
        print("Update aborted: Could not uninstall current version.")
        return
    if not run_installer(path_to_setup_exe):
        print("Update aborted: Could not run the installer.")
        return
    print("Update completing. Installing New Version of Abib.")
    print("Closing down the old version of Abib...")
    from sys import exit as sys_exit
    sys_exit(0)
