from __future__ import annotations
import re
from typing import Dict, Set, TYPE_CHECKING
import fcs

if TYPE_CHECKING:
    from Abib import MainWindow

def iterate_list(keywords: list[str], r_list: list, win: MainWindow) -> None:
    """Iterate over r_list and find all the occurrences of key(s) in keywords."""
    win.occurring = 0
    win.occur = []
    for i in win.occurs:
        coordinates = []
        for key in keywords:
            pattern = fcs.create_pattern(key)
            for m in re.finditer(pattern, r_list[i]):
                win.occurring += 1
                coordinates.append((m.start(), m.end()))
        if coordinates:
            win.occur.append(coordinates)

def findf3_ww_ac(x1: int, x2: int, numwords: int, _set: Dict[str, Set], r_list: list, win: MainWindow) -> None:
    """Whole words (phrase)."""
    liszt = win.key.split(' ')
    s = _set[liszt[0]] & _set[liszt[1]]
    if numwords > 2:
        for i in range(2, numwords):
            j = liszt[i]
            s = s & _set[j]
    win.occur = sorted(list(s))
    win.occurs = []

    pattern = re.compile(rf"\b{re.escape(win.key)}\b")

    for i in win.occur:
        if x1 <= i <= x2 and pattern.search(r_list[i]):
            win.occurs.append(i)

    liszt = [win.key]
    iterate_list(liszt, r_list, win)
    c = 0
    for i in win.occur:
        li = len(i)
        c += li
    win.occurring = c

def findf3_ww_all(x1: int, x2: int, numwords: int, _set: Dict[str, Set], r_list: list, win: MainWindow) -> None:
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
    win.occur = sorted(list(s))
    win.occurs = []
    for i in win.occur:
        if i < x1 or i > x2:
            continue
        win.occurs.append(i)
    iterate_list(liszt, r_list, win)
    win.occurring = len(win.occurs)

def findf3_ww_any(x1: int, x2: int, _set: Dict[str, Set], r_list: list, win: MainWindow) -> None:
    """Find any of the words."""
    liszt = win.key.split(' ')
    s = set()
    for word in liszt:
        if word in _set:
            s.update(_set[word])
    win.occurs = sorted([i for i in s if x1 <= i <= x2])
    win.occur = []
    check_count_sort(liszt, r_list, win)

def check_count_sort(liszt: list[str], r_list: list, win: MainWindow) -> None:
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
    win.occurring = len(win.occurs)
