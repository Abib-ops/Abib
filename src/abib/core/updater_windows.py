# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Windows-only installer flow for the updater.

This module touches Windows APIs (``ctypes.windll``, ``cmd.exe``, the Inno
Setup uninstaller) and must only be imported on Windows. The portable version
check lives in ``abib.core.updater``, which dispatches here when
``plat.is_windows()`` is true.
"""

import ctypes
import subprocess
from ctypes import wintypes
from pathlib import Path

import requests

# Paths and URLs
uninstaller_path = r"C:\Program Files\Abib\unins000.exe"


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
                download_file.writelines(response.iter_content(chunk_size=1024))
            print(f"Download complete. Installer saved to {download_path}")
            return True
        else:
            print(f"Download failed. Status code: {response.status_code}")
            return False
    except requests.exceptions.RequestException as ee:
        print(f"An error occurred while downloading the upgrade: {ee!s}")
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

        shell32 = ctypes.windll.shell32
        kernel32 = ctypes.windll.kernel32

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
        shell32 = ctypes.windll.shell32
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
