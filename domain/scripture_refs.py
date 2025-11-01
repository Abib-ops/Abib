from __future__ import annotations

from typing import Tuple, Optional

from roman import fromRoman

import fcs
import shared as sh


def resolve_reference(bits: list) -> tuple[Optional[int], Optional[int], Optional[int]]:
    """Resolve the book, chapter, and verse using fcs.isRoman.

    Returns a tuple (book_number, chapter, verse) where each element may be
    None if it cannot be resolved.
    - bits[0]: book name (string)
    - bits[1]: chapter (roman or int, optional)
    - bits[2]: verse (roman or int, optional)
    """
    # Step 1: Resolve the book name
    book_number = sh.bibledict.get(bits[0].lower(), None)
    if not book_number:
        return None, None, None

    # Step 2: Resolve chapter (bits[1])
    chapter: Optional[int] = 1
    if len(bits) > 1 and bits[1] not in (None, ""):
        if fcs.isRoman(bits[1]):
            try:
                chapter = int(fromRoman(bits[1].upper()))
            except Exception:
                return book_number, None, None
        else:
            try:
                chapter = int(bits[1])
            except ValueError:
                return book_number, None, None

    # Step 3: Resolve verse (bits[2])
    verse: Optional[int] = 1
    if len(bits) > 2 and bits[2] not in (None, ""):
        if fcs.isRoman(bits[2]):
            try:
                verse = int(fromRoman(bits[2].upper()))
            except Exception:
                return book_number, chapter, None
        else:
            try:
                verse = int(bits[2])
            except ValueError:
                return book_number, chapter, None

    return book_number, chapter, verse


def calculate_book_line(book: int, chapter: int, verse: int, current_line_num: int) -> int:
    """Calculate and return a specific line index from sh.Info.

    book, chapter, verse are 1-based values; will be converted to 0-based for lookup.
    Raises ValueError for invalid inputs or out-of-range.
    """
    # Subtract 1 from the book, chapter, and verse for a zero-based sh.Info index.
    book_id = int(book) - 1
    chapter_idx = int(chapter) - 1
    verse_idx = int(verse) - 1

    if book_id < 0 or chapter_idx < 0 or verse_idx < 0:
        raise ValueError("Invalid chapter or verse range.")

    try:
        return sh.Info.index([book_id, chapter_idx, verse_idx])
    except (ValueError, IndexError) as exc:
        raise ValueError("Invalid book, chapter, or verse.") from exc
