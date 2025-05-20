#!/usr/bin/env python
"""
Copyright 2025 Andrew Kingston.

This file is part of Abib Bible Reader.

Abib is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public Licence as published by
the Free Software Foundation, either version 3 of the Licence or
any later version.

Abib is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public Licence for more details.

You should have received a copy of the GNU General Public Licence
along with Abib.  If not, see <https://www.gnu.org/licenses/>.

For linux use:
Make sure python is up to date in your distro
Copy the Abib folder from the installation media or download to the home folder
Navigate to the folder where you have put Abib
do
$ chmod +x myscript.py
$ python3 myscript.py or ./myscript.py
do
pip install wheel
then
Depending on the error you may get for a missing dependency
do
pip install pyside6

Photo Credit: Abibofgod.com for the splash screen.

Spurgeon's Morning and Evening Readings Obtained from www.spurgeon.org.
Reformatted by Eternal Life Ministries.
Additional Bible-based resources are available at www.spurgeongems.org.

                      .
               .               .
            .                      .                      .
          .                            .             .
        .      o                           .     .
       .                                      .
        .                                  .     .
          .                            .             .
            .                      .                      .
               .               .
                       .


Abib Bible Reader אביב

Using PySide6-6.9.0 and python3.13.3 (64-bit).

20/05/2025
"""

CURRENT_VERSION = "412.7"

import re
import time
from os import environ
from sys import exit, argv, setrecursionlimit
setrecursionlimit(200)

# Suppress pygame welcome message
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

# Pygame is solely used for an error sound.
from pygame import mixer

from copy import deepcopy
from pathlib import Path
from io import open
from itertools import chain
from json import load, JSONDecodeError

from roman import fromRoman
from typing import Any

from PySide6.QtWidgets import (QMainWindow, QTextEdit, QVBoxLayout, QWidget, QDialogButtonBox, QApplication,
                               QToolBar, QPlainTextEdit, QLineEdit, QComboBox, QGridLayout, QMessageBox,
                               QSplashScreen, QPushButton, QDialog, QSizePolicy, QSpacerItem, QHBoxLayout,
                               QStatusBar, QFileDialog, QCheckBox, QLabel)

from PySide6.QtGui import (QAction, QMouseEvent, QKeyEvent, QSyntaxHighlighter, QIcon, QColor, QFont, QPixmap,
                           QTextCursor, QTextCharFormat)

from PySide6.QtCore import Qt, QRect, QSize, QEvent, QTimer

from PySide6.QtPrintSupport import QPrintDialog

import requests
import subprocess
import ctypes

import fcs
import shared as sh

from find import Ui_Dialog

try:
    from ctypes import windll  # Only exists on Windows.
except ImportError:
    windll = None  # Linux or Mac if here.
    pass

try:
    # Included in the try/except block for Mac/Linux
    myappid = f'Abib Bible Reader.{CURRENT_VERSION}'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception as e:
    print(f"Error setting APP ID: {e}")

# Define global theme state
theme_state = {
    "is_dark_mode": False  # Default is light mode
}

mixer.init()


def back_push(current_position) -> None:
    """Push onto the back stack."""

    if len(back) == 0:
        saving = (current_position, w.y, w.hiLita.lineinc, w.hiLita.keyinc, w.hiLita.fmt,
                  w.hiLita.length, w.no_f3_yet, w.occurring, w.key, w.dlg)
        back.append(saving)
    else:
        if back[-1][0] == current_position and back[-1][1] == w.y:
            pass
        else:
            saving = (current_position, w.y, w.hiLita.lineinc, w.hiLita.keyinc,
                      w.hiLita.fmt, w.hiLita.length, w.no_f3_yet,
                      w.occurring, w.key, w.dlg)
            back.append(saving)


def back_pop() -> int:
    """Pop from the back stack."""

    current_position = 0
    if back:
        saving = back.pop()
        current_position = saving[0]
        w.y = saving[1]
        w.hiLita.lineinc = saving[2]
        w.hiLita.keyinc = saving[3]
        w.hiLita.fmt = saving[4]
        w.hiLita.length = saving[5]
        w.no_f3_yet = saving[6]
        w.occurring = saving[7]
        w.key = saving[8]
        w.dlg = saving[9]

    return current_position


def forward_push(current_position) -> None:
    """Push onto the forward stack."""

    if len(forward) == 0:
        saving = (current_position, w.y, w.hiLita.lineinc, w.hiLita.keyinc, w.hiLita.fmt,
                  w.hiLita.length, w.no_f3_yet, w.occurring, w.key, w.dlg)
        forward.append(saving)
    else:
        if forward[-1][0] == current_position and forward[-1][1] == w.y:
            pass
        else:
            saving = (current_position, w.y, w.hiLita.lineinc, w.hiLita.keyinc,
                      w.hiLita.fmt, w.hiLita.length, w.no_f3_yet,
                      w.occurring, w.key, w.dlg)
            forward.append(saving)


def forward_pop() -> int:
    """Pop from the forward stack."""

    current_position = 0
    if len(forward) > 0:
        saving = forward.pop()
        current_position = saving[0]
        w.y = saving[1]
        w.hiLita.lineinc = saving[2]
        w.hiLita.keyinc = saving[3]
        w.hiLita.fmt = saving[4]
        w.hiLita.length = saving[5]
        w.no_f3_yet = saving[6]
        w.occurring = saving[7]
        w.key = saving[8]
        w.dlg = saving[9]

    return current_position


def iterate_list(keywords: list[str], r_list: list) -> None:
    """Iterate over r_list and find all the occurrences of key(s) in keywords."""

    #  global w ----- Probably unnecessary!
    w.occurring = 0
    w.occur = []
    for i in w.occurs:
        coordinates = []
        for key in keywords:
            pattern = fcs.create_pattern(key)
            for m in re.finditer(pattern, r_list[i]):
                w.occurring += 1
                coordinates.append((m.start(), m.end()))
        if coordinates:
            w.occur.append(coordinates)


def findf3_ww_ac(x1: int, x2: int, numwords: int, _set: dict[str, set], r_list: list) -> None:
    """Match whole words (phrase)."""

    liszt = w.key.split(' ')
    s = _set[liszt[0]] & _set[liszt[1]]
    if numwords > 2:
        for i in range(2, numwords):
            j = liszt[i]
            s = s & _set[j]
    w.occur = sorted(list(s))
    w.occurs = []
    pattern = rf"\b{w.key}\b"
    for i in w.occur:
        if i < x1 or i > x2:
            continue
        if re.search(pattern, r_list[i]):
            pass
        else:
            continue
        w.occurs.append(i)
    liszt = [w.key]
    iterate_list(liszt, r_list)
    c = 0
    for i in w.occur:
        li = len(i)
        c += li
    w.occurring = c


def findf3_ww_all(x1: int, x2: int, numwords: int, _set: dict[str, set], r_list: list) -> None:
    """Match all the words (phrase)."""

    liszt = w.key.split(' ')
    try:
        s = _set[liszt[0]] & _set[liszt[1]]
    except KeyError:
        print(f'liszt[0] {liszt[0]}')
        print(f'liszt[1] {liszt[1]}')
        raise KeyError

    if numwords > 2:
        for i in range(2, numwords):
            s = s & _set[liszt[i]]
    w.occur = sorted(list(s))
    w.occurs = []
    for i in w.occur:
        if i < x1 or i > x2:
            continue
        w.occurs.append(i)
    iterate_list(liszt, r_list)
    w.occurring = len(w.occurs)


def check_count_sort(liszt: list[str], r_list: list) -> None:
    """Check matched words are whole, count and sort w.occurs (Any)."""

    w.count = []
    iterate_list(liszt, r_list)
    lo = len(w.occur)
    for i in range(lo):
        w.count.append(len(w.occur[i]))

    w.count, w.occurs, w.occur = zip(
        *sorted(zip(w.count, w.occurs, w.occur), reverse=True))

    w.occur = list(w.occur)
    w.occurs = list(w.occurs)

    newt: list = []
    newts: list = []
    j = w.count[0]
    k = 0
    t: list = []
    ts: list = []
    for i in w.count:
        if (i == j) and (k < lo):
            wok = w.occur[k]
            t.append(wok)
            woks = w.occurs[k]
            ts.append(woks)
            k += 1
            j = i
        elif (i != j) or (k == lo-1):
            t.reverse()
            ts.reverse()
            newt.append(t)
            newts.append(ts)
            t = []
            ts = []
            if k < lo:
                j = w.count[k]
                wok = w.occur[k]
                t.append(wok)
                woks = w.occurs[k]
                ts.append(woks)
                k += 1
    t.reverse()
    ts.reverse()
    newt.append(t)
    newts.append(ts)
    w.occur = list(chain.from_iterable(newt))
    w.occurs = list(chain.from_iterable(newts))
    w.occurring = len(w.occurs)


def prep_statusbar_message(index: int):
    """Prepare the statusbar message."""

    book = sh.Info[index][0]
    chapter = sh.Info[index][1] + 1
    occurrence = sh.Info[index][2] + 1
    book_name = w.nwin[book]

    if w.occurrence == w.occurring:
        end_message = "."
        w.no_f3_yet = 0
    else:
        end_message = '...'

    ye = f'Occurrence {w.occurrence}/{w.occurring} of "{w.keym}"'

    if book in sh.onechapterbooks:
        w.message = f'{ye}  -  {book_name} {occurrence} KJV{end_message}'
    else:
        w.message = f'{ye}  -  {book_name} {chapter}:{occurrence} KJV{end_message}'


def occurrent1() -> int:
    """Count occurrence(s) of w.key and give current_position and w.y values.

    w.occurs is a list of all the current_position values in the search results.
    w.occur is a corresponding list which gives the start w.y and finish w.yend of
    the searched for item in the particular verse.
    w.occurring is the total number of times the search key was found.
    w.verse is the number of the items in the search list.
    len(w.occur[w.verse]) is the number of search results in a particular verse.
    w.finding is the number of items found within the verse.
    """

    current_position = w.occurs[-1]  # Workaround for PyCharm linter.

    if w.verse < len(w.occurs):
        w.finding += 1
        current_position = w.occurs[w.verse]  # Aligns with w.occur(w.verse)
        if w.finding + 1 <= len(w.occur[w.verse]):
            w.y = w.occur[w.verse][w.finding][0]
            w.yend = w.occur[w.verse][w.finding][1]
            w.occurrence += 1
            prep_statusbar_message(current_position)
        elif w.verse + 1 < len(w.occurs):
            w.verse += 1
            w.finding = 0
            w.y = w.occur[w.verse][w.finding][0]
            w.yend = w.occur[w.verse][w.finding][1]
            w.occurrence += 1
            current_position = w.occurs[w.verse]
            prep_statusbar_message(current_position)
    elif w.verse >= len(w.occurs):
        current_position = w.occurs[-1]  # Last item

    # print(f'len(w.occurs = {len(w.occurs)})')
    # print(f'w.occurring = {w.occurring}')

    return current_position


def findf3_ww_any(x1: int, x2: int, numwords: int, _set: dict[str, set], r_list: list) -> None:
    """Match any word."""

    liszt: list[str] = w.key.split(' ')
    s: set = set()
    s = s.union(_set[liszt[0]], _set[liszt[1]])
    if numwords > 2:
        for i in range(2, numwords):
            s = s.union(_set[liszt[i]])
    w.occur = sorted(list(s))
    w.occurs = []
    for i in w.occur:
        if i < x1 or i > x2:
            continue
        w.occurs.append(i)

    check_count_sort(liszt, r_list)


def make_offset(ln: int) -> int:
    """Enable highlighting of first verses while showing the titles above."""

    # print('make_offset')
    n: str = KJV[ln][0]
    m: str
    spacesfound: int = 0
    lx: int = Amap[13940] - 1
    ec: int = 2
    if n.isalpha() or ln in P119:
        if ln in P119:
            ec = 1
        while spacesfound < 2:
            if spacesfound == ec:
                break
            ln -= 1
            n = KJV[ln][0]
            m = KJV[ln][1]
            if n == ' ':
                spacesfound += 1
            elif n == 'P' and m == 'S' and ln != lx:
                ec = 1

    return ln


def reset_attributes() -> None:
    """Instance attribute resetting routine."""

    # print('reset_attributes')
    # w.gent = None
    w.y = 0
    w.hiLita.lineinc = 0
    w.hiLita.keyinc = 0
    w.occurring = 0
    w.occurrence = 0
    w.key = ' '
    w.message = ''
    if w.dlg is not None:
        w.dlg.checks = [1, 0, 5]  # Is this necessary?
    w.occurs = []
    w.occur = []


def centerer(widt: int, heigh: int) -> tuple:
    """Provide central screen origin points for windows"""

    w_origin = int(half_width - (widt / 2))
    h_origin = int(half_height - (heigh / 2))

    return w_origin, h_origin


def format_status_message(q1, q2, q3):
    """Helper to format a message based on conditions."""

    q4 = w.nwin[q1]
    if q1 in sh.onechapterbooks:
        return f"{q4} {q3} KJV"
    return f"{q4} {q2}:{q3} KJV"


def sizer(window_height: int, window_width: int) -> tuple[int, int]:
    """Adjust window size to fit the screen."""

    if window_height > height:
        window_height = int(height * 0.95)
    if window_width > width:
        window_width = int(width * 0.95)

    return window_height, window_width


def commentary() -> None:
    """Commentary key."""

    # Create an instance of CalvinCommentary
    # calvincom = CalvinCommentary()

    # Access a specific commentary
    # book_name = "Genesis"
    # print(f"{book_name} Commentary:", calvincom.get_commentary(book_name))
    print('Future feature')


def calculate_book_line(book: str, chapter: int, verse: int, current_line_num: int) -> int:
    """
    This function calculates and returns a specific line index from the global variable
    'sh.Info' based on the given book, chapter, and verse parameters.

    The book, chapter, and verse values are adjusted to zero-based indexing before computation.
    An error is raised if the values are invalid or out of range for the dataset referenced by
    'sh.Info'.

    :param book: The book identifier is provided as a string parsed into an integer.
    :param chapter: The chapter number. Must be a positive integer.
    :param verse: The verse number. Must be a positive integer.
    :param current_line_num: The current line number. Must be a positive integer.
    :return: The calculated line index corresponding to the book, chapter, and verse or defaults to current_line_num.
    :rtype: int
    :default: If the book, chapter, or verse is invalid or out of range for processing,
              the line index will be set to current_line_num.
    """
    rv: int = current_line_num  # default return value.

    # Subtract 1 from the book, chapter, and verse for a zero-based sh.Info index.
    book_id = int(book) - 1
    chapter = int(chapter) - 1
    verse = int(verse) - 1

    try:
        if book_id < 0 or chapter < 0 or verse < 0:
            message = f"Invalid chapter or verse range."
            w.on_error(message, 750, True)
            # print(message)
            # Return the default index from sh.Info
            return sh.Info.index([0, 0, 0])

        # Return the calculated index from sh.Info
        rv = sh.Info.index([book_id, chapter, verse])
        return rv

    except (ValueError, IndexError):
        message = f"Invalid book, chapter, or verse."
        w.on_error(message, 750, True)
        # print(message)
        # Return the default index from sh.Info
        return rv


def resolve_reference(bits: list) -> tuple:
    """Resolve the book, chapter, and verse using fcs.isRoman."""

    # Debugging: Show the split bits
    # print(f"Resolving reference bits: {bits}")

    # Step 1: Resolve the book name
    book_number = sh.bibledict.get(bits[0].lower(), None)
    # print(f"Book resolved to: {book_number}")
    if not book_number:
        return None, None, None

    # Step 2: Resolve chapter (bits[1])
    chapter = '1'
    if len(bits) > 1:
        if fcs.isRoman(bits[1]):  # If it's a Roman numeral
            # print(f"Chapter is Roman: {bits[1]}")
            chapter = fromRoman(bits[1].upper())  # Convert Roman numeral
        else:  # Otherwise, try parsing it as an integer
            try:
                chapter = int(bits[1])
                # print(f"Chapter is Integer: {chapter}")
            except ValueError:
                message = f"Invalid chapter: {bits[1]}"
                w.on_error(message, 750, True)
                # print(message)
                return book_number, None, None

    # Step 3: Resolve verse (bits[2])
    verse = '1'
    if len(bits) > 2:
        if fcs.isRoman(bits[2]):  # If it's a Roman numeral
            # print(f"Verse is Roman: {bits[2]}")
            verse = fromRoman(bits[2].upper())  # Convert Roman numeral
        else:  # Otherwise, try parsing it as an integer
            try:
                verse = int(bits[2])
                # print(f"Verse is Integer: {verse}")
            except ValueError:
                message = f"Invalid verse: {bits[2]}"
                w.on_error(message, 750, True)
                # print(message)
                return book_number, chapter, None

    # Debugging: Show final resolved reference
    # print(f"Resolved reference: (Book: {book_number}, Chapter: {chapter}, Verse: {verse})")
    return book_number, chapter, verse


# Paths (can be dynamically defined within Abib at runtime)
uninstaller_path = r"C:\Program Files\Abib\unins000.exe"
upgrade_installer_path = Path.home() / "Downloads"
new_version_path = r"C:\Program Files\Abib\Abib.exe"
GITHUB_API_URL = "https://api.github.com/repos/Abib-ops/Abib/releases/latest"


def check_for_updates(parent=None):
    """
    Check for updates, download the latest installer, and install it silently if a new version is available.
    """
    try:
        # Step 1: Fetch the latest release information from GitHub
        response = requests.get(GITHUB_API_URL)
        response.raise_for_status()
        data = response.json()

        # Fetch the latest version and download URL
        latest_version = data.get("tag_name", "").strip()
        assets = data.get("assets", [])
        exe_url = None

        for asset in assets:
            if asset.get("name", "").endswith(".exe"):  # Look for the Windows installer
                exe_url = asset.get("browser_download_url")
                break

        # Step 2: Compare CURRENT_VERSION with latest_version
        if latest_version and exe_url:
            output: int = fcs.compare_versions(CURRENT_VERSION, latest_version)
            if output == -1:  # A newer version is available
                reply = QMessageBox.question(parent,
                                                       "Update Available",
                                                       f"A new version ({latest_version}) is available. Do you want to download and install it?",
                                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                                       QMessageBox.StandardButton.No
                                                       )
                if reply == QMessageBox.StandardButton.Yes:
                    return True, latest_version, exe_url
                else:
                    return False, "", ""
            elif output >= 0:  # The current version is up to date.
                return False, "", ""
            return None
        else:
            QMessageBox.warning(parent, "Error", "Failed to fetch the latest version details.")
            return None
    except requests.exceptions.RequestException as ere:
        QMessageBox.critical(parent, "Error", f"Failed to check for updates: {str(ere)}")
        return None


# Step 1: Download upgrade installer
def download_upgrade(version, exe_url):
    """
    Download the upgrade installer from the provided URL and save it to the Downloads folder.

    :param version: The latest version number (for naming the installer file).
    :param exe_url: The URL of the installer executable file to download.
    :return: True if the download was successful, False otherwise.
    """
    try:
        print(f"Downloading the upgrade (version: {version}) from {exe_url}...")

        # Make the GET request to download the file
        response = requests.get(exe_url, stream=True)

        # Check if the request was successful
        if response.status_code == 200:
            # Define the download path in the user's Downloads folder
            download_path = Path.home() / "Downloads" / f"Abib_setup_{version}_win.exe"

            # Save the file to the local Downloads folder
            with open(download_path, "wb") as download_file:
                for chunk in response.iter_content(chunk_size=1024):  # Stream chunks
                    download_file.write(chunk)

            print(f"Download complete. Installer saved to {download_path}")
            return True

        else:
            print(f"Download failed. Status code: {response.status_code}")
            return False

    except requests.exceptions.RequestException as ee:
        print(f"An error occurred while downloading the upgrade: {str(ee)}")
        return False


# Step 2: Initiate uninstaller
def run_uninstaller():
    print("Running Abib uninstaller...")
    uninstall_process = subprocess.Popen([uninstaller_path, "/SILENT", "/VERYSILENT"])
    uninstall_process.wait()
    if uninstall_process.returncode == 0:
        print("Uninstalled successfully.")
    else:
        print(f"Uninstallation failed with return code {uninstall_process.returncode}")
        return False
    return True


# Step 3: Install the upgrade
def run_installer(installer_path: str) -> bool:
    """
        Run the installer with elevated privileges using ShellExecute.
        """
    try:
        # Request elevated privileges to execute the installer
        result = ctypes.windll.shell32.ShellExecuteW(
            None,  # No parent window
            "runas",  # Verb to request elevation
            installer_path,  # Path to the installer
            "/SILENT, /VERYSILENT, /NORESTART, /SUPPRESSMSGBOXES",  # Arguments for the installer (silent mode)
            None,  # Default working directory
            0  # Show the installer window (SW_SHOWNORMAL)
        )
        if result <= 32:
            print(f"Failed to run the installer. Error code: {result}")
            return False
        print("Installer is running...")
        return True
    except Exception as ee:
        print(f"An error occurred while running the installer: {ee}")
        return False


# Main update process
def update_abib():
    # print("Checking for updates...")
    update_available, version, exe_url = check_for_updates()
    if not update_available:
        # print("No update available.")
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
    exit(0)  # Exit the old instance of the application


class MainWindow(QMainWindow):
    """MainWindow class."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialise."""
        super(MainWindow, self).__init__(*args, **kwargs)

        # Load saved settings or initialise default ones.
        # self.feature = None
        self.text_edit_window = None
        self.text_edit = None
        self.history_index = None
        self.command_history = None
        self.about_window = None
        self.is_dark_mode: None = None
        # Use the already-loaded settings
        self.settings = settings
        # self.textEditor: None = None
        self.path1: None = None
        self.display_verse_input: None = None
        self.comboBox_1: None = None
        self.comboBox_2: None = None
        self.comboBox_3: None = None
        self.hiLita: None = None
        self.buttonQ: None = None
        self.buttonf3: None = None
        self.buttonf4: None = None
        self.buttonf5: None = None
        self.buttonf6: None = None
        self.buttonf7: None = None
        self.buttonf8: None = None
        self.buttonf9: None = None
        self.buttonf10: None = None
        self.buttonf11: None = None
        self.buttonf12: None = None
        self.buttonf13: None = None
        self.buttonf14: None = None
        self.statusBar: None = None
        self.okButton: None = None
        self.dlg: None = None  # No external window yet.
        self.gent: None = None
        self.textEditor: QPlainTextEdit = QPlainTextEdit()
        # Store a reference to the secondary window to manage its lifecycle
        self.secondary_window = None
        self.feature = self.feature

        #Qt.QTimer.singleShot(0, lambda: self.sme("PM", -1))  # Adjusted to yesterday evening's reading.

        self.nwin: list[str] = [
            'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy',
            'Joshua', 'Judges', 'Ruth', 'I Samuel', 'II Samuel', 'I Kings',
            'II Kings', 'I Chronicles', 'II Chronicles', 'Ezra', 'Nehemiah',
            'Esther', 'Job', 'Psalms', 'Proverbs', 'Ecclesiastes',
            'Song of Solomon', 'Isaiah', 'Jeremiah', 'Lamentations',
            'Ezekiel', 'Daniel', 'Hosea', 'Joel', 'Amos', 'Obadiah', 'Jonah',
            'Micah', 'Nahum', 'Habakkuk', 'Zephaniah', 'Haggai', 'Zechariah',
            'Malachi', 'Matthew', 'Mark', 'Luke', 'John', 'Acts', 'Romans',
            'I Corinthians', 'II Corinthians', 'Galatians', 'Ephesians',
            'Philippians', 'Colossians', 'I Thessalonians',
            'II Thessalonians', 'I Timothy', 'II Timothy', 'Titus',
            'Philemon', 'Hebrews', 'James', 'I Peter', 'II Peter', 'I John',
            'II John', 'III John', 'Jude', 'Revelation']

        # Set up for Genesis 1:1
        self.nchapters: list[str] = []
        for _ in range(1, 51):
            self.nchapters.append(str(_))
        self.nverses: list[str] = []
        for _ in range(1, 32):
            self.nverses.append(str(_))

        noa: int = len(argv)
        self.fontsize: int = 14
        self.winwidth: int = 480  # Initial width of Abib Bible.
        self.winheight: int = 810  # Initial height of Abib Bible.
        if noa > 1:
            try:
                self.fontsize = int(argv[1])
                self.winwidth = int(argv[2])
                self.winheight = int(argv[3])
            except ValueError:
                pass

        self.initui()

    def initui(self) -> None:
        """Initialise Mainwindow GUI."""

        w_origin, h_origin = centerer(self.winwidth, self.winheight)
        self.setGeometry(w_origin, h_origin, self.winwidth, self.winheight)

        fixedfont: QFont = QFont("Cascadia Mono", self.fontsize, QFont.Weight.Medium)
        self.textEditor.setFont(fixedfont)
        self.textEditor.setReadOnly(True)

        self.display_verse_input: QLineEdit = QLineEdit()
        self.display_verse_input.setToolTip("F2, Enter or OK to search for a verse.")
        # self.display_verse_input.returnPressed.connect(self.goto_line)
        self.display_verse_input.setGeometry(QRect(50, 50, 200, 25))  # Reduce the width to 200
        self.display_verse_input.installEventFilter(self)  # Install event filter for custom key handling

        # Store command history and variables
        self.command_history = []
        self.history_index = -1

        self.comboBox_1: QComboBox = QComboBox()
        self.comboBox_1.addItems(self.nwin)
        self.comboBox_1.setCurrentIndex(0)
        self.comboBox_1.activated.connect(self.goto_book)

        self.comboBox_2: QComboBox = QComboBox()
        self.comboBox_2.addItems(self.nchapters)
        self.comboBox_2.setCurrentIndex(0)
        self.comboBox_2.activated.connect(self.goto_chapter)

        self.comboBox_3: QComboBox = QComboBox()
        self.comboBox_3.addItems(self.nverses)
        self.comboBox_3.setCurrentIndex(0)
        self.comboBox_3.activated.connect(self.goto_verse)

        self.hiLita: SyntaxHighlighter = SyntaxHighlighter(self.textEditor.document())

        grid: QGridLayout = QGridLayout()
        grid.setSpacing(2)
        self.setLayout(grid)

        grid.addWidget(self.textEditor, 0, 0, 1, 3)
        self.textEditor.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        grid.addWidget(self.comboBox_1, 1, 0)
        self.comboBox_1.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.comboBox_2, 1, 1)
        self.comboBox_2.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.comboBox_3, 1, 2)
        self.comboBox_3.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        grid.addWidget(self.display_verse_input, 2, 0)
        self.display_verse_input.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.okButton = QPushButton("OK")
        self.okButton.setStyleSheet("QPushButton { text-align: left; }")
        self.okButton.setGeometry(QRect(200, 200, 75, 30))  # Position the "OK" button

        grid.addWidget(self.okButton, 2, 1)
        self.okButton.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.okButton.setToolTip("Enter")
        self.display_verse_input.returnPressed.connect(self.goto_line)
        self.okButton.clicked.connect(self.goto_line)

        self.buttonQ = QPushButton("Quit")
        self.buttonQ.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonQ.clicked.connect(exit)
        grid.addWidget(self.buttonQ, 2, 2)
        self.buttonQ.setToolTip("Close Abib")
        self.buttonQ.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Create a horizontal layout for Find and Find Next buttons
        find_buttons_layout = QHBoxLayout()

        self.buttonf3 = QPushButton("Find", self)
        self.buttonf3.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf3.clicked.connect(self.f3)
        self.buttonf3.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonf3.setToolTip("F3")
        find_buttons_layout.addWidget(self.buttonf3)

        self.buttonf4 = QPushButton("Find Next")
        self.buttonf4.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf4.clicked.connect(self.f4)
        self.buttonf4.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonf4.setToolTip("F4")
        find_buttons_layout.addWidget(self.buttonf4)

        # Add the horizontal layout to the grid at row 3, column 0
        grid.addLayout(find_buttons_layout, 3, 0)

        self.buttonf5 = QPushButton("Back")
        self.buttonf5.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf5.clicked.connect(self.f5)
        grid.addWidget(self.buttonf5, 3, 1)
        self.buttonf5.setToolTip("F5")
        self.buttonf5.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.buttonf6 = QPushButton("Forward")
        self.buttonf6.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf6.clicked.connect(self.f6)
        grid.addWidget(self.buttonf6, 3, 2)
        self.buttonf6.setToolTip("F6")
        self.buttonf6.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Create a horizontal layout for Book- and Book+ buttons
        book_buttons_layout = QHBoxLayout()

        self.buttonf7 = QPushButton("Book-")
        self.buttonf7.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf7.clicked.connect(self.earlier_book)
        self.buttonf7.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonf7.setToolTip("F7")
        book_buttons_layout.addWidget(self.buttonf7)

        self.buttonf8 = QPushButton("Book+")
        self.buttonf8.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf8.clicked.connect(self.later_book)
        self.buttonf8.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.buttonf8.setToolTip("F8")
        book_buttons_layout.addWidget(self.buttonf8)

        # Add the horizontal layout to the grid at row 4, column 0
        grid.addLayout(book_buttons_layout, 4, 0)

        self.buttonf10 = QPushButton("Chapter-")
        self.buttonf10.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf10.clicked.connect(self.earlier_chapter)
        grid.addWidget(self.buttonf10, 4, 1)
        self.buttonf10.setToolTip("F10")
        self.buttonf10.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.buttonf11 = QPushButton("Chapter+")
        self.buttonf11.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf11.clicked.connect(self.later_chapter)
        grid.addWidget(self.buttonf11, 4, 2)
        self.buttonf11.setToolTip("F11")
        self.buttonf11.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Create a horizontal layout for Fullscreen and Devotional buttons
        full_buttons_layout = QHBoxLayout()

        self.buttonf9 = QPushButton("Fullscreen")
        self.buttonf9.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf9.clicked.connect(self.f9)
        full_buttons_layout.addWidget(self.buttonf9)
        self.buttonf9.setToolTip("F9")
        self.buttonf9.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.buttonf12 = QPushButton("Devotional")
        self.buttonf12.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf12.clicked.connect(self.f12)
        full_buttons_layout.addWidget(self.buttonf12)
        self.buttonf12.setToolTip("F12")
        self.buttonf12.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Add the horizontal layout to the grid at row 5, column 0
        grid.addLayout(full_buttons_layout, 5, 0)

        self.buttonf13 = QPushButton("")
        self.buttonf13.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf13.clicked.connect(commentary)
        grid.addWidget(self.buttonf13, 5, 1)
        self.buttonf13.setToolTip("Ctrl + Shift + C")
        self.buttonf13.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.buttonf14 = QPushButton("Pilgrim's Progress")
        self.buttonf14.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf14.clicked.connect(self.feature)
        grid.addWidget(self.buttonf14, 5, 2)
        self.buttonf14.setToolTip("Ctrl + Shift + ?")
        self.buttonf14.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        container: QWidget = QWidget()
        container.setLayout(grid)
        self.setCentralWidget(container)
        self.display_verse_input.setFocus()

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        file_toolbar = QToolBar("File")
        file_toolbar.setIconSize(QSize(14, 14))
        self.addToolBar(file_toolbar)
        file_menu = self.menuBar().addMenu("&File")

        # Create a Path object for the file path.
        icon1_path = Path('images') / 'blue-folder-open-document.png'
        # Use str() to convert Path object to string for QIcon.
        open_file_action = QAction(QIcon(str(icon1_path)), "Open file...", self)
        open_file_action.setStatusTip("Open file")
        open_file_action.triggered.connect(self.file_open)
        file_menu.addAction(open_file_action)
        file_toolbar.addAction(open_file_action)

        icon2_path = Path('images') / 'printer.png'
        print_action = QAction(QIcon(str(icon2_path)), "Print...", self)
        print_action.setStatusTip("Print current page")
        print_action.triggered.connect(self.file_print)
        file_menu.addAction(print_action)
        file_toolbar.addAction(print_action)

        icon3_path = Path('images') / 'exit.png'
        exit_action = QAction(QIcon(str(icon3_path)), "Exit", self)
        exit_action.setStatusTip("Exit the program")
        exit_action.triggered.connect(exit)
        file_menu.addAction(exit_action)

        edit_toolbar = QToolBar("Edit")
        edit_toolbar.setIconSize(QSize(14, 14))
        self.addToolBar(edit_toolbar)
        edit_menu = self.menuBar().addMenu("&Edit")

        icon4_path = Path('images') / 'document-copy.png'
        copy_action = QAction(QIcon(str(icon4_path)), "Copy", self)
        copy_action.setStatusTip("Copy selected text")
        copy_action.triggered.connect(self.textEditor.copy)
        edit_toolbar.addAction(copy_action)
        edit_menu.addAction(copy_action)

        icon5_path = Path('images') / 'selection-input.png'
        select_action = QAction(QIcon(str(icon5_path)), "Select all", self)
        select_action.setStatusTip("Select all text")
        select_action.triggered.connect(self.textEditor.selectAll)
        edit_menu.addAction(select_action)

        help_menu = self.menuBar().addMenu("&Help")
        icon6_path = Path('images') / 'license.png'
        copyright_action = QAction(QIcon(str(icon6_path)), "LICENSE", self)
        copyright_action.setStatusTip("License")
        copyright_action.triggered.connect(self.copyright)
        help_menu.addAction(copyright_action)

        help_menu.addSeparator()
        icon7_path = Path('images') / 'question.png'
        help_action = QAction(QIcon(str(icon7_path)), "Abib Help", self)
        help_action.setStatusTip("Help file")
        help_action.triggered.connect(self.helper)
        help_menu.addAction(help_action)

        help_menu.addSeparator()
        icon8_path = Path('images') / 'details.png'
        readme_action = QAction(QIcon(str(icon8_path)), "Readme", self)
        readme_action.setStatusTip("Readme file")
        readme_action.triggered.connect(self.readme)
        help_menu.addAction(readme_action)

        help_menu.addSeparator()
        icon9_path = Path('images') / 'about.png'
        about_action = QAction(QIcon(str(icon9_path)), "About", self)
        about_action.setStatusTip("About Abib")
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        help_menu.addSeparator()
        icon10_path = Path('images') / 'settings.png'
        settings_action = QAction(QIcon(str(icon10_path)), "Settings", self)
        settings_action.setStatusTip("Settings")
        settings_action.triggered.connect(self.open_settings_dialog)
        help_menu.addAction(settings_action)

        self.secondary_window = SecondaryWindow("Text to display", self.geometry())
        self.secondary_window.text_display = QPlainTextEdit()

        # Apply theme from settings during initialisation.
        self.set_theme(self.settings)

        # self.update_title()
        self.show()

        # Placeholder for the AboutWindow (lazy-loaded)
        self.about_window = None

    # noinspection PyUnresolvedReferences
    def eventFilter(self, source, event):
        """Custom event filter to handle key events on QLineEdit."""

        if source == self.display_verse_input and event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Up:  # Handle Up Arrow
                if self.command_history and self.history_index > 0:
                    self.history_index -= 1
                    self.display_verse_input.setText(self.command_history[self.history_index])
                elif self.command_history and self.history_index == -1:
                    self.history_index = len(self.command_history) - 1
                    self.display_verse_input.setText(self.command_history[self.history_index])
                return True

            elif event.key() == Qt.Key_Down:  # Handle Down Arrow
                if self.command_history and self.history_index < len(self.command_history) - 1:
                    self.history_index += 1
                    self.display_verse_input.setText(self.command_history[self.history_index])
                elif self.history_index == len(self.command_history) - 1:
                    self.history_index += 1
                    self.display_verse_input.clear()  # Clear input when navigating below the last command
                return True

            elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:  # Handle Enter
                current_text = self.display_verse_input.text().strip()
                if current_text:
                    self.command_history.append(current_text)  # Add current text to history
                    self.history_index = -1  # Reset history index
                    # print(f"Executed: {current_text}")  # Simulate command execution
                    # print("Return key intercepted in eventFilter")  # Debugging
                    self.goto_line()  # Trigger goto_line manually
                    self.display_verse_input.clear()  # Clear the input field after submission
                return True

        return super().eventFilter(source, event)

    def feature(self) -> None:
        """For a future feature key."""

        # print('Pilgrims-Progress')
        # Persist the reference to the window
        self.text_edit_window = TextDocumentWindow()  # Instantiate the window
        self.text_edit_window.text_display = QTextEdit()
        self.text_edit_window.text_display.setPlainText("Pilgrims-Progress Content.")
        self.text_edit_window.show()  # Show the window
        self.text_edit_window.highlight_references()

    def show_about_dialog(self):
        """Show the 'About' window when Help -> About is clicked."""

        # Initialize AboutWindow if it hasn't been created
        if self.about_window is None:
            self.about_window = AboutWindow()

        self.about_window.show()
        self.about_window.raise_()  # Bring the "About" window to the front
        self.about_window.activateWindow()  # Give the "About" window focus

    def helper(self) -> None:
        """Help section."""

        self.file_open(str(Path(sh.current_directory / 'HELP.txt')))
        winwidth: int = 830
        winheight: int = 1343

        # Allow for small screen sizes
        winheight, winwidth = sizer(winheight, winwidth)

        w_origin, h_origin = centerer(winwidth, winheight)
        self.setGeometry(w_origin, h_origin, winwidth, winheight)
        w.otherFileFlag = True

    def copyright(self) -> None:
        """Licence."""

        self.file_open(str(Path(sh.current_directory / 'LICENSE')))
        winwidth: int = 940
        winheight: int = 1343

        # Allow for small screen sizes
        winheight, winwidth = sizer(winheight, winwidth)

        w_origin, h_origin = centerer(winwidth, winheight)
        self.setGeometry(w_origin, h_origin, winwidth, winheight)
        w.otherFileFlag = True

    def readme(self) -> None:
        """Readme file."""

        self.file_open(str(Path(sh.current_directory / 'README.txt')))
        winwidth: int = 830
        winheight: int = 1343

        # Allow for small screen sizes
        winheight, winwidth =  sizer(winheight, winwidth)

        w_origin, h_origin = centerer(winwidth, winheight)
        self.setGeometry(w_origin, h_origin, winwidth, winheight)
        w.otherFileFlag = True

    def reload(self) -> None:
        """Reload KJB_PCE.txt"""

        if w.otherFileFlag is True:
            # print('reloaded')
            w.otherFileFlag = False
            self.file_open(str(Path(sh.current_directory / 'KJB_PCE.txt')))
            winwidth: int = 480
            winheight: int = 800
            w_origin, h_origin = centerer(winwidth, winheight)
            reset_attributes()
            self.setGeometry(w_origin, h_origin, winwidth, winheight)

    # ENTRY POINT FOR F3 FIND.
    # Create a slot for launching the find dialog box.

    def onFindBtnClicked(self) -> None:
        """Launch the Find dialog box."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.

        if self.dlg is None:
            self.dlg = FindDialog(self)
            self.dlg.exec()
        else:
            self.show_find_window()

    def show_find_window(self) -> None:
        """Show the Find window."""

        if self.dlg is None:
            self.dlg = FindDialog(self)
            self.dlg.show()
        else:
            self.dlg.show()

    def close_find_window(self) -> None:
        """Close the Find window."""

        self.dlg.hide()

    def toggle_fullscreen(self) -> None:
        """Fullscreen."""

        if self.windowState() & Qt.WindowState.WindowFullScreen:
            self.showNormal()
        else:
            self.showFullScreen()

    # ENTRY POINT FOR F4 FIND NEXT.
    def find_next(self) -> None:
        """Spaghetti Junction."""

        self.display_verse_input.setFocus()

        if self.dlg.checks[0] != 1 or self.dlg.checks[2] == 6:
            self.find_f4_alt()
        elif self.dlg.checks[0] == 1:
            if self.gent is None:
                self.f3()
            else:
                self.find_f4()

    def make_key_whole(self, _key: str, _dict: dict, _set: dict[str, set]) -> tuple[int, str]:
        """Make _key conform to Match whole word only.

        Return the number of whole words in _key.
        """

        numstart, _key = fcs.split_strip(_key)
        words: list = _key.split()
        words = [item for item in words if item in _dict]
        _key = ''
        for i in words:
            _key += i + ' '
        _key = _key[:-1]  # Remove the last space character.
        num = len(words)
        if num != numstart and (self.dlg.checks[0] == 2 or self.dlg.checks[1] == 3):
            # A word or part of a word was removed.
            num = 0

        return num, _key

    def prepare_key_for_find(self) -> None:
        """Adjust 'key' for searching in Rnew, which has no Unicode italics.

        It also has a different apostrophe and uses æ and Æ.
        """

        p = "():,’;-?[].!<>"
        ae: list[str] = ['aea', 'aeu', 'aes', 'aet', 'aene', 'aeno', 'AEno', 'AEne', 'Aeno', 'Aene']
        ae_unicode: list[str] = ['æa', 'æu', 'æs', 'æt', 'æne', 'æno', 'Æno', 'Æne', 'Æno', 'Æne']
        count = -1
        for _ in ae:
            count += 1
            if _ in w.key:
                index = w.key.find(_)
                j = len(_)
                j += index
                w.key = w.key[:index] + ae_unicode[count] + w.key[j:]
                break
        line = ''
        for _ in w.key:
            if _ in p:
                if _ == '-' and self.dlg.checks[0] != 1:
                    continue
                else:
                    line += _
                    continue
            ch = ord(_)
            if ch in range(119860, 119885):
                ch -= 119795
                line += chr(ch)
            elif ch in range(119886, 119911):
                ch -= 119789
                line += chr(ch)
            elif ch == 119997:
                ch = 104
                line += chr(ch)
            elif ch == 39:
                ch = 8217
                line += chr(ch)
            else:
                line += _
        w.key = line

    def findf3(self, x_start: int, x_end: int) -> None:
        """Find function."""

        #self.display_verse_input.setFocus()
        current_position = self.get_line_number()
        savedx = current_position
        error_flag = False

        self.prepare_key_for_find()
        x1 = book_bounds[x_start]
        x2 = book_bounds[x_end + 1] - 1
        current_position = x1

        w.no_f3_yet = 1

        w.keym = w.key
        if w.key == '' or w.key == ' ':
            w.y = -1
            w.no_f3_yet = 0
            w.occurring = 0
            self.statusBar.clearMessage()
            self.statusBar.repaint()
        else:
            self.statusBar.showMessage('Finding...')
            self.statusBar.repaint()
            keylow = w.key.lower()
            w.y = 0
            w.occurring = 0

            if self.dlg.checks[2] == 6:
                self.iterate_regex(Rnew, x1, x2)
                if w.occurring != 0:
                    w.y = w.occur[0][0][0]
                    w.occurrence = 0
                    w.verse = 0
                    w.finding = -1
                    current_position = occurrent1()
                    self.statusBar.showMessage(w.message)
                    self.statusBar.repaint()
            else:
                tv = self.dlg.checks[0] == 1   # Raw
                if tv is not True:
                    current_position = self.findf3_ww(x1, x2)
                elif tv is True:
                    # Raw.
                    current_position = self.findf3_raw(current_position, x1, x2, keylow)

        if w.occurring == 0:
            current_position = savedx
            self.on_error('Not found...', 2000, True)
            error_flag = True

        if w.key in ('q', 'Q'):
            self.display_verse_input.clear()
            exit()
        if error_flag is not True:
            self.goto_line_find(current_position)

    def iterate_regex(self, r: list, x1: int, x2: int) -> None:
        """Iterate over R and find all the occurrences of key(s) in liszt."""

        w.occurring = 0
        w.occur = []
        w.occurs = []
        if self.dlg.checks[1] == 1:             # Match case
            pattern = rf"{w.key}"
        else:
            assert self.dlg.checks[1] == 0      # Ignore the case
            pattern = rf"(?i){w.key}"
        for _ in range(x1, x2):
            coordinate = []
            try:
                for m in re.finditer(pattern, r[_]):
                    w.occurring += 1
                    coordinate.append((m.start(), m.end()))
            except re.error:
                msg = 'Regular Expression Error.'
                self.on_error(msg, 2000, True)
                w.occurring = 0
                break
            if coordinate:
                w.occur.append(coordinate)
                w.occurs.append(_)

    def findf3_raw(self, current_position: int, x1: int, x2: int, keylow: str) -> int:
        """Find Raw."""

        if self.dlg.checks[1] == 1:  # Match case
            w.occurring += sum(Rnew[_].count(w.key) for _ in range(x1, x2))
        elif self.dlg.checks[1] == 0:  # Lower case
            w.occurring += sum(Rlow[_].count(keylow) for _ in range(x1, x2))

        if w.occurring != 0:
            w.occurrence = 0
            current_position = self.occurrent(x1, x2)
            self.statusBar.showMessage(w.message)
            self.statusBar.repaint()

        return current_position

    def assign_values(self) -> Any:
        """Can't remember what this does."""

        # print('assign_values')
        numwords: int
        w.verse = 0
        if self.dlg.checks[1] == 1:             # Match case.
            dic: Any = stripped_dict
            key: str = w.key
            # set_ and set_dict are dictionaries of words in the KJV Bible.
            # For each word, there is a set of verse/line numbers where the word occurs.
            set_: dict[Any, set] = set_dict
            r_list: list | tuple = Rstp
        else:
            assert self.dlg.checks[1] == 0      # The Case isn't checked.
            dic = strpd_low_dict
            key = w.key.lower()
            set_ = set_lowdict
            r_list = Rlsp
        numwords, w.key = self.make_key_whole(key, dic, set_)
        w.keym = w.key  # 16/12/2024

        return numwords, set_, r_list

    def findf3_ww(self, x1: int, x2: int) -> int:
        """Find Whole Words."""

        numwords, set_, r_list = self.assign_values()
        current_position: int = 0  # Pointer to the first verse with the searched for key.
        if numwords == 1:
            self.findf3_ww_1(x1, x2, set_, r_list)   # Match the whole single word.
            if w.occurring != 0:
                w.occurrence = 0
                w.verse = 0
                w.finding = -1
                current_position = occurrent1()
                self.statusBar.showMessage(w.message)
                self.statusBar.repaint()
        elif numwords > 1:
            if self.dlg.checks[0] == 2:
                findf3_ww_ac(x1, x2, numwords, set_, r_list)
            elif self.dlg.checks[0] == 3:
                findf3_ww_all(x1, x2, numwords, set_, r_list)
            elif self.dlg.checks[0] == 4:
                numwords, w.key = fcs.any_of_the_words_lookup(w.key, set_)
                findf3_ww_any(x1, x2, numwords, set_, r_list)
            if w.occurring != 0:
                if self.dlg.checks[0] != 2:     # Not whole words
                    current_position = w.occurs[0]
                    w.occurrence = 1
                    prep_statusbar_message(current_position)
                elif self.dlg.checks[0] == 2:   # Whole words
                    w.occurrence = 0
                    w.verse = 0
                    w.finding = -1
                    current_position = occurrent1()
                self.statusBar.showMessage(w.message)
                self.statusBar.repaint()
        else:
            w.occurring = 0

        return current_position

    def findf3_ww_1(self, x1: int, x2: int, _set: dict[str, set], r_list: list) -> None:
        """Match the whole single word."""

        try:
            w.occur = sorted(list(_set[w.key]))
        except KeyError:
            w.occurring = 0
        else:
            w.occurs = []
            for i in w.occur:
                if i < x1 or i > x2:
                    continue
                w.occurs.append(i)
            # List of lists with tuple of the word positions, within the related verse.
            liszt = [w.key]
            if self.dlg.checks[0] == 4:
                check_count_sort(liszt, r_list)
            else:
                iterate_list(liszt, r_list)

            if self.dlg.checks[0] > 2:
                w.occur_ww_1 = deepcopy(w.occur)
                j = -1
                for i in w.occur_ww_1:
                    j += 1
                    li = len(i)
                    if li > 1:
                        a = i[0][0]
                        b = i[li-1][1]
                        _ = w.occur_ww_1.pop(j)
                        w.occur_ww_1.insert(j, [(a, b)])
                w.occurring = len(w.occur_ww_1)   # 16/12/24
        # List of verses containing the searched for item.
        # Number of occurrences of the searchitem within the range x1 to x2.

    def occurrent(self, x1: int, x2: int):
        """Count occurrences of the item searched for."""

        if w.occurrence == 0:
            self.gent = self.gen(w.key, x1, x2)
        current_position, w.y, w.occurrence = next(self.gent)
        prep_statusbar_message(current_position)

        return current_position

    def find_f4(self) -> None:
        """Repeat find frontend for raw search."""

        if w.occurrence < w.occurring:
            current_position = self.get_line_number()

            if forward:
                back_push(current_position)
                while forward:
                    b_ = forward.pop()
                    back.append(b_)
            else:
                forward.clear()
                back_push(current_position)

            # Ensure self.gent is a valid generator
            if self.gent is None:
                raise ValueError(
                    "self.gent has not been initialized. It must be assigned a valid generator before calling find_f4.")

            try:
                current_position, w.y, w.occurrence = next(self.gent)
            except StopIteration:
                # Handle generator exhaustion if needed
                self.statusBar.showMessage("Search completed: no more matches.")
                return

            # Set the status bar message and other UI updates.
            prep_statusbar_message(current_position)
            self.statusBar.showMessage(w.message)
            self.statusBar.repaint()
            self.goto_line_find(current_position)

    def find_f4_alt(self) -> None:
        """Repeat find frontend for Match whole words."""

        if len(w.occurs) > 0 and w.occurrence < w.occurring:
            current_position = self.get_line_number()
            if forward:
                back_push(current_position)
                while forward:
                    b_ = forward.pop()
                    back.append(b_)
            else:
                current_position = w.occurs[w.verse]
                forward.clear()
                back_push(current_position)

            if self.dlg.checks[0] == 2 or self.dlg.checks[2] == 6:
                current_position = occurrent1()
            elif self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4:
                if w.verse < len(w.occurs) - 1:
                    w.verse += 1
                    current_position = w.occurs[w.verse]
                    w.occurrence += 1
                    prep_statusbar_message(current_position)

            self.statusBar.showMessage(w.message)
            self.statusBar.repaint()
            self.goto_line_find(current_position)

    def gen(self, key: str, x1: int, x2: int):
        """Return the next position of the searched for key."""

        current_position = -1
        d1 = 0
        if self.dlg.checks[1] == 1:
            files_path = Path(sh.current_directory) / "PCE-find.txt"
        else:
            assert self.dlg.checks[1] == 0
            files_path = Path(sh.current_directory) / "PCE-lower.txt"
            key = key.lower()

        # Debugging: Print the file path
        # print(f"Constructed file path: {files_path}")

        # Check if the file exists before opening it
        if not files_path.exists():
            # print(f"Error: File '{files_path}' not found.")
            raise FileNotFoundError(f"File '{files_path}' does not exist.")

        # Open and read the file line by line
        try:
            line = (z for z in files_path.open('r', encoding='utf-8'))
        except FileNotFoundError as e2:
            print(f"Error opening file: {e2}")
            raise

        while True:
            current_position += 1
            yt = 0
            if current_position > x2:
                break
            a = next(line)
            if current_position < x1:
                continue
            while key in a:
                d1 += 1
                w.y = int(a.find(key))
                if w.y != -1:
                    yt = yt + w.y + 1        #  Expected int got '() -> int' instead
                    a = a[w.y + 1:]
                    w.y = yt - 1
                    yield current_position, w.y, d1

    def goto_line_find(self, current_position: int) -> None:
        """Find function - prepare for output."""

        ln: int = Amap[current_position]
        self.adjust_highlighting(ln, current_position)
        self.move_to_line(ln)

    def stripped_punctuation_adjust(self, ln: int, current_position: int, start: int, end: int, truth: bool) -> int:
        """Addition for 'Match whole words only'.

        This adjustment allows for no punctuation in the stripped search text.
        """

        add: int
        if '¶ ' in KJV[ln] and truth is True:
            w.y += 2
            end = w.y
        if self.dlg.checks[1] == 0:
            add = fcs.repeat_find(Ldic[current_position], start, end)
        else:
            add = fcs.repeat_find(Rdic[current_position], start, end)
        return add

    def stripped_punctuation_adjust_ki(self, current_position: int, start: int, end: int) -> int:
        """Addition for 'Match whole words only'.

        This adjustment allows for no punctuation in the stripped search text.
        """

        add: int
        if self.dlg.checks[1] == 0:
            add = fcs.repeat_find_keyinc(Ldic[current_position], start, end)
        else:
            add = fcs.repeat_find_keyinc(Rdic[current_position], start, end)

        return add

    def adjust_highlighting(self, ln: int, _x: int) -> None:
        """Adjust highlighting for longer length Unicode characters."""

        add = 0
        if self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4:
            w.occur[w.verse].sort(key=lambda _x: _x[0])
            w.y = w.occur[w.verse][0][0]
            lenoccur = len(w.occur[w.verse])
            w.yend = w.occur[w.verse][lenoccur - 1][1]
            w.key = Rstp[_x][w.y:w.yend]
            lkey = len(w.key)
        elif self.dlg.checks[2] == 6:
            lkey = w.yend - w.y
            w.hiLita.length = lkey
        else:
            lkey = len(w.key)

        if self.dlg.checks[0] != 1:
            start = 0
            assert isinstance(w.y, int)
            end: int = w.y
            add = self.stripped_punctuation_adjust(ln, _x, start, end, True)
        lineinc = add

        ignore = [8217]
        litz = []
        lr = len(KJV[ln])
        for _ in range(lr):
            unich = ord(KJV[ln][_])
            if unich in ignore:
                pass
            elif unich > 230:
                litz.append(_)
        j = 0
        for i in litz:
            if i < w.y + add:
                j += 1
        lineinc += j
        er = w.y + lkey
        endof = er + add
        w.hiLita.lineinc = lineinc
        self.keyinc_section(endof, add, ln, _x)

    def keyinc_section(self, endof: int, add: int, ln: int, current_position: int) -> None:
        """keyinc section."""

        unich = 32
        num = 0
        ignore = [8217]
        litz = []
        assert isinstance(w.y, int)
        start = w.y + add
        if self.dlg.checks[0] != 1:  # Not Raw
            end = start + len(w.key)  # change w.yend
            num = self.stripped_punctuation_adjust_ki(current_position, start, end)
        lav = len(KJV[ln])
        if start > lav or endof > lav:
            pass
        else:
            for i in range(start, endof + num):
                try:
                    unich = ord(KJV[ln][i])
                except IndexError:
                    pass
                if unich in ignore:
                    pass
                elif unich > 230:
                    litz.append(i)
        keyinc = len(litz) + num
        w.hiLita.keyinc = keyinc

    def display_verse(self, current_position: int) -> None:
        """Display Bible text in textEditor."""

        # print('display_verse')
        ln: int = Amap[current_position]
        if current_position in starts_with_italics:  # Verses that start with italics.
            w.hiLita.keyinc = 1
        else:
            w.hiLita.keyinc = 0
        self.move_to_line(ln)
        self.display_verse_input.clear()
        if w.message == '':
            self.ref_to_statusbar(current_position)

    def move_to_line(self, ln: int) -> None:
        """Display engine."""

        # print('move_to_line')
        self.textEditor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.on_text_changed(ln)
        ln = make_offset(ln)
        linecursor = QTextCursor(
            self.textEditor.document().findBlockByLineNumber(ln))
        self.textEditor.moveCursor(QTextCursor.MoveOperation.End)
        self.textEditor.setTextCursor(linecursor)
        self.textEditor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        if self.dlg is not None:
            if self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4:
                w.key = w.store

    def on_text_changed(self, ln: int) -> None:
        """Highlighting."""

        # print('on_text_changed')
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(linehighlightcolor))
        fmt.setForeground(QColor(linetextcolor))

        w.hiLita.clear = True
        w.hiLita.clear_highlight()

        try:
            if self.dlg is not None:
                if self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4:
                    w.store = w.key
                    w.hiLita.clear = False
                    keys = sorted(w.occur[w.verse])
                    current_position = Amap.index(ln)
                    for i in keys:
                        w.key = '+' * (i[1] - i[0])
                        w.y = i[0]
                        self.adjust_highlighting(ln, current_position)

            w.hiLita.setFormat(w.hiLita.position, w.hiLita.length, fmt)
            w.hiLita.highlight_line(ln, fmt)
        except ValueError:
            pass

    def se_display_verse(self, current_position: int) -> None:
        """Display Bible text in textEditor after a back or forward pop."""

        ln: int = Amap[current_position]
        if current_position in starts_with_italics:  # Verses that start with italics.
            w.hiLita.keyinc = 1

        self.textEditor.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        fmt = QTextCharFormat()
        fmt.setBackground(QColor(linehighlightcolor))
        fmt.setForeground(QColor(linetextcolor))
        w.hiLita.clear = True
        w.hiLita.clear_highlight()
        w.hiLita.setFormat(w.hiLita.position, w.hiLita.length, fmt)
        w.hiLita.highlight_line(ln, fmt)
        ln = make_offset(ln)
        linecursor = QTextCursor(
            self.textEditor.document().findBlockByLineNumber(ln))
        self.textEditor.moveCursor(QTextCursor.MoveOperation.End)
        self.textEditor.setTextCursor(linecursor)
        self.textEditor.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.ref_to_statusbar(current_position)

    def ref_to_statusbar(self, current_position: int) -> None:
        """Display messages in the status bar."""

        q1, q2, q3 = sh.Info[current_position][0], sh.Info[current_position][1] + 1, sh.Info[current_position][2] + 1
        message = w.message if w.message else format_status_message(q1, q2, q3)

        self.statusBar.showMessage(message)
        self.statusBar.repaint()

    # ENTRY POINT FOR F2 DISPLAY VERSE.
    def goto_line(self, ref: str = '') -> None:
        """Move display to line requested."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        current_position: int = self.get_line_number()
        forward.clear()
        back_push(current_position)
        if not ref:
            ref = self.display_verse_input.text()
            # print(f"ref: {ref}")
        ref = fcs.remove_junk(ref)
        if ref in ('q', 'Q'):
            self.display_verse_input.clear()
            exit()
        # print(f"ref in goto_line: {ref}")
        current_position = self.reference_to_line_number(ref)
        if current_position == -1:
            self.display_verse_input.clear()
        else:
            if current_position < 0:
                current_position = 0
            if current_position > sh.LAST_VERSE_IN_BIBLE:
                current_position = sh.LAST_VERSE_IN_BIBLE
            self.display_verse(current_position)

    def  goto_book(self, _index: int) -> None:
        """Move display to line requested by comboBox_1."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        current_position = self.get_line_number()
        forward.clear()
        back_push(current_position)
        book: int = self.comboBox_1.currentIndex()
        # book is an index 0-65
        if book == sh.BOOKS_IN_THE_BIBLE - 1:
            b = 22  # Number of chapters in Revelation
        else:
            a: int = sh.Info.index([book + 1, 0, 0])
            b: int = sh.Info[a - 1][1] + 1  # No. of chapters in the book.
        w.nchapters = []
        for _ in range(1, b + 1):
            w.nchapters.append(str(_))
        self.comboBox_2.clear()
        self.comboBox_2.addItems(self.nchapters)
        self.comboBox_3.clear()
        self.nverses = ['1']
        self.comboBox_3.addItems(self.nverses)
        ref = w.nwin[book]
        ref = ref.replace(' ', '')
        # print(f"ref in goto_book: {ref}")
        current_position = self.reference_to_line_number(ref, book)
        if current_position < 0:
            current_position = 0
        if current_position > sh.LAST_VERSE_IN_BIBLE:
            current_position = sh.LAST_VERSE_IN_BIBLE
        self.display_verse(current_position)
        self.goto_chapter(_index)

    def goto_chapter(self, _index: int) -> None:
        """Move display to line requested by comboBox_2."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        book: int = self.comboBox_1.currentIndex()
        chapter: int = self.comboBox_2.currentIndex()
        if chapter == int(w.nchapters[-1]) - 1:
            # No. of verses in the chapter.
            if book == sh.BOOKS_IN_THE_BIBLE - 1:
                d = 21
            else:
                c: int = sh.Info.index([book + 1, 0, 0]) - 1
                d: int = sh.Info[c][2] + 1
        else:
            try:
                c = sh.Info.index([book, chapter + 1, 0]) - 1
            except ValueError:
                c = sh.Info.index([book + 1, 0, 0]) - 1
            d = sh.Info[c][2] + 1
        w.nverses = []
        for _ in range(1, d + 1):
            w.nverses.append(str(_))
        self.comboBox_3.clear()
        self.comboBox_3.addItems(self.nverses)

        ref = w.nwin[book]
        ref = ref.replace(' ', '')
        ref = f"{ref} {str(chapter + 1)}"

        # print(f"ref in goto_chapter: {ref}")
        current_position = self.reference_to_line_number(ref, book, chapter)
        if current_position < 0:
            current_position = 0
        if current_position > sh.LAST_VERSE_IN_BIBLE:
            current_position = sh.LAST_VERSE_IN_BIBLE
        self.display_verse(current_position)

    def goto_verse(self, _index: int) -> None:
        """Move display to line requested by comboBox_3."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        book: int = self.comboBox_1.currentIndex()
        chapter: int = self.comboBox_2.currentIndex()
        verse: int = self.comboBox_3.currentIndex()

        ref = w.nwin[book]
        ref = ref.replace(' ', '')
        ref = f"{ref} {str(chapter + 1)}.{verse + 1}"
        # print(f"ref in goto_verse: {ref}")
        current_position = self.reference_to_line_number(ref, book, chapter)
        if current_position < 0:
            current_position = 0
        if current_position > sh.LAST_VERSE_IN_BIBLE:
            current_position = sh.LAST_VERSE_IN_BIBLE
        # print(f"current_position in goto_verse: {current_position}")
        self.display_verse(current_position)

    def reference_to_line_number(self, reference_text: str, book: int = 0, chapter: int = 0) -> int:
        """Convert reference text to a line number in the Bible."""

        # print(f"2367 Original reference_text: {reference_text}")

        # Clean up prefixes like 'Chap' to prevent incorrect matching
        # Also, remove spaces and convert ':' to '.'
        reference_text = fcs.clean_chap_prefix(reference_text)  # For example, 'Chap2:3' -> '2:3'
        # print(f"2372 After cleaning chapter prefix: {reference_text}")

        # Check for book names that are adjacent to roman chapter references.
        reference_text = fcs.check_roman_chapter_adjacent(reference_text)
        # For example, 'GenesisX.IV' -> 'Genesis.X.IV'

        # print(f"2376 After checking for adjacent book names: {reference_text}")

        # Letters like iv, ix, xl, xc, i, v, x, l, c, d, m,
        # which could be roman numerals need to be distinguished from book names here.
        # If they are alone, they are probably meant as book abbreviations:
        # e.g. i -> Isaiah, l -> Leviticus, c -> Colossians, d -> Deuteronomy and m -> Micah.
        roman_book: list = ['i', 'l', 'c', 'd', 'm']
        # So,
        if reference_text.lower() in roman_book:
            pass  # Here if it's a single letter that must not be converted to numeric.
        else:
            # Convert Roman numerals to numeric values
            reference_text = fcs.convert_roman_to_integer(reference_text)
            reference_text = reference_text.replace(' ', '')
        # print(f"2389 After converting Roman numerals: {reference_text}")

        # Check if the input is in a valid format:
        #   1. "book.chapter.verse" (e.g., genesis.1.2)
        #   2. "chapter.verse" (e.g., 3.4)
        #   3. A single integer (e.g., 7)
        reference_text = reference_text.replace(' ', '.')
        # print(f"2396 Reference Text: '{reference_text}'")

        if (re.match(r"^[1-4]?[a-zA-Z]+\.\d+\.\d+(,\d+)*$", reference_text)) or fcs.is_float_re(reference_text):

            # Input is preformatted, skip additional processing
            # print(f"2401 Input appears to be preformatted: {reference_text}")
            pass
        else:
            # Preprocess the input if it's not in the expected format
            # print(f"2404 Processed reference_text: {reference_text}")

            # Special handling for input formats like "Genesis2:3" or "Genesis2.3"
            pattern = r"^([1-4]?[a-zA-Z]+)(?:\s*|\.)?(\d+)?(?:[.:](\d+))?$"
            matched = re.match(pattern, reference_text)
            if not matched:
                message = "Invalid format. Please enter a valid reference."
                # print(f"2411 Input does not match the expected format: {reference_text}")
                self.on_error(message, 750, True)
                return -1  # Input is invalid

            # Extract the parts based on matched groups
            input_book = matched.group(1)  # Book name
            input_chapter = matched.group(2)  # Chapter (e.g., '3')
            input_verse = matched.group(3)  # Verse (e.g., '4')

            # Use the current context if 'book' or 'chapter' is missing
            book = input_book.strip() if input_book else book  # Default to the current book
            chapter = int(input_chapter) if input_chapter else str(int(chapter + 1))  # Default to current chapter
            verse = int(input_verse) if input_verse else '1'  # Verse stays as-is or '1'

            # Normalise the reference to the standard "book.chapter.verse" format
            if book not in sh.onechapterbooks:
                reference_text = f"{book}.{chapter}.{verse}"

            try:
                if sh.bibledict[book] - 1 in sh.onechapterbooks:
                    # print(f"2434 Book is in onechapterbooks: {book}")
                    # print(f"2435 book: {book}")
                    # print(f"2436 chapter: {chapter}")
                    # print(f"2437 verse: {verse}")
                    if chapter == 1:
                        reference_text = f"{book}.{chapter}.{verse}"
                    else:
                        verse = chapter
                        chapter = '1'
                        reference_text = f"{book}.{chapter}.{verse}"
            except KeyError:
                pass

            # print(f"2447 Fixed reference_text: {reference_text}")

        # Use the processed text for further resolving
        current_line = self.get_line_number()

        # Handle numeric-only references (e.g. "34")
        if self.is_integer(reference_text):
            verse = int(reference_text) - 1
            # print(f"2456 verse: {verse}")
            position = self.calculate_position(current_line, verse)
            # print(f"2458 position: {position}")
            return position  # If it is outside the current chapter, it stays in the same place.

        # Handle floating point-style references (e.g., "23.7")
        reference_text = reference_text.replace(":", ".")
        if fcs.is_float_re(reference_text):
            reference_text = fcs.attach_book_name(reference_text, current_line)

        # Split the reference into parts for resolving
        bits = fcs.split_reference(reference_text)
        # print(f"2469 Split reference: {bits}")

        book_num, chapter, verse = resolve_reference(bits)
        # print(f"2064 book_num: {book_num} chapter: {chapter} verse: {verse}")

        if not book_num:
            self.error_invalid_book()

        if book_num is None or chapter is None or verse is None:
            return -1

        try:
            position = calculate_book_line(book_num, chapter, verse, current_line)
            if position is not None:
                return position
        except ValueError:
            self.error_invalid_verse_or_position()

        # If no valid position was found, return -1
        return -1

    # Helper Methods

    @staticmethod
    def calculate_position(current_line: int, new_verse: int) -> int:
        """Calculate the absolute position of a verse from the current line.
           Only allows valid positions within the same chapter."""

        inf: list = sh.Info[current_line]
        current_chapter: int = inf[1]
        # print(f"2474 current_chapter: {current_chapter}")
        current_verse = inf[2]
        # print(f"2475 current_verse: {current_verse}")
        # print(f"2476 current_line: {current_line}")
        # print(f"new_verse: {new_verse}")

        if new_verse >= 0:
            new_line: int = current_line - current_verse + new_verse
        else:
            new_line = current_line + new_verse + 1
            new_verse = current_verse + new_verse + 1

        # print(f"2477 new_line: {new_line}")

        message = f"Out of bounds. No verse {new_verse + 1} here!"
        try:
            new_chapter: int = sh.Info[new_line][1]
            # print(f"2484 new_chapter: {new_chapter}")
        except IndexError:
            # print(">>>>>>>>>>>>>>>")
            w.on_error(message, 750, True)
            return_value = current_line
        else:
            if new_chapter != current_chapter:
                # print("<<<<<<<<<<<<<<")
                w.on_error(message, 750, True)
                return_value = current_line
            else:
                return_value = new_line

        # print(f"2476 return_value: {return_value}")

        return return_value

    @staticmethod
    def is_integer(value: Any) -> bool:
        """True if the value is an integer."""

        val: str = str(value)
        if val.startswith('-'):
            return val[1:].isdigit()

        return val.isdigit()

    def error_invalid_book(self):
        """Handle book not found."""

        message: str = f"Not a book name."
        self.on_error(message, 750, True)
        # print(message)

    def error_invalid_verse_or_position(self):
        """Handle invalid chapter/verse errors."""

        message: str = f"Invalid chapter or verse."
        self.on_error(message, 750, True)
        # print(message)

    def get_line_number(self):
        """Find the line number of the verse at the top of the screen."""

        self.textEditor.moveCursor(QTextCursor.MoveOperation.StartOfLine)
        linenumber: int = self.textEditor.textCursor().blockNumber()
        if linenumber in Amap:
            current_position: int = Amap.index(linenumber)
        else:
            if linenumber < Amap[0]:
                current_position = 0
            elif linenumber > KJB_PCE_LASTLINE - 118:
                current_position = sh.LAST_VERSE_IN_BIBLE
            else:
                for _ in range(10):
                    if linenumber + _ in Amap:
                        linenumber += _
                        break
                else:
                    return sh.LAST_VERSE_IN_BIBLE
                current_position = Amap.index(linenumber)

        return current_position

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Mouse trapping routine."""

        if event.buttons() == Qt.MouseButton.LeftButton:
            current_position: int = self.get_line_number()
            self.ref_to_statusbar(current_position)
        elif event.buttons() == Qt.MouseButton.RightButton:
            pass
        elif event.buttons() == Qt.MouseButton.MiddleButton and w.no_f3_yet == 1:
            self.f4()
        elif event.buttons() == Qt.MouseButton.MiddleButton and w.no_f3_yet == 0:
            current_position = self.get_line_number()
            self.ref_to_statusbar(current_position)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Key trapping routine."""

        qtcore_keys_dict = {
            Qt.Key.Key_F2: self.f2,
            Qt.Key.Key_F3: self.f3,
            Qt.Key.Key_F4: self.f4,
            Qt.Key.Key_F5: self.f5,
            Qt.Key.Key_F6: self.f6,
            Qt.Key.Key_F7: self.earlier_book,
            Qt.Key.Key_F8: self.later_book,
            Qt.Key.Key_F9: self.f9,
            Qt.Key.Key_F10: self.earlier_chapter,
            Qt.Key.Key_F11: self.later_chapter,
            Qt.Key.Key_C: self.C,
            Qt.Key.Key_Question: self.feature,
            Qt.Key.Key_F12: self.f12,
            Qt.Key.Key_Q: exit}

        if event.key():
            try:
                qtcore_keys_dict[event.key()]()
            except KeyError:
                pass
        else:
            pass

    def f2(self) -> None:
        """F2 key for passage reference entry."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        self.display_verse_input.setFocus()
        self.statusBar.clearMessage()

    def f3(self) -> None:
        """F3 key for find key entry."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        current_position: int = self.get_line_number()
        forward.clear()
        back_push(current_position)
        self.onFindBtnClicked()

    def f4(self) -> None:
        """Find the next key F4."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        if w.key == ' ' or w.no_f3_yet == 0:
            pass
        else:
            self.textEditor.setFocus()
            self.find_next()

    def f5(self) -> None:
        """Back key."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        w.message = ''
        if len(back) > 0:
            current_position: int = self.get_line_number()
            forward_push(current_position)
            current_position = back_pop()
            self.se_display_verse(current_position)

    def f6(self) -> None:
        """Forward key."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        if len(forward) > 0:
            current_position: int = self.get_line_number()
            back_push(current_position)
            current_position = forward_pop()
            self.se_display_verse(current_position)

    def f9(self) -> None:
        """F9 Fullscreen toggle key."""

        self.toggle_fullscreen()

    def f12(self) -> None:
        """F12 Devotional key."""

        self.display_secondary_window()

    @staticmethod
    def C() -> None:
        """Commentary key."""
        commentary()

    def question(self) -> None:
        """Feature key."""
        self.feature()

    def earlier_book(self) -> None:
        """Move to the earlier book."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        current_position: int = self.get_line_number()
        book: int = sh.Info[current_position][0]
        newbook: int = book - 1
        if newbook < 0:
            self.on_error('No earlier book!', 3000, True)
        else:
            current_position = sh.Info.index([newbook, 0, 0])
            forward.clear()
            back_push(current_position)
            self.display_verse(current_position)

    def later_book(self) -> None:
        """Move to the later book."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        current_position: int = self.get_line_number()
        book: int = sh.Info[current_position][0]
        newbook: int = book + 1
        if newbook > sh.BOOKS_IN_THE_BIBLE - 1:
            self.on_error('No later book!', 3000, True)
        else:
            current_position = sh.Info.index([newbook, 0, 0])
            forward.clear()
            back_push(current_position)
            self.display_verse(current_position)

    def earlier_chapter(self) -> None:
        """Move to the earlier chapter."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        current_position: int = self.get_line_number()
        book: int = sh.Info[current_position][0]
        chapter: int = sh.Info[current_position][1]
        newchapter: int = chapter - 1
        if newchapter < 0:
            newbook: int = book - 1
            if newbook < 0:
                self.on_error('No earlier chapter!', 3000, True)
                return
            while True:
                if sh.Info[current_position][0] == book:
                    current_position -= 1
                else:
                    break
            newchapter = sh.Info[current_position][1]
            book = newbook
        current_position = sh.Info.index([book, newchapter, 0])
        forward.clear()
        back_push(current_position)
        self.display_verse(current_position)

    def later_chapter(self) -> None:
        """Move to the later chapter."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        current_position: int = self.get_line_number()
        book: int = sh.Info[current_position][0]
        chapter: int = sh.Info[current_position][1]
        newchapter: int = chapter + 1
        try:
            current_position = sh.Info.index([book, newchapter, 0])
        except ValueError:
            newbook: int = book + 1
            if newbook > sh.BOOKS_IN_THE_BIBLE - 1:
                self.on_error('No later chapter!', 3000, True)
                return
            while True:
                if sh.Info[current_position][0] == book:
                    current_position += 1
                else:
                    break
            newchapter = sh.Info[current_position][1]
            book = newbook
        current_position = sh.Info.index([book, newchapter, 0])
        forward.clear()
        back_push(current_position)
        self.display_verse(current_position)

    def on_error(self, message: str, millisecond_delay: int, clearbool: bool) -> None:
        """Error message handler."""

        current_position: int = self.get_line_number()
        self.statusBar.showMessage(message)
        self.statusBar.repaint()

        lm: float = millisecond_delay / 1000 + len(message) / 25
        self.beep(current_position, lm)

        if clearbool:
            self.statusBar.clearMessage()
            w.message = ''

    def beep(self, current_position: int, lm: float) -> None:
        """Makes a beep sound and clears the message."""

        # Initialise Pygame's mixer
        mixer.init()

        # Load your sound effect file (e.g. 'sound.wav')
        beep_sound = mixer.Sound('sound.mp3')
        beep_sound.set_volume(0.5)  # Set volume to 50%

        # Play the sound effect
        beep_sound.play()

        self.statusBar.repaint()

        # Delay for 'lm' second.
        time.sleep(lm)

        w.message = ''
        self.ref_to_statusbar(current_position)
        self.statusBar.repaint()

    def dialog_critical(self, exception_text: str) -> None:
        """Error message dialog."""

        dlg: QMessageBox = QMessageBox(self)
        dlg.setText(exception_text)
        dlg.setIcon(QMessageBox.Icon.Critical)
        dlg.show()

    def file_open(self, path1: str) -> None:
        """File opening routine."""

        # print('file_open ', path1)
        if path1:
            pass
        else:
            path1, _ = QFileDialog.getOpenFileName(
                self, "Open file", "",
                "Text documents (*.txt);All files (*.*)")
            # print(path1, ' Opened')
        if path1:
            try:
                with open(path1, "r", encoding="utf-8") as f_open:
                    w.PCE_text = f_open.read()
            except Exception as e3:
                self.dialog_critical(str(e3))
            else:
                self.path1 = path1
                if path1[-11:] == r'KJB_PCE.txt':
                    # _ = '****END OF THE NOTICE OF COPYRIGHT****'
                    length_of_copyright_notice: int = w.PCE_text.find(EOTNOC)
                    if length_of_copyright_notice == -1:
                        print('Failed to find the line ', EOTNOC)
                        print('Cannot continue until this is put right.')
                        exit()
                    total_length: int = length_of_copyright_notice + len(EOTNOC) + 1
                    w.PCE_text = w.PCE_text[total_length:]
                self.textEditor.setPlainText(w.PCE_text)
                self.update_title()

                if path1[-11:] == r'KJB_PCE.txt':
                    w.otherFileFlag = False
                    self.display_verse(0)
                else:
                    w.otherFileFlag = True

    def file_print(self) -> None:
        """File print routine."""

        dlg: QPrintDialog = QPrintDialog()
        if dlg.exec_():
            self.textEditor.print_(dlg.printer())

    def update_title(self) -> None:
        """Title update routine."""

        if Path(self.path1).stem == 'KJB_PCE':
            self.setWindowTitle(f"  THE HOLY BIBLE      Authorized King James Version")
        else:
            title: str = f"{Path(self.path1).stem if self.path1 else ''}"
            title = title.replace("Pilgrims-Progress", "The Pilgrim's Progress by John Bunyan.")
            self.setWindowTitle(title)

    def open_settings_dialog(self):
        """Open the settings dialog and update settings if the user confirms."""

        dialog = SettingsDialog(self)

        # Populate the settings dialog with current settings
        dialog.splash_checkbox.setChecked(self.settings.get("show_splash", False))
        dialog.theme_combobox.setCurrentText(self.settings.get("theme", "Light"))

        if dialog.exec():  # If the dialog is accepted (OK button).

            # Get settings from the dialog and explicitly set show_splash

            # Ensure the theme is updated
            self.settings["theme"] = dialog.theme_combobox.currentText()
            # Ensure the show_splash setting is updated
            self.settings["show_splash"] = dialog.splash_checkbox.isChecked()

            # DEBUG: Print settings before saving
            print("Settings before saving:", self.settings)

            # Save settings to the file
            fcs.save_settings_to_file(self.settings, user_settings_path)

            # Apply theme (if needed)
            self.set_theme(self.settings)

    def set_theme(self, the_settings):
        """Set the theme based on the value retrieved from settings."""

        theme_key = 'theme'  # Key in the dictionary pointing to the theme.
        current_theme = the_settings.get(theme_key, 'Light')  # Default to Light mode if not set

        # Update the settings with the currently applied theme
        if current_theme == 'Dark' and not theme_state["is_dark_mode"]:
            self.toggle_dark_mode()
            self.settings[theme_key] = 'Dark'  # Ensure settings reflect this theme
        elif current_theme == 'Light' and theme_state["is_dark_mode"]:
            self.toggle_dark_mode()
            self.settings[theme_key] = 'Light'  # Ensure settings reflect this theme

        # Save updated theme settings
        # print(f"Saving updated theme settings: {the_settings}")
        fcs.save_settings_to_file(self.settings, user_settings_path)

    def display_secondary_window(self, offset: int = 0) -> None:
        """Creates and displays the secondary window to show SME text.
        Ensures the secondary window is non-blocking."""

        # Get the SME text (from the sme method)
        try:
            sme_text = self.sme(offset)
            # print('\n', sme_text)
        except Exception as e4:
            sme_text = f"Error: {e4}"

        if not self.secondary_window or not self.secondary_window.isVisible():
            # Create a new secondary window if it doesn't exist or is closed
            self.secondary_window = SecondaryWindow(sme_text, self.geometry())
            self.secondary_window.show()
        else:
            # If the window is already open, update its contents.
            self.secondary_window.update_content(sme_text)
            self.secondary_window.raise_()
            self.secondary_window.activateWindow()

        self.update_text_display_theme()

    def sme(self, adjustment: int = 0) -> str:
        """C H Spurgeon's Morning and Evening Readings."""

        global date_file  # Needed because of assignment.

        date_file = fcs.get_date_file(date_file[2], adjustment)
        # print(f"date_file: {date_file} adjustment: {adjustment}")

        # Move to the Bible text reference at the end
        # of the SME daily reading's first line.
        a: str = sme_data[date_file[0]][date_file[1]]
        i: int = a[1:].index('"')  # Should be the 2nd " at the end, before the reference.
        j: int = a.index('\n')
        i += 2
        # print(a[i:j])
        sme_ref: str = a[i:j]
        self.goto_line(sme_ref)

        # print(f"{date_file[0]} — {date_file[1]}")
        # print(data[date_file[0]][morn_or_even])

        sme_text = f"{date_file[0]} — {date_file[1]}\n\n{sme_data[date_file[0]][date_file[1]]}"
        # print(sme_text)

        # Return the text if it exists
        try:
            return sme_text
        except KeyError:
            return f"No entry for {date_file[0]} in {date_file[1]}."

    def toggle_dark_mode(self):
        """Apply or remove dark mode for the QPlainTextEdit widget."""

        global theme_state  # Needed because of assignment.

        # Toggle dark mode state
        theme_state["is_dark_mode"] = not theme_state["is_dark_mode"]
        # print(f"Dark mode toggled: {'On' if theme_state['is_dark_mode'] else 'Off'}.")

        if self.textEditor is not None:
            if theme_state["is_dark_mode"]:
                # print("Applying dark mode to QPlainTextEdit widget.")
                # Apply dark mode (only change background and text colour)
                self.textEditor.setStyleSheet("""
                        QPlainTextEdit {
                            background-color: #121212;  /* Dark background */
                            color: #ffffff;  /* White text */
                        }
                    """)
            else:
                # print("Applying light theme to QPlainTextEdit widget.")
                # Revert to light mode (only change background and text colour)
                self.textEditor.setStyleSheet("""
                        QPlainTextEdit {
                            background-color: #ffffff;  /* Light background */
                            color: #000000;  /* Black text */
                        }
                    """)

        self.update_text_display_theme()

    def update_text_display_theme(self) -> None:
        """Update the text display theme based on the current theme 'theme_state'."""

        # Ensure the secondary window and its text display exist
        if self.secondary_window and self.secondary_window.text_display:
            # Apply the theme
            self.secondary_window.apply_theme(theme_state["is_dark_mode"])
            # print(f"Theme applied is {theme_state['is_dark_mode']}")
        else:
            # Fallback if secondary_window is not ready
            print("Error: Secondary window is not initialized or its text display is unavailable.")
            if not self.secondary_window:
                print("Secondary window is not initialized.")
            else:
                print("Secondary window's text display is unavailable.")
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ End of MainWindow class ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


class SecondaryWindow(QDialog):

    def __init__(self, text: str, parent_geometry: QRect = None):
        """
        Initialise the secondary window to display text.
        :param text: The text to display in the window.
        :param parent_geometry: The geometry of the parent (primary) window for positioning.
        """
        super().__init__()

        # Validate 'text'
        if not isinstance(text, str):
            raise ValueError(f"Expected a string for 'text', but got {type(text).__name__}")

        # Set default geometry if 'parent_geometry' is None
        if parent_geometry is None:
            parent_geometry = QRect(100, 100, 640, 480)  # Default example fallback

        # Window setup
        self.setWindowTitle("C H Spurgeon's Morning and Evening Readings")
        self.setGeometry(
            parent_geometry.x() + parent_geometry.width() + 20,  # Adjacent to parent
            parent_geometry.y(),
            640,
            518
        )

        self.text = text

        # Text display
        self.text_display = QPlainTextEdit()
        self.text_display.setPlainText(text)
        self.text_display.setReadOnly(True)  # Make it read-only

        # Apply the font from the main window
        self.fontsize = 10
        font: QFont = QFont("Cascadia Mono", self.fontsize, QFont.Weight.Medium)
        self.text_display.setFont(font)

        # Layout
        layout = QVBoxLayout(self)
        layout.addWidget(self.text_display)

        # Create a container for buttons
        button_layout = QHBoxLayout()

        # Add a spacer to push buttons to the right
        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        button_layout.addSpacerItem(spacer)

        # Left navigation button
        self.left_button: QPushButton = QPushButton("←", self)
        self.left_button.setFixedSize(30, 30)  # Small square size
        self.left_button.clicked.connect(self.navigate_left)
        button_layout.addWidget(self.left_button)


        # Right navigation button
        self.right_button: QPushButton = QPushButton("→", self)
        self.right_button.setFixedSize(30, 30)  # Small square size
        self.right_button.clicked.connect(self.navigate_right)
        button_layout.addWidget(self.right_button)

        # Add the button layout to the main layout
        layout.addLayout(button_layout)

    @staticmethod
    def navigate_left() -> None:
        """Navigate to the left."""
        os = -12
        w.display_secondary_window(os)

    @staticmethod
    def navigate_right() -> None:
        """Navigate to the right."""
        os = 12  # 12 hours forward
        w.display_secondary_window(os)

    def update_content(self, new_text: str) -> None:
        """
        Updates the displayed content of the secondary window.
        """
        self.text_display.setPlainText(new_text)

    def apply_theme(self, is_dark_mode: bool):
        """
        Apply light or dark theme to the text_display widget.
        :param is_dark_mode: Whether to apply dark mode (True) or light mode (False).
        """
        if is_dark_mode:
            self.text_display.setStyleSheet("""
                QPlainTextEdit {
                            background-color: #121212;  /* Dark background */
                            color: #ffffff;  /* White text */
                        }
                    """)
        else:
            self.text_display.setStyleSheet("""
                QPlainTextEdit {
                            background-color: #ffffff;  /* Light background */
                            color: #000000;  /* Black text */
                        }
                    """)


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.layout = QVBoxLayout(self)

        # Create the splash checkbox
        self.splash_checkbox = QCheckBox("Show Splash Screen")
        self.layout.addWidget(self.splash_checkbox)

        # Create theme combobox
        self.theme_combobox = QComboBox()
        self.theme_combobox.addItems(["Light", "Dark"])
        self.layout.addWidget(self.theme_combobox)

        # Create the button box with correct typing
        button_types = QDialogButtonBox.StandardButton
        buttons = button_types.Ok | button_types.Cancel  # type: ignore
        self.button_box = QDialogButtonBox(buttons)

        # Connect the button box signals
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        # Add the button box to the layout
        self.layout.addWidget(self.button_box)


class AboutWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Abib {CURRENT_VERSION}")

        self.resize(480, 810)  # Set the initial window size
        self.content = None
        self.about_window = None

        # Create a QLabel widget
        self.label = QLabel(self)

        # Load About.txt content
        self.content = self.about()

        # Set the contents of the QLabel
        self.label.setText(self.content)

        # Center align content
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.fontsize = 14
        fixedfont: QFont = QFont("Cascadia Mono", self.fontsize, QFont.Weight.Bold)
        self.label.setFont(fixedfont)

        # Set the QLabel as the central widget
        self.setCentralWidget(self.label)

    def about(self) -> str:
        """Load the 'About' content from ABOUT.txt."""

        self.content: str = ""
        try:
            with open("ABOUT.txt", "r", encoding="utf-8") as file_about:
                self.content = file_about.read()
        except FileNotFoundError:
            self.content = "ABOUT.txt file not found."
        except UnicodeDecodeError:
            self.content = "Error: Unable to decode ABOUT.txt. Please make sure the file encoding is UTF-8."

        winwidth: int = 480
        winheight: int = 810

        # Allow for small screen sizes
        winheight, winwidth = sizer(winheight, winwidth)

        w_origin, h_origin = centerer(winwidth, winheight)
        self.setGeometry(w_origin, h_origin, winwidth, winheight)
        # w.otherFileFlag = True

        return self.content


class SyntaxHighlighter(QSyntaxHighlighter):
    """Syntax highlighter."""

    def __init__(self, parent) -> None:
        """Initialise highlighter."""
        super(SyntaxHighlighter, self).__init__(parent)
        self._highlight_lines = {}
        self.lineinc = 0
        self.keyinc = 0
        self.position = 0
        self.length = 1
        self.fmt = None
        self.clear = False

    def highlight_line(self, line_num, fmt) -> None:
        """Highlight lines."""

        if isinstance(line_num, int) and \
                (line_num >= 0) and (isinstance(fmt, QTextCharFormat)):
            self._highlight_lines[line_num] = fmt
            block = self.document().findBlockByLineNumber(line_num)
            self.rehighlightBlock(block)

    def clear_highlight(self) -> None:
        """Clear highlight."""

        if self.clear is True:
            self._highlight_lines = {}
            self.rehighlight()

    def highlightBlock(self, text) -> None:
        """Highlight a block."""

        # Ensure _highlight_lines is populated
        if not self._highlight_lines:
            # print("Skipping highlight: _highlight_lines not populated yet.")
            return

        blockNumber = self.currentBlock().blockNumber()
        self.fmt = self._highlight_lines.get(blockNumber)
        if self.fmt is not None:
            # noinspection PyTypeChecker
            self.position = w.y +  self.lineinc
            if w.dlg is not None:
                if w.dlg.checks[2] != 6:
                    self.length = len(w.key) + self.keyinc
                else:
                    self.length += self.keyinc
            else:
                self.length = len(w.key) + self.keyinc
            self.setFormat(self.position, self.length, self.fmt)
            # print(f'Block {blockNumber} {KJV[blockNumber]}')


class TextDocumentWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.current_reference = None
        self.setWindowTitle("Text Document Viewer")
        self.resize(800, 600)

        # Load Bible data from a JSON file
        bible_data = fcs.load_json_dict("bible_data.json")
        self.bible_data = bible_data

        # Main layout and text editor
        self.layout = QVBoxLayout()  # Directly set a layout for QDialog
        self.setLayout(self.layout)

        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Cascadia Mono", 12))
        self.text_edit.setReadOnly(True)  # Set to False if you want it editable
        self.layout.addWidget(self.text_edit)

        # Connect the vertical scroll bar signal to continuously save the scroll position
        self.text_edit.verticalScrollBar().valueChanged.connect(self.save_scroll_position)

        # Display the content of Pilgrim's Progress file
        self.load_text_file("Pilgrims-Progress.txt")
        self.text_edit.viewport().setMouseTracking(True)
        self.text_edit.viewport().installEventFilter(self)
        self.text_edit.viewport().setAttribute(Qt.WidgetAttribute.WA_Hover, True)

        self.popup_window = None  # Track if a popup exists

        self.canonical_books = {
            1: "Genesis",
            2: "Exodus",
            3: "Leviticus",
            4: "Numbers",
            5: "Deuteronomy",
            6: "Joshua",
            7: "Judges",
            8: "Ruth",
            9: "1 Samuel",
            10: "2 Samuel",
            11: "1 Kings",
            12: "2 Kings",
            13: "1 Chronicles",
            14: "2 Chronicles",
            15: "Ezra",
            16: "Nehemiah",
            17: "Esther",
            18: "Job",
            19: "Psalms",
            20: "Proverbs",
            21: "Ecclesiastes",
            22: "Song of Solomon",
            23: "Isaiah",
            24: "Jeremiah",
            25: "Lamentations",
            26: "Ezekiel",
            27: "Daniel",
            28: "Hosea",
            29: "Joel",
            30: "Amos",
            31: "Obadiah",
            32: "Jonah",
            33: "Micah",
            34: "Nahum",
            35: "Habakkuk",
            36: "Zephaniah",
            37: "Haggai",
            38: "Zechariah",
            39: "Malachi",
            40: "Matthew",
            41: "Mark",
            42: "Luke",
            43: "John",
            44: "Acts",
            45: "Romans",
            46: "1 Corinthians",
            47: "2 Corinthians",
            48: "Galatians",
            49: "Ephesians",
            50: "Philippians",
            51: "Colossians",
            52: "1 Thessalonians",
            53: "2 Thessalonians",
            54: "1 Timothy",
            55: "2 Timothy",
            56: "Titus",
            57: "Philemon",
            58: "Hebrews",
            59: "James",
            60: "1 Peter",
            61: "2 Peter",
            62: "1 John",
            63: "2 John",
            64: "3 John",
            65: "Jude",
            66: "Revelation",
        }

    @staticmethod
    def save_scroll_position(value):
        """
        Save the current vertical scroll position immediately.
        """

        # Update the settings dictionary with the new value
        w.settings["last_read_position"] = value

        # Persist the settings to disk.
        fcs.save_settings_to_file(w.settings, user_settings_file)

    def load_text_file(self, file_path1):
        """
        Load the content of the specified file and display it in the text editor.
        Update the window title with the name of the loaded file.
        """
        # Get last read position; default to 0 if not set
        last_position: int = w.settings.get("last_read_position", 0)
        # print(f"Loaded last_read_position = {last_position}")
        try:
            with open(file_path1, 'r', encoding='utf-8') as file1:
                content = file1.read()
                self.text_edit.setText(content)

                # Set the scrollbar to the last read position after loading the text
                QTimer.singleShot(100, lambda: self.text_edit.verticalScrollBar().setValue(last_position))

                # Extract the file name from the file path
                file_name = file_path1.removesuffix(".txt")

                # Update the window title to match the file name
                self.setWindowTitle(file_name)
        except FileNotFoundError:
            self.text_edit.setText("Error: File not found.")
        except Exception as e1:
            self.text_edit.setText(f"Error loading file: {e1}")

    def get_chapter_text(self, book, chapter):
        """
        Retrieve the text of a specific chapter from the Bible data.
        :param book: The name of the book (e.g. 'Genesis')
        :param chapter: The chapter number as a string (e.g. '1')
        :return: A concatenated string of all verses in the chapter.
        """
        if (
                book in self.bible_data
                and chapter in self.bible_data[book]
        ):
            # Combine all verses in the chapter
            verses = self.bible_data[book][chapter]
            return "\n".join(f"{verse_num}: {text}" for verse_num, text in verses.items())
        else:
            return f"Chapter {chapter} of {book} not found."

    def highlight_references(self):
        """Highlight scripture references in the text."""
        text = self.text_edit.toPlainText()

        # Find all scripture references using a regex pattern
        references: list = self.find_scripture_references(text)

        # Highlight references
        cursor = self.text_edit.textCursor()
        fmt = QTextCharFormat()
        fmt.setForeground(QColor("blue"))
        fmt.setFontUnderline(True)

        # Clear previous formatting
        cursor.select(QTextCursor.SelectionType.Document)
        no_format = QTextCharFormat()
        cursor.setCharFormat(no_format)

        # Apply new highlights
        for match in references:
            start, length = match['start'], match['length']
            cursor.setPosition(start)
            cursor.movePosition(QTextCursor.MoveOperation.Right, QTextCursor.MoveMode.KeepAnchor, length)
            cursor.setCharFormat(fmt)

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Leave:
            # The mouse has left the viewport, so close the popup
            self.closePopup()
        elif event.type() == QEvent.Type.MouseMove:
            # Optionally, verify if the MouseMove event is outside your highlight area
            # and close the popup if needed
            cursor = self.text_edit.cursorForPosition(event.position().toPoint())
            position = cursor.position()
            text = self.text_edit.toPlainText()
            references = self.find_scripture_references(text)
            over_reference = any(ref['start'] <= position <= ref['start'] + ref['length'] for ref in references)
            if not over_reference:
                self.closePopup()
            else:
                self.handle_hover(event)
        return super().eventFilter(obj, event)

    def handle_hover(self, event):
        """Detect whether a highlighted reference was hovered and display its text."""

        # Get the mouse cursor position and associated text position.
        cursor = self.text_edit.cursorForPosition(event.position().toPoint())
        position = cursor.position()
        text = self.text_edit.toPlainText()
        references = self.find_scripture_references(text)

        # Find a reference under the current mouse position.
        hovered_reference = None
        for ref in references:
            if ref["start"] <= position <= ref["start"] + ref["length"]:
                hovered_reference = ref
                break

        if hovered_reference is None:
            # No reference under the mouse:
            if self.popup_window is not None:
                self.popup_window.close()
                self.popup_window = None
            self.current_reference = None
            return

        # Determine if the current hovered reference is the same as the previously stored one
        same_reference = (
                self.current_reference is not None and
                self.current_reference["start"] == hovered_reference["start"] and
                self.current_reference["length"] == hovered_reference["length"]
        )

        if same_reference:
            # If the mouse is still within the current reference...
            # Check whether the popup exists and is visible.
            if self.popup_window is None or not self.popup_window.isVisible():
                # The popup was closed externally (or never created), so re-create it.
                pass  # Continue to creating it, below.
            else:
                # Update the popup's position.
                cursor = self.text_edit.cursorForPosition(event.position().toPoint())
                cursor_rect = self.text_edit.cursorRect(cursor)
                global_cursor_top_left = self.text_edit.mapToGlobal(cursor_rect.topLeft())
                text_edit_top_left = self.text_edit.mapToGlobal(self.text_edit.rect().topLeft())
                popup_x = text_edit_top_left.x()
                popup_y = global_cursor_top_left.y() + 60  # Adjust the vertical offset for a couple of lines down
                self.popup_window.move(popup_x, popup_y)
                return
        else:
            # Hovered reference differs from current_reference.
            if self.popup_window is not None:
                self.popup_window.close()
                self.popup_window = None

            # Update the current_reference to the new one.
            self.current_reference = hovered_reference

        # Create a new popup for the hovered/current reference.
        self.popup_window = QWidget()
        self.popup_window.setWindowFlags(Qt.WindowType.ToolTip)
        self.popup_window.setStyleSheet("border: 2px solid blue;")

        scriptures, canonical = self.get_scripture(hovered_reference)
        scripture = scriptures + "\n" + canonical + " KJV"

        label = QLabel(scripture, self.popup_window)
        label.setFont(self.text_edit.font())
        label.setWordWrap(True)
        label.setFixedWidth(self.text_edit.width())
        label.adjustSize()

        layout = QVBoxLayout(self.popup_window)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label)
        self.popup_window.adjustSize()

        # Position the popup relative to the cursor.
        cursor = self.text_edit.cursorForPosition(event.position().toPoint())
        cursor_rect = self.text_edit.cursorRect(cursor)
        global_cursor_top_left = self.text_edit.mapToGlobal(cursor_rect.topLeft())
        text_edit_top_left = self.text_edit.mapToGlobal(self.text_edit.rect().topLeft())
        popup_x = text_edit_top_left.x()
        popup_y = global_cursor_top_left.y() + 60  # Adjust vertical offset as needed
        self.popup_window.move(popup_x, popup_y)

        self.popup_window.show()

    def closePopup(self):
        if self.popup_window and self.popup_window.isVisible():
            self.popup_window.close()
            self.popup_window = None

    @staticmethod
    def find_scripture_references(text):
        """Find scripture references using regex, supporting multiple verses."""
        references = []
        pattern = (
            r'(?:(?<=^)|(?<=[^\w]))'  # Start at the beginning or after a non-word character
            r'([1-3]?\s?[A-Za-z]+)(?:\.)?\s+'  # Book name with an optional period
            r'(?:(\d{1,3}):'  # Option A: With colon (capture chapter in group 2)
            r'(\d{1,3}(?:(?:,\s*\d{1,3})+|(?:-\d{1,3}))?)'  # Capture verses in group 3
            r'|'  # OR
            r'(\d{1,3}(?:(?:,\s*\d{1,3})+|(?:-\d{1,3}))?)'  # Option B: Without a colon, capture verses in group 4
            r')\b'
        )
        for match in re.finditer(pattern, text):
            full_text = match.group(0).lstrip()  # remove any leading whitespace
            book = match.group(1)
            if match.group(3):  # Option A: chapter and verses provided
                chapter = int(match.group(2))
                verses = match.group(3)
            elif match.group(4):  # Option B: No colon; assume a one-chapter book if applicable
                chapter = 1
                verses = match.group(4)
                if book.strip().lower() not in {"obad", "phlm", "2john", "3john", "jude"}:
                    continue
            else:
                continue

            references.append({
                'text': full_text,
                'book': book,
                'chapter': chapter,
                'verse': verses,
                'start': match.start() + (len(match.group(0)) - len(full_text)),
                'length': len(full_text)
            })
        return references

    def get_scripture(self, reference):
        """Takes a reference and returns the scripture text."""

        book = reference['book']
        chapter = reference['chapter']
        verse = reference['verse']

        # Lookup scripture from Bible data
        scripture_text = self.lookup_scripture(book, chapter, verse)

        normalized_book = self.normalize_book_input(book)
        book_id = sh.bibledict.get(normalized_book)
        if not book_id:
            return "Scripture not found."

        # Mapping from book numbers to canonical names.
        full_book = self.canonical_books.get(book_id, book)
        if book_id - 1 in sh.onechapterbooks:
            full_reference = f"{full_book} {verse}"
        else:
            full_reference = f"{full_book} {chapter}:{verse}"

        return scripture_text, full_reference

    @staticmethod
    def normalize_book_input(book_input: str) -> str:
        # Convert to lowercase and remove non-alphanumeric characters.
        return re.sub(r'\W+', '', book_input.lower())

    def lookup_scripture(self, book, chapter, verses):
        # print(f"Looking up scripture for {book} {chapter}:{verses}")
        normalized_book = self.normalize_book_input(book)
        book_id = sh.bibledict.get(normalized_book)
        if not book_id:
            print(f"Book not found: {book}")
            print(f"Normalized book: {normalized_book}")
            print(f"Book ID: {book_id}")
            return "Scripture not found."

        # Mapping from book numbers to canonical names.
        full_book = self.canonical_books.get(book_id, book)

        chapter_data = self.bible_data.get(full_book, {}).get(str(chapter), {})

        verse_numbers = []
        # Split by comma in case we have multiple verses or ranges.
        for part in verses.split(','):
            part = part.strip()
            if '-' in part:
                try:
                    start, end = part.split('-', 1)
                    start = int(start.strip())
                    end = int(end.strip())
                    # Generate a list of verse numbers from start to end, inclusive.
                    if start <= end:
                        verse_numbers.extend(range(start, end + 1))
                    else:
                        verse_numbers.extend(range(start, end - 1, -1))
                except ValueError:
                    print(f"Scripture not found for {book} {chapter}:{part}")
                    return "Scripture not found."
            else:
                try:
                    verse_numbers.append(int(part))
                except ValueError:
                    print(f"Scripture not found for {book} {chapter}:{part}")
                    return "Scripture not found."

        results = []
        for ve in verse_numbers:
            verse_text = str(ve) + ' ' + chapter_data.get(str(ve))
            if verse_text is None:
                results.append(f"Verse {ve} not found.")
            else:
                results.append(verse_text)

        # Join multiple verses with line breaks. Adjust as needed.
        return "\n".join(results)


class FindDialog(QDialog):
    """Find dialog."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        # Create an instance of the GUI
        self.ui = Ui_Dialog()
        # Run the .setupUi() method to show the GUI
        self.ui.setupUi(self)

        # checks[0] is 1-4 for radiobuttons 1 to 4
        # checks[1] is 0-1 for checkBox
        # checks[2] is 5-6 for radiobuttons 5 & 6
        self.checks = [1, 0, 5]
        self.setGeometry(700, 300, 400, 378)

        self.ui.lineEdit_1.setToolTip("press RETURN to find")
        # self.ui.lineEdit_1.setEchoMode(QLineEdit.Normal)
        self.ui.lineEdit_1.returnPressed.connect(self.getter)
        self.ui.lineEdit_1.setClearButtonEnabled(False)
        self.ui.lineEdit_1.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.ui.pushButton_1.clicked.connect(self.ui.lineEdit_1.clear)

        self.ui.comboBox_1.addItems(w.nwin)
        self.ui.comboBox_2.addItems(w.nwin)
        self.ui.comboBox_1.setCurrentIndex(0)
        self.ui.comboBox_2.setCurrentIndex(sh.BOOKS_IN_THE_BIBLE - 1)


        QOk = QDialogButtonBox.StandardButton.Ok
        self.ui.buttonBox.button(QOk).setEnabled(True)
        self.ui.buttonBox.button(QOk).setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.buttonBox.button(QOk).clicked.connect(self.getter)
        QCancel = QDialogButtonBox.StandardButton.Cancel
        self.ui.buttonBox.button(QCancel).setEnabled(True)
        self.ui.buttonBox.button(QCancel).setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.buttonBox.button(QCancel).clicked.connect(w.close_find_window)

        self.ui.lineEdit_1.setFocus()

        self.ui.comboBox_1.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.comboBox_2.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_1.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_2.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_3.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_4.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_5.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_6.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.ui.checkBox.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.ui.lineEdit_1.textChanged.connect(self.ui.lineEdit_1.setFocus)
        self.ui.pushButton_1.hide()

        # Dynamically show/hide the clear button based on text presence
        self.ui.lineEdit_1.textChanged.connect(self.toggle_clear_button)

    def toggle_clear_button(self):
        if self.ui.lineEdit_1.text():
            self.ui.pushButton_1.show()
            self.ui.lineEdit_1.setFocus()
        else:
            self.ui.pushButton_1.hide()
            self.ui.lineEdit_1.setFocus()

    def getter(self) -> None:
        """Get values from the find window and transfer to findf3."""

        i: int
        j: int
        w.key = self.ui.lineEdit_1.text()
        i, j = self.get_scope()
        self.get_checks()
        w.findf3(i, j)
        w.close_find_window()

    def get_scope(self) -> tuple[int, int]:
        """Get the scope from the comboboxes."""

        i: int = self.ui.comboBox_1.currentIndex()
        j: int = self.ui.comboBox_2.currentIndex()
        if i > j:
            a: int = i
            i = j
            j = a
            self.ui.comboBox_1.setCurrentIndex(i)
            self.ui.comboBox_1.setCurrentIndex(j)

        return i, j

    def check_changed(self) -> None:
        """Ensure that the checkBox is correct."""

        if self.ui.checkBox.isChecked():
            self.checks[1] = 1
        else:
            self.checks[1] = 0

    def radiobutton1_4_changed(self) -> None:
        """Ensure that radiobuttons 1 to 4 are correct."""

        if self.ui.radiobutton_1.isChecked():
            self.checks[0] = 1
        elif self.ui.radiobutton_2.isChecked():
            self.checks[0] = 2
        elif self.ui.radiobutton_3.isChecked():
            self.checks[0] = 3
        elif self.ui.radiobutton_4.isChecked():
            self.checks[0] = 4

    def radiobutton5_6_changed(self) -> None:
        """Ensure that radiobuttons 5 & 6 are correct."""

        if self.ui.radiobutton_6.isChecked():
            self.checks[2] = 6
            self.ui.radiobutton_1.setChecked(True)
            self.checks[0] = 1
        else:
            self.checks[2] = 5

    def get_checks(self) -> None:
        """Store the states of the checkboxes in the list checks."""

        self.checks = [1, 0, 5]
        self.check_changed()
        self.radiobutton1_4_changed()
        self.radiobutton5_6_changed()


if __name__ == '__main__':

    app: QApplication = QApplication()
    app.setApplicationName("Abib")

    # If settings.json exists in the user's "APPDATA/Abib" folder, then do nothing.
    user_settings_file = sh.user_settings_dir / "settings.json"  # User's settings.json.
    if user_settings_file.exists():
        pass
    else:
        fcs.setup_Abib_settings(sh.user_settings_dir)
    user_settings_path: str = str(user_settings_file)

    # Load settings if the file is found (default if not).
    settings: dict = fcs.load_settings_from_file(user_settings_path)

    # Show the splash screen if enabled in settings
    splash_path = sh.current_directory / "images" / "Abib_barley.png"
    if settings.get("show_splash", False):  # Default to False if the key is missing.
        splash = QSplashScreen(QPixmap(splash_path))
        splash.show()

    if sh.system() == 'Windows':
        app.processEvents()

    width, height = app.primaryScreen().size().toTuple()
    half_width = width / 2
    half_height = height / 2

    w: MainWindow = MainWindow()

    back: list = []
    forward: list = []

    # integers
    x: int = 0
    w.y = 0
    w.hiLita.lineinc = 0
    w.hiLita.keyinc = 0
    w.hiLita.length = 1
    w.no_f3_yet = 0
    w.yend = 0
    w.finding = 0
    w.verse = 0
    w.occurring = 0
    w.occurrence = 0
    w.occur = []
    w.occurs = []
    w.count = []
    w.PCE_text = []
    w.key = ' '
    w.keym = ''
    w.message = ''
    w.store = ' '
    # w.hiLita.clear = True
    w.gent = None
    w.otherFileFlag = True
    # Initialise date_index (hours relative to today's date)
    # w.date_index: int = 0

    linehighlightcolor: QColor = QColor("#0138b7")
    linetextcolor: QColor = QColor("#ffffff")

    update_abib()

    book_bounds: list[int] = [
        0, 1533, 2746, 3605, 4893, 5852, 6510, 7128, 7213, 8023,
        8718, 9534, 10253, 11195, 12017, 12297, 12703, 12870,
        13940, 16 , 17316, 17538, 17655, 18947, 20311, 20465,
        21738, 22095, 22292, 22365, 22511, 22532, 22580, 22685,
        22732, 22788, 22841, 22879, 23090, 23145, 24216, 24894,
        26045, 26924, 27931, 28364, 28801, 29058, 29207, 29362,
        29466, 29561, 29650, 29697, 29810, 29893, 29939, 29964,
        30267, 30375, 30480, 30541, 30646, 30659, 30673, 30698,
        31102]

    starts_with_italics: list[int] = [6203, 13009, 14972, 15412, 22195, 28117]

    # -------------------------------------------------- #
    KJB_PCE_LASTLINE = 36199
    # Including about 70 blank lines at the end which are
    # retained and 118 lines of copyright notice at the
    # beginning which are removed below.
    # Plus, there are about 182 lines comprising
    # THE HOLY BIBLE title etc.
    # TO THE MOST HIGH AND MIGHTY PRINCE JAMES,
    # THE EPISTLE DEDICATORY
    # THE TRANSLATORS TO THE READER
    # THE NAMES AND ORDER OF THE BOOKS OF THE
    # OLD AND NEW TESTAMENT, WITH ABBREVIATIONS.
    #
    # So, that is 31,102 + 70 + 118 + 182 + 66 BOOK TITLES +
    # THE 1,189 CHAPTER TITLES AND BLANK LINES = 36,199
    # -------------------------------------------------- #

    # Construct full file path using pathlib
    file_path = str(Path(sh.str_cwd) / "KJB_PCE.txt")
    # Pass the constructed path to fcs.readio
    KJV = fcs.readio('', file_path, KJB_PCE_LASTLINE)

    EOTNOC: str = '****END OF THE NOTICE OF COPYRIGHT****\n'

    i_: int = 0
    try:
        i_ = KJV.index(EOTNOC)
    except ValueError:
        print('Failed to find the line ', EOTNOC)
        print('Cannot continue until this is put right.')
        exit('Reinstalling the program should resolve this.')
    KJV = KJV[i_ + 1:]
    KJV = tuple(KJV)

    assert (len(KJV) == KJB_PCE_LASTLINE - 118)

    # Use pathlib to construct the path
    file_path = str(Path(sh.str_cwd) / "Amap.txt")

    # Pass the constructed path to the function
    Amap: list = sh.readfile('', file_path, sh.EOF_AMAP)

    Amap = Amap[17:]

    Ps119: list[int] = [
        15907, 15915, 15923, 15931, 15939, 15947, 15955, 15963, 15971, 15979,
        15987, 15995, 16003, 16011, 16019, 16027, 16035, 16043, 16051, 16059,
        16067]
    P119: list = []
    for _ in Ps119:
        v: Any = Amap[_]
        P119.append(v)

    # Open KJB_PCE.txt
    w.file_open(str(sh.base_dir / "KJB_PCE.txt"))

    # Read stripped_dict.txt
    with open("stripped_dict.txt", encoding="utf-8") as f:
        stripped_dict: Any = load(f)

    # Read strpd_low_dict.txt
    with open("strpd_low_dict.txt", encoding="utf-8") as f:
        strpd_low_dict: Any = load(f)

    # Load dictionaries using fcs.load_list_set_dict
    set_dict: dict[Any, set] = fcs.load_list_set_dict("list_dict.json", stripped_dict)
    set_lowdict: dict[Any, set] = fcs.load_list_set_dict("list_lowdict.json", strpd_low_dict)

    # Read and process PCE-find.txt
    Rnew = fcs.readio('', str(Path(sh.base_dir / "PCE-find.txt")), sh.EOF_BIBLE_TEXT)
    Rnew = tuple(Rnew)
    Rdic: dict[int, Any] = dict(enumerate(Rnew))  # Convert Rnew to dictionary.

    # Read and process PCE-lower.txt
    Rlow = fcs.readio('', str(Path(sh.base_dir / "PCE-lower.txt")), sh.EOF_BIBLE_TEXT)
    Rlow = tuple(Rlow)
    Ldic: dict[int, Any] = dict(enumerate(Rlow))  # Convert Rlow to dictionary.

    # Read PCE-stripped.txt
    Rstp = fcs.readio('', str(Path(sh.base_dir / "PCE-stripped.txt")), sh.EOF_BIBLE_TEXT)
    Rstp = tuple(Rstp)

    # Read PCE-stripped_lower.txt
    Rlsp = fcs.readio('', str(Path(sh.base_dir / "PCE-stripped_lower.txt")), sh.EOF_BIBLE_TEXT)
    Rlsp = tuple(Rlsp)

    try:
        with open("morning_evening.json", "r", encoding="utf-8") as file:
            sme_data = load(file)  # Load JSON data
    except JSONDecodeError as e:
        print(f"JSON file is invalid: {e}")

    date_file: tuple = fcs.get_date_file()

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Plugin socket.
    # Paste the plugin here for probably single use and run Abib to run
    # it.  This enables utility plugins to use the functions of Abib.
    # Beware of overwriting previous files accidentally.
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # *** PLACE YOUR PLUGIN HERE (between the two lines) ***

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # Set the application icon
    app_icon: QIcon = QIcon(str(sh.icon_path))  # Convert the Path object to string for QIcon
    app.setWindowIcon(app_icon)

    w.show()
    exit(app.exec())
# This is a new line that ends the file.
