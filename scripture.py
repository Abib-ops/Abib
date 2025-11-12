# -*- coding: utf-8 -*-
"""
Scripture parsing, normalisation, and lookup utilities.

Centralises logic used by the UI (Abib.TextDocumentWindow) and utilities (scan_owen_refs.py)
so it can be maintained and tested in one place.
"""
from __future__ import annotations

import re
from typing import Any, Dict, List
from roman import fromRoman, InvalidRomanNumeralError
import shared as sh

# Canonical book names keyed by 'book' id (1-based), aligning with shared.bibledict
CANONICAL_BOOKS: Dict[int, str] = {
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


def normalize_book_input(book_input: str) -> str:
    """Normalise a user/book token to a bibledict key.

    - Lowercase and strip
    - Convert leading Roman I/II/III to 1/2/3
    - Remove non-word characters
    - Map legacy tokens (e.g. Cant. -> canticles)
    """
    s = book_input.strip().lower()
    s = re.sub(r"^(iii)(?=\b|\s|\.)", "3", s)
    s = re.sub(r"^(ii)(?=\b|\s|\.)", "2", s)
    s = re.sub(r"^(i)(?=\b|\s|\.)", "1", s)
    s = re.sub(r"\W+", "", s)
    legacy_map = {
        "cant": "canticles",
        "canticle": "canticles",
        "canticles": "canticles",
    }
    if s in legacy_map:
        s = legacy_map[s]
    return s


# Precompile the reference pattern used by both UI and scanner
_ord_re = r"(?:(?:[1-3]|i{1,3})\.?\s*)?"  # 1/2/3 or i/ii/iii with optional dot
_book_re = r"[A-Za-z]+"  # validated later
_arabic_re = r"(?P<chap_a>\d{1,3})\s*:\s*(?P<vers_a>\d{1,3}(?:\s*[-–]\s*\d{1,3})?(?:\s*,\s*\d{1,3}(?:\s*[-–]\s*\d{1,3})?)*)"
_roman_re = r"(?P<chap_r>[ivxlcdm]+)\.?\s*(?:v(?:er\.)?\s*)?(?P<vers_r>\d{1,3}(?:\s*[-–]\s*\d{1,3})?(?:\s*,\s*\d{1,3}(?:\s*[-–]\s*\d{1,3})?)*)"
_nochap_re = r"(?P<vers_only>\d{1,3}(?:\s*[-–]\s*\d{1,3})?(?:\s*,\s*\d{1,3}(?:\s*[-–]\s*\d{1,3})?)*)"

_PATTERN = rf"""
    (?<!\w)
    (?P<book>{_ord_re}{_book_re})\.?\s+
    (?:{_arabic_re}|{_roman_re}|{_nochap_re})
    (?=[\s);:,.]|$)
"""


def find_scripture_references(text: str) -> List[Dict[str, Any]]:
    """Find scripture references in a given text.

    Returns a list of dicts: {text, book, chapter, verse, start, length}
    """
    references: List[Dict[str, Any]] = []
    for m in re.finditer(_PATTERN, text, re.IGNORECASE | re.VERBOSE):
        full = m.group(0)
        lstripped = full.lstrip()
        lead = len(full) - len(lstripped)
        book_raw = m.group("book")
        normalized = normalize_book_input(book_raw)
        book_id = sh.bibledict.get(normalized)
        if not book_id:
            continue

        if m.group("chap_a") and m.group("vers_a"):
            try:
                chapter = int(m.group("chap_a"))
            except ValueError:
                continue
            verses = m.group("vers_a")
        elif m.group("chap_r") and m.group("vers_r"):
            chap_rom = m.group("chap_r").upper()
            try:
                chapter = fromRoman(chap_rom)
            except (InvalidRomanNumeralError, ValueError):
                continue
            verses = m.group("vers_r")
        elif m.group("vers_only"):
            if (book_id - 1) not in sh.onechapterbooks:
                continue
            chapter = 1
            verses = m.group("vers_only")
        else:
            continue

        verses = verses.strip()
        verses = re.sub(r"[\s)\];:.,]+$", "", verses)
        start = m.start() + lead
        length = len(lstripped)
        references.append(
            {
                "text": lstripped,
                "book": book_raw,
                "chapter": chapter,
                "verse": verses,
                "start": start,
                "length": length,
            }
        )

        # Handle semicolon-separated continuations inheriting book and possibly chapter,
        # e.g. "John 3:16; 4:5, 12-15" or one-chapter books like "Jude 5; 7-9".
        # We scan forward from the end of this match for additional segments starting with ';'.
        pos = m.end()
        last_book_display = book_raw
        last_chapter = chapter
        # Pattern for later segments: ; <chapter>:<verses> OR ; <verses-only>
        cont_re = re.compile(
            r"^\s*;\s*(?:(?P<chap>\d{1,3})\s*[:.]\s*(?P<vers>\d{1,3}(?:\s*[-–]\s*\d{1,3})?(?:\s*,\s*\d{1,3}(?:\s*[-–]\s*\d{1,3})?)*)|(?P<vers_only>\d{1,3}(?:\s*[-–]\s*\d{1,3})?(?:\s*,\s*\d{1,3}(?:\s*[-–]\s*\d{1,3})?)*))",
            re.IGNORECASE,
        )
        while pos < len(text):
            tail = text[pos:]
            m2 = cont_re.match(tail)
            if not m2:
                break
            seg_full = m2.group(0)
            seg_lstripped = seg_full.lstrip()
            seg_lead = len(seg_full) - len(seg_lstripped)
            start2 = pos + seg_lead
            # Determine chapter and verses
            if m2.group("chap") and m2.group("vers"):
                try:
                    chapter2 = int(m2.group("chap"))
                except ValueError:
                    chapter2 = None
                verses2 = m2.group("vers")
                if chapter2 is None:
                    break
                last_chapter = chapter2
                references.append(
                    {
                        "text": seg_lstripped,
                        "book": last_book_display,
                        "chapter": chapter2,
                        "verse": re.sub(r"[\s)\];:.,]+$", "", verses2.strip()),
                        "start": start2,
                        "length": len(seg_lstripped),
                    }
                )
            else:
                # verse-only continuation
                verses2 = m2.group("vers_only")
                chap_for_vers_only: int | None = None
                if last_chapter is not None:
                    chap_for_vers_only = last_chapter
                elif (sh.bibledict.get(normalized) or 0) and (book_id - 1) in sh.onechapterbooks:
                    chap_for_vers_only = 1
                if chap_for_vers_only is None:
                    # cannot resolve chapter for this continuation; stop chaining
                    break
                references.append(
                    {
                        "text": seg_lstripped,
                        "book": last_book_display,
                        "chapter": chap_for_vers_only,
                        "verse": re.sub(r"[\s)\];:.,]+$", "", verses2.strip()),
                        "start": start2,
                        "length": len(seg_lstripped),
                    }
                )
            pos += len(seg_full)
    return references


def lookup_scripture(bible_data: Dict[str, Any], book: str, chapter: int, verses: str) -> str:
    """Look up verse text(s) from bible_data, returning a human-readable string.

    - Normalizes book token
    - Supports verse lists and ranges, including en/em dashes
    - Returns a friendly message when a verse is not found
    """
    normalized_book = normalize_book_input(book)
    book_id = sh.bibledict.get(normalized_book)
    if not book_id:
        return "Scripture not found."

    full_book = CANONICAL_BOOKS.get(book_id, book)
    chapter_data = bible_data.get(full_book, {}).get(str(chapter), {})

    verses = verses.replace("–", "-").replace("—", "-")
    verse_numbers: List[int] = []
    for part in verses.split(','):
        part = part.strip().replace("–", "-").replace("—", "-")
        if '-' in part:
            try:
                start_s, end_s = part.split('-', 1)
                start_i = int(start_s.strip())
                end_i = int(end_s.strip())
                if start_i <= end_i:
                    verse_numbers.extend(range(start_i, end_i + 1))
                else:
                    verse_numbers.extend(range(start_i, end_i - 1, -1))
            except ValueError:
                return "Scripture not found."
        else:
            try:
                verse_numbers.append(int(part))
            except ValueError:
                return "Scripture not found."

    results: List[str] = []
    for ve in verse_numbers:
        verse_text = chapter_data.get(str(ve))
        if verse_text is None:
            results.append(f"Verse {ve} not found.")
        else:
            results.append(str(ve) + " " + verse_text)
    return "\n".join(results)
