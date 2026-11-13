# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Look up Gill and Matthew Henry commentary for a Bible reference."""

import html
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from abib.services.mhcc_index import MhccIndex, MhccPassage
from abib.services.other_works_reference_index import ReferenceKey


@dataclass(frozen=True)
class CommentaryEntry:
    work_stem: str
    source: Literal["gill", "mhcc"]
    label: str
    snippet: str
    book: int
    chapter: int
    verse: int
    work_path: str | None = None
    abs_start: int | None = None
    length: int | None = None


def _plain_snippet(value: str, limit: int = 240) -> str:
    text = html.unescape(re.sub(r"<[^>]*>", " ", value))
    text = " ".join(text.split())
    if len(text) > limit:
        return text[:limit].rstrip() + "…"
    return text


def _mhcc_snippet(text: str, passage: MhccPassage, limit: int = 240) -> str:
    following = text[passage.start + passage.length:].lstrip("\r\n \t")
    if passage.kind == "chapter":
        next_section = re.search(r"(?m)^Verses?\s+\d", following)
        if next_section is not None:
            following = following[:next_section.start()]
        return _plain_snippet(following, limit)
    paragraph = re.split(r"\n\s*\n", following, maxsplit=1)[0]
    return _plain_snippet(paragraph, limit)


class CommentaryLookup:
    """Find available Gill and MHCC commentary for a one-based reference key."""

    def __init__(self, other_works_map: dict[str, str], gill_db_path: str | Path) -> None:
        self._other_works_map = dict(other_works_map)
        self._gill_db_path = Path(gill_db_path)
        self._mhcc_text_cache: dict[tuple[str, int, int], str] = {}

    def lookup(self, key: ReferenceKey) -> tuple[CommentaryEntry, ...]:
        book, chapter, verse = key
        if book < 1 or (chapter is not None and chapter < 1) or verse < 1:
            return ()
        chapter_number = chapter or 1
        entries: list[CommentaryEntry] = []

        gill_snippet = self._lookup_gill(book, chapter_number, verse)
        if gill_snippet is not None:
            entries.append(
                CommentaryEntry(
                    "Gill", "gill", "Gill", gill_snippet, book, chapter_number, verse,
                )
            )

        mhcc_path = self._find_mhcc_path()
        if mhcc_path is not None:
            try:
                passage = MhccIndex(mhcc_path).lookup(book, chapter_number, verse)
                if passage is not None:
                    text = self._read_mhcc_text(mhcc_path)
                    label = "Matthew Henry"
                    if passage.kind != "section":
                        label = f"{label} — {passage.label}"
                    entries.append(
                        CommentaryEntry(
                            "MHCC",
                            "mhcc",
                            label,
                            _mhcc_snippet(text, passage),
                            book,
                            chapter_number,
                            verse,
                            str(mhcc_path),
                            passage.start,
                            passage.length,
                        )
                    )
            except (OSError, UnicodeError, ValueError):
                return tuple(entries)
        return tuple(entries)

    def _lookup_gill(self, book: int, chapter: int, verse: int) -> str | None:
        if not self._gill_db_path.is_file():
            return None
        try:
            with sqlite3.connect(str(self._gill_db_path)) as connection:
                row = connection.execute(
                    "SELECT data FROM commentary "
                    "WHERE book = ? AND chapter = ? AND fromverse = ? LIMIT 1",
                    (book, chapter, verse),
                ).fetchone()
                if row is None:
                    row = connection.execute(
                        "SELECT data FROM commentary "
                        "WHERE book = ? AND chapter = ? AND fromverse <= ? "
                        "AND COALESCE(toverse, fromverse) >= ? "
                        "ORDER BY (COALESCE(toverse, fromverse) - fromverse) ASC LIMIT 1",
                        (book, chapter, verse, verse),
                    ).fetchone()
        except sqlite3.Error:
            return None
        if row is None or row[0] is None:
            return None
        return _plain_snippet(str(row[0]))

    def _find_mhcc_path(self) -> Path | None:
        for stem, value in self._other_works_map.items():
            if stem.casefold() == "mhcc":
                path = Path(value)
                if path.is_file():
                    return path
        return None

    def _read_mhcc_text(self, path: Path) -> str:
        resolved = path.resolve()
        stat = resolved.stat()
        cache_key = (str(resolved), stat.st_mtime_ns, stat.st_size)
        text = self._mhcc_text_cache.get(cache_key)
        if text is None:
            text = resolved.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
            self._mhcc_text_cache = {cache_key: text}
        return text