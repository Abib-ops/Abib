# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from abib.core import fcs

if TYPE_CHECKING:
    from abib.Abib import MainWindow
    from abib.services.data_loader import SearchData


# The runtime search data tables (``Rnew``, ``Rlow``, ``Rstp``, ``Rlsp`` and the
# stripped/set dictionaries) are registered here once at startup by ``app.run``
# (and again if the indexes are reloaded). Holding them in an explicit context
# removes the previous hidden coupling where the engine reached back into the
# ``abib.Abib`` module globals via a deferred import.
_search_data: SearchData | None = None


def set_search_data(data: SearchData) -> None:
    """Register the loaded search data tables for the search engine to use.

    Called once at startup (and again if the search indexes are reloaded) so the
    search functions can read the runtime data tables without importing
    ``abib.Abib``.
    """

    global _search_data
    _search_data = data


def _data() -> SearchData:
    """Return the registered search data, raising if it has not been set yet."""

    if _search_data is None:
        raise RuntimeError(
            "Search data has not been loaded; call set_search_data() first."
        )
    return _search_data


def get_search_data() -> SearchData:
    """Public accessor for the registered search data tables.

    Used by callers (e.g. ``MainWindow`` highlighting helpers) that need the raw
    ``Rnew``/``Rlow`` tables without reaching back into the ``abib.Abib`` module.
    """

    return _data()


def get_next_occurrence(win: MainWindow) -> int:
    """Count occurrence(s) of win.key and give current_position and win.y values.

    win.occurs is a list of all the current_position values in the search results.
    win.occur is a corresponding list which gives the start win.y and finish win.yend of
    the searched for item in the particular verse.
    win.occurring is the total number of times the search key was found.
    win.verse is the number of the items in the search list.
    len(win.occur[win.verse]) is the number of search results in a particular verse.
    win.finding is the number of items found within the verse.
    """

    if win.dlg is not None and win.dlg.checks[0] in (3, 4):
        current_position = win.occurs[win.verse]
        win.finding = 0
        if win.occur[win.verse]:
            win.occur[win.verse].sort(key=lambda _x: _x[0])
            win.y = win.occur[win.verse][0][0]
            win.yend = win.occur[win.verse][0][1]
        win.occurrence += 1
        win.statusBar.showMessage(win.nav.get_status_message(current_position))
        return current_position

    current_position = win.occurs[-1]

    if win.verse < len(win.occurs):
        win.finding += 1
        current_position = win.occurs[win.verse]
        if win.finding + 1 <= len(win.occur[win.verse]):
            win.y = win.occur[win.verse][win.finding][0]
            win.yend = win.occur[win.verse][win.finding][1]
            win.occurrence += 1
            win.statusBar.showMessage(win.nav.get_status_message(current_position))
        elif win.verse + 1 < len(win.occurs):
            win.verse += 1
            win.finding = 0
            win.y = win.occur[win.verse][win.finding][0]
            win.yend = win.occur[win.verse][win.finding][1]
            win.occurrence += 1
            current_position = win.occurs[win.verse]
            win.statusBar.showMessage(win.nav.get_status_message(current_position))
    elif win.verse >= len(win.occurs):
        current_position = win.occurs[-1]

    return current_position


def make_key_whole(win: MainWindow, _key: str, _dict: dict, _set: dict[str, set]) -> tuple[int, str]:
    """Make _key conform to Match whole word only.

    Return the number of whole words in the _key variable.
    """

    numstart, _key = fcs.split_strip(_key)
    words: list = _key.split()
    words = [item for item in words if item in _dict]
    _key = ''
    for i in words:
        _key += i + ' '
    _key = _key[:-1]  # Remove the last space character.
    num = len(words)
    if num != numstart and (win.dlg.checks[0] == 2 or win.dlg.checks[1] == 3):
        # A word or part of a word was removed.
        num = 0

    return num, _key


def prepare_key_for_find(win: MainWindow) -> None:
    """Adjust 'key' for searching in Rnew, which has no Unicode italics.

    It also has a different apostrophe and uses æ and Æ.
    """

    p = "():,’;-?[].!<>"
    ae: list[str] = ['aea', 'aeu', 'aes', 'aet', 'aene', 'aeno', 'AEno', 'AEne', 'Aeno', 'Aene']
    ae_unicode: list[str] = ['æa', 'æu', 'æs', 'æt', 'æne', 'æno', 'Æno', 'Æne', 'Æno', 'Æne']
    count = -1
    for _ in ae:
        count += 1
        if _ in win.key:
            index = win.key.find(_)
            j = len(_)
            j += index
            win.key = win.key[:index] + ae_unicode[count] + win.key[j:]
            break
    line = ''
    for _ in win.key:
        if _ in p:
            if _ == '-' and win.dlg.checks[0] != 1:
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
    win.key = line


def iterate_regex(win: MainWindow, r: tuple, x1: int, x2: int) -> None:
    """Iterate over R and find all the occurrences of key(s) in liszt."""

    win.occurring = 0
    win.occur = []
    win.occurs = []
    if win.dlg.checks[1] == 1:             # Match case
        pattern = rf"{win.key}"
    else:
        assert win.dlg.checks[1] == 0      # Ignore the case
        pattern = rf"(?i){win.key}"
    # Iterate inclusively within the provided limits [x1, x2]
    for _ in range(x1, x2 + 1):
        coordinate = []
        try:
            for m in re.finditer(pattern, r[_]):
                win.occurring += 1
                coordinate.append((m.start(), m.end()))
        except re.error:
            msg = 'Regular Expression Error.'
            win.on_error(msg, 2000, True)
            win.occurring = 0
            break
        if coordinate:
            win.occur.append(coordinate)
            win.occurs.append(_)


def find_raw(win: MainWindow, current_position: int, x1: int, x2: int, keylow: str) -> int:
    """Find Raw."""

    data = _data()

    win.occurs = []
    win.occur = []

    # Count occurrences inclusively within the provided limits [x1, x2]
    if win.dlg.checks[1] == 1:  # Match case
        source = data.Rnew
        search_key = win.key
    elif win.dlg.checks[1] == 0:  # Lower case
        source = data.Rlow
        search_key = keylow
    else:
        source = data.Rnew
        search_key = win.key

    for i in range(x1, x2 + 1):
        coordinate = []
        start_search = 0
        while True:
            y = source[i].find(search_key, start_search)
            if y == -1:
                break
            coordinate.append((y, y + len(search_key)))
            win.occurring += 1
            start_search = y + 1
        if coordinate:
            win.occur.append(coordinate)
            win.occurs.append(i)

    if win.occurring != 0:
        win.occurrence = 0
        current_position = occurrent(win, x1, x2)
        if win.message:
            win.statusBar.showMessage(win.message)
        win.statusBar.repaint()

    return current_position


def assign_values(win: MainWindow):
    """Resolve dictionaries/sources for the current match-case setting."""

    data = _data()

    numwords: int
    win.verse = 0
    if win.dlg.checks[1] == 1:             # Match case.
        dic = data.stripped_dict
        key: str = win.key
        # set_ and set_dict are dictionaries of words in the KJV Bible.
        # For each word, there is a set of verse/line numbers where the word occurs.
        set_: dict = data.set_dict
        r_list = data.Rstp
    else:
        assert win.dlg.checks[1] == 0      # The Case isn't checked.
        dic = data.strpd_low_dict
        key = win.key.lower()
        set_ = data.set_lowdict
        r_list = data.Rlsp
    numwords, win.key = make_key_whole(win, key, dic, set_)
    win.keym = win.key  # 16/12/2024

    return numwords, set_, r_list


def find_whole_word(win: MainWindow, x1: int, x2: int) -> int:
    """Find Whole Words."""

    numwords, set_, r_list = assign_values(win)
    current_position: int = 0  # Pointer to the first verse with the searched for key.
    if numwords == 1:
        find_whole_word_single(win, x1, x2, set_, r_list)   # Match the whole single word.
        if win.dlg.checks[0] in (3, 4):
            win.occurring = len(win.occurs)
        if win.occurring != 0:
            win.occurrence = 0
            win.verse = 0
            win.finding = -1
            current_position = get_next_occurrence(win)
            if win.message:
                win.statusBar.showMessage(win.message)
            win.statusBar.repaint()
    elif numwords > 1:
        if win.dlg.checks[0] == 2:
            find_whole_word_phrase(x1, x2, numwords, set_, r_list, win)
        elif win.dlg.checks[0] == 3:
            find_whole_word_all(x1, x2, numwords, set_, r_list, win)
        elif win.dlg.checks[0] == 4:
            _, win.key = fcs.any_of_the_words_lookup(win.key, set_)
            find_whole_word_any(x1, x2, set_, r_list, win)
        if win.occurring != 0:
            if win.dlg.checks[0] in (2, 3, 4):
                win.occurrence = 0
                win.verse = 0
                win.finding = -1
                current_position = get_next_occurrence(win)
            if win.message:
                win.statusBar.showMessage(win.message)
            win.statusBar.repaint()
    else:
        win.occurring = 0

    return current_position


def find_whole_word_single(win: MainWindow, x1: int, x2: int, _set: dict[str, set], r_list: list | tuple) -> None:
    """Match the whole single word."""

    try:
        win.occur = sorted(_set[win.key])
    except KeyError:
        win.occurring = 0
    else:
        win.occurs = []
        for i in win.occur:
            if i < x1 or i > x2:
                continue
            win.occurs.append(i)
        # List of lists with tuple of the word positions, within the related verse.
        liszt = [win.key]
        if win.dlg.checks[0] == 4:
            check_count_sort(liszt, r_list, win)
        else:
            iterate_list(liszt, r_list, win)
    # List of verses containing the searched for item.
    # Number of occurrences of the searchitem within the range x1 to x2.


def occurrent(win: MainWindow, x1: int, x2: int) -> int:
    """Count occurrences of the item searched for."""

    if win.occurrence == 0:
        win.gent = gen(win, win.key, x1, x2)
    gent = win.gent
    assert gent is not None
    current_position, win.y, win.occurrence = next(gent)
    win.statusBar.showMessage(win.nav.get_status_message(current_position))

    return current_position


def gen(win: MainWindow, key: str, x1: int, x2: int):
    """Return the next position of the searched for key using in-memory data."""

    data = _data()
    d1 = 0
    if win.dlg.checks[1] == 1:
        source = data.Rnew
    else:
        source = data.Rlow
        key = key.lower()

    for current_position in range(x1, x2 + 1):
        if current_position >= len(source):
            break
        a = source[current_position]
        start_search = 0
        while True:
            y = a.find(key, start_search)
            if y == -1:
                break
            d1 += 1
            win.y = y
            start_search = y + 1
            yield current_position, win.y, d1


def iterate_list(keywords: list[str], r_list: list | tuple, win: MainWindow) -> None:
    """Iterate over r_list and find all the occurrences of key(s) in keywords."""
    win.occurring = 0
    win.occur = []
    
    # Pre-compile patterns to avoid redundant work in the loop
    patterns = [re.compile(fcs.create_pattern(key)) for key in keywords]
    
    for i in win.occurs:
        coordinates = []
        text = r_list[i]
        for pattern in patterns:
            for m in pattern.finditer(text):
                win.occurring += 1
                coordinates.append((m.start(), m.end()))
        win.occur.append(coordinates)

def find_whole_word_phrase(x1: int, x2: int, numwords: int, _set: dict[str, set], r_list: list | tuple, win: MainWindow) -> None:
    """Whole words (phrase)."""
    liszt = win.key.split(' ')
    s = _set[liszt[0]] & _set[liszt[1]]
    if numwords > 2:
        for i in range(2, numwords):
            j = liszt[i]
            s = s & _set[j]
    win.occur = sorted(s)
    win.occurs = []

    pattern = re.compile(rf"\b{re.escape(win.key)}\b")

    for i in win.occur:
        text = r_list[i]
        if x1 <= i <= x2 and pattern.search(text):
            win.occurs.append(i)

    liszt = [win.key]
    iterate_list(liszt, r_list, win)

def find_whole_word_all(x1: int, x2: int, numwords: int, _set: dict[str, set], r_list: list | tuple, win: MainWindow) -> None:
    """Match all the words (phrase)."""
    liszt = win.key.split(' ')
    try:
        s = _set[liszt[0]] & _set[liszt[1]]
    except KeyError:
        print(f'liszt[0] {liszt[0]}')
        print(f'liszt[1] {liszt[1]}')
        raise KeyError

    if numwords > 2:
        for i in range(2, numwords):
            s = s & _set[liszt[i]]
    win.occur = sorted(s)
    win.occurs = []
    for i in win.occur:
        if i < x1 or i > x2:
            continue
        win.occurs.append(i)
    iterate_list(liszt, r_list, win)
    win.occurring = len(win.occurs)

def find_whole_word_any(x1: int, x2: int, _set: dict[str, set], r_list: list | tuple, win: MainWindow) -> None:
    """Find any of the words."""
    liszt = win.key.split(' ')
    s = set()
    for word in liszt:
        if word in _set:
            s.update(_set[word])
    win.occurs = sorted([i for i in s if x1 <= i <= x2])
    win.occur = []
    check_count_sort(liszt, r_list, win)
    win.occurring = len(win.occurs)

def check_count_sort(liszt: list[str], r_list: list | tuple, win: MainWindow) -> None:
    """Check matched words are whole, count and sort win.occurs (Any)."""
    win.count = []
    iterate_list(liszt, r_list, win)
    lo = len(win.occur)

    if lo == 0:
        win.occurring = 0
        return

    for i in range(lo):
        win.count.append(len(win.occur[i]))

    win.count, win.occurs, win.occur = zip(
        *sorted(zip(win.count, win.occurs, win.occur), reverse=True))

    win.occur = list(win.occur)
    win.occurs = list(win.occurs)

    newt: list = []
    newts: list = []
    j = win.count[0]
    k = 0
    t: list = []
    ts: list = []
    for i in win.count:
        if (i == j) and (k < lo):
            wok = win.occur[k]
            t.append(wok)
            woks = win.occurs[k]
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
                t.append(win.occur[k])
                ts.append(win.occurs[k])
                j = i
                k += 1
    
    if t: # handle last group
        t.reverse()
        ts.reverse()
        newt.append(t)
        newts.append(ts)

    win.occur = [item for sublist in newt for item in sublist]
    win.occurs = [item for sublist in newts for item in sublist]
