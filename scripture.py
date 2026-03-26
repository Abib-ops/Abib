# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

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
    - Convert leading ordinals: 1st/2nd/3rd and First/Second/Third to 1/2/3
    - Convert leading Roman I/II/III to 1/2/3
    - Remove non-word characters
    - Map legacy tokens (e.g. Cant. -> canticles)
    """
    s = book_input.strip().lower()
    # Normalise Arabic ordinals with suffixes at the very start (allow optional space and optional trailing dot)
    # Examples handled: 1st John, 1 st. John, 1stJohn, 2nd-Thess, 3rdJn
    s = re.sub(r"^1\s*st\.?", "1", s)
    s = re.sub(r"^2\s*nd\.?", "2", s)
    s = re.sub(r"^3\s*rd\.?", "3", s)

    # Normalise written-out ordinals at the very start
    # Examples: First John, Second Corinthians, Third John
    s = re.sub(r"^first\b", "1", s)
    s = re.sub(r"^second\b", "2", s)
    s = re.sub(r"^third\b", "3", s)

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


def classify_book_input(user_input: str) -> Dict[str, Any]:
    """Classify a free-form input for quick-jump intent.

    Returns a dict with keys:
      - status: one of {"none", "exact", "short_with_sep", "ambiguous_prefix"}
      - key: normalized dict key (when applicable)
      - book_id: int id (1-66) when applicable
      - matched_abbr: the short abbreviation that matched (for UI messaging), optional

    Rules implemented (from product suggestions):
      1) Exact match only: if the fully normalised string is a known key -> "exact".
      2) Short abbreviation acceptance requires a clear separator afterwards when more follows
         (e.g. "am 1:1", "am.1:1", "am:1" or just "am").
         If satisfied -> "short_with_sep".
      3) If the input begins with a valid abbreviation but lacks a clear separator (e.g. "amaziah"),
         mark as "ambiguous_prefix" and provide the most plausible book (typically by the longest
         matching abbreviation key).
    """
    raw = (user_input or "").strip()
    if not raw:
        return {"status": "none"}

    # Exact normalisation first
    normalized_full = normalize_book_input(raw)
    book_id = sh.bibledict.get(normalized_full)
    if book_id:
        return {"status": "exact", "key": normalized_full, "book_id": book_id}

    # Work with the raw lowercase text to reason about separators
    s = raw.lower()
    # Acceptable separator characters between a short abbr and the chapter/verse
    sep_chars = set(" .:-\t/\u00A0")

    # Build a list of candidate abbreviation keys (pure alpha, up to 3 chars)
    short_alpha_keys = [k for k in sh.bibledict.keys() if k.isalpha() and len(k) <= 3]
    # Track the longest matching abbreviation to bias toward more specific keys
    best_match: str | None = None
    for k in short_alpha_keys:
        if s.startswith(k):
            if best_match is None or len(k) > len(best_match):
                best_match = k

    if best_match:
        bid = sh.bibledict.get(best_match)
        # Determine if we have a clear separator or the abbr is the whole input
        if len(s) == len(best_match):
            return {"status": "short_with_sep", "key": best_match, "book_id": bid, "matched_abbr": best_match}
        next_char = s[len(best_match)]
        if next_char in sep_chars:
            return {"status": "short_with_sep", "key": best_match, "book_id": bid, "matched_abbr": best_match}
        # Otherwise it's an ambiguous start (e.g. amaziah). Suggest the matched book but do not auto-jump.
        return {"status": "ambiguous_prefix", "key": best_match, "book_id": bid, "matched_abbr": best_match}

    # Also detect startswith any longer known key (e.g. "jonas" starts with "jonas" exact, already handled;
    # here we care about misleading beginnings that match full long keys like "amos" -> would have matched above).
    # If starts with any known key but with letters glued without a separator (rare), treat as ambiguous too.
    for k in sh.bibledict.keys():
        if s.startswith(k):
            bid2 = sh.bibledict[k]
            if len(s) == len(k) or s[len(k)] in sep_chars:
                # Would have been exact earlier; treat as none here
                break
            return {"status": "ambiguous_prefix", "key": k, "book_id": bid2, "matched_abbr": k}

    return {"status": "none"}


# Precompile the reference pattern used by both UI and scanner
# Define a broader whitespace class that includes common Unicode spaces seen in ebooks/PDFs.
_WS = r"[\s\u00A0\u202F\u2007\u2009\u200A\u2000-\u2006]"
# No-newline whitespace class for intra-reference glue (spaces/tabs and narrow no-breaks only).
# This prevents matches from spanning across line breaks into list bullets like "-2" on the next line.
_NO_NL_WS = r"[\t \u00A0\u202F\u2007\u2009\u200A\u2000-\u2006]"

_ORD_SUFFIX = r"(?:st|nd|rd)?"  # for Arabic 1st/2nd/3rd
_ORD_WORDS = r"(?:first|second|third)"  # written-out ordinals
_SEP = rf"(?:{_WS}*[-.]?{_WS}*)"  # allow optional spaces with optional hyphen or dot between ordinal and book
_ord_re = rf"(?:(?:[1-3]{_ORD_SUFFIX}|i{{1,3}}|{_ORD_WORDS}){_SEP})?"  # 1/2/3(+suffix)
# or i/ii/iii or words with optional sep
_book_re = r"[A-Za-z]+"  # validated later
# Allow colon or dot between Arabic chapter and verse, e.g. 22:17 or 22.17
# Build reusable verse-unit and list patterns.
# Accept open-ended ranges like "29-" or "29--" (to the end of the chapter)
# by making the second number optional when a hyphen/dash is present.
# Use no-newline whitespace around hyphens/commas to avoid bleeding across lines.
_VERSE_UNIT = rf"\d{{1,3}}(?:{_NO_NL_WS}*[-–]{{1,2}}(?:{_NO_NL_WS}*\d{{1,3}})?)?"
_VERSE_LIST = rf"{_VERSE_UNIT}(?:{_NO_NL_WS}*,{_NO_NL_WS}*{_VERSE_UNIT})*"

_arabic_re = rf"(?P<chap_a>\d{{1,3}}){_NO_NL_WS}*[:.]{_NO_NL_WS}*(?P<vers_a>{_VERSE_LIST})"
# Allow optional dot or colon after Roman chapter, e.g., xxii. 17 or xxii:17 or xxii 17
_roman_re = rf"(?P<chap_r>[ivxlcdm]+){_NO_NL_WS}*[:.]?{_NO_NL_WS}*(?:v(?:er\.)?{_NO_NL_WS}*)?(?P<vers_r>{_VERSE_LIST})"
_nochap_re = rf"(?P<vers_only>{_VERSE_LIST})"
# Chapter-only (no verses) after a book, used to carry forward book context in lists like
# "Ps 2; 16; 18:43; 69:7-9".
# Do not confuse with chapter:verse; the lookahead forbids ':' or '.'.
_chap_only_ar = rf"(?P<chap_only_a>\d{{1,3}})(?=(?:{_WS}|[);,\\.\"'“”‘’]|$))"
_chap_only_ro = rf"(?P<chap_only_r>[ivxlcdm]+)(?=(?:{_WS}|[);,\\.\"'“”‘’]|$))"

_PATTERN = rf"""
    (?<!\w)
    (?P<book>{_ord_re}{_book_re})\.?{_WS}*
    (?:{_arabic_re}|{_roman_re}|{_nochap_re}|{_chap_only_ar}|{_chap_only_ro})
    # Allow quotes or allowed punctuation to immediately follow
    (?=(?:{_WS}|[);:,.\"'“”‘’]|$))
"""

# Compile once for performance; allows scanning whole documents efficiently
_PATTERN_RE = re.compile(_PATTERN, re.IGNORECASE | re.VERBOSE)

# Precompile the continuation pattern at module scope.
# Enhancements:
# - Allow both comma and semicolon separators for continuations that start a new chapter
#   (either Arabic or Roman numerals), e.g. ", 4:5" or ", lxvii. 1".
# - Keep verse-only continuations (e.g. "; 5-7") restricted to semicolon to avoid
#   ambiguity with comma-separated verse lists inside a single reference (e.g. "John 3:16, 18").
_CONTINUATION_RE = re.compile(
    rf"^{_WS}*(?P<sep>[,;]){_WS}*"
    rf"(?:"
    rf"(?P<chap_a>\d{{1,3}}){_NO_NL_WS}*[:.]{_NO_NL_WS}*(?P<vers_a>{_VERSE_LIST})"
    rf"|(?P<chap_r>[ivxlcdm]+){_NO_NL_WS}*[:.]?{_NO_NL_WS}*(?P<vers_r>{_VERSE_LIST})"
    rf"|(?P<vers_only>{_VERSE_LIST})"
    rf")",
    re.IGNORECASE,
)


def find_scripture_references(text: str) -> List[Dict[str, Any]]:
    """Find scripture references in a given text.

    Returns a list of dicts: {text, book, chapter, verse, start, length}
    """
    references: List[Dict[str, Any]] = []

    scan_pos = 0
    n = len(text)
    while scan_pos < n:
        m = _PATTERN_RE.search(text, scan_pos)
        if not m:
            break

        full = m.group(0)
        # Strip leading whitespace using the broadened whitespace class
        lstripped = re.sub(rf"^{_WS}+", "", full)
        lead = len(full) - len(lstripped)
        book_raw = m.group("book")
        normalized = normalize_book_input(book_raw)
        book_id = sh.bibledict.get(normalized)

        # If this candidate doesn't map to a valid book, advance one character from
        # the match start so we can discover overlapping matches (e.g. after list markers like "o. ")
        if not book_id:
            scan_pos = m.start() + 1
            continue

        # Determine chapter/verses
        if m.group("chap_a") and m.group("vers_a"):
            try:
                chapter = int(m.group("chap_a"))
            except ValueError:
                scan_pos = m.start() + 1
                continue
            verses = m.group("vers_a")
        elif m.group("chap_r") and m.group("vers_r"):
            chap_rom = m.group("chap_r").upper()
            try:
                chapter = fromRoman(chap_rom)
            except (InvalidRomanNumeralError, ValueError):
                scan_pos = m.start() + 1
                continue
            verses = m.group("vers_r")
        elif m.group("chap_only_a") or m.group("chap_only_r"):
            # Chapter-only after a book: set context but do not emit a reference for the
            # chapter itself (consistent with semicolon chapter markers being ignored).
            # Guard against false positives from glued tokens like "ABDI" => "ABD" + "I" (Obadiah i)
            # and "OBAL" => "OBA" + "L" (Obadiah l).
            # Require at least one separator (space or similar whitespace)
            # between the book token and a Roman chapter-only.
            if m.group("chap_only_r"):
                # Compute the gap between the end of the book token and the start of the roman chapter
                gap_start = m.end("book")
                gap_end = m.start("chap_only_r")
                if gap_end <= gap_start:
                    # No separator at all: reject this match and advance
                    scan_pos = m.start() + 1
                    continue
            if m.group("chap_only_a"):
                try:
                    chapter = int(m.group("chap_only_a"))
                except ValueError:
                    scan_pos = m.start() + 1
                    continue
            else:
                chap_rom2 = m.group("chap_only_r").upper()
                try:
                    chapter = fromRoman(chap_rom2)
                except (InvalidRomanNumeralError, ValueError):
                    scan_pos = m.start() + 1
                    continue
            verses = ""
        elif m.group("vers_only"):
            vo = m.group("vers_only")
            if (book_id - 1) in sh.onechapterbooks:
                # In one-chapter books, a book plus vers-only is valid (chapter = 1)
                chapter = 1
                verses = vo
            else:
                # Keep the current regex order but reinterpret a simple number as chapter-only
                # when it immediately follows the book name (e.g. "Ps 2" sets chapter context).
                if re.fullmatch(r"\d{1,3}", vo or ""):
                    try:
                        chapter = int(vo)
                    except ValueError:
                        scan_pos = m.start() + 1
                        continue
                    verses = ""
                else:
                    # For multi-chapter books, non-numeric vers-only (like "5-7") after the book
                    # is not a valid top-level match; advance to allow overlaps.
                    scan_pos = m.start() + 1
                    continue
        else:
            scan_pos = m.start() + 1
            continue

        # Clean and trim verses using broadened whitespace class
        verses = re.sub(rf"^{_WS}+", "", verses)
        verses = re.sub(rf"(?:{_WS}|[)\];:.,\"'“”‘’])+$", "", verses)

        start = m.start() + lead
        length = len(lstripped)
        # Only emit references that include verses.
        # Chapter-only references are used to update the context for continuations but are not interactive.
        if verses:
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

        # Handle continuations inheriting the same book and possibly chapter.
        # Supports:
        # - Semicolon or comma followed by a new chapter (Arabic or Roman), e.g.,
        #   "Ps.
        #   xxxi. 16, lxvii. 1, cxix. 135" or "John 3:16; 4:5".
        # - Semicolon and verse-only for one-chapter continuation within the same book, e.g.
        #   "Jude 5; 7-9".
        #   Verse-only via comma is deliberately not supported to avoid
        #   colliding with comma-separated verse lists inside a single reference.
        # We scan forward from the end of this match for additional segments.
        tail_pos = m.end()
        last_chapter = chapter
        while tail_pos < n:
            tail = text[tail_pos:]
            m2 = _CONTINUATION_RE.match(tail)
            if not m2:
                break
            sep = m2.group("sep") or ""
            # Check for book-start lookahead to avoid consuming ordinals of new books
            # (e.g. "2Jo 1:9; 3Jo 1:11" should not take "3" as a verse/chapter of 2 John).
            is_chapter_only = False
            if m2.group("vers_only"):
                vo_raw = m2.group("vers_only")
                if re.fullmatch(r"\d{1,3}", vo_raw or ""):
                    after = tail[len(m2.group(0)) :]
                    after = re.sub(rf"^{_WS}+", "", after)
                    # Heuristic for the new book start: digit, uppercase letter, or ordinal suffix
                    if after and (
                        after[0].isdigit()
                        or after[0].isupper()
                        or re.match(r"(?:st|nd|rd|th)\b", after, re.I)
                    ):
                        break

                    # Special rule: after a full reference, a semicolon followed by a
                    # number alone (e.g. "; 4") indicates a chapter marker, not a
                    # standalone verse reference — but only for multi‑chapter books.
                    # For one‑chapter books (e.g. Jude), "; 7" must be treated as verses in chapter 1.
                    # Update the last_chapter and skip emitting a reference for this segment when applicable.
                    if sep == ";" and (book_id - 1) not in sh.onechapterbooks:
                        try:
                            last_chapter = int(vo_raw)
                            is_chapter_only = True
                        except ValueError:
                            pass
            
            seg_full = m2.group(0)
            seg_lstripped = seg_full.lstrip()
            seg_lead = len(seg_full) - len(seg_lstripped)
            start2 = tail_pos + seg_lead

            if m2.group("chap_a") and m2.group("vers_a"):
                try:
                    chapter2 = int(m2.group("chap_a"))
                except ValueError:
                    break
                verses2 = m2.group("vers_a")
                last_chapter = chapter2
            elif m2.group("chap_r") and m2.group("vers_r"):
                try:
                    chapter2 = fromRoman(m2.group("chap_r").upper())
                except (InvalidRomanNumeralError, ValueError):
                    break
                verses2 = m2.group("vers_r")
                last_chapter = chapter2
            elif is_chapter_only:
                verses2 = ""
            elif m2.group("vers_only"):
                # vers-only; reuse last_chapter.
                # Allow both comma and semicolon here; we already matched _CONTINUATION_RE,
                # which ensures one of them was present.
                # Comma is safe because _PATTERN_RE
                # already greedily matched on-line lists.
                verses2 = m2.group("vers_only")
            else:
                break

            verses2 = re.sub(rf"^{_WS}+", "", verses2)
            verses2 = re.sub(rf"(?:{_WS}|[)\];:.,\"'“”‘’])+$", "", verses2)

            if verses2:
                references.append(
                    {
                        "text": seg_lstripped,
                        "book": book_raw,
                        "chapter": last_chapter,
                        "verse": verses2,
                        "start": start2,
                        "length": len(seg_lstripped),
                    }
                )

            tail_pos += len(seg_full)

        # Continue the main scan after the end of this match and any continuations consumed
        scan_pos = tail_pos

    return references


def lookup_scripture(bible_data: Dict[str, Any], book: str, chapter: int, verses: str) -> str:
    """Look up verse text(s) from bible_data, returning a human-readable string.

    - Normalises book token
    - Supports verse lists and ranges, including en/em dashes
    - Returns a friendly message when a verse is not found
    """
    normalized_book = normalize_book_input(book)
    book_id = sh.bibledict.get(normalized_book)
    if not book_id:
        return "Scripture not found."

    full_book = CANONICAL_BOOKS.get(book_id, book)
    chapter_data = bible_data.get(full_book, {}).get(str(chapter), {})

    # Normalise dashes and whitespace
    verses = verses.replace("–", "-").replace("—", "-")

    # Determine the maximum verse available in this chapter (used for clamping)
    try:
        max_verse_in_chapter = max(int(k) for k in chapter_data.keys()) if chapter_data else 0
    except (ValueError, TypeError):
        max_verse_in_chapter = 0

    verse_numbers: List[int] = []
    for raw_part in verses.split(','):
        part = raw_part.strip().replace("–", "-").replace("—", "-")
        # Collapse multiple hyphens to a single hyphen so "29--" becomes "29-"
        part = re.sub(r"-{2,}", "-", part)

        if '-' in part:
            start_s, end_s = part.split('-', 1)
            try:
                start_i = int(start_s.strip())
            except (ValueError, TypeError):
                return "Scripture not found."

            end_s = (end_s or "").strip()
            if end_s == "":
                # Dangling hyphen with no numeric end: treat as a single verse.
                # Discard the hyphen semantics and use only the start verse.
                end_i = start_i
            else:
                try:
                    end_i = int(end_s)
                except (ValueError, TypeError):
                    return "Scripture not found."

            # Clamp end within known chapter bounds if available
            if max_verse_in_chapter:
                end_i = min(end_i, max_verse_in_chapter)

            if start_i <= end_i:
                verse_numbers.extend(range(start_i, end_i + 1))
            else:
                # Descending ranges are rare; preserve previous behaviour
                verse_numbers.extend(range(start_i, end_i - 1, -1))
        else:
            try:
                verse_numbers.append(int(part))
            except (ValueError, TypeError):
                return "Scripture not found."

    results: List[str] = []
    for ve in verse_numbers:
        verse_text = chapter_data.get(str(ve))
        if verse_text is None:
            results.append(f"Verse {ve} not found.")
        else:
            results.append(str(ve) + " " + verse_text)
    return "\n".join(results)
