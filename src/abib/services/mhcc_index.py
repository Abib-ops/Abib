# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Build and query a structural index for Matthew Henry's Concise Commentary."""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from abib.core import shared as sh

BOOK_RULE_RE = re.compile(r"^\s*_{10,}\s*$")
CHAPTER_RE = re.compile(r"^Chapter\s+(\d+)\s*$", re.IGNORECASE)
SECTION_RE = re.compile(r"^Verses?\s+([\d\s,–—-]+)\s*$", re.IGNORECASE)
VERSE_TOKEN_RE = re.compile(r"(\d+)(?:\s*[-–—]\s*(\d+))?")


@dataclass(frozen=True)
class MhccPassage:
    start: int
    length: int
    label: str
    kind: Literal["section", "chapter", "book"]


@dataclass(frozen=True)
class _Section:
    ranges: tuple[tuple[int, int], ...]
    passage: MhccPassage


@dataclass
class _Chapter:
    passage: MhccPassage
    sections: list[_Section] = field(default_factory=list)
    implicit: bool = False


@dataclass
class _Book:
    passage: MhccPassage
    chapters: dict[int, _Chapter] = field(default_factory=dict)


_INDEX_CACHE: dict[tuple[str, int, int], dict[int, _Book]] = {}
_CHAPTER_COUNTS: dict[int, int] | None = None


def _normalise_book_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.casefold())


def _known_chapter_counts() -> dict[int, int]:
    global _CHAPTER_COUNTS
    if _CHAPTER_COUNTS is None:
        counts: dict[int, int] = {}
        for entry in sh.Info:
            if len(entry) >= 2:
                book_number = int(entry[0]) + 1
                chapter_number = int(entry[1]) + 1
                counts[book_number] = max(counts.get(book_number, 0), chapter_number)
        _CHAPTER_COUNTS = counts
    return _CHAPTER_COUNTS


def parse_section_label(label: str) -> tuple[tuple[int, int], ...] | None:
    """Parse a ``Verse 3`` / ``Verses 1-5`` / ``Verses 1, 2`` heading into verse ranges."""
    match = SECTION_RE.fullmatch(label)
    if match is None:
        return None
    ranges: list[tuple[int, int]] = []
    for token in re.split(r"\s*,\s*", match.group(1).strip()):
        token_match = VERSE_TOKEN_RE.fullmatch(token.strip())
        if token_match is None:
            return None
        first = int(token_match.group(1))
        last = int(token_match.group(2) or first)
        if first > last:
            first, last = last, first
        ranges.append((first, last))
    return tuple(ranges) if ranges else None


def find_book_titles(lines: list[str]) -> dict[int, tuple[int, str]]:
    """Find recognized book-title lines following MHCC separator rules."""
    from abib.core.scripture import CANONICAL_BOOKS

    aliases = {_normalise_book_title(key): value for key, value in sh.bibledict.items()}
    title_rows: dict[int, tuple[int, str]] = {}
    for index, line in enumerate(lines):
        if not BOOK_RULE_RE.fullmatch(line.rstrip("\r\n")):
            continue
        title_index = index + 1
        while title_index < len(lines) and not lines[title_index].strip():
            title_index += 1
        if title_index >= len(lines):
            continue
        title = lines[title_index].strip()
        book_number = aliases.get(_normalise_book_title(title))
        if book_number is not None and book_number in CANONICAL_BOOKS:
            title_rows[title_index] = (book_number, title)
    return title_rows


def parse_chapter_heading(label: str) -> int | None:
    """Return the chapter number from a ``Chapter N`` heading, if present."""
    match = CHAPTER_RE.fullmatch(label)
    return int(match.group(1)) if match is not None else None


def _parse_text(text: str) -> dict[int, _Book]:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.splitlines(keepends=True)
    title_rows = find_book_titles(lines)

    books: dict[int, _Book] = {}
    current_book: _Book | None = None
    current_chapter: _Chapter | None = None
    offset = 0
    for index, line in enumerate(lines):
        clean_line = line.rstrip("\r\n")
        title_info = title_rows.get(index)
        if title_info is not None:
            book_number, title = title_info
            passage = MhccPassage(offset, len(clean_line), title, "book")
            current_book = _Book(passage)
            books[book_number] = current_book
            current_chapter = None
            offset += len(line)
            continue

        if current_book is not None:
            label = clean_line.strip()
            chapter_number = parse_chapter_heading(label)
            if chapter_number is not None:
                passage = MhccPassage(offset, len(clean_line), label, "chapter")
                chapter = current_book.chapters.get(chapter_number)
                if chapter is None:
                    chapter = _Chapter(passage)
                    current_book.chapters[chapter_number] = chapter
                else:
                    chapter.passage = passage
                    chapter.implicit = False
                current_chapter = chapter
            else:
                ranges = parse_section_label(label)
                if ranges is not None:
                    passage = MhccPassage(offset, len(clean_line), label, "section")
                    if current_chapter is None:
                        current_chapter = current_book.chapters.get(1)
                        if current_chapter is None:
                            implicit_passage = MhccPassage(offset, len(clean_line), "Chapter 1", "chapter")
                            current_chapter = _Chapter(implicit_passage, implicit=True)
                            current_book.chapters[1] = current_chapter
                    current_chapter.sections.append(_Section(ranges, passage))
        offset += len(line)
    return books


class MhccIndex:
    """Find the section (or nearest chapter/book heading) for a Bible verse."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)

    def lookup(self, book_number: int, chapter: int, verse: int) -> MhccPassage | None:
        """Return the best MHCC passage for a one-based Bible reference."""
        if book_number < 1 or chapter < 1 or verse < 1:
            return None
        if chapter > _known_chapter_counts().get(book_number, 0):
            return None

        books = self._load_index()
        book = books.get(book_number)
        if book is None:
            return None
        chapter_data = book.chapters.get(chapter)
        if chapter_data is None:
            return book.passage if chapter == 1 else None

        for section in chapter_data.sections:
            if any(start <= verse <= end for start, end in section.ranges):
                return section.passage
        return chapter_data.passage

    def _load_index(self) -> dict[int, _Book]:
        path = self.path.resolve()
        stat = path.stat()
        cache_key = (str(path), stat.st_mtime_ns, stat.st_size)
        cached = _INDEX_CACHE.get(cache_key)
        if cached is not None:
            return cached

        text = path.read_text(encoding="utf-8")
        parsed = _parse_text(text)
        for old_key in [key for key in _INDEX_CACHE if key[0] == str(path)]:
            del _INDEX_CACHE[old_key]
        _INDEX_CACHE[cache_key] = parsed
        return parsed