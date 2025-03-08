#!/usr/bin/env python
"""
Copyright 2025 Andrew Kingston.

This file is part of Abib Bible Reader.

Abib is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

Abib is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with Abib.  If not, see <https://www.gnu.org/licenses/>.

For linux use:
Make sure python is up-to-date in your distro
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
Version 410.1 using PySide6.8.2.1 and python3.13.2 (64-bit).
07/03/2025
----------
"""
import re
import time
from os import environ
from sys import exit, argv

# Suppress pygame welcome message
environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "1"

from pygame import mixer

from copy import deepcopy
from io import open
from itertools import chain
from json import load, loads, dump, JSONDecodeError
from os import path, getenv
from pathlib import Path
from platform import system
from shutil import copy2
from string import ascii_letters, digits

from roman import fromRoman, InvalidRomanNumeralError
from typing import Any
from datetime import datetime, timedelta

from PySide6 import QtCore
from PySide6 import QtGui
from PySide6 import QtPrintSupport
from PySide6 import QtWidgets
from PySide6.QtGui import QIcon, QColor, QFont, QPixmap
from PySide6.QtPrintSupport import QPrintDialog
from PySide6.QtWidgets import (QDialogButtonBox, QApplication, QPlainTextEdit, QLineEdit, QComboBox,
                               QGridLayout, QWidget, QMessageBox, QSplashScreen, QPushButton, QDialog,
                               QSizePolicy, QSpacerItem)

from find import Ui_Dialog

try:
    from ctypes import windll  # Only exists on Windows.
except ImportError:
    windll = None  # Linux if here, this satisfies PyCharm's fastidiousness.
    pass

try:
    # Included in try/except block for Mac/Linux
    myappid = 'Abib Bible Reader.410.1'
    windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
except Exception as e:
    print(f"Error setting APP ID: {e}")

# Define global theme state
theme_state = {
    "is_dark_mode": False  # Default is light mode
}
date_index: int = 0  # Hours relative to today's date.

mixer.init()

def readfile(input_path: str, input_filename: str, file_length: int) -> list:
    """File reading routine — reads a text file into a list."""

    # print('readio ', input_filename)
    err = "Abib is not in the same directory as its files and folders.\n"
    output_listname = []
    try:
        with open(f'{input_path}{input_filename}', 'r') as f_read:
            for _ in range(file_length):
                x5 = f_read.readline()
                try:
                    i_line = int(x5.splitlines()[0])  # Convert to int if possible
                except ValueError:
                    i_line = x5.splitlines()[0]  # Keep as string if conversion fails
                output_listname.append(i_line)
    except FileNotFoundError:
        exit(err)  # Exit program with an error message

    return output_listname


def split_strip(_key: str) -> tuple[int, str]:
    """Remove whitespace from '_key' entered as passage reference."""

    p = " ()[];:'!<>,.-?"       # Characters to strip ’ not needed.

    # Split the string into words, strip the unwanted characters from each word,
    # and filter out any resulting empty words.
    word_list = [word.strip(p) for word in _key.split(' ') if word.strip(p)]

    num = len(word_list)        # Count the number of words
    _key = ' '.join(word_list)  # Join words back into a single string

    return num, _key


def back_push(x_) -> None:
    """Push onto the back stack."""

    if len(back) == 0:
        saving = (x_, w.y, w.hiLita.lineinc, w.hiLita.keyinc, w.hiLita.fmt,
                  w.hiLita.length, w.no_f3_yet, w.occurring, w.key, w.dlg)
        back.append(saving)
    else:
        if back[-1][0] == x_ and back[-1][1] == w.y:
            pass
        else:
            saving = (x_, w.y, w.hiLita.lineinc, w.hiLita.keyinc,
                      w.hiLita.fmt, w.hiLita.length, w.no_f3_yet,
                      w.occurring, w.key, w.dlg)
            back.append(saving)


def back_pop() -> int:
    """Pop from the back stack."""

    x_ = 0
    if back:
        saving = back.pop()
        x_ = saving[0]
        w.y = saving[1]
        w.hiLita.lineinc = saving[2]
        w.hiLita.keyinc = saving[3]
        w.hiLita.fmt = saving[4]
        w.hiLita.length = saving[5]
        w.no_f3_yet = saving[6]
        w.occurring = saving[7]
        w.key = saving[8]
        w.dlg = saving[9]

    return x_


def forward_push(x_) -> None:
    """Push onto the forward stack."""

    if len(forward) == 0:
        saving = (x_, w.y, w.hiLita.lineinc, w.hiLita.keyinc, w.hiLita.fmt,
                  w.hiLita.length, w.no_f3_yet, w.occurring, w.key, w.dlg)
        forward.append(saving)
    else:
        if forward[-1][0] == x_ and forward[-1][1] == w.y:
            pass
        else:
            saving = (x_, w.y, w.hiLita.lineinc, w.hiLita.keyinc,
                      w.hiLita.fmt, w.hiLita.length, w.no_f3_yet,
                      w.occurring, w.key, w.dlg)
            forward.append(saving)


def forward_pop() -> int:
    """Pop from the forward stack."""

    x_ = 0
    if len(forward) > 0:
        saving = forward.pop()
        x_ = saving[0]
        w.y = saving[1]
        w.hiLita.lineinc = saving[2]
        w.hiLita.keyinc = saving[3]
        w.hiLita.fmt = saving[4]
        w.hiLita.length = saving[5]
        w.no_f3_yet = saving[6]
        w.occurring = saving[7]
        w.key = saving[8]
        w.dlg = saving[9]

    return x_


def create_pattern(key):
    """Create a regex pattern based on the given key."""
    return rf"\b{key[:-2]}[s’][s’]" if key[-2:] == "s’" else rf"\b{key}\b"


def iterate_list(keywords: list[str], r_list: list) -> None:
    """Iterate over r_list and find all the occurrences of key(s) in keywords."""

    #  global w ----- Probably unnecessary!
    w.occurring = 0
    print(f'w.occurring = {w.occurring}')
    w.occur = []
    for i in w.occurs:
        coordinates = []
        for key in keywords:
            pattern = create_pattern(key)
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
    """Prepare statusbar message."""

    book = Info[index][0]
    chapter = Info[index][1] + 1
    occurrence = Info[index][2] + 1
    book_name = w.nwin[book]

    if w.occurrence == w.occurring:
        end_message = "."
        w.no_f3_yet = 0
    else:
        end_message = '...'

    ye = f'Occurrence {w.occurrence}/{w.occurring} of "{w.keym}"'

    if book in onechapterbooks:
        w.message = f'{ye}  -  {book_name} {occurrence} KJV{end_message}'
    else:
        w.message = f'{ye}  -  {book_name} {chapter}:{occurrence} KJV{end_message}'


def occurrent1() -> int:
    """Count occurrence(s) of w.key and give x_ and w.y values.

    w.occurs is a list of all the x_ values in the search results.
    w.occur is a corresponding list which gives the start w.y and finish w.yend of
    the searched for item in the particular verse.
    w.occurring is the total number of times the search key was found.
    w.verse is the number of the items in the search list.
    len(w.occur[w.verse]) is the number of search results in a particular verse.
    w.finding is the number of items found within the verse.
    """

    x_ = w.occurs[-1]  # Workaround for PyCharm linter.

    if w.verse < len(w.occurs):
        w.finding += 1
        x_ = w.occurs[w.verse]  # Aligns with w.occur(w.verse)
        if w.finding + 1 <= len(w.occur[w.verse]):
            w.y = w.occur[w.verse][w.finding][0]
            w.yend = w.occur[w.verse][w.finding][1]
            w.occurrence += 1
            prep_statusbar_message(x_)
        elif w.verse + 1 < len(w.occurs):
            w.verse += 1
            w.finding = 0
            w.y = w.occur[w.verse][w.finding][0]
            w.yend = w.occur[w.verse][w.finding][1]
            w.occurrence += 1
            x_ = w.occurs[w.verse]
            prep_statusbar_message(x_)
    elif w.verse >= len(w.occurs):
        x_ = w.occurs[-1]  # Last item

    # print(f'len(w.occurs = {len(w.occurs)})')
    # print(f'w.occurring = {w.occurring}')

    return x_


def punctuation_counter(text: str) -> int:
    """Count the number of punctuation characters in text."""

    p = "()[];:!<>,.-?"  # ’ not needed because in the search file.
    num: int = 0
    for _ in p:
        k = text.count(_)
        num += k

    return num


def repeat_find(rx: str, start: int, end: int) -> int:
    """Repeat find of lengthening text.

    rx is the verse from the PCE-find.txt file
    or a similar file without italics.
    """

    flag: bool = True
    numb: int
    sumb: int = 0
    repeats: int = 0
    while flag is True:
        text: str = rx[start:end + sumb]
        numb = punctuation_counter(text)
        sumb += numb
        start = end + sumb - numb
        repeats += 1
        if repeats > 15 or numb == 0:
            flag = False

    return sumb


def repeat_find_keyinc(rx: str, start: int, end: int) -> int:
    """Repeat find of lengthening text.

    rx is the verse from the PCE-find.txt file
    or a similar file without italics."""

    numb: int
    sumb = 0
    while True:
        text: str = rx[start:end]
        numb = punctuation_counter(text)
        sumb += numb
        if numb == 0:
            break
        start = end
        end += numb

    return sumb


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
    """Enable highlighting of first verses, while showing titles above."""

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


def readio(input_path: str, input_filename: str, file_length: int) -> list:
    """Read Bible files."""

    # print('readio ', input_filename)
    output_listname: list = []
    f_readio = open(f'{input_path}{input_filename}', 'r', encoding="utf-8")
    for _ in range(file_length):
        x5: str = f_readio.readline()
        i = f'{x5.splitlines()[0]}\n'
        output_listname.append(i)
    f_readio.close()

    return output_listname


def load_json_dict(file_dict: Any) -> Any:
    """Load a dictionary with JSON."""

    # print('load_json_dict ', file_dict)
    with open(file_dict, "r", encoding='utf-8') as read_file:
        file1 = load(read_file)

    return file1


def load_list_set_dict(input_filename: str, ref_dict: Any) -> dict[Any, set]:
    """Load a list_dict.txt/json file that is a dictionary of Bible words.

    As keys and values, lists of verse numbers of the Bible.

    The lists are converted to sets after reading, to return them to the
    format required for use. The ref_dict is used to get the relevant keys.

    The reason for this is that apparently JSON cannot deal with sets.

    The input_filename will be of the form 'list_[name].txt/json'.
    The receiving files name should be of the form 'set_[name]'.
    """

    # print('load_list_set_dict ', input_filename)
    setdict: dict[Any, set] = {}
    listdict: Any = load_json_dict(input_filename)
    sd: list = list(ref_dict)
    lsd: int = len(sd)
    for n in range(lsd):
        setdict[sd[n]] = set(listdict[sd[n]])

    return setdict


def is_float_re(string_: str) -> bool:
    """Take a string and determine if it represents a float.

    Many thanks to:
    https://stackoverflow.com/users/1399279/sethmmorton.
    """
    pattern = r"^[-+]?(?:\b[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][-+]?[0-9]+\b)?$"
    m = re.match(pattern, string_)  # Use re.match directly

    return m is not None  # More Pythonic than `return True if m else False`


def any_of_the_words_lookup(_key: str, _set: dict[str, set]) -> tuple[int, str]:
    """Takes _key and splits it into separate words in liszt,
    which are then looked up in the set of Bible words.
    Returns modified _key and count in num of occurrences of the words in it."""

    liszt: list[str] = _key.split(' ')

    # use a set to eliminate duplicates, keep words found in _set
    unique_words = set(word for word in liszt if word in _set)

    _key = ' '.join(unique_words)  # join the set into a string

    num = len(unique_words)  # count the number of unique words

    return num, _key


def centerer(widt: int, heigh: int) -> tuple:
    """Provide central screen origin points for windows"""

    w_origin = int(half_width - (widt / 2))
    h_origin = int(half_height - (heigh / 2))

    return w_origin, h_origin


def format_status_message(q1, q2, q3):
    """Helper to format a message based on conditions."""

    q4 = w.nwin[q1]
    if q1 in onechapterbooks:
        return f"{q4} {q3} KJV"
    return f"{q4} {q2}:{q3} KJV"


def sizer(window_height: int, window_width: int) -> tuple[int, int]:
    """Adjust window size to fit screen."""

    if window_height > height:
        window_height = int(height * 0.95)
    if window_width > width:
        window_width = int(width * 0.95)

    return window_height, window_width

def squeeze(char: str, s: str) -> str:
    """Remove duplicate characters. For example, '.....' is replaced with '.'."""

    while char * 2 in s:
        s = s.replace(char * 2, char)

    return s

def remove_junk(text: str) -> str:
    """Remove junk characters from text.  Junk characters are any non-alphabetic characters,
       numbers or any of the normal punctuation characters.
       Plus, the text must start and finish with a letter or a number."""

    # print(f"remove_junk: {text}")
    # Define allowed characters using a set for fast membership checks.
    allowed_set = set(ascii_letters + digits + "():,’;-?[].!<> ")
    # Filter out characters not in the allowed set.
    rex: str = "".join(ch for ch in text if ch in allowed_set)

    if text.lstrip('-').isdigit():
        return text  # Return the number as-is if it's valid
    else:
        #  Remove any junk from the beginning of a reference.
        try:
            m: int = re.search("[a-zA-Z0-9]+", rex).start()
            rex: str = rex[m:]
        except AttributeError:
            pass

        #  Remove any junk from the end of a reference.
        try:
            k: int = re.search("[a-zA-Z0-9]+", rex[::-1]).start()
            if k > 0:
                rex = rex[:-k]
        except AttributeError:
            pass

        #  Remove possible duplicate '.' or ':' chapter verse seperator.
        rex = squeeze('.', rex)
        rex = squeeze(':', rex)

        #  Remove possible KJV ending.
        if rex.endswith(' KJV'):
            rex = rex[:-4]

    return rex

def load_settings_from_file(filename="settings.json"):
    """
    Load the settings dictionary from a JSON file.
    If the file is missing, empty, malformed, or has partial settings, return defaults.
    """
    # Default settings
    default_settings = {
        "theme": "Light",
        "show_splash": False
    }

    # Check if the file exists
    if not path.exists(filename):
        print("Settings file does not exist. Using default settings.")
        return default_settings

    # Attempt to read the file
    try:
        with open(filename, "r") as file1:
            # Read and parse the JSON
            content = file1.read().strip()  # Handle an empty file gracefully
            if not content:  # File is empty
                print("Settings file is empty. Falling back to default settings.")
                return default_settings

            settings_here = loads(content)  # Try to parse JSON

            # Add missing keys with their default values
            for key, value in default_settings.items():
                settings_here.setdefault(key, value)

            # print("Loaded settings:", settings_here)
            return settings_here

    except JSONDecodeError:
        print("Settings file is malformed. Overwriting with default settings.")
        return default_settings
    except Exception as err:
        print(f"Error loading settings: {err}. Using default settings.")
        return default_settings

def save_settings_to_file(the_settings, filename="settings.json"):
    """
    Save the given settings dictionary to a JSON file.
    """
    try:
        # Explicitly annotate the file object
        with open(filename, "w") as file1:
            # noinspection PyTypeChecker
            dump(the_settings, file1, indent=4)  # Save as JSON with pretty formatting
    except IOError as e1:
        print(f"Error saving settings to file: {e1}")

def setup_Abib_settings(abib_directory: Path) -> None:
    """ Setup Abib user folder containing the 'settings.json' file."""

    # Create the Abib directory if it doesn't exist
    abib_directory.mkdir(parents=True, exist_ok=True)
    # print(f"Created Abib directory: {abib_directory}")

    # Path to the source settings.json file to copy (e.g. in your current working directory)
    source_settings_file = Path("settings.json")
    # print(f"source_settings_file: {source_settings_file}")

    # Copy the file to the target user directory ... But don't if it exists!
    if source_settings_file.is_file():
        print(f"Source settings.json found: {source_settings_file}")
        if path.exists(abib_directory):
            copy2(source_settings_file, abib_directory)
            print(f"Copied settings.json to {abib_directory}")
        else:
            print(f"Abib settings.json was found: {abib_directory} ... Skipping copy.")


def isRoman(s: str) -> bool:
    """Regular expression to match valid Roman numerals"""

    roman_pattern = r"^M{0,4}(CM|CD|D?C{0,3})(XC|XL|L?X{0,3})(IX|IV|V?I{0,3})$"
    s = s.upper()
    return bool(re.match(roman_pattern, s))


def commentary() -> None:
    """Commentary key."""

    # Create an instance of CalvinCommentary
    # calvincom = CalvinCommentary()

    # Access a specific commentary
    # book_name = "Genesis"
    # print(f"{book_name} Commentary:", calvincom.get_commentary(book_name))
    print('Future feature')

def feature() -> None:
    """For a future feature key."""

    print('Future feature')


def get_date_file(adjustment: int = 0) -> tuple:
    """Process date into desired format."""

    global date_index  # Needed because date_index is assigned to here.

    try:
        date_index += adjustment
    except NameError:
        date_index = adjustment
    # print(f"date_index: {date_index}")

    morn_or_even: str = ''

    # Get today's date
    today = datetime.now() + timedelta(hours=date_index)
    # print(f"Today's date: {today}")

    # Extract the full month name
    month = today.strftime("%B")  # E.g., "February"

    # Extract the day as an integer (which automatically avoids padding issues)
    day = today.day  # E.g., 3

    # Combine the month and day
    formatted_date = f"{month} {day}"
    # Determine if it's morning or evening
    if today.hour < 12:
        morn_or_even = "morning"
    elif today.hour >= 12:
        morn_or_even = "evening"

    date_file1: tuple = (formatted_date, morn_or_even,)

    return date_file1


def convert_roman_to_numeric(reference_text):
    """
    Converts all Roman numeral occurrences in the reference text to numeric values.
    Roman numerals are case-insensitive (e.g. IV == iv == 4).
    """
    # Regex to match Roman numerals (case-insensitive)
    pattern = re.compile(r'\b(IV|IX|XL|XC|L|C|D|M|I|V|X)+\b', re.IGNORECASE)

    def replacer(matched):
        # Extract the matched Roman numeral
        roman_numeral = matched.group(0)
        try:
            # Use `fromRoman` to convert Roman numeral to an integer
            return str(fromRoman(roman_numeral))
        except InvalidRomanNumeralError:
            # In case of invalid Roman numerals, return the original text
            return roman_numeral

    # Replace all valid Roman numerals in the reference text with their numeric equivalents
    return pattern.sub(replacer, reference_text)


def attach_book_name(reference_text: str, current_line: int) -> str:
    """Attach a book name to the floating-point reference."""

    z1 = Info[current_line][0] + 1
    book_name = next((key for key, value in bibledict.items() if value == z1), "")
    return f"{book_name} {reference_text}"


def split_reference(reference_text: str) -> list:
    """
    Split a Bible reference into components based on the book, chapter, and verse,
    ensuring contiguous letters and numbers (e.g. 'g2.6') are split correctly.
    """

    # First, split on delimiters (space, period, colon)
    intermediate_parts = re.split(r'[ .:]+', reference_text)
    # print(f"865 Split reference: {reference_text} into {intermediate_parts}")

    final_parts = []

    # Further split parts with mixed letters and numbers (e.g., 'g2' -> ['g', '2'])
    part_number: int = -1
    for part in intermediate_parts:
        part_number += 1
        # Use regex to separate letters and digits if mixed
        if part_number == 0 and part in bibledict:
            final_parts.append(part)
            # print(f"876 Part: {part} is a book name")
        else:
            match = re.findall(r'[a-zA-Z]+|\d+', part)
            final_parts.extend(match)

    if len(final_parts) > 1:
        try:
            if int(final_parts[0]):
                final_parts[1] = f"{final_parts[0]}{final_parts[1]}"
                del final_parts[0]
        except ValueError:
            pass

    if len(final_parts) == 4:
        final_parts = final_parts[:-1]

    return final_parts


def tidy(text: str, parts: list) ->  str:
    """Tidy up the reference parts."""

    abbr: list = ['d', 'c', 'l', 'm']
    full_names: list = ['deuteronomy', 'colossians', 'leviticus', 'micah']

    d: str = parts[0][0]
    # print(f"918 d: {d}")

    if d in abbr:
        # Get the corresponding full name
        try:
            a: str = full_names[abbr.index(d)]
            # print(f"920 '{d}' is an abbreviation for '{a}'.")
        except ValueError:
            # print(f"922 '{d}' is not in the list.")
            raise ValueError("ValueError")

        text = f"{a}{text[1:]}"
        # print(f"933 text: {text}")

    return text


def check_roman_chapter_adjacent(reference_text: str) -> str:
    """Check if the reference text can be split further into a book, chapter, and verse.
    Specifically, if the first part of the reference text is a book in bibledict adjacent
    to a chapter number in roman numerals, then the reference text is split further."""

    #  Note: 'mi' is 1001 in roman numerals and will be converted later if we don't act.

    div: int = 0
    divis: int
    reference_parts = split_reference(reference_text)
    # print(f"948 Reference parts: {reference_parts}")

    # len_parts: int = len(reference_parts)
    # print(f"951 len_parts: {len_parts}")

    try:
        # Do this part only if the book name is invalid.
        if reference_parts[0] not in bibledict and reference_parts[0][0] in bibledict:
            reference_text = tidy(reference_text, reference_parts)
            # print(f"956 After tidy: reference_text: {reference_text}")
    except IndexError:
        return '958 Error: No reference parts.'

    reference_parts = split_reference(reference_text)
    len_parts = len(reference_parts)
    # print(f"948 Reference parts: {reference_parts}")
    ref = reference_parts[0]
    len_ref: int = len(ref)
    # print(f"962 Reference text length: {len_ref} ref = {ref}")

    if (ref in bibledict or isRoman(ref)) and ref != 'mi':
        # print(f"965 ref: {ref} no need to split further.")
        return reference_text
    else:
        # print(f"969 Reference text: {ref} needs to be split.")
        pass

        # Find the start of the roman numeral.
        for i in range(len_ref, 0, -1):
            if isRoman(ref[i:]):
                div = i
            else:
                break

        divis = len_ref - div
        roman_number: str = ref[-divis:]
        # print(f"980 Roman number: {roman_number}")
        # print(f"981 divis = {divis}")
        # print(f"982 ref = {ref}")

        # Find the end of the bible book name.
        results = []
        for i in range(len_ref):
            if ref[:i] in bibledict:
                results.append(i)
        # print(f"989 Results: {results}")

        if results:
            rr1: str = ref[:results[-1]]
            # print(f"993 results[-1] = {results[-1]}")
            # print(f"994 Book name is: {rr1}")
            if divis + results[-1] == len_ref:
                if len_parts == 1:
                    reference_text = f"{rr1} {ref[-divis:]}"
                elif len_parts == 2:
                    reference_text = f"{rr1} {ref[-divis:]}.{reference_parts[1]}"
                # print(f"997 Reference text: {reference_text}")
                reference_parts = split_reference(reference_text)
                len_parts = len(reference_parts)
            elif divis + results[-1] > len_ref:
                lbn: int =len(rr1)  # Length of the book name.
                book = ref[:lbn]
                # print(f"1001 Book name: {book}")
                roman_number = ref[lbn:]
                reference_text = f"{book} {roman_number}" # roman number is the chapter.
            else:
                # print(f"1005 Reference text: {reference_text} is unchanged.")
                pass

            if bibledict[rr1] - 1 in onechapterbooks:
                pass
            else:
                # print(f"1011 Reference parts: {reference_parts}")
                match len_parts:
                    case 1:
                        reference_text = f"{rr1}"
                    case 2:
                        reference_text = f"{rr1}  {roman_number}"
                    case 3:
                        reference_text = f"{rr1} {roman_number}.{reference_parts[2]}"
                    case _:
                        reference_text = f"Error: {reference_text} is invalid."

                # print(f"1012 Reference text @ end adj: {reference_text}")

    return reference_text


def calculate_book_line(book: str, chapter: int, verse: int) -> int:
    """
    This function calculates and returns a specific line index from the global variable
    'Info' based on given book, chapter, and verse parameters. The book, chapter,
    and verse values are adjusted to zero-based indexing before computation. An error
    is raised if the values are invalid or out of range for the dataset referenced by
    'Info'.

    :param book: The book identifier provided as a string that is parsed into an integer.
    :param chapter: The chapter number. Must be a positive integer.
    :param verse: The verse number. Must be a positive integer.
    :return: The calculated line index corresponding to the book, chapter, and verse.
    :rtype: int
    :default: If the book, chapter, or verse is invalid or out of range for processing,
              the line index will be set to zero. i.e. to Genesis chapter 1, verse 1.
    """

    try:
        # Subtract 1 from book, chapter, and verse for zero-based Info index.
        book_id = int(book) - 1
        chapter = int(chapter) - 1
        verse = int(verse) - 1

        if book_id < 0 or chapter < 0 or verse < 0:
            message = f"Invalid chapter or verse range."
            w.on_error(message, 750, True)
            # print(message)
            # Return the default index from Info
            return Info.index([0, 0, 0])

        # Return the calculated index from Info
        return Info.index([book_id, chapter, verse])

    except (ValueError, IndexError):
        message = f"Invalid book, chapter, or verse."
        w.on_error(message, 750, True)
        # print(message)
        # Return the default index from Info
        return Info.index([0, 0, 0])

def clean_chapter_prefix(reference_text: str) -> str:
    """Clean 'Chap' prefixes from the reference text."""

    reference_text = reference_text.lower()
    reference_text = reference_text.replace(':', '.')
    if reference_text.startswith('chap'):
        ref = reference_text.replace('chap', '')
        return ref.strip('.')

    # Remove spaces from '2 Corinthians' etc..
    reference_text = reference_text[:3].replace(' ', '') + reference_text[3:]

    # Remove spaces enclosed by a-z
    reference_text = re.sub(r"(?<=[a-z]) (?=[a-z])", "", reference_text)

    # Remove all after a comma, e.g. zechariah.1.12,13
    reference_text = reference_text.split(",")[0]

    return reference_text

def resolve_reference(bits: list) -> tuple:
    """Resolve the book, chapter, and verse using isRoman."""

    # Debugging: Show the split bits
    # print(f"Resolving reference bits: {bits}")

    # Step 1: Resolve the book name
    book_number = bibledict.get(bits[0].lower(), None)
    # print(f"Book resolved to: {book_number}")
    if not book_number:
        return None, None, None

    # Step 2: Resolve chapter (bits[1])
    chapter = '1'
    if len(bits) > 1:
        if isRoman(bits[1]):  # If it's a Roman numeral
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
        if isRoman(bits[2]):  # If it's a Roman numeral
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


class AboutWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("")

        self.resize(480, 800)  # Set initial window size
        self.content = None
        self.about_window = None

        # Create a QLabel widget
        self.label = QtWidgets.QLabel(self)

        # Load About.txt content
        self.content = self.about()

        # Set the contents of the QLabel
        self.label.setText(self.content)

        # Center align content
        self.label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        self.fontsize = 14
        fixedfont: QFont = QtGui.QFont("Cascadia Mono", self.fontsize, QtGui.QFont.Weight.Bold)
        self.label.setFont(fixedfont)

        # Set the QLabel as the central widget
        self.setCentralWidget(self.label)

    def about(self) -> str:
        """Load the About content from ABOUT.txt."""

        self.content: str = ""
        try:
            with open("ABOUT.txt", "r", encoding="utf-8") as file_about:
                self.content = file_about.read()
        except FileNotFoundError:
            self.content = "ABOUT.txt file not found."
        except UnicodeDecodeError:
            self.content = "Error: Unable to decode ABOUT.txt. Please make sure the file encoding is UTF-8."

        winwidth: int = 480
        winheight: int = 800

        # Allow for small screen sizes
        winheight, winwidth = sizer(winheight, winwidth)

        w_origin, h_origin = centerer(winwidth, winheight)
        self.setGeometry(w_origin, h_origin, winwidth, winheight)
        # w.otherFileFlag = True

        return self.content


class MainWindow(QtWidgets.QMainWindow):
    """MainWindow class."""

    def __init__(self, *args, **kwargs) -> None:
        """Initialise."""
        super(MainWindow, self).__init__(*args, **kwargs)

        # Load saved settings or initialise default ones.
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
        self.textEditor: QPlainTextEdit = QtWidgets.QPlainTextEdit()
        # Store a reference to the secondary window to manage its lifecycle
        self.secondary_window = None

        #QtCore.QTimer.singleShot(0, lambda: self.sme("PM", -1))  # Adjusted to yesterday evening's reading.

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

        fixedfont: QFont = QtGui.QFont("Cascadia Mono", self.fontsize, QtGui.QFont.Weight.Medium)
        self.textEditor.setFont(fixedfont)
        self.textEditor.setReadOnly(True)

        self.display_verse_input: QLineEdit = QtWidgets.QLineEdit()
        self.display_verse_input.setToolTip("F2 Enter or OK to search for a verse.")
        # self.display_verse_input.returnPressed.connect(self.goto_line)
        self.display_verse_input.setGeometry(QtCore.QRect(50, 50, 200, 25))  # Reduce the width to 200

        self.comboBox_1: QComboBox = QtWidgets.QComboBox()
        self.comboBox_1.addItems(self.nwin)
        self.comboBox_1.setCurrentIndex(0)
        self.comboBox_1.activated.connect(self.goto_book)

        self.comboBox_2: QComboBox = QtWidgets.QComboBox()
        self.comboBox_2.addItems(self.nchapters)
        self.comboBox_2.setCurrentIndex(0)
        self.comboBox_2.activated.connect(self.goto_chapter)

        self.comboBox_3: QComboBox = QtWidgets.QComboBox()
        self.comboBox_3.addItems(self.nverses)
        self.comboBox_3.setCurrentIndex(0)
        self.comboBox_3.activated.connect(self.goto_verse)

        self.hiLita: SyntaxHighlighter = SyntaxHighlighter(self.textEditor.document())

        grid: QGridLayout = QtWidgets.QGridLayout()
        grid.setSpacing(2)
        self.setLayout(grid)

        grid.addWidget(self.textEditor, 0, 0, 1, 3)
        self.textEditor.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        grid.addWidget(self.comboBox_1, 1, 0)
        self.comboBox_1.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.comboBox_2, 1, 1)
        self.comboBox_2.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        grid.addWidget(self.comboBox_3, 1, 2)
        self.comboBox_3.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        grid.addWidget(self.display_verse_input, 2, 0)
        self.display_verse_input.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.okButton = QtWidgets.QPushButton("OK")
        self.okButton.setStyleSheet("QPushButton { text-align: left; }")
        self.okButton.setGeometry(QtCore.QRect(200, 200, 75, 30))  # Position the "OK" button

        grid.addWidget(self.okButton, 2, 1)
        self.okButton.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.okButton.setToolTip("Enter")
        self.display_verse_input.returnPressed.connect(self.submitAction)
        self.okButton.clicked.connect(self.submitAction)

        self.buttonQ = QtWidgets.QPushButton("Quit")
        self.buttonQ.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonQ.clicked.connect(exit)
        grid.addWidget(self.buttonQ, 2, 2)
        self.buttonQ.setToolTip("Close Abib")
        self.buttonQ.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        # Create a horizontal layout for Find and Find Next buttons
        find_buttons_layout = QtWidgets.QHBoxLayout()

        self.buttonf3 = QtWidgets.QPushButton("Find", self)
        self.buttonf3.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf3.clicked.connect(self.f3)
        self.buttonf3.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.buttonf3.setToolTip("F3")
        find_buttons_layout.addWidget(self.buttonf3)

        self.buttonf4 = QtWidgets.QPushButton("Find Next")
        self.buttonf4.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf4.clicked.connect(self.f4)
        self.buttonf4.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.buttonf4.setToolTip("F4")
        find_buttons_layout.addWidget(self.buttonf4)

        # Add the horizontal layout to the grid at row 3, column 0
        grid.addLayout(find_buttons_layout, 3, 0)

        self.buttonf5 = QtWidgets.QPushButton("Back")
        self.buttonf5.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf5.clicked.connect(self.f5)
        grid.addWidget(self.buttonf5, 3, 1)
        self.buttonf5.setToolTip("F5")
        self.buttonf5.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.buttonf6 = QtWidgets.QPushButton("Forward")
        self.buttonf6.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf6.clicked.connect(self.f6)
        grid.addWidget(self.buttonf6, 3, 2)
        self.buttonf6.setToolTip("F6")
        self.buttonf6.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        # Create a horizontal layout for Book- and Book+ buttons
        book_buttons_layout = QtWidgets.QHBoxLayout()

        self.buttonf7 = QtWidgets.QPushButton("Book-")
        self.buttonf7.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf7.clicked.connect(self.earlier_book)
        self.buttonf7.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.buttonf7.setToolTip("F7")
        book_buttons_layout.addWidget(self.buttonf7)

        self.buttonf8 = QtWidgets.QPushButton("Book+")
        self.buttonf8.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf8.clicked.connect(self.later_book)
        self.buttonf8.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.buttonf8.setToolTip("F8")
        book_buttons_layout.addWidget(self.buttonf8)

        # Add the horizontal layout to the grid at row 4, column 0
        grid.addLayout(book_buttons_layout, 4, 0)

        self.buttonf10 = QtWidgets.QPushButton("Chapter-")
        self.buttonf10.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf10.clicked.connect(self.earlier_chapter)
        grid.addWidget(self.buttonf10, 4, 1)
        self.buttonf10.setToolTip("F10")
        self.buttonf10.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.buttonf11 = QtWidgets.QPushButton("Chapter+")
        self.buttonf11.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf11.clicked.connect(self.later_chapter)
        grid.addWidget(self.buttonf11, 4, 2)
        self.buttonf11.setToolTip("F11")
        self.buttonf11.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        # Create a horizontal layout for Fullscreen and Devotional buttons
        full_buttons_layout = QtWidgets.QHBoxLayout()

        self.buttonf9 = QtWidgets.QPushButton("Fullscreen")
        self.buttonf9.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf9.clicked.connect(self.f9)
        full_buttons_layout.addWidget(self.buttonf9)
        self.buttonf9.setToolTip("F9")
        self.buttonf9.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.buttonf12 = QtWidgets.QPushButton("Devotional")
        self.buttonf12.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf12.clicked.connect(self.f12)
        full_buttons_layout.addWidget(self.buttonf12)
        self.buttonf12.setToolTip("F12")
        self.buttonf12.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        # Add the horizontal layout to the grid at row 5, column 0
        grid.addLayout(full_buttons_layout, 5, 0)

        self.buttonf13 = QtWidgets.QPushButton("")
        self.buttonf13.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf13.clicked.connect(commentary)
        grid.addWidget(self.buttonf13, 5, 1)
        self.buttonf13.setToolTip("Ctrl + Shift + C")
        self.buttonf13.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        self.buttonf14 = QtWidgets.QPushButton("")
        self.buttonf14.setStyleSheet("QPushButton { text-align: left; }")
        self.buttonf14.clicked.connect(feature)
        grid.addWidget(self.buttonf14, 5, 2)
        self.buttonf14.setToolTip("Ctrl + Shift + ?")
        self.buttonf14.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

        container: QWidget = QtWidgets.QWidget()
        container.setLayout(grid)
        self.setCentralWidget(container)
        self.display_verse_input.setFocus()

        self.statusBar = QtWidgets.QStatusBar()
        self.setStatusBar(self.statusBar)

        file_toolbar = QtWidgets.QToolBar("File")
        file_toolbar.setIconSize(QtCore.QSize(14, 14))
        self.addToolBar(file_toolbar)
        file_menu = self.menuBar().addMenu("&File")

        # Create a Path object for the file path.
        icon1_path = Path('images') / 'blue-folder-open-document.png'
        # Use str() to convert Path object to string for QtGui.QIcon.
        open_file_action = QtGui.QAction(QtGui.QIcon(str(icon1_path)), "Open file...", self)
        open_file_action.setStatusTip("Open file")
        open_file_action.triggered.connect(self.file_open)
        file_menu.addAction(open_file_action)
        file_toolbar.addAction(open_file_action)

        icon2_path = Path('images') / 'printer.png'
        print_action = QtGui.QAction(QtGui.QIcon(str(icon2_path)), "Print...", self)
        print_action.setStatusTip("Print current page")
        print_action.triggered.connect(self.file_print)
        file_menu.addAction(print_action)
        file_toolbar.addAction(print_action)

        icon3_path = Path('images') / 'exit.png'
        exit_action = QtGui.QAction(QtGui.QIcon(str(icon3_path)), "Exit", self)
        exit_action.setStatusTip("Exit the program")
        exit_action.triggered.connect(exit)
        file_menu.addAction(exit_action)

        edit_toolbar = QtWidgets.QToolBar("Edit")
        edit_toolbar.setIconSize(QtCore.QSize(14, 14))
        self.addToolBar(edit_toolbar)
        edit_menu = self.menuBar().addMenu("&Edit")

        icon4_path = Path('images') / 'document-copy.png'
        copy_action = QtGui.QAction(QtGui.QIcon(str(icon4_path)), "Copy", self)
        copy_action.setStatusTip("Copy selected text")
        copy_action.triggered.connect(self.textEditor.copy)
        edit_toolbar.addAction(copy_action)
        edit_menu.addAction(copy_action)

        icon5_path = Path('images') / 'selection-input.png'
        select_action = QtGui.QAction(QtGui.QIcon(str(icon5_path)), "Select all", self)
        select_action.setStatusTip("Select all text")
        select_action.triggered.connect(self.textEditor.selectAll)
        edit_menu.addAction(select_action)

        help_menu = self.menuBar().addMenu("&Help")
        icon6_path = Path('images') / 'license.png'
        copyright_action = QtGui.QAction(QtGui.QIcon(str(icon6_path)), "LICENSE", self)
        copyright_action.setStatusTip("License")
        copyright_action.triggered.connect(self.copyright)
        help_menu.addAction(copyright_action)

        help_menu.addSeparator()
        icon7_path = Path('images') / 'question.png'
        help_action = QtGui.QAction(QtGui.QIcon(str(icon7_path)), "Abib Help", self)
        help_action.setStatusTip("Help file")
        help_action.triggered.connect(self.helper)
        help_menu.addAction(help_action)

        help_menu.addSeparator()
        icon8_path = Path('images') / 'details.png'
        readme_action = QtGui.QAction(QtGui.QIcon(str(icon8_path)), "Readme", self)
        readme_action.setStatusTip("Readme file")
        readme_action.triggered.connect(self.readme)
        help_menu.addAction(readme_action)

        help_menu.addSeparator()
        icon9_path = Path('images') / 'about.png'
        about_action = QtGui.QAction(QtGui.QIcon(str(icon9_path)), "About", self)
        about_action.setStatusTip("About Abib")
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)

        help_menu.addSeparator()
        icon10_path = Path('images') / 'settings.png'
        settings_action = QtGui.QAction(QtGui.QIcon(str(icon10_path)), "Settings", self)
        settings_action.setStatusTip("Settings")
        settings_action.triggered.connect(self.open_settings_dialog)
        help_menu.addAction(settings_action)

        self.secondary_window = SecondaryWindow("Text to display", self.geometry())
        self.secondary_window.text_display = QtWidgets.QPlainTextEdit()

        # Apply theme from settings during initialisation.
        self.set_theme(self.settings)

        self.update_title()
        self.show()

        # Placeholder for the AboutWindow (lazy-loaded)
        self.about_window = None

    def show_about_dialog(self):
        """Show the About window when Help -> About is clicked."""

        # Initialize AboutWindow if it hasn't been created
        if self.about_window is None:
            self.about_window = AboutWindow()

        self.about_window.show()
        self.about_window.raise_()  # Bring the "About" window to the front
        self.about_window.activateWindow()  # Give the "About" window focus

    def submitAction(self):
        """Action to perform when OK button or Enter key is pressed."""
        # user_input = self.display_verse_input.text()  # Get text from lineEdit
        # print(f"You typed: {user_input}")
        self.goto_line()

    def helper(self) -> None:
        """Help section."""

        self.file_open(str(Path(current_directory / 'HELP.txt')))
        winwidth: int = 830
        winheight: int = 1343

        # Allow for small screen sizes
        winheight, winwidth = sizer(winheight, winwidth)

        w_origin, h_origin = centerer(winwidth, winheight)
        self.setGeometry(w_origin, h_origin, winwidth, winheight)
        w.otherFileFlag = True

    def copyright(self) -> None:
        """Licence."""

        self.file_open(str(Path(current_directory / 'LICENSE')))
        winwidth: int = 940
        winheight: int = 1343

        # Allow for small screen sizes
        winheight, winwidth = sizer(winheight, winwidth)

        w_origin, h_origin = centerer(winwidth, winheight)
        self.setGeometry(w_origin, h_origin, winwidth, winheight)
        w.otherFileFlag = True

    def readme(self) -> None:
        """Readme file."""

        self.file_open(str(Path(current_directory / 'README.txt')))
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
            self.file_open(str(Path(current_directory / 'KJB_PCE.txt')))
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
        """Close Find window."""

        self.dlg.hide()

    def toggle_fullscreen(self) -> None:
        """Fullscreen."""

        if self.windowState() & QtCore.Qt.WindowState.WindowFullScreen:
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

        numstart, _key = split_strip(_key)
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
        """Adjust key for searching in Rnew, which has no Unicode italics.

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
        x_ = self.get_line_number()
        savedx = x_
        error_flag = False

        self.prepare_key_for_find()
        x1 = book_bounds[x_start]
        x2 = book_bounds[x_end + 1] - 1
        x_ = x1

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
                    x_ = occurrent1()
                    self.statusBar.showMessage(w.message)
                    self.statusBar.repaint()
            else:
                tv = self.dlg.checks[0] == 1   # Raw
                if tv is not True:
                    x_ = self.findf3_ww(x1, x2)
                elif tv is True:
                    # Raw.
                    x_ = self.findf3_raw(x_, x1, x2, keylow)

        if w.occurring == 0:
            x_ = savedx
            self.on_error('Not found...', 2000, True)
            error_flag = True

        if w.key in ('q', 'Q'):
            self.display_verse_input.clear()
            exit()
        if error_flag is not True:
            self.goto_line_find(x_)

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

    def findf3_raw(self, x_: int, x1: int, x2: int, keylow: str) -> int:
        """Find Raw."""

        if self.dlg.checks[1] == 1:  # Match case
            w.occurring += sum(Rnew[_].count(w.key) for _ in range(x1, x2))
        elif self.dlg.checks[1] == 0:  # Lower case
            w.occurring += sum(Rlow[_].count(keylow) for _ in range(x1, x2))

        if w.occurring != 0:
            w.occurrence = 0
            x_ = self.occurrent(x1, x2)
            self.statusBar.showMessage(w.message)
            self.statusBar.repaint()

        return x_

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
        x_: int = 0  # Pointer to the first verse with the searched for key.
        if numwords == 1:
            self.findf3_ww_1(x1, x2, set_, r_list)   # Match the whole single word.
            if w.occurring != 0:
                w.occurrence = 0
                w.verse = 0
                w.finding = -1
                x_ = occurrent1()
                self.statusBar.showMessage(w.message)
                self.statusBar.repaint()
        elif numwords > 1:
            if self.dlg.checks[0] == 2:
                findf3_ww_ac(x1, x2, numwords, set_, r_list)
            elif self.dlg.checks[0] == 3:
                findf3_ww_all(x1, x2, numwords, set_, r_list)
            elif self.dlg.checks[0] == 4:
                numwords, w.key = any_of_the_words_lookup(w.key, set_)
                findf3_ww_any(x1, x2, numwords, set_, r_list)
            if w.occurring != 0:
                if self.dlg.checks[0] != 2:     # Not whole words
                    x_ = w.occurs[0]
                    w.occurrence = 1
                    prep_statusbar_message(x_)
                elif self.dlg.checks[0] == 2:   # Whole words
                    w.occurrence = 0
                    w.verse = 0
                    w.finding = -1
                    x_ = occurrent1()
                self.statusBar.showMessage(w.message)
                self.statusBar.repaint()
        else:
            w.occurring = 0

        return x_

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
        """Count occurrences of item searched for."""

        if w.occurrence == 0:
            self.gent = self.gen(w.key, x1, x2)
        x_, w.y, w.occurrence = next(self.gent)
        prep_statusbar_message(x_)

        return x_

    def find_f4(self) -> None:
        """Repeat find frontend for raw search."""

        if w.occurrence < w.occurring:
            x_ = self.get_line_number()

            if forward:
                back_push(x_)
                while forward:
                    b_ = forward.pop()
                    back.append(b_)
            else:
                forward.clear()
                back_push(x_)

            # Ensure self.gent is a valid generator
            if self.gent is None:
                raise ValueError(
                    "self.gent has not been initialized. It must be assigned a valid generator before calling find_f4.")

            try:
                x_, w.y, w.occurrence = next(self.gent)
            except StopIteration:
                # Handle generator exhaustion if needed
                self.statusBar.showMessage("Search completed: no more matches.")
                return

            # Set status bar message and other UI updates.
            prep_statusbar_message(x_)
            self.statusBar.showMessage(w.message)
            self.statusBar.repaint()
            self.goto_line_find(x_)

    def find_f4_alt(self) -> None:
        """Repeat find frontend for Match whole words."""

        if len(w.occurs) > 0 and w.occurrence < w.occurring:
            x_ = self.get_line_number()
            if forward:
                back_push(x_)
                while forward:
                    b_ = forward.pop()
                    back.append(b_)
            else:
                x_ = w.occurs[w.verse]
                forward.clear()
                back_push(x_)

            if self.dlg.checks[0] == 2 or self.dlg.checks[2] == 6:
                x_ = occurrent1()
            elif self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4:
                if w.verse < len(w.occurs) - 1:
                    w.verse += 1
                    x_ = w.occurs[w.verse]
                    w.occurrence += 1
                    prep_statusbar_message(x_)

            self.statusBar.showMessage(w.message)
            self.statusBar.repaint()
            self.goto_line_find(x_)

    def gen(self, key: str, x1: int, x2: int):
        """Return next position of the searched for key."""

        x_ = -1
        d1 = 0
        if self.dlg.checks[1] == 1:
            files_path = Path(current_directory) / "PCE-find.txt"
        else:
            assert self.dlg.checks[1] == 0
            files_path = Path(current_directory) / "PCE-lower.txt"
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
            x_ += 1
            yt = 0
            if x_ > x2:
                break
            a = next(line)
            if x_ < x1:
                continue
            while key in a:
                d1 += 1
                w.y = int(a.find(key))
                if w.y != -1:
                    yt = yt + w.y + 1        #  Expected int got '() -> int' instead
                    a = a[w.y + 1:]
                    w.y = yt - 1
                    yield x_, w.y, d1

    def goto_line_find(self, x_: int) -> None:
        """Find function - prepare for output."""

        ln: int = Amap[x_]
        self.adjust_highlighting(ln, x_)
        self.move_to_line(ln)

    def stripped_punctuation_adjust(self, ln: int, x_: int, start: int, end: int, truth: bool) -> int:
        """Addition for 'Match whole words only'.

        This adjustment allows for no punctuation in the stripped search text.
        """

        add: int
        if '¶ ' in KJV[ln] and truth is True:
            w.y += 2
            end = w.y
        if self.dlg.checks[1] == 0:
            add = repeat_find(Ldic[x_], start, end)
        else:
            add = repeat_find(Rdic[x_], start, end)
        return add

    def stripped_punctuation_adjust_ki(self, x_: int, start: int, end: int) -> int:
        """Addition for 'Match whole words only'.

        This adjustment allows for no punctuation in the stripped search text.
        """

        add: int
        if self.dlg.checks[1] == 0:
            add = repeat_find_keyinc(Ldic[x_], start, end)
        else:
            add = repeat_find_keyinc(Rdic[x_], start, end)

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

    def keyinc_section(self, endof: int, add: int, ln: int, x_: int) -> None:
        """keyinc section."""

        unich = 32
        num = 0
        ignore = [8217]
        litz = []
        assert isinstance(w.y, int)
        start = w.y + add
        if self.dlg.checks[0] != 1:  # Not Raw
            end = start + len(w.key)  # change w.yend
            num = self.stripped_punctuation_adjust_ki(x_, start, end)
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

    def display_verse(self, x_: int) -> None:
        """Display Bible text in textEditor."""

        # print('display_verse')
        ln: int = Amap[x_]
        if x_ in starts_with_italics:  # Verses that start with italics.
            w.hiLita.keyinc = 1
        else:
            w.hiLita.keyinc = 0
        self.move_to_line(ln)
        self.display_verse_input.clear()
        if w.message == '':
            self.ref_to_statusbar(x_)

    def move_to_line(self, ln: int) -> None:
        """Display engine."""

        # print('move_to_line')
        self.textEditor.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        self.on_text_changed(ln)
        ln = make_offset(ln)
        linecursor = QtGui.QTextCursor(
            self.textEditor.document().findBlockByLineNumber(ln))
        self.textEditor.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.textEditor.setTextCursor(linecursor)
        self.textEditor.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth)
        if self.dlg is not None:
            if self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4:
                w.key = w.store

    def on_text_changed(self, ln: int) -> None:
        """Highlighting."""

        # print('on_text_changed')
        fmt = QtGui.QTextCharFormat()
        fmt.setBackground(QtGui.QColor(linehighlightcolor))
        fmt.setForeground(QtGui.QColor(linetextcolor))

        w.hiLita.clear = True
        w.hiLita.clear_highlight()

        try:
            if self.dlg is not None:
                if self.dlg.checks[0] == 3 or self.dlg.checks[0] == 4:
                    w.store = w.key
                    w.hiLita.clear = False
                    keys = sorted(w.occur[w.verse])
                    x_ = Amap.index(ln)
                    for i in keys:
                        w.key = '+' * (i[1] - i[0])
                        w.y = i[0]
                        self.adjust_highlighting(ln, x_)

            w.hiLita.setFormat(w.hiLita.position, w.hiLita.length, fmt)
            w.hiLita.highlight_line(ln, fmt)
        except ValueError:
            pass

    def se_display_verse(self, x_: int) -> None:
        """Display Bible text in textEditor after back or forward pop."""

        ln: int = Amap[x_]
        if x_ in starts_with_italics:  # Verses that start with italics.
            w.hiLita.keyinc = 1

        self.textEditor.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.NoWrap)
        fmt = QtGui.QTextCharFormat()
        fmt.setBackground(QtGui.QColor(linehighlightcolor))
        fmt.setForeground(QtGui.QColor(linetextcolor))
        w.hiLita.clear = True
        w.hiLita.clear_highlight()
        w.hiLita.setFormat(w.hiLita.position, w.hiLita.length, fmt)
        w.hiLita.highlight_line(ln, fmt)
        ln = make_offset(ln)
        linecursor = QtGui.QTextCursor(
            self.textEditor.document().findBlockByLineNumber(ln))
        self.textEditor.moveCursor(QtGui.QTextCursor.MoveOperation.End)
        self.textEditor.setTextCursor(linecursor)
        self.textEditor.setLineWrapMode(QtWidgets.QPlainTextEdit.LineWrapMode.WidgetWidth)
        self.ref_to_statusbar(x_)

    def ref_to_statusbar(self, x_: int) -> None:
        """Display messages in the status bar."""

        q1, q2, q3 = Info[x_][0], Info[x_][1] + 1, Info[x_][2] + 1
        message = w.message if w.message else format_status_message(q1, q2, q3)

        self.statusBar.showMessage(message)
        self.statusBar.repaint()

    # ENTRY POINT FOR F2 DISPLAY VERSE.
    def goto_line(self, ref: str ='') -> None:
        """Move display to line requested."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        x_: int = self.get_line_number()
        forward.clear()
        back_push(x_)
        if not ref:
            ref = self.display_verse_input.text()
        ref = remove_junk(ref)
        if ref in ('q', 'Q'):
            self.display_verse_input.clear()
            exit()
        # print(f"ref in goto_line: {ref}")
        x_ = self.reference_to_line_number(ref)
        if x_ == -1:
            self.display_verse_input.clear()
        else:
            if x_ < 0:
                x_ = 0
            if x_ > LAST_VERSE_IN_BIBLE:
                x_ = LAST_VERSE_IN_BIBLE
            self.display_verse(x_)

    def goto_book(self, _index: int) -> None:
        """Move display to line requested by comboBox_1."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        x_ = self.get_line_number()
        forward.clear()
        back_push(x_)
        book: int = self.comboBox_1.currentIndex()
        # book is an index 0-65
        if book == BOOKS_IN_THE_BIBLE - 1:
            b = 22  # Number of chapters in Revelation
        else:
            a: int = Info.index([book + 1, 0, 0])
            b: int = Info[a - 1][1] + 1  # No. of chapters in the book.
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
        x_ = self.reference_to_line_number(ref, book)
        if x_ < 0:
            x_ = 0
        if x_ > LAST_VERSE_IN_BIBLE:
            x_ = LAST_VERSE_IN_BIBLE
        self.display_verse(x_)
        self.goto_chapter(_index)

    def goto_chapter(self, _index: int) -> None:
        """Move display to line requested by comboBox_2."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        book: int = self.comboBox_1.currentIndex()
        chapter: int = self.comboBox_2.currentIndex()
        if chapter == int(w.nchapters[-1]) - 1:
            # No. of verses in the chapter.
            if book == BOOKS_IN_THE_BIBLE - 1:
                d = 21
            else:
                c: int = Info.index([book + 1, 0, 0]) - 1
                d: int = Info[c][2] + 1
        else:
            try:
                c = Info.index([book, chapter + 1, 0]) - 1
            except ValueError:
                c = Info.index([book + 1, 0, 0]) - 1
            d = Info[c][2] + 1
        w.nverses = []
        for _ in range(1, d + 1):
            w.nverses.append(str(_))
        self.comboBox_3.clear()
        self.comboBox_3.addItems(self.nverses)

        ref = w.nwin[book]
        ref = ref.replace(' ', '')
        ref = f"{ref} {str(chapter + 1)}"

        # print(f"ref in goto_chapter: {ref}")
        x_ = self.reference_to_line_number(ref, book, chapter)
        if x_ < 0:
            x_ = 0
        if x_ > LAST_VERSE_IN_BIBLE:
            x_ = LAST_VERSE_IN_BIBLE
        self.display_verse(x_)

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
        x_ = self.reference_to_line_number(ref, book, chapter)
        if x_ < 0:
            x_ = 0
        if x_ > LAST_VERSE_IN_BIBLE:
            x_ = LAST_VERSE_IN_BIBLE
        # print(f"x_ in goto_verse: {x_}")
        self.display_verse(x_)

    def reference_to_line_number(self, reference_text: str, book: int = 0, chapter: int = 0) -> int:
        """Convert reference text to a line number in the Bible."""

        # print(f"2367 Original reference_text: {reference_text}")

        # Clean up prefixes like 'Chap' to prevent incorrect matching
        # Also, remove spaces and convert ':' to '.'
        reference_text = clean_chapter_prefix(reference_text)  # For example, 'Chap2:3' -> '2:3'
        # print(f"2372 After cleaning chapter prefix: {reference_text}")

        # Check for book names that are adjacent to roman chapter references.
        reference_text = check_roman_chapter_adjacent(reference_text)  # For example, 'GenesisX.IV' -> 'Genesis.X.IV'
        # print(f"2376 After checking for adjacent book names: {reference_text}")

        # Letters like iv, ix, xl, xc, i, v, x, l, c, d, m,
        # which could be roman numerals need to be distinguished from book names here.
        # If they are alone, they are probably meant as book abbreviations:
        # e.g. i -> Isaiah, l -> Leviticus, c -> Colossians, d -> Deuteronomy and m -> Micah.
        roman_book: list = ['i', 'l', 'c', 'd', 'm']
        # So,
        if reference_text.lower() in roman_book:
            pass  # Here if a single letter that must not be converted to numeric.
        else:
            # Convert Roman numerals to numeric values
            reference_text = convert_roman_to_numeric(reference_text)
            reference_text = reference_text.replace(' ', '')
        # print(f"2389 After converting Roman numerals: {reference_text}")

        # Check if the input is in a valid format:
        #   1. "book.chapter.verse" (e.g., genesis.1.2)
        #   2. "chapter.verse" (e.g., 3.4)
        #   3. A single integer (e.g., 7)
        reference_text = reference_text.replace(' ', '.')
        # print(f"2396 Reference Text: '{reference_text}'")

        if (re.match(r"^[1-4]?[a-zA-Z]+\.\d+\.\d+(,\d+)*$", reference_text)) or is_float_re(reference_text):

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

            # Use the current context if book or chapter is missing
            book = input_book.strip() if input_book else book  # Default to the current book
            chapter = int(input_chapter) if input_chapter else str(int(chapter + 1))  # Default to current chapter
            verse = int(input_verse) if input_verse else '1'  # Verse stays as-is or '1'

            # Normalize the reference to the standard "book.chapter.verse" format
            if book not in onechapterbooks:
                reference_text = f"{book}.{chapter}.{verse}"

            try:
                if bibledict[book] - 1 in onechapterbooks:
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

        # Handle numeric-only references (e.g., "34")
        if self.is_integer(reference_text):
            verse = int(reference_text) - 1
            # print(f"2456 verse: {verse}")
            position = self.calculate_position(current_line, verse)
            # print(f"2458 position: {position}")
            return position  # If it is outside the current chapter, it stays in the same place.

        # Handle floating point-style references (e.g., "23.7")
        reference_text = reference_text.replace(":", ".")
        if is_float_re(reference_text):
            reference_text = attach_book_name(reference_text, current_line)

        # Split the reference into parts for resolving
        bits = split_reference(reference_text)
        # print(f"2469 Split reference: {bits}")

        book_num, chapter, verse = resolve_reference(bits)

        if not book_num:
            self.error_invalid_book()

        if book_num is None or chapter is None or verse is None:
            return -1

        try:
            position = calculate_book_line(book_num, chapter, verse)
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

        inf: list = Info[current_line]
        current_chapter: int = inf[1]
        # print(f"2474 current_chapter: {current_chapter}")
        current_verse = inf[2]
        # print(f"2475 current_verse: {current_verse}")

        if new_verse > 0:
            new_line: int = current_line - current_verse + new_verse
        else:
            new_line = current_line + new_verse + 1

        # print(f"2477 new_line: {new_line}")

        try:
            new_chapter: int = Info[new_line][1]
        except IndexError:
            return_value = current_line
            message = f"The verse is out of bounds. No {new_verse + 1} here!"
            w.on_error(message, 750, True)
        else:
            if new_chapter == current_chapter:
                return_value = new_line
            else:
                return_value = current_line

        # print(f"2476 return_value: {return_value}")

        return return_value

    @staticmethod
    def is_integer(value: Any) -> bool:
        """True if value is an integer."""

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

        self.textEditor.moveCursor(QtGui.QTextCursor.MoveOperation.StartOfLine)
        linenumber: int = self.textEditor.textCursor().blockNumber()
        if linenumber in Amap:
            x_: int = Amap.index(linenumber)
        else:
            if linenumber < Amap[0]:
                x_ = 0
            elif linenumber > KJB_PCE_LASTLINE - 118:
                x_ = LAST_VERSE_IN_BIBLE
            else:
                for _ in range(10):
                    if linenumber + _ in Amap:
                        linenumber += _
                        break
                else:
                    return LAST_VERSE_IN_BIBLE
                x_ = Amap.index(linenumber)

        return x_

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        """Mouse trapping routine."""

        if event.buttons() == QtCore.Qt.MouseButton.LeftButton:
            x_: int = self.get_line_number()
            self.ref_to_statusbar(x_)
        elif event.buttons() == QtCore.Qt.MouseButton.RightButton:
            pass
        elif event.buttons() == QtCore.Qt.MouseButton.MiddleButton and w.no_f3_yet == 1:
            self.f4()
        elif event.buttons() == QtCore.Qt.MouseButton.MiddleButton and w.no_f3_yet == 0:
            x_ = self.get_line_number()
            self.ref_to_statusbar(x_)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        """Key trapping routine."""

        qtcore_keys_dict = {
            QtCore.Qt.Key.Key_F2: self.f2,
            QtCore.Qt.Key.Key_F3: self.f3,
            QtCore.Qt.Key.Key_F4: self.f4,
            QtCore.Qt.Key.Key_F5: self.f5,
            QtCore.Qt.Key.Key_F6: self.f6,
            QtCore.Qt.Key.Key_F7: self.earlier_book,
            QtCore.Qt.Key.Key_F8: self.later_book,
            QtCore.Qt.Key.Key_F9: self.f9,
            QtCore.Qt.Key.Key_F10: self.earlier_chapter,
            QtCore.Qt.Key.Key_F11: self.later_chapter,
            QtCore.Qt.Key.Key_C: self.C,
            QtCore.Qt.Key.Key_Question: self.question,
            QtCore.Qt.Key.Key_F12: self.f12,
            QtCore.Qt.Key.Key_Q: exit}

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
        x_: int = self.get_line_number()
        forward.clear()
        back_push(x_)
        self.onFindBtnClicked()

    def f4(self) -> None:
        """Find next key F4."""

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
            x_: int = self.get_line_number()
            forward_push(x_)
            x_ = back_pop()
            self.se_display_verse(x_)

    def f6(self) -> None:
        """Forward key."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        if len(forward) > 0:
            x_: int = self.get_line_number()
            back_push(x_)
            x_ = forward_pop()
            self.se_display_verse(x_)

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

    @staticmethod
    def question() -> None:
        """Feature key."""
        feature()

    def earlier_book(self) -> None:
        """Move to the earlier book."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        x_: int = self.get_line_number()
        book: int = Info[x_][0]
        newbook: int = book - 1
        if newbook < 0:
            self.on_error('No earlier book!', 3000, True)
        else:
            x_ = Info.index([newbook, 0, 0])
            forward.clear()
            back_push(x_)
            self.display_verse(x_)

    def later_book(self) -> None:
        """Move to the later book."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        x_: int = self.get_line_number()
        book: int = Info[x_][0]
        newbook: int = book + 1
        if newbook > BOOKS_IN_THE_BIBLE - 1:
            self.on_error('No later book!', 3000, True)
        else:
            x_ = Info.index([newbook, 0, 0])
            forward.clear()
            back_push(x_)
            self.display_verse(x_)

    def earlier_chapter(self) -> None:
        """Move to the earlier chapter."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        x_: int = self.get_line_number()
        book: int = Info[x_][0]
        chapter: int = Info[x_][1]
        newchapter: int = chapter - 1
        if newchapter < 0:
            newbook: int = book - 1
            if newbook < 0:
                self.on_error('No earlier chapter!', 3000, True)
                return
            while True:
                if Info[x_][0] == book:
                    x_ -= 1
                else:
                    break
            newchapter = Info[x_][1]
            book = newbook
        x_ = Info.index([book, newchapter, 0])
        forward.clear()
        back_push(x_)
        self.display_verse(x_)

    def later_chapter(self) -> None:
        """Move to the later chapter."""

        self.reload()  # Reload KJB_PCE.txt if another file loaded.
        reset_attributes()
        x_: int = self.get_line_number()
        book: int = Info[x_][0]
        chapter: int = Info[x_][1]
        newchapter: int = chapter + 1
        try:
            x_ = Info.index([book, newchapter, 0])
        except ValueError:
            newbook: int = book + 1
            if newbook > BOOKS_IN_THE_BIBLE - 1:
                self.on_error('No later chapter!', 3000, True)
                return
            while True:
                if Info[x_][0] == book:
                    x_ += 1
                else:
                    break
            newchapter = Info[x_][1]
            book = newbook
        x_ = Info.index([book, newchapter, 0])
        forward.clear()
        back_push(x_)
        self.display_verse(x_)

    def on_error(self, message: str, millisecond_delay: int, clearbool: bool) -> None:
        """Error message handler."""

        x_: int = self.get_line_number()
        self.statusBar.showMessage(message)
        self.statusBar.repaint()

        lm: float = millisecond_delay / 1000 + len(message) / 25
        self.beep(x_, lm)

        if clearbool:
            self.statusBar.clearMessage()
            w.message = ''

    def beep(self, x_: int, lm: float) -> None:
        """Makes a beep sound, and clears the message."""

        # Initialize Pygame's mixer
        mixer.init()

        # Load your sound effect file (e.g., 'sound.wav')
        beep_sound = mixer.Sound('sound.mp3')
        beep_sound.set_volume(0.5)  # Set volume to 50%

        # Play the sound effect
        beep_sound.play()

        self.statusBar.repaint()

        # Delay for 'lm' second.
        time.sleep(lm)

        w.message = ''
        self.ref_to_statusbar(x_)
        self.statusBar.repaint()

    def dialog_critical(self, exception_text: str) -> None:
        """Error message dialog."""

        dlg: QMessageBox = QtWidgets.QMessageBox(self)
        dlg.setText(exception_text)
        dlg.setIcon(QtWidgets.QMessageBox.Icon.Critical)
        dlg.show()

    def file_open(self, path1: str) -> None:
        """File opening routine."""

        # print('file_open ', path1)
        if path1:
            pass
        else:
            path1, _ = QtWidgets.QFileDialog.getOpenFileName(
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

        dlg: QPrintDialog = QtPrintSupport.QPrintDialog()
        if dlg.exec_():
            self.textEditor.print_(dlg.printer())

    def update_title(self) -> None:
        """Title update routine."""

        self.setWindowTitle(f"{Path(self.path1).stem if self.path1 else ''}  -  Abib Bible v410.1")

    def open_settings_dialog(self):
        """
        Open the settings dialog and update settings if the user confirms.
        """
        dialog = SettingsDialog(self)

        # Populate the settings dialog with current settings
        dialog.splash_checkbox.setChecked(self.settings.get("show_splash", False))
        dialog.theme_combobox.setCurrentText(self.settings.get("theme", "Light"))

        if dialog.exec():  # If the dialog is accepted (OK button).
            # Get settings from the dialog and explicitly set show_splash
            self.settings["theme"] = dialog.theme_combobox.currentText()  # Ensure the theme is updated
            self.settings["show_splash"] = dialog.splash_checkbox.isChecked()  # Ensure splash checkbox updates settings

            # DEBUG: Print settings before saving
            # print("Settings before saving:", self.settings)

            # Save settings to the file
            save_settings_to_file(self.settings, user_settings_path)

            # Apply theme (if needed)
            self.set_theme(self.settings)

    def set_theme(self, the_settings):
        """Set theme based on the value retrieved from settings."""
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
        save_settings_to_file(self.settings, user_settings_path)

    def display_secondary_window(self, offset: int = 0) -> None:
        """
        Creates and displays the secondary window to show SME text.
        Ensures the secondary window is non-blocking.
        """
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

        date_file = get_date_file(adjustment)
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

        # Ensure secondary window and its text display exist
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


class SecondaryWindow(QDialog):

    def __init__(self, text: str, parent_geometry: QtCore.QRect = None):
        """
        Initialize the secondary window to display text.
        :param text: The text to display in the window.
        :param parent_geometry: The geometry of the parent (primary) window for positioning.
        """
        super().__init__()

        # Validate 'text'
        if not isinstance(text, str):
            raise ValueError(f"Expected a string for 'text', but got {type(text).__name__}")

        # Set default geometry if 'parent_geometry' is None
        if parent_geometry is None:
            parent_geometry = QtCore.QRect(100, 100, 640, 480)  # Default example fallback

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
        self.text_display = QtWidgets.QPlainTextEdit()
        self.text_display.setPlainText(text)
        self.text_display.setReadOnly(True)  # Make it read-only

        # Apply the font from the main window
        self.fontsize = 10
        font: QFont = QtGui.QFont("Cascadia Mono", self.fontsize, QtGui.QFont.Weight.Medium)
        self.text_display.setFont(font)

        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(self.text_display)

        # Create a container for buttons
        button_layout = QtWidgets.QHBoxLayout()

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


class SettingsDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Settings")
        self.layout = QtWidgets.QVBoxLayout(self)

        # Create splash checkbox
        self.splash_checkbox = QtWidgets.QCheckBox("Show Splash Screen")
        self.layout.addWidget(self.splash_checkbox)

        # Create theme combobox
        self.theme_combobox = QComboBox()
        self.theme_combobox.addItems(["Light", "Dark"])
        self.layout.addWidget(self.theme_combobox)

        # Define the OK and Cancel buttons
        QOk = QDialogButtonBox.StandardButton.Ok
        QCancel = QDialogButtonBox.StandardButton.Cancel

        # Create the button box
        self.button_box = QDialogButtonBox(QOk | QCancel)
        self.button_box.button(QOk).setText("OK")
        self.button_box.button(QCancel).setText("Cancel")

        # Enable the buttons (already enabled by default, but this is to ensure clarity)
        self.button_box.button(QOk).setEnabled(True)
        self.button_box.button(QCancel).setEnabled(True)

        # Explicitly declare the type of the button (`QPushButton`)
        ok_button: QPushButton = self.button_box.button(QOk)
        ok_button.clicked.connect(self.on_ok_clicked)
        cancel_button: QPushButton = self.button_box.button(QCancel)
        cancel_button.clicked.connect(self.on_cancel_clicked)

        # Add the button box to the layout
        self.layout.addWidget(self.button_box)

    def on_ok_clicked(self):
        """
        Action when OK is clicked.
        """
        # QMessageBox.information(self, "Info", "OK button clicked")
        self.accept()  # Close the dialog, marking it as 'accepted'

    def on_cancel_clicked(self):
        """
        Action when Cancel is clicked.
        """
        # QMessageBox.warning(self, "Warning", "Cancel button clicked")
        self.reject()  # Close the dialog, marking it as 'rejected'


class SyntaxHighlighter(QtGui.QSyntaxHighlighter):
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
                (line_num >= 0) and (isinstance(fmt, QtGui.QTextCharFormat)):
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


class FindDialog(QtWidgets.QDialog):
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
        # self.ui.lineEdit_1.setEchoMode(QtWidgets.QLineEdit.Normal)
        self.ui.lineEdit_1.returnPressed.connect(self.getter)
        self.ui.lineEdit_1.setClearButtonEnabled(False)
        self.ui.lineEdit_1.setFocusPolicy(QtCore.Qt.FocusPolicy.StrongFocus)

        self.ui.pushButton_1.clicked.connect(self.ui.lineEdit_1.clear)

        self.ui.comboBox_1.addItems(w.nwin)
        self.ui.comboBox_2.addItems(w.nwin)
        self.ui.comboBox_1.setCurrentIndex(0)
        self.ui.comboBox_2.setCurrentIndex(BOOKS_IN_THE_BIBLE - 1)


        QOk = QDialogButtonBox.StandardButton.Ok
        self.ui.buttonBox.button(QOk).setEnabled(True)
        self.ui.buttonBox.button(QOk).setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ui.buttonBox.button(QOk).clicked.connect(self.getter)
        QCancel = QDialogButtonBox.StandardButton.Cancel
        self.ui.buttonBox.button(QCancel).setEnabled(True)
        self.ui.buttonBox.button(QCancel).setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ui.buttonBox.button(QCancel).clicked.connect(w.close_find_window)

        self.ui.lineEdit_1.setFocus()

        self.ui.comboBox_1.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ui.comboBox_2.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_1.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_2.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_3.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_4.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_5.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ui.radiobutton_6.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)
        self.ui.checkBox.setFocusPolicy(QtCore.Qt.FocusPolicy.NoFocus)

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
        """Ensure that checkBox is correct."""

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

    current_directory: Path = Path.cwd()
    str_cwd: str = str(current_directory)
    # settings_file: Path = current_directory / 'settings.json'
    user_settings_dir: Path = Path.cwd()  # Initialize with the current working directory as a placeholder value.

    if system() == 'Windows':
        user_settings_dir = Path(getenv("APPDATA")) / "Abib"  # User's directory.
    elif system() == 'Darwin':
        user_settings_dir = Path.home() / "Library" / "Application Support" / "Abib"
    elif system() == 'Linux':
        user_settings_dir = Path.home() / ".config" / "Abib"
    else:
        print("Unknown operating system.")
        exit()

    # If settings.json exists in "Abib" then do nothing.
    user_settings_file = user_settings_dir / "settings.json"  # User's settings.json.
    if user_settings_file.exists():
        pass
    else:
        setup_Abib_settings(user_settings_dir)
    user_settings_path: str = str(user_settings_file)

    # Load settings if the file is found (default if not).
    settings: dict = load_settings_from_file(user_settings_path)

    # Construct the path to the icon regardless of the operating system.
    icon_path: Path = current_directory / "images" / "abib_icon0.ico"
    if not icon_path.is_file():
        raise FileNotFoundError(f"Icon file not found: {icon_path}")

    app: QApplication = QtWidgets.QApplication()
    app.setApplicationName("Abib")

    # Show the splash screen if enabled in settings
    splash_path = current_directory / "images" / "Abib_barley.png"
    if settings.get("show_splash", False):  # Default to False if the key is missing.
        splash = QSplashScreen(QPixmap(splash_path))
        splash.show()

    app.processEvents()

    width, height = app.primaryScreen().size().toTuple()
    half_width = width / 2
    half_height = height / 2

    MAX_VERSES_PER_CHAPTER = 176
    MAX_CHAPTER_COUNT = 150
    BOOKS_IN_THE_BIBLE = 66
    CHAPTERS_IN_THE_BIBLE = 1189
    LAST_VERSE_IN_BIBLE = 31101  # The first verse being zero.
    EOF_BIBLE_TEXT = LAST_VERSE_IN_BIBLE + 1
    EOF_AMAP = EOF_INFO = EOF_BIBLE_TEXT + 17

    w: MainWindow = MainWindow()

    back: list = []
    forward: list = []
    onechapterbooks: tuple[int, int, int, int, int] = (30, 56, 62, 63, 64)

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

    linehighlightcolor: QColor = QtGui.QColor("#0138b7")
    linetextcolor: QColor = QtGui.QColor("#ffffff")

    bibledict: dict[str, int] = {
        'genesis': 1, 'ge': 1, 'gen': 1, 'g': 1, 'gene': 1, 'ot': 1,
        'exodus': 2, 'ex': 2, 'exo': 2, 'e': 2, 'exod': 2,
        'leviticus': 3, 'le': 3, 'lev': 3, 'levi': 3, 'l': 3, 'levt': 3, 'levtics': 3,
        'numbers': 4, 'nu': 4, 'num': 4, 'number': 4, 'n': 4, 'numb': 4,
        'deuteronomy': 5, 'de': 5, 'deut': 5, 'deu': 5, 'd': 5,
        'joshua': 6, 'jos': 6, 'josh': 6, 'j': 6,
        'judges': 7, 'jdg': 7, 'ju': 7, 'jud': 7, 'judg': 7, 'judge': 7,
        'ruth': 8, 'ru': 8, 'rut': 8, 'r': 8,
        '1samuel': 9, '1s': 9, '1sa': 9, '1sam': 9, '1bk': 9, 'ibk': 9,
        'Isamuel': 9, 'Isam': 9,
        'isamuel': 9, 'isam': 9,
        '2samuel': 10, '2s': 10, '2sa': 10, '2sam': 10, '2bk': 10, 'iibk': 10,
        'iisamuel': 10, 'iis': 10, 'iisa': 10, 'iisam': 10,
        '1kings': 11, '1k': 11, '1ki': 11, '1kin': 11, '1king': 11, '3bk': 11,
        'ikings': 11, 'ik': 11, 'iki': 11, 'ikin': 11, 'iking': 11, 'iiibk': 11, 'iiikings': 11,
        '2kings': 12, '2k': 12, '2ki': 12, '2kin': 12, '2king': 12, '4bk': 12,
        'iikings': 12, 'iik': 12, 'iiki': 12, 'iikin': 12, 'iiking': 12, 'ivbk': 12, 'iiiibk': 12, 'ivkings': 12,
        '1chronicles': 13, '1ch': 13, '1chr': 13, '1chronicle': 13, '1c': 13,
        '1chro': 13, '1chron': 13, '1chroni': 13, '1chronic': 13, '1cr': 13,
        'ichro': 13, 'ichron': 13, 'ichroni': 13, 'ichronic': 13, 'icr': 13,
        'ichronicles': 13, 'ich': 13, 'ichr': 13, 'ichronicle': 13, 'ic': 13,
        '2chronicles': 14, '2ch': 14, '2chr': 14, '2chronicle': 14, '2c': 14,
        'iichronicles': 14, 'iich': 14, 'iichr': 14, 'iichronicle': 14, 'iic': 14,
        'ezra': 15, 'ezr': 15, 'ez': 15,
        'nehemiah': 16, 'ne': 16, 'neh': 16, 'nehe': 16, 'neem': 16,
        'esther': 17, 'es': 17, 'est': 17, 'esth': 17, 'esthe': 17, 'esta': 17,
        'job': 18, 'jb': 18,
        'psalms': 19, 'psalm': 19, 'ps': 19, 'psa': 19, 'p': 19,
        'proverbs': 20, 'pr': 20, 'pro': 20, 'prov': 20, 'proverb': 20,
        'ecclesiastes': 21, 'ec': 21, 'ecc': 21, 'eccl': 21, 'ecclesiaste': 21, 'eccles': 21,
        'songofsolomon': 22, 'songofsongs': 22, 'so': 22, 'son': 22, 'song': 22,
        'sos': 22, 'songs': 22, 's': 22, 'ss': 22, 'ca': 22, 'canticles': 22, 'sng': 22,
        'isaiah': 23, 'isai': 23, 'esaias': 23, 'i': 23, 'is': 23, 'isa': 23, 'ish': 23,
        'jeremiah': 24, 'je': 24, 'jer': 24, 'jeremy': 24,
        'lamentations': 25, 'la': 25, 'lam': 25, 'lamentation': 25, 'lame': 25,
        'ezekiel': 26, 'eze': 26, 'ezek': 26, 'ezk': 26, 'zek': 26,
        'daniel': 27, 'da': 27, 'dan': 27, 'dani': 27,
        'hosea': 28, 'ho': 28, 'hos': 28, 'h': 28, 'hose': 28,
        'joel': 29, 'joe': 29, 'jol': 29,
        'amos': 30, 'am': 30, 'amo': 30, 'a': 30,
        'obadiah': 31, 'ob': 31, 'oba': 31, 'obad': 31, 'o': 31,
        'jonah': 32, 'jon': 32, 'jona': 32,
        'micah': 33, 'mi': 33, 'mic': 33, 'm': 33, 'mica': 33,
        'nahum': 34, 'na': 34, 'nah': 34, 'nam': 34,
        'habakkuk': 35, 'hab': 35, 'haba': 35, 'habak': 35, 'ha': 35, 'hb': 35,
        'zephaniah': 36, 'zp': 36, 'zep': 36, 'zeph': 36, 'z': 36, 'ze': 36,
        'haggai': 37, 'hag': 37, 'hagg': 37, 'hg': 37, 'haggi': 37,
        'zechariah': 38, 'zc': 38, 'zec': 38, 'zech': 38,
        'malachi': 39, 'mal': 39, 'mala': 39, 'malac': 39, 'ma': 39,
        'matthew': 40, 'mt': 40, 'mat': 40, 'matt': 40, 'nt': 40,
        'mark': 41, 'mr': 41, 'mk': 41, 'mar': 41, 'mrk': 41,
        'luke': 42, 'lu': 42, 'lk': 42, 'luk': 42,
        'john': 43, 'joh': 43, 'jn': 43, 'jno': 43, 'jo': 43, 'jhn': 43, 'jh': 43,
        'acts': 44, 'ac': 44, 'act': 44,
        'romans': 45, 'ro': 45, 'rom': 45, 'roman': 45, 'roma': 45,
        '1corinthians': 46, '1co': 46, '1cor': 46, '1corinthian': 46,
        'icorinthians': 46, 'ico': 46, 'icor': 46, 'icorinthian': 46,
        '2corinthians': 47, '2co': 47, '2cor': 47, '2corinthian': 47,
        'iicorinthians': 47, 'iico': 47, 'iicor': 47, 'iicorinthian': 47,
        'galatians': 48, 'ga': 48, 'gal': 48, 'galatian': 48, 'gala': 48,
        'ephesians': 49, 'ep': 49, 'eph': 49, 'ephesian': 49, 'ephe': 49,
        'philippians': 50, 'php': 50, 'philip': 50, 'phil': 50, 'ph': 50, 'phili': 50,
        'colossians': 51, 'co': 51, 'col': 51, 'colossian': 51, 'c': 51,
        '1thessalonians': 52, '1th': 52, '1the': 52, '1thess': 52,
        '1thessalonian': 52, '1t': 52, '1thes': 52,
        'ithessalonians': 52, 'ith': 52, 'ithe': 52, 'ithess': 52,
        'ithessalonian': 52, 'it': 52, 'ithes': 52,
        '2thessalonians': 53, '2th': 53, '2the': 52, '2thess': 53,
        '2thessalonian': 53, '2t': 53, '2thes': 53,
        'iithessalonians': 53, 'iith': 53, 'iithe': 52, 'iithess': 53,
        'iithessalonian': 53, 'iit': 53, 'iithes': 53,
        '1timothy': 54, '1ti': 54, '1tim': 54,
        'itimothy': 54, 'iti': 54, 'itim': 54,
        '2timothy': 55, '2ti': 55, '2tim': 55,
        'iitimothy': 55, 'iiti': 55, 'iitim': 55,
        'titus': 56, 'ti': 56, 'tit': 56, 't': 56,
        'philemon': 57, 'phm': 57, 'phi': 57, 'phl': 57, 'phile': 57, 'philo': 57,
        'hebrews': 58, 'he': 58, 'heb': 58, 'hebrew': 58, 'hebr': 58,
        'james': 59, 'ja': 59, 'jas': 59, 'jam': 59, 'jame': 59, 'jim': 59, 'jamo': 59,
        '1peter': 60, '1p': 60, '1pe': 60, '1pet': 60, '1pete': 60,
        'Ipeter': 60, 'Ip': 60, 'Ipe': 60, 'Ipet': 60, 'Ipete': 60,
        'ipeter': 60, 'ip': 60, 'ipe': 60, 'ipet': 60, 'ipete': 60,
        '2peter': 61, '2p': 61, '2pe': 61, '2pet': 61, '2pete': 61,
        'IIpeter': 61, 'IIp': 61, 'IIpe': 61, 'IIpet': 61, 'IIpete': 61,
        'iipeter': 61, 'iip': 61, 'iipe': 61, 'iipet': 61, 'iipete': 61,
        '1john': 62, '1j': 62, '1jo': 62, '1joh': 62, '1jn': 62, '1jno': 62,
        'ijohn': 62, 'ij': 62, 'ijo': 62, 'ijoh': 62, 'ijn': 62, 'ijno': 62,
        '2john': 63, '2j': 63, '2jo': 63, '2joh': 63, '2jn': 63, '2jno': 63,
        'iijohn': 63, 'iij': 63, 'iijo': 63, 'iijoh': 63, 'iijn': 63, 'iijno': 63,
        '3john': 64, '3j': 64, '3jo': 64, '3joh': 64, '3jn': 64, '3jno': 64,
        'iiijohn': 64, 'iiij': 64, 'iiijo': 64, 'iiijoh': 64, 'iiijn': 64, 'iiijno': 64,
        'jude': 65, 'jd': 65, 'jde': 65,
        'revelation': 66, 'revelationofjohn': 66, 're': 66, 'rev': 66, 'theapocalypseofjohn': 66,
        'revelations': 66, 'reve': 66, 'apocalypse': 66, 'apocalypseofjohn': 66,
    }

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
    file_path = str(Path(str_cwd) / "KJB_PCE.txt")
    # Pass the constructed path to readio
    KJV = readio('', file_path, KJB_PCE_LASTLINE)

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
    file_path = str(Path(str_cwd) / "Amap.txt")

    # Pass the constructed path to the function
    Amap: list = readfile('', file_path, EOF_AMAP)

    Amap = Amap[17:]

    Ps119: list[int] = [
        15907, 15915, 15923, 15931, 15939, 15947, 15955, 15963, 15971, 15979,
        15987, 15995, 16003, 16011, 16019, 16027, 16035, 16043, 16051, 16059,
        16067]
    P119: list = []
    for _ in Ps119:
        v: Any = Amap[_]
        P119.append(v)

    # Create the base directory as a Path object
    base_dir = Path(str_cwd)

    # Read Info.txt
    Info = []
    Inf: list = readfile('', str(Path(base_dir / "Info.txt")), EOF_INFO)
    Inf = Inf[17:]  # Skip the first 17 elements
    for _ in range(LAST_VERSE_IN_BIBLE + 1):
        Info.append(loads(Inf[_]))
    Info = tuple(Info)

    # Open KJB_PCE.txt
    w.file_open(str(base_dir / "KJB_PCE.txt"))

    # Read stripped_dict.txt
    with open("stripped_dict.txt", encoding="utf-8") as f:
        stripped_dict: Any = load(f)

    # Read strpd_low_dict.txt
    with open("strpd_low_dict.txt", encoding="utf-8") as f:
        strpd_low_dict: Any = load(f)

    # Load dictionaries using load_list_set_dict
    set_dict: dict[Any, set] = load_list_set_dict("list_dict.json", stripped_dict)
    set_lowdict: dict[Any, set] = load_list_set_dict("list_lowdict.json", strpd_low_dict)

    # Read and process PCE-find.txt
    Rnew = readio('', str(Path(base_dir / "PCE-find.txt")), EOF_BIBLE_TEXT)
    Rnew = tuple(Rnew)
    Rdic: dict[int, Any] = dict(enumerate(Rnew))  # Convert Rnew to dictionary.

    # Read and process PCE-lower.txt
    Rlow = readio('', str(Path(base_dir / "PCE-lower.txt")), EOF_BIBLE_TEXT)
    Rlow = tuple(Rlow)
    Ldic: dict[int, Any] = dict(enumerate(Rlow))  # Convert Rlow to dictionary.

    # Read PCE-stripped.txt
    Rstp = readio('', str(Path(base_dir / "PCE-stripped.txt")), EOF_BIBLE_TEXT)
    Rstp = tuple(Rstp)

    # Read PCE-stripped_lower.txt
    Rlsp = readio('', str(Path(base_dir / "PCE-stripped_lower.txt")), EOF_BIBLE_TEXT)
    Rlsp = tuple(Rlsp)

    try:
        with open("morning_evening.json", "r", encoding="utf-8") as file:
            sme_data = load(file)  # Load JSON data
    except JSONDecodeError as e:
        print(f"JSON file is invalid: {e}")

    date_file: tuple = get_date_file()

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # Plugin socket.
    # Paste the plugin here for probably single use and run Abib to run
    # it.  This enables utility plugins to use the functions of Abib.
    # Beware of over-writing previous files accidentally.
    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++
    # *** PLACE YOUR PLUGIN HERE (between the two lines) ***

    # +++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

    # Set the application icon
    app_icon: QIcon = QIcon(str(icon_path))  # Convert the Path object to string for QIcon
    app.setWindowIcon(app_icon)

    w.show()
    exit(app.exec())
# This is a new line that ends the file.
