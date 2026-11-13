# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


import re
import unicodedata
from collections.abc import Iterable, Sequence

from abib.core.scripture import CANONICAL_BOOKS


def clean_verse_text(text: str, *, strip_verse_number: bool = True) -> str:
    """Remove display-only verse markers and normalize KJV italic letters."""
    if strip_verse_number:
        text = re.sub(r"^\s*(?:¶\s*)?\d+\s+", "", text)
        text = re.sub(r"^\s*¶\s*", "", text)
    text = re.sub(r"¶\s*", "", text)

    text = "".join(
        "h" if character == "\u210e" else
        unicodedata.normalize("NFKD", character)
        if "MATHEMATICAL" in unicodedata.name(character, "") else character
        for character in text
    )
    return re.sub(r"\s+", " ", text).strip()


def format_reference_range(
        first: int,
        last: int,
        info: Sequence[Sequence[int]],
        one_chapter_books: Iterable[int]) -> str:
    """Format the inclusive scripture range between two verse positions."""
    if first < 0 or last < first:
        raise ValueError("Invalid verse position range")

    first_info = info[first]
    last_info = info[last]
    first_book, first_chapter, first_verse = (
        int(first_info[0]), int(first_info[1]) + 1, int(first_info[2]) + 1
    )
    last_book, last_chapter, last_verse = (
        int(last_info[0]), int(last_info[1]) + 1, int(last_info[2]) + 1
    )
    one_chapter_set = set(one_chapter_books)

    def book_name(book_index: int) -> str:
        name = CANONICAL_BOOKS.get(book_index + 1, str(book_index + 1))
        return "Psalm" if name == "Psalms" else name

    def reference(book_index: int, chapter: int, verse: int) -> str:
        name = book_name(book_index)
        if book_index in one_chapter_set:
            return f"{name} {verse}"
        return f"{name} {chapter}:{verse}"

    start = reference(first_book, first_chapter, first_verse)
    if first_book != last_book:
        return f"{start}-{reference(last_book, last_chapter, last_verse)}"
    if first_chapter == last_chapter:
        if first_verse == last_verse:
            return start
        if first_book in one_chapter_set:
            return f"{book_name(first_book)} {first_verse}-{last_verse}"
        return f"{book_name(first_book)} {first_chapter}:{first_verse}-{last_verse}"
    return f"{start}-{last_chapter}:{last_verse}"


def format_citation(text: str, reference: str) -> str:
    """Format verse text as a quoted citation with its scripture reference."""
    return f'"{text}" ({reference})'