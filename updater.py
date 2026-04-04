# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from pathlib import Path
import ctypes
from ctypes import wintypes
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
                # Already on the latest or newer (dev) version — inform the user
                try:
                    QMessageBox.information(
                        parent,
                        "Up to date",
                        f"You are already on the latest version (current: {CURRENT_VERSION}).",
                    )
                except (RuntimeError, AttributeError, TypeError):
                    # Keep silent if the UI is unavailable or the widget state is invalid
                    pass
                return False, "", ""
            return None
        else:
            QMessageBox.warning(parent, "Error", "Failed to fetch the latest version details.")
            return None
    except requests.exceptions.RequestException:
        try:
            QMessageBox.warning(parent, "Update check failed", "Could not reach the update server. Please try again later.")
        except (RuntimeError, AttributeError, TypeError):
            pass
        return None
    except ValueError:
        try:
            QMessageBox.warning(parent, "Update check failed", "Received an unexpected response from the update server.")
        except (RuntimeError, AttributeError, TypeError):
            pass
        return None


def perform_update(version: str, exe_url: str) -> None:
    """Perform the update steps.

    Downloads the installer, then creates a temporary batch script to handle
    the uninstallation and installation after the current process exits.
    """
    path_to_setup_exe = Path.home() / "Downloads" / f"Abib_setup_{version}_win.exe"
    print("Update process started...")
    
    if not download_upgrade(version, exe_url):
        print("Update aborted: Could not download upgrade.")
        return

    # Create a batch script to perform the update after we exit.
    # This avoids file-locking issues with Abib.exe.
    updater_bat = Path.home() / "Downloads" / "abib_updater.bat"
    
    # We want the uninstaller to run, then the installer.
    # We use a loop to wait for Abib.exe to close.
    # 'tasklist' is used to check if Abib.exe is still running.
    
    bat_content = f"""@echo off
setlocal
echo Waiting for Abib to close...
:loop
tasklist /FI "IMAGENAME eq Abib.exe" 2>NUL | find /I /N "Abib.exe">NUL
if "%ERRORLEVEL%"=="0" (
    timeout /t 1 /nobreak >nul
    goto loop
)

echo Running uninstaller...
if exist "{uninstaller_path}" (
    "{uninstaller_path}" /SILENT /NORESTART /SUPPRESSMSGBOXES
)

echo Running installer...
"{path_to_setup_exe}" /SILENT /NORESTART /SUPPRESSMSGBOXES

echo Update complete.
del "%~f0"
"""

    try:
        updater_bat.write_text(bat_content)
    except OSError as e:
        print(f"Failed to create update script: {e}")
        return

    print("Launching update script and closing Abib...")
    try:
        # Start the batch file in a new process group/console so it survives our exit
        subprocess.Popen(
            ["cmd.exe", "/c", str(updater_bat)],
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
    except OSError as e:
        print(f"Failed to launch update script: {e}")
        return

    from sys import exit as sys_exit
    sys_exit(0)


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
    """Run the existing Abib uninstaller with elevation and wait for completion.

    Uses ShellExecuteExW with SEE_MASK_NOCLOSEPROCESS so we can wait on the
    uninstaller process.
    Falls back to subprocess.run if Shell APIs are unavailable.
    If the uninstaller is not found, we skip the uninstallation
    and allow the installer to proceed (return True).
    """
    print("Running Abib uninstaller...")
    try:
        # If the uninstaller doesn't exist (e.g. portable run), skip gracefully
        if not Path(uninstaller_path).exists():
            print("Uninstaller not found; skipping uninstall step.")
            return True

        # Constants and structures for ShellExecuteExW
        SEE_MASK_NOCLOSEPROCESS = 0x00000040

        class SHELLEXECUTEINFOW(ctypes.Structure):
            _fields_ = [
                ("cbSize", wintypes.DWORD),
                ("fMask", wintypes.ULONG),
                ("hwnd", wintypes.HWND),
                ("lpVerb", wintypes.LPCWSTR),
                ("lpFile", wintypes.LPCWSTR),
                ("lpParameters", wintypes.LPCWSTR),
                ("lpDirectory", wintypes.LPCWSTR),
                ("nShow", ctypes.c_int),
                ("hInstApp", wintypes.HINSTANCE),
                ("lpIDList", ctypes.c_void_p),
                ("lpClass", wintypes.LPCWSTR),
                ("hkeyClass", wintypes.HKEY),
                ("dwHotKey", wintypes.DWORD),
                ("hIcon", wintypes.HANDLE),
                ("hProcess", wintypes.HANDLE),
            ]

        shell32 = cast(Any, ctypes.windll).shell32
        kernel32 = cast(Any, ctypes.windll).kernel32

        params = "/SILENT /NORESTART /SUPPRESSMSGBOXES"
        sei = SHELLEXECUTEINFOW()
        sei.cbSize = ctypes.sizeof(SHELLEXECUTEINFOW)
        sei.fMask = SEE_MASK_NOCLOSEPROCESS
        sei.hwnd = None
        sei.lpVerb = "runas"
        sei.lpFile = uninstaller_path
        sei.lpParameters = params
        sei.lpDirectory = None
        sei.nShow = 1  # SW_SHOWNORMAL
        sei.hInstApp = None
        sei.lpIDList = None
        sei.lpClass = None
        sei.hkeyClass = None
        sei.dwHotKey = 0
        sei.hIcon = None
        sei.hProcess = None

        ok = shell32.ShellExecuteExW(ctypes.byref(sei))
        if not ok:
            print("Failed to start uninstaller (ShellExecuteExW returned False).")
            return False

        # Wait for the process to complete if a handle was returned
        if sei.hProcess:
            INFINITE = 0xFFFFFFFF
            kernel32.WaitForSingleObject(sei.hProcess, INFINITE)
            exit_code = wintypes.DWORD(0)
            rc = 0
            if kernel32.GetExitCodeProcess(sei.hProcess, ctypes.byref(exit_code)):
                try:
                    rc = int(exit_code.value)
                except (ValueError, TypeError):
                    rc = 0
            kernel32.CloseHandle(sei.hProcess)
            if rc == 0:
                print("Uninstalled successfully.")
                return True
            else:
                print(f"Uninstallation failed with return code {rc}")
                return False
        else:
            # No process handle; assume it started successfully
            print("Uninstaller started (no process handle available to wait on).")
            return True
    except (AttributeError, OSError, ctypes.ArgumentError) as ee:
        print(f"Error running uninstaller: {ee}")
        # Fallback: try without elevation using the subprocess
        try:
            proc = subprocess.run([uninstaller_path, "/SILENT", "/VERYSILENT", "/NORESTART"], check=False)
            if proc.returncode == 0:
                print("Uninstalled successfully (fallback).")
                return True
            print(f"Uninstallation failed (fallback) with return code {proc.returncode}")
            return False
        except (FileNotFoundError, PermissionError, OSError) as e2:
            print(f"Fallback uninstaller error: {e2}")
            return False


def run_installer(installer_path: str) -> bool:
    """
    Run the installer with elevated privileges using ShellExecute.
    """
    try:
        # Help static analysis: cast windll to Any so ShellExecuteW is recognised on Windows
        shell32 = cast(Any, ctypes.windll).shell32
        # Use standard Inno Setup switches separated by spaces (commas are not required)
        params = "/SILENT /NORESTART /SUPPRESSMSGBOXES"
        result = shell32.ShellExecuteW(
            None,
            "runas",
            installer_path,
            params,
            None,
            1,  # SW_SHOWNORMAL
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
    # print ("Checking for updates...")
    try:
        result = check_for_updates()
        if result is None:
            return
        update_available, version, exe_url = result
    except TypeError:
        return

    if not update_available:
        return
    # Delegate to the shared implementation to avoid duplicated logic
    perform_update(version, exe_url)
