# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Utilities for parsing and resolving scripture references.

Indexing contract (prominent):
- All public inputs and outputs in this module are 1-based for (book, chapter, verse).
  - resolve_reference(...) returns (book, chapter, verse) as 1-based integers when available.
  - calculate_book_line(book, chapter, verse, ...) expects 1-based integers.
- Internally, these values are converted to 0-based indices only for looking up into `shared.Info`,
  which stores triples as [book_id, chapter_idx, verse_idx] with 0-based indexing.

Examples
- resolve_reference(["Genesis", "1", "1"]) -> (1, 1, 1)
- calculate_book_line(1, 1, 1, _) -> index of [0, 0, 0] in `shared.Info`

Notes
- Book-name matching relies on `shared.bibledict`; see that mapping for accepted names.
- Chapter/verse text may be Arabic numerals or valid Roman numerals (e.g. "iv", "XII").
"""
from __future__ import annotations

from typing import Optional, Sequence, Union, Dict, NamedTuple

from roman import fromRoman, InvalidRomanNumeralError

import fcs
import shared as sh

# Typing aliases for clearer contracts
Bits = Sequence[Union[str, int, None]]

class RefParts(NamedTuple):
    """Named tuple representing a resolved scripture reference.

    Attributes
    - book: Optional numeric book id (1-based), or None if unresolved
    - chapter: Optional chapter number (1-based), or None if unresolved
    - verse: Optional verse number (1-based), or None if unresolved
    """
    book: Optional[int]
    chapter: Optional[int]
    verse: Optional[int]


def _norm_str(x) -> Optional[str]:
    """Normalise an input to a stripped string or None.

    - None -> None
    - int/float -> str(value)
    - str -> stripped string or None if empty after the strip
    - other types -> None
    """
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return str(x)
    if isinstance(x, str):
        s = x.strip()
        return s if s != "" else None
    return None


def _parse_component(val: object) -> Optional[int]:
    """Parse a chapter/verse component which may be roman, int-like, or None.

    Returns an int on success, or None if invalid/unset.
    """
    s = _norm_str(val)
    if s is None:
        return None
    if fcs.isRoman(s):
        try:
            return int(fromRoman(s.upper()))
        except (InvalidRomanNumeralError, ValueError, TypeError):
            return None
    try:
        return int(s)
    except (ValueError, TypeError):
        return None


def _parse_verse_component(val: object) -> Optional[int]:
    """Parse a verse component that may include ranges/lists.

    Accepts inputs like:
    - "29" -> 29
    - "29-30" -> 29 (start of range)
    - "29-" or "29--" -> 29 (open-ended range)
    - "29-31,33-35" -> 29 (first unit in a list)
    - Roman numerals are also accepted for the first token (e.g. "xv--" -> 15).

    Returns an int on success, or None if invalid/unset.
    """
    s = _norm_str(val)
    if s is None:
        return None
    # Consider only the first unit before a comma/semicolon
    import re as _re
    first_unit = _re.split(r"[,;]", s, maxsplit=1)[0]
    first_unit = first_unit.strip()
    # Extract a leading Roman numeral or arabic number from the unit
    m = _re.match(r"^(?P<roman>[ivxlcdm]+)|^(?P<num>\d+)", first_unit, flags=_re.IGNORECASE)
    if not m:
        return None
    roman = m.group("roman")
    num = m.group("num")
    if roman:
        try:
            return int(fromRoman(roman.upper()))
        except (InvalidRomanNumeralError, ValueError, TypeError):
            return None
    try:
        return int(num)
    except (ValueError, TypeError):
        return None


def resolve_reference(bits: Bits) -> RefParts:
    """Resolve the (book, chapter, verse) from a user-supplied sequence of parts.

    All numbers in the public API are 1-based.

    Contract
    - bits is a finite sequence where:
      - bits[0]: required book name (str); matching is done against sh.bibledict using lowercased text.
      - bits[1]: optional chapter; may be an int, int-like string, or a Roman numeral string (e.g. "iv", "XII").
      - bits[2]: optional verse; same accepted forms as chapter.
    - Whitespace in string parts is stripped prior to processing.
    Empty strings are treated as missing (None).

    Returns
    - A 3-tuple: (book_number, chapter, verse).
    Each item may be None if that part cannot be resolved.
      - If the book cannot be resolved, returns (None, None, None).
      - If chapter text is invalid (present but unparsable), returns (book_number, None, None).
      - If verse text is invalid (present but unparsable), returns (book_number, chapter, None).
      - If chapter/verse are omitted entirely, they default to 1.

    Notes
    - This function is strict about book-name keys; it does not perform case-insensitive corrections beyond
      the lowercasing for lookup and does not rename keys.
    """
    # Step 1: Resolve the book name (normalise once)
    book_raw = _norm_str(bits[0]) if bits else None
    if not book_raw:
        return RefParts(None, None, None)
    try:
        book_number = sh.bibledict.get(book_raw.lower(), None)
    except (AttributeError, TypeError):
        return RefParts(None, None, None)
    if not book_number:
        return RefParts(None, None, None)

    # Step 2: Resolve chapter (bits[1])
    chapter: Optional[int] = 1
    if len(bits) > 1:
        parsed_ch = _parse_component(bits[1])
        if parsed_ch is None:
            return RefParts(book_number, None, None)
        chapter = parsed_ch

    # Step 3: Resolve verse (bits[2])
    verse: Optional[int] = 1
    if len(bits) > 2:
        # Verses can be lists/ranges (e.g. "29--", "29-31,33");
        # for navigation we use the first verse number present.
        parsed_vs = _parse_verse_component(bits[2])
        if parsed_vs is None:
            return RefParts(book_number, chapter, None)
        verse = parsed_vs

    return RefParts(book_number, chapter, verse)


# --- Fast lookup helpers for calculate_book_line ---
from functools import lru_cache

@lru_cache(maxsize=1)
def _build_info_map() -> Dict[tuple[int, int, int], int]:
    """Build a map from (book_id, chapter_idx, verse_idx) to absolute line.

    sh.Info stores zero-based triples [book_id, chapter_idx, verse_idx] in order.
    This converts it into an O(1) lookup dict.
    Cached once for the process.
    """
    # Guard against malformed Info content without masking unrelated issues
    try:
        return { (int(b), int(c), int(v)) : idx for idx, (b, c, v) in enumerate(sh.Info) }
    except (TypeError, ValueError) as exc:
        # If Info contains unexpected shapes, re-raise with context
        raise ValueError("shared.Info is not iterable over 3-item numeric sequences") from exc


@lru_cache(maxsize=10_000)
def _lookup_line(book_id: int, chapter_idx: int, verse_idx: int) -> int:
    """Return absolute line index for a 'zero-based' (book_id, chapter_idx, verse_idx)."""
    return _build_info_map()[(book_id, chapter_idx, verse_idx)]


def calculate_book_line(book: int, chapter: int, verse: int, _current_line_num: int) -> int:
    """Return the absolute 0-based line index in `sh.Info` for a reference.

    Parameters
    - book: 1-based book number (int)
    - chapter: 1-based chapter number (int)
    - verse: 1-based verse number (int)
    - _current_line_num: Unused.
      Kept for compatibility with existing call sites.
      This parameter may be removed in a future clean-up.

    Returns
    - The index (int) into `sh.Info` corresponding to the (book, chapter, verse).

    Raises
    - ValueError: if any of the inputs are invalid (noninteger or < 1), or if the
      triplet does not exist in `sh.Info`.

    Notes
    - Inputs are 1-based and are converted internally to 0-based before lookup.
    - The function intentionally does not use `_current_line_num`.
    It is present
      only to preserve the public signature during migration.
    """
    # Explicitly mark unused parameter to satisfy linters and convey intent.
    _ = _current_line_num  # unused; kept for API compatibility  # noqa: F841, ARG002
    # Convert inputs and guard against bad types/values with clear errors.
    try:
        book_id = int(book) - 1
        chapter_idx = int(chapter) - 1
        verse_idx = int(verse) - 1
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Book/chapter/verse must be integers (got book={book!r}, chapter={chapter!r}, verse={verse!r})"
        ) from exc

    # Validate 1-based contract (>= 1 before conversion)
    if book_id < 0 or chapter_idx < 0 or verse_idx < 0:
        raise ValueError(
            f"Values must be >= 1 (got book={book}, chapter={chapter}, verse={verse})"
        )

    # Lookup in Info; rethrow with explicit context if not found
    try:
        return _lookup_line(book_id, chapter_idx, verse_idx)
    except KeyError as exc:
        raise ValueError(
            f"Invalid book/chapter/verse (no match in Info) — book={book}, chapter={chapter}, verse={verse}"
        ) from exc
    except (ValueError, IndexError, TypeError) as exc:
        raise ValueError(
            f"Invalid book/chapter/verse (no match in Info) — book={book}, chapter={chapter}, verse={verse}"
        ) from exc
