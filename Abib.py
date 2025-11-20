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
Make sure python is up to date in your distro (But < 3.14)
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

Using PySide6-6.10.0 and python3.13.9 (64-bit).

20/11/2025

"""

import re
import time
from sys import exit, setrecursionlimit
setrecursionlimit(200)

from copy import deepcopy
from pathlib import Path
from itertools import chain, islice

from typing import Any, Dict, Set, List
from text_window import TextDocumentWindow as ExternalTextDocumentWindow
from history import History
history = History()
back = history.back
forward = history.forward

# Global window 'handle' placeholder; set by app.run() at startup
w: Any | None = None
# Global splash screen reference (kept alive until the user disables it in settings)
splash: Any | None = None

from PySide6.QtWidgets import (QMainWindow, QWidget,
                               QPlainTextEdit, QLineEdit, QComboBox, QGridLayout, QMessageBox,
                               QPushButton, QHBoxLayout, QInputDialog,
                               QStatusBar, QFileDialog, QSplashScreen)

from PySide6.QtGui import (QMouseEvent, QKeyEvent, QSyntaxHighlighter, QColor, QFont,
                           QTextCursor, QTextCharFormat, QPixmap, QKeySequence, QShortcut)

from PySide6.QtCore import Qt, QRect, QEvent

import fcs
import shared as sh

from find_dialog import FindDialog
from ui_helpers import NoZoomPlainTextEdit
from windows import SecondaryWindow as ExtSecondaryWindow, AboutWindow as ExtAboutWindow
from settings_dialog import SettingsDialog
from ui.themes import ThemeManager, ThemeState
from services.audio import AudioService
from services.settings import SettingsService
from services.printing import PrintingService
from domain.scripture_refs import resolve_reference as parse_ref, calculate_book_line as calc_line
from ui.actions import setup_shortcuts, setup_menus_and_toolbars

# ---- Module-level placeholders (populated at runtime by app.run) ----
# These keep static analysis quiet and preserve runtime assignment from app.py
KJV: tuple | list = ()
Amap: list = []
Ps119: list[int] = []
P119: list = []
book_bounds: list[int] = []
starts_with_italics: list[int] = []
KJB_PCE_LASTLINE: int = 0
EOTNOC: str = ""
Rnew: tuple = ()
Rdic: dict = {}
Rlow: tuple = ()
Ldic: dict = {}
Rstp: tuple = ()
Rlsp: tuple = ()
# Search dictionaries and sources
stripped_dict: dict = {}
strpd_low_dict: dict = {}
set_dict: dict = {}
set_lowdict: dict = {}
# Screen metrics
width: int = 0
height: int = 0
half_width: float = 0.0
half_height: float = 0.0
# Colours
linehighlightcolor = None
linetextcolor = None

try:
    from ctypes import windll  # Only exists on Windows.
except ImportError:
    windll = None  # Linux or Mac if here.

CURRENT_VERSION = sh.CURRENT_VERSION

try:
    myappid = f"Abib Bible Reader.{CURRENT_VERSION}"
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except (AttributeError, OSError) as e:
    # AttributeError: non-Windows (windll is None); OSError: Windows API failure
    print(f"Error setting APP ID: {e}")


def back_push(current_position: int) -> None:
    """Push onto the back stack (delegates to History)."""
    history.back_push(w, current_position)


def back_pop() -> int:
    """Pop from the back stack (delegates to History)."""
    return history.back_pop(w)


def forward_push(current_position) -> None:
    """Push onto the forward stack (delegates to History)."""
    history.forward_push(w, int(current_position))


def forward_pop() -> int:
    """Pop from the forward stack (delegates to History)."""
    return history.forward_pop(w)


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


def findf3_ww_ac(x1: int, x2: int, numwords: int, _set: Dict[str, Set], r_list: list) -> None:
    """Match whole words (phrase)."""

    liszt = w.key.split(' ')
    s = _set[liszt[0]] & _set[liszt[1]]
    if numwords > 2:
        for i in range(2, numwords):
            j = liszt[i]
            s = s & _set[j]
    w.occur = sorted(list(s))
    w.occurs = []

    pattern = re.compile(rf"\b{re.escape(w.key)}\b")

    for i in w.occur:
        if x1 <= i <= x2 and pattern.search(r_list[i]):
            w.occurs.append(i)

    liszt = [w.key]
    iterate_list(liszt, r_list)
    c = 0
    for i in w.occur:
        li = len(i)
        c += li
    w.occurring = c


def findf3_ww_all(x1: int, x2: int, numwords: int, _set: Dict[str, Set], r_list: list) -> None:
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

    # If no occurrences found, set occurring to 0 and return early
    if lo == 0:
        w.occurring = 0
        return

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
        elif (i != j) or (k == lo - 1):
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


def findf3_ww_any(x1: int, x2: int, numwords: int, _set: Dict[str, Set], r_list: list) -> None:
    """Match any word."""

    liszt: list[str] = w.key.split(' ')
    s: Set = set()
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
    # Determine the start of Psalms dynamically (avoid magic number 13940)
    try:
        psalms_book_idx: int = sh.bibledict['psalms'] - 1  # 0-based book index
        # Use islice to avoid direct indexing, keeping linters/type-checkers happy
        psalms_start_verse_idx: int = next(islice(book_bounds, psalms_book_idx, None))
    except (KeyError, StopIteration, TypeError):
        psalms_start_verse_idx = 13940  # Fallback if data not yet loaded
    # Avoid direct indexing into Amap; use islice with safe fallbacks
    try:
        lx_source = next(islice(Amap, psalms_start_verse_idx, None))
        lx: int = int(lx_source) - 1
    except (StopIteration, TypeError, ValueError):
        # Fallbacks if Amap not ready; use known Psalms start or zero
        try:
            lx: int = int(next(islice(Amap, 13940, None))) - 1
        except (StopIteration, TypeError, ValueError):
            lx = 0
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
    """Open a Calvin commentary file by letting the user choose from the Calvin folder."""
    try:
        calvin_dir = Path(sh.str_cwd) / "Calvin"
        files = sorted([p for p in calvin_dir.glob("*.txt") if p.is_file()])
        if not files:
            QMessageBox.information(
                None,
                "Calvin Commentaries",
                "No commentary files found in the Calvin folder."
            )
            return
        labels = sorted(p.name for p in files)
        choice, ok = QInputDialog.getItem(
            w,  # parent to keep it on top of the main window
            "Calvin Commentaries",
            "Open:",
            labels,
            0,
            False,
        )
        if ok and choice:
            path = str(calvin_dir / choice)
            try:
                w.open_text_file_in_window(path)
            except (RuntimeError, FileNotFoundError, OSError, ValueError, AttributeError) as e4:
                print("Could not open commentary window:", e4)
    except (OSError, RuntimeError, ValueError) as e5:
        QMessageBox.warning(None, "Calvin Commentaries", f"An error occurred: {e5}")


class MainWindow(QMainWindow):
    """MainWindow class."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialise."""
        super(MainWindow, self).__init__(*args, **kwargs)

        # Load saved settings or initialise default ones.

        # Settings service and window geometry
        self.settings_service = SettingsService()
        x6, y6, width6, height6 = self.settings_service.get_window_geometry("main_window")
        self.setGeometry(x6, y6, width6, height6)

        # self.feature = None
        self.text_edit_window = None
        self.text_edit = None
        self.history_index = None
        self.command_history = None
        self.about_window = None
        self.is_dark_mode: None = None
        # Use SettingsService-managed settings dict
        self.settings = self.settings_service.settings
        # self.textEditor: None = None
        self.path1: None = None
        self.display_verse_input: None = None
        self.comboBox_1: None = None
        self.comboBox_2: None = None
        self.comboBox_3: None = None
        self.hiLita: None = None
        # Theme toggle button (replaces the old Quit button in the UI)
        self.buttonTheme: None = None
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
        self.other_works_combo: QComboBox | None = None
        # Predeclare UI elements that are instantiated in initui to satisfy linters
        self.last_work_btn: QPushButton | None = None
        # Keyboard shortcut for reopening the last Other Work (predeclared for linters)
        self.shortcut_last_work: QShortcut | None = None
        self.other_works_map: Dict[str, str] = {}
        self.statusBar: None = None
        self.okButton: None = None
        self.dlg: None = None  # No external window yet.
        self.gent: None = None
        # self.textEditor: QPlainTextEdit = QPlainTextEdit()
        self.textEditor = NoZoomPlainTextEdit()
        # Predeclare actions bundle to satisfy linters (assigned in initui)
        self.actions_bundle = None

        # Theme manager (extract dark mode logic)
        # Initialise 'ThemeManager' based on persisted settings
        is_dark = self.settings.get("theme", "Light") == "Dark"
        self.theme = ThemeManager(ThemeState(is_dark_mode=is_dark))

        # Services
        self.audio = AudioService()
        self.printing = PrintingService()

        # Reading plans (SME) service
        from domain.reading_plans import ReadingPlans
        self.reading_plans = ReadingPlans()

        # Store a reference to the secondary window to manage its lifecycle
        self.secondary_window = None

        # Create keyboard shortcuts via the centralised helper
        self.shortcuts_bundle = setup_shortcuts(self)

        #Qt.QTimer.singleShot(0, lambda: self.sme("PM", -1))  # Adjusted to yesterday evening's reading.

        self.nwin: List[str] = [
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
        self.nchapters: List[str] = []
        for _ in range(1, 51):
            self.nchapters.append(str(_))
        self.nverses: List[str] = []
        for _ in range(1, 32):
            self.nverses.append(str(_))

        # noa: int = len(argv)
        self.fontsize: int = 14
        # self.winwidth: int = width6  # Initial width of Abib Bible.
        # self.winheight: int = height6  # Initial height of Abib Bible.
        """
        if noa > 1:
            try:
                self.fontsize = int(argv[1])
                self.winwidth = int(argv[2])
                self.winheight = int(argv[3])
            except ValueError:
                pass
        """

        self.initui()

    def initui(self) -> None:
        """Initialise Mainwindow GUI."""

        # w_origin, h_origin = centerer(self.winwidth, self.winheight)
        # self.setGeometry(w_origin, h_origin, self.winwidth, self.winheight)

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

        # Theme toggle button (Light/Dark), replacing the old Quit button
        self.buttonTheme = QPushButton("Light/Dark")
        self.buttonTheme.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonTheme.clicked.connect(self.toggle_dark_mode)
        grid.addWidget(self.buttonTheme, 2, 2)
        self.buttonTheme.setToolTip("Toggle Light/Dark theme")
        self.buttonTheme.setFocusPolicy(Qt.FocusPolicy.NoFocus)

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

        self.buttonf13 = QPushButton("Commentary")
        self.buttonf13.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf13.clicked.connect(commentary)
        grid.addWidget(self.buttonf13, 5, 1)
        self.buttonf13.setToolTip("Open Calvin’s Commentaries (Ctrl+Shift+C)")
        self.buttonf13.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Bottom-right: combo box of Other Works (with a quick "Last" button)
        self.other_works_combo = QComboBox()
        self.other_works_combo.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        # Create a small horizontal layout to hold the combo and the Last button
        other_works_layout = QHBoxLayout()
        other_works_layout.setContentsMargins(0, 0, 0, 0)
        other_works_layout.addWidget(self.other_works_combo)

        # Option A: Add a one-click button to jump to the last read item
        self.last_work_btn = QPushButton("Last")
        self.last_work_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        # Make the "Last" button roughly half its natural/suggested width
        try:
            suggested_w = self.last_work_btn.sizeHint().width()
            self.last_work_btn.setFixedWidth(max(40, int(suggested_w * 0.5)))
        except (RuntimeError, AttributeError, TypeError):
            # If sizeHint isn't available for any reason, skip resizing gracefully
            pass
        self.last_work_btn.setToolTip("Open the last read book (Ctrl+L)")
        self.last_work_btn.clicked.connect(self._select_last_other_work)
        other_works_layout.addWidget(self.last_work_btn)

        grid.addLayout(other_works_layout, 5, 2)

        # Populate the combo with .txt files from 'Other Works'
        other_works_dir = Path(sh.str_cwd) / "Other Works"
        files = sorted([p for p in other_works_dir.glob("*.txt") if p.is_file()])
        self.other_works_map = {p.stem: str(p) for p in files}
        # Populate combo filtered by settings['show_work'] values
        self._refresh_other_works_combo()

        # Default selection: last viewed item if available; else Pilgrims-Progress; else leave as first item
        last_work = self.settings.get("last_other_work") if isinstance(self.settings, dict) else None
        if last_work and last_work in self.other_works_map:
            self.other_works_combo.setCurrentText(last_work)
        elif "Pilgrims-Progress" in self.other_works_map:
            self.other_works_combo.setCurrentText("Pilgrims-Progress")

        # When selection changes, open or update the document reader window
        self.other_works_combo.currentTextChanged.connect(self._open_other_work)
        # Also handle a user clicking the already-selected item (e.g., default on first click)
        self.other_works_combo.activated.connect(
            lambda index: self._open_other_work(self.other_works_combo.itemText(index))
        )

        # Option B: Keyboard shortcut to jump to the last read Other Work
        try:
            self.shortcut_last_work = QShortcut(QKeySequence("Ctrl+L"), self)
            self.shortcut_last_work.setContext(Qt.ShortcutContext.WindowShortcut)
            self.shortcut_last_work.activated.connect(self._select_last_other_work)
        except (RuntimeError, AttributeError, TypeError):
            # If shortcuts aren't available on this platform/Qt version, ignore gracefully
            pass
        container: QWidget = QWidget()
        container.setLayout(grid)
        self.setCentralWidget(container)
        self.display_verse_input.setFocus()

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)

        # Build menus, toolbars, and actions via the centralised helper
        self.actions_bundle = setup_menus_and_toolbars(self)

        self.secondary_window = ExtSecondaryWindow(
                    "Text to display",
                    navigate_left_cb=lambda: self.display_secondary_window(-12),
                    navigate_right_cb=lambda: self.display_secondary_window(12),
                )

        # Apply theme from settings during initialisation.
        self.set_theme(self.settings)

        # self.update_title()
        self.show()

        # Placeholder for the AboutWindow (lazy-loaded)
        self.about_window = None

        self.apply_font_size()  # Set an initial font size from settings

    def _refresh_other_works_combo(self) -> None:
        """Repopulate the Other Works combo according to settings['show_work'] filter."""
        if not self.other_works_combo:
            return
        self.other_works_combo.blockSignals(True)
        try:
            self.other_works_combo.clear()
            allowed: List[str] = []
            try:
                show_map = dict(self.settings.get("show_work") or {})
            except (TypeError, ValueError, AttributeError):
                # If settings are not a mapping, or the value cannot be cast to dict,
                # fall back to an empty mapping without swallowing unrelated errors.
                show_map = {}
            for stem in sorted(self.other_works_map.keys()):
                if str(show_map.get(stem, "false")).lower() == "true":
                    allowed.append(stem)
            if allowed:
                self.other_works_combo.addItems(allowed)
        finally:
            self.other_works_combo.blockSignals(False)

    def _build_show_works_menu(self, settings_menu) -> None:
        """Populate the given Settings submenu with a tickable list of Other Works.

        Toggling an item updates settings['show_work'] and refreshes the combo box.
        """
        # Clear any prior dynamic actions after the first static action (Open Settings...)
        # We'll rebuild from scratch to reflect file system and settings changes.
        # Remove all actions after the first if the first is our 'Open Settings...' action
        actions = settings_menu.actions()
        # Keep the first (Open Settings...) if present, clear the rest
        for act in actions[1:]:
            settings_menu.removeAction(act)

        # Separator between Open Settings and the list
        settings_menu.addSeparator()

        show_map = dict(self.settings.get("show_work") or {})
        # Ensure keys exist for current files
        for stem in sorted(self.other_works_map.keys()):
            if stem not in show_map:
                show_map[stem] = "false"

        # Build checkable actions
        from PySide6.QtGui import QAction
        for stem in sorted(self.other_works_map.keys()):
            checked = str(show_map.get(stem, "false")).lower() == "true"
            act = QAction(stem, self)
            act.setCheckable(True)
            act.setChecked(checked)

            def _make_toggler(name: str):
                def _toggle(_checked: bool):
                    # Update settings with string booleans
                    show_map_local = dict(self.settings.get("show_work") or {})
                    show_map_local[name] = "true" if _checked else "false"
                    self.settings["show_work"] = show_map_local
                    self.settings_service.save(self.settings)
                    self._refresh_other_works_combo()
                return _toggle

            act.toggled.connect(_make_toggler(stem))
            settings_menu.addAction(act)

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

        # Pass the event to the parent class
        return super().eventFilter(source, event)

    def closeEvent(self, event: Any):
        """Handle window close event - save geometry"""
        geometry = self.geometry()
        self.settings_service.save_window_geometry(
            "main_window",
            geometry.x(), geometry.y(), geometry.width(), geometry.height()
        )
        event.accept()

    def increase_font_size(self):
        current_size = self.settings_service.get_bible_font_size()
        new_size = min(current_size + 2, 72)  # Max size of 72
        self.settings_service.update_bible_font_size(new_size)
        # print(f"DEBUG: Increase Bible fontsize to: {new_size}")
        self.apply_font_size()

    def decrease_font_size(self):
        current_size = self.settings_service.get_bible_font_size()
        new_size = max(current_size - 2, 8)  # Min size of 8
        self.settings_service.update_bible_font_size(new_size)
        # print(f"DEBUG: Decrease Bible fontsize to: {new_size}")
        self.apply_font_size()

    def apply_font_size(self):
        self.fontsize = self.settings_service.get_bible_font_size()
        # Create a QFont object and apply it to the QPlainTextEdit
        font = QFont("Cascadia Mono", self.fontsize)
        self.textEditor.setFont(font)

    def feature(self) -> None:
        """Open the Other Works reader window for the currently selected item."""
        current_stem = None
        combo = getattr(self, "other_works_combo", None)
        if isinstance(combo, QComboBox):
            try:
                current_stem = combo.currentText()
            except RuntimeError:
                # The widget may have been deleted/disposed by Qt
                current_stem = None
        if current_stem and hasattr(self, "other_works_map"):
            self._open_other_work(current_stem)
        else:
            # Fallback: open default Pilgrims Progress if available
            other_works_dir = Path(sh.str_cwd) / "Other Works"
            pp = other_works_dir / "Pilgrims-Progress.txt"
            path = str(pp) if pp.exists() else None
            if path:
                self._open_text_file_in_window(path)

    def open_text_file_in_window(self, path: str) -> None:
        """Public wrapper to open or update the external text reader window."""
        self._open_text_file_in_window(path)

    def _open_text_file_in_window(self, path: str) -> None:
        """Open the ExternalTextDocumentWindow with the given file path 
           or update existing, then focus it."""
        if getattr(self, "text_edit_window", None) is None:
            self.text_edit_window = ExternalTextDocumentWindow(
                initial_file_path=path,
                settings=self.settings,
                settings_path=getattr(self, "user_settings_path", None)
            )
            # When the user clicks a scripture reference in the reader, navigate here
            try:
                self.text_edit_window.referenceActivated.connect(self._on_reader_reference_activated)
                setattr(self.text_edit_window, "_connected_to_main", True)
            except (AttributeError, RuntimeError, TypeError):
                pass
            # Apply the current theme to the new window and its editor
            try:
                self.text_edit_window.apply_theme(self.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            # Apply palette to the window; ThemeManager handles internal safety
            self.theme.apply_widget(self.text_edit_window)
        else:
            self.text_edit_window.load_text_file(path)
            # Ensure the signal is connected even if the window already existed
            try:
                if not getattr(self.text_edit_window, "_connected_to_main", False):
                    self.text_edit_window.referenceActivated.connect(self._on_reader_reference_activated)
                    setattr(self.text_edit_window, "_connected_to_main", True)
            except (AttributeError, RuntimeError, TypeError):
                pass
            try:
                self.text_edit_window.apply_theme(self.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            self.theme.apply_widget(self.text_edit_window)
        self.text_edit_window.show()
        self.text_edit_window.raise_()
        self.text_edit_window.activateWindow()

    def _on_reader_reference_activated(self, ref: str) -> None:
        """Navigate the Bible main window to the clicked reference from the reader window."""
        try:
            # Use existing navigation, which handles all parsing and UI updates
            self.goto_line(ref)
            # Bring the main window to the front so the user sees the context
            try:
                self.show()
                self.raise_()
                self.activateWindow()
            except (RuntimeError, AttributeError):
                pass
        except (ValueError, TypeError, KeyError, IndexError, RuntimeError):
            # Be resilient: if parsing fails, ignore silently
            pass

    def _open_other_work(self, stem: str) -> None:
        """Open or update the TextDocumentWindow for the selected Other Works item."""
        if not stem or not hasattr(self, "other_works_map"):
            return
        path = self.other_works_map.get(stem)
        if not path:
            return
        # Open/update the reader window
        self._open_text_file_in_window(path)
        # Persist last selected work in settings so the combo defaults next launch
        try:
            if isinstance(self.settings, dict):
                self.settings["last_other_work"] = stem
                # Save via settings service if available
                if getattr(self, "settings_service", None):
                    self.settings_service.save(self.settings)
        except (OSError, TypeError, ValueError, RuntimeError):
            # Be tolerant: failure to persist should not break the opening
            pass

    def _select_last_other_work(self) -> None:
        """Re-select and open the last read Other Works item in the combo box.

        Implements Option A (button) and is also used by Option B (Ctrl+L shortcut).
        """
        try:
            if not hasattr(self, "other_works_map"):
                return
            last_work = self.settings.get("last_other_work") if isinstance(self.settings, dict) else None
            if not last_work:
                return
            if last_work not in self.other_works_map:
                return

            # Find the index in the combo for robustness
            idx = self.other_works_combo.findText(last_work)
            if idx < 0:
                return

            # If it's already selected, Qt won't emit signals; open explicitly
            if self.other_works_combo.currentIndex() == idx:
                self._open_other_work(last_work)
                return

            # Otherwise, switch selection without emitting signals twice, then open explicitly
            try:
                self.other_works_combo.blockSignals(True)
                self.other_works_combo.setCurrentIndex(idx)
            finally:
                try:
                    self.other_works_combo.blockSignals(False)
                except (RuntimeError, AttributeError, TypeError):
                    pass
            # Ensure the reader opens even if a platform doesn't emit currentTextChanged
            self._open_other_work(last_work)
        except (RuntimeError, AttributeError, KeyError, TypeError, ValueError):
            # Be silent on any unexpected issue
            pass

    def show_about_dialog(self):
        """Show the 'About' window when Help -> About is clicked."""

        # Initialize AboutWindow if it hasn't been created
        if self.about_window is None:
            self.about_window = ExtAboutWindow(f"Abib {CURRENT_VERSION}")
        # Apply the theme palette to the About window (apply_widget is internally safe)
        self.theme.apply_widget(self.about_window)
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

        if w.otherFileFlag:
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
            # Apply theme palette to Find dialog (apply_widget is internally safe)
            self.theme.apply_widget(self.dlg)
            self.dlg.exec()
        else:
            self.show_find_window()

    def show_find_window(self) -> None:
        """Show the Find window."""

        if self.dlg is None:
            self.dlg = FindDialog(self)
            # Apply theme palette to Find dialog (apply_widget is internally safe)
            self.theme.apply_widget(self.dlg)
            self.dlg.show()
        else:
            # Ensure the theme is applied before showing
            self.theme.apply_widget(self.dlg)
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

    def make_key_whole(self, _key: str, _dict: Dict, _set: Dict[str, Set]) -> tuple[int, str]:
        """Make _key conform to Match whole word only.

        Return the number of whole words in _key.
        """

        numstart, _key = fcs.split_strip(_key)
        words: List = _key.split()
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
        ae: List[str] = ['aea', 'aeu', 'aes', 'aet', 'aene', 'aeno', 'AEno', 'AEne', 'Aeno', 'Aene']
        ae_unicode: List[str] = ['æa', 'æu', 'æs', 'æt', 'æne', 'æno', 'Æno', 'Æne', 'Æno', 'Æne']
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
        try:
            x1 = int(next(islice(book_bounds, x_start, None)))
        except (StopIteration, TypeError, ValueError):
            x1 = 0
        try:
            x2 = int(next(islice(book_bounds, x_end + 1, None))) - 1
        except (StopIteration, TypeError, ValueError):
            x2 = sh.LAST_VERSE_IN_BIBLE
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
                if not tv:
                    current_position = self.findf3_ww(x1, x2)
                elif tv:
                    # Raw.
                    current_position = self.findf3_raw(current_position, x1, x2, keylow)

        if w.occurring == 0:
            current_position = savedx
            self.on_error('Not found...', 2000, True)
            error_flag = True

        if w.key in ('q', 'Q'):
            self.display_verse_input.clear()
            exit()
        if not error_flag:
            self.goto_line_find(current_position)

    def iterate_regex(self, r: tuple, x1: int, x2: int) -> None:
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
            set_: Dict[Any, Set] = set_dict
            r_list: List | tuple = Rstp
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

    def findf3_ww_1(self, x1: int, x2: int, _set: Dict[str, Set], r_list: List) -> None:
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

    def occurrent(self, x1: int, x2: int) -> int:
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

        try:
            ln = int(next(islice(Amap, current_position, None)))
        except (StopIteration, TypeError, ValueError):
            ln = 0
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
            if unich not in ignore and unich > 230:
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
        if not(start > lav or endof > lav):
            for i in range(start, endof + num):
                try:
                    unich = ord(KJV[ln][i])
                except IndexError:
                    pass
                if unich not in ignore and unich > 230:
                    litz.append(i)
        keyinc = len(litz) + num
        w.hiLita.keyinc = keyinc

    def display_verse(self, current_position: int) -> None:
        """Display Bible text in textEditor."""

        # print('display_verse')
        try:
            ln = int(next(islice(Amap, current_position, None)))
        except (StopIteration, TypeError, ValueError):
            ln = 0
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

        try:
            ln = int(next(islice(Amap, current_position, None)))
        except (StopIteration, TypeError, ValueError):
            ln = 0
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
        roman_book: List = ['i', 'l', 'c', 'd', 'm']
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
        #   2. "chapter.verse" (e.g. 3.4)
        #   3. A single integer (e.g. 7)
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

        book_num, chapter, verse = parse_ref(bits)
        # print(f"2064 book_num: {book_num} chapter: {chapter} verse: {verse}")

        if not book_num:
            self.error_invalid_book()

        if book_num is None or chapter is None or verse is None:
            return -1

        try:
            position = calc_line(book_num, chapter, verse, current_line)
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

        inf: List = sh.Info[current_line]
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
            # Safely get the first element of Amap without direct indexing (for linters/type-checkers)
            try:
                first_amap = int(next(islice(Amap, 0, None)))
            except (StopIteration, TypeError, ValueError):
                first_amap = 0
            if linenumber < first_amap:
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

        # Play error sound via audio service (non-blocking and safe)
        self.audio.play_error()

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
            except (FileNotFoundError, PermissionError, OSError, UnicodeDecodeError) as e3:
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
        self.printing.print_plain_text(self.textEditor, parent=self)

    def update_title(self) -> None:
        """Title update routine."""

        if Path(self.path1).stem == 'KJB_PCE':
            self.setWindowTitle(f"  THE HOLY BIBLE      Authorized King James Version")
        else:
            title: str = f"{Path(self.path1).stem if self.path1 else ''}"
            title = title.replace("Pilgrims-Progress", "The Pilgrim's Progress by John Bunyan.")
            self.setWindowTitle(title)

    def open_settings_dialog(self):
        """Open the settings dialog.
          Option B behavior:
        - Clicking 'Reset to defaults' applies defaults immediately (persist + theme + splash).
        - OK/Cancel then simply close the dialog; OK still saves any manual changes made after.
        """

        dialog = SettingsDialog(self)

        # Populate the settings dialog with current settings
        prev_show_splash = bool(self.settings.get("show_splash", False))
        dialog.splash_checkbox.setChecked(prev_show_splash)
        dialog.theme_combobox.setCurrentText(self.settings.get("theme", "Light"))

        # Ensure dialog follows current theme palette
        self.theme.apply_widget(dialog)

        # Option B: apply defaults immediately when the reset button is clicked
        def _apply_defaults_immediately() -> None:
            # Read the current state to determine splash transition
            prev = bool(self.settings.get("show_splash", False))
            default_settings = fcs.get_default_settings()
            defaults_show_splash = bool(default_settings.get("show_splash", False))

            # Replace entire settings with defaults and persist immediately
            try:
                self.settings.clear()
                self.settings.update(default_settings)
            except (AttributeError, TypeError):
                # Fallback: replace the reference if clear/update fails for any reason
                self.settings = dict(default_settings)
            self.settings_service.save(self.settings)

            # Apply theme across UI right away
            self.set_theme(self.settings)

            # Manage splash visibility transitions immediately
            self._update_splash_visibility(prev, defaults_show_splash)

            # Prevent double-application on the OK path (Option A logic)
            dialog.was_reset_to_defaults = False

        try:
            dialog.reset_defaults_btn.clicked.connect(_apply_defaults_immediately)
        except (RuntimeError, AttributeError, TypeError):
            # Ignore failures to connect signal due to Qt object state or missing attributes
            pass

        if dialog.exec():  # If the dialog is accepted (OK button)
            # Determine new values; if the user pressed 'Reset to defaults', then use canonical defaults
            # (In Option B we set was_reset_to_defaults = False after immediate applying.)
            if getattr(dialog, "was_reset_to_defaults", False):
                defaults = fcs.get_default_settings()
                new_theme = defaults.get("theme", "Light")
                new_show_splash = bool(defaults.get("show_splash", False))
            else:
                new_theme = dialog.theme_combobox.currentText()
                new_show_splash = dialog.splash_checkbox.isChecked()

            # Update in-memory settings
            self.settings["theme"] = new_theme
            self.settings["show_splash"] = new_show_splash

            # Save settings via service
            self.settings_service.save(self.settings)

            # Apply theme (if needed)
            self.set_theme(self.settings)

            # Manage splash visibility based on the checkbox change
            # Use module-level globals maintained by app.run()
            global splash, w
            # Update splash screen visibility based on prior and new states
            self._update_splash_visibility(prev_show_splash, new_show_splash)

    @staticmethod
    def _update_splash_visibility(prev_show: bool, new_show: bool) -> None:
        """Show/hide the splash screen according to previous and new settings.
        Encapsulates the duplicated logic used in the Settings dialog flows.
        Safe against Qt object lifetime issues and missing resources.
        """
        global splash, w
        # Turning splash OFF: finish/close and clear the global reference
        if prev_show and not new_show:
            try:
                if splash is not None:
                    try:
                        splash.finish(w)
                    except (RuntimeError, AttributeError, TypeError):
                        splash.close()
            except (RuntimeError, AttributeError):
                pass
            splash = None
        # Turning splash ON: create if absent and show
        if (not prev_show) and new_show:
            try:
                if splash is None:
                    splash_path = sh.current_directory / "images" / "Abib_barley.png"
                    pix = QPixmap(str(splash_path))
                    # Use size().isEmpty() instead of isNull() to avoid stub/type warnings
                    new_splash = QSplashScreen(pix) if not pix.size().isEmpty() else QSplashScreen()
                    new_splash.show()
                    splash = new_splash
            except (RuntimeError, AttributeError, OSError):
                # Ignore failures to avoid disrupting the UI
                pass

    def _refresh_theme_across_ui(self) -> None:
        """Apply the app palette, style the main editor, update secondary windows, and
        re-theme any open dialogs/windows.
         Centralised to avoid duplication."""
        # Apply application-wide palette first so dialogs/menus follow suit
        self.theme.apply_app_palette()
        # Apply to the main editor and secondary window
        self.theme.apply_to_editor(self.textEditor)
        self.update_text_display_theme()
        # Also refresh any currently open dialogs/windows
        if getattr(self, 'dlg', None):
            self.theme.apply_widget(self.dlg)
        if getattr(self, 'about_window', None):
            self.theme.apply_widget(self.about_window)
        if getattr(self, 'text_edit_window', None):
            try:
                self.text_edit_window.apply_theme(self.theme.state.is_dark_mode)
            except (RuntimeError, AttributeError):
                pass
            self.theme.apply_widget(self.text_edit_window)

    def set_theme(self, the_settings):
        """Apply the theme from settings using ThemeManager without legacy globals."""

        theme_key = 'theme'
        current_theme = the_settings.get(theme_key, 'Light')

        # Set ThemeManager state explicitly to match settings
        self.theme.state.is_dark_mode = (current_theme == 'Dark')

        # Apply the palette and refresh all open UI elements
        self._refresh_theme_across_ui()

        # Ensure settings reflect what's applied and persist
        self.settings[theme_key] = 'Dark' if self.theme.state.is_dark_mode else 'Light'
        self.settings_service.save(self.settings)

    def display_secondary_window(self, offset: int = 0) -> None:
        """Creates and displays the secondary window to show SME text.
        Ensures the secondary window is non-blocking."""

        # Get the SME text (from the sme method)
        try:
            sme_text = self.sme(offset)
        except (KeyError, IndexError, ValueError, TypeError) as e4:
            sme_text = f"Error: {e4}"

        if not self.secondary_window or not self.secondary_window.isVisible():
            # Create a new secondary window if it doesn't exist or is closed
            self.secondary_window = ExtSecondaryWindow(
                sme_text,
                navigate_left_cb=lambda: self.display_secondary_window(-12),
                navigate_right_cb=lambda: self.display_secondary_window(12),
            )
            self.secondary_window.show()
        else:
            # If the window is already open, update its contents.
            self.secondary_window.update_content(sme_text)
            self.secondary_window.raise_()
            self.secondary_window.activateWindow()

        self.update_text_display_theme()

    def sme(self, adjustment: int = 0) -> str:
        """C H Spurgeon's Morning and Evening Readings.

        Delegates to ReadingPlans service and navigates to the referenced scripture.
        """

        try:
            sme_text, sme_ref = self.reading_plans.get_sme(adjustment)
        except (KeyError, TypeError, ValueError) as err:
            # Narrow exception handling to expected data/parsing issues
            return f"Error retrieving SME: {err}"

        if sme_ref:
            try:
                self.goto_line(sme_ref)
            except (ValueError, TypeError, KeyError, IndexError):
                # Ignore navigation errors; still show text
                pass
        return sme_text

    def toggle_dark_mode(self):
        """Toggle dark mode using ThemeManager and persist to settings."""

        # Toggle via ThemeManager
        is_dark = self.theme.toggle()

        # Persist selection in settings
        self.settings["theme"] = "Dark" if is_dark else "Light"
        self.settings_service.save(self.settings)

        # Apply the palette and refresh all open UI elements
        self._refresh_theme_across_ui()

    def update_text_display_theme(self) -> None:
        """Update the text display theme using ThemeManager."""

        # Apply to the secondary window if available
        if self.secondary_window and getattr(self.secondary_window, 'text_display', None):
            self.theme.apply_to_secondary(self.secondary_window)
        else:
            # Fallback if secondary_window is not ready
            print("Error: Secondary window is not initialized or its text display is unavailable.")
            if not self.secondary_window:
                print("Secondary window is not initialized.")
            else:
                print("Secondary window's text display is unavailable.")
#  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~ End of MainWindow class ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


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

        if self.clear:
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
            self.position = w.y + self.lineinc
            if w.dlg is not None:
                if w.dlg.checks[2] != 6:
                    self.length = len(w.key) + self.keyinc
                else:
                    self.length += self.keyinc
            else:
                self.length = len(w.key) + self.keyinc
            self.setFormat(self.position, self.length, self.fmt)
            # print(f'Block {blockNumber} {KJV[blockNumber]}')


if __name__ == '__main__':
    # Bootstrap moved to app.run() for cleaner modularisation (PR10)
    from app import run
    run()
