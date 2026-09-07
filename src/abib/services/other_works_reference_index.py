# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-
from __future__ import annotations

import gzip
import hashlib
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from abib.core import scripture
from abib.core import shared as sh

ReferenceKey = tuple[int, int | None, int]


@dataclass(frozen=True)
class OtherWorkReferenceOccurrence:
    work_stem: str
    work_path: str
    reference_key: ReferenceKey
    reference_label: str
    matched_text: str
    abs_start: int
    length: int
    snippet: str


@dataclass(frozen=True)
class OtherWorkReferenceGroup:
    reference_label: str
    occurrences: tuple[OtherWorkReferenceOccurrence, ...]


def normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n")


def compute_sha256_utf8(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def reference_key(book: Any, chapter: Any, verse: Any) -> ReferenceKey | None:
    normalized_book = scripture.normalize_book_input(str(book or ""))
    book_id = sh.bibledict.get(normalized_book)
    if not book_id:
        return None
    try:
        chapter_number = int(chapter) if chapter not in (None, "") else None
        first_verse = _first_verse_number(str(verse or ""))
    except (TypeError, ValueError):
        return None
    if first_verse <= 0:
        return None
    return book_id, chapter_number, first_verse


def reference_label_from_key(key: ReferenceKey) -> str:
    book_id, chapter, verse = key
    book_name = scripture.CANONICAL_BOOKS.get(book_id, str(book_id))
    if chapter is None or (book_id - 1) in sh.onechapterbooks:
        return f"{book_name} {verse}"
    return f"{book_name} {chapter}:{verse}"


class OtherWorksReferenceIndex:
    """Build and query a scripture-reference index for enabled Other Works."""

    def __init__(
            self,
            other_works_map: dict[str, str],
            show_work_settings: dict[str, bool] | None = None,
            companions_dir: str | Path | None = None) -> None:
        self._other_works_map = dict(other_works_map)
        self._show_work_settings = show_work_settings or {}
        self._companions_dir = Path(companions_dir) if companions_dir is not None else Path(sh.str_cwd) / "Other Works companions"
        self._index: dict[ReferenceKey, list[OtherWorkReferenceOccurrence]] | None = None

    def rebuild(self) -> None:
        self._index = None

    def lookup(self, reference: str) -> OtherWorkReferenceGroup | None:
        key = self.key_for_reference(reference)
        if key is None:
            return None
        self._ensure_index()
        assert self._index is not None
        occurrences = tuple(sorted(self._index.get(key, ()), key=lambda occ: (occ.work_stem.casefold(), occ.abs_start)))
        if not occurrences:
            return None
        return OtherWorkReferenceGroup(reference_label_from_key(key), occurrences)

    @staticmethod
    def key_for_reference(reference: str) -> ReferenceKey | None:
        refs = scripture.find_scripture_references(reference)
        if not refs:
            return None
        first = refs[0]
        return reference_key(first.get("book"), first.get("chapter"), first.get("verse"))

    def _ensure_index(self) -> None:
        if self._index is not None:
            return

        by_key: dict[ReferenceKey, list[OtherWorkReferenceOccurrence]] = defaultdict(list)
        for work_stem, work_path in self._enabled_works():
            text_path = Path(work_path)
            try:
                content = normalize_text(text_path.read_text(encoding="utf-8", errors="replace"))
            except (OSError, UnicodeError, ValueError):
                continue
            refs = self._load_companion_refs(text_path, content)
            if refs is None:
                refs = scripture.find_scripture_references(content)
            for ref in refs:
                occurrence = self._occurrence_from_ref(work_stem, text_path, content, ref)
                if occurrence is not None:
                    by_key[occurrence.reference_key].append(occurrence)
        self._index = dict(by_key)

    def _enabled_works(self) -> tuple[tuple[str, str], ...]:
        works: list[tuple[str, str]] = []
        for work_stem, work_path in self._other_works_map.items():
            visible = self._show_work_settings.get(work_stem, True)
            if self._show_work_settings and str(visible).lower() == "false":
                continue
            works.append((work_stem, work_path))
        return tuple(sorted(works, key=lambda item: item[0].casefold()))

    def _load_companion_refs(self, text_path: Path, content: str) -> list[dict[str, Any]] | None:
        content_hash = compute_sha256_utf8(content)
        for path in self._companion_candidates(text_path):
            data = _load_json(path)
            if data is None:
                continue
            try:
                if int(data.get("format", 0)) != 1:
                    continue
                if data.get("content_sha256") != content_hash:
                    continue
                refs = data.get("refs")
            except (AttributeError, TypeError, ValueError):
                continue
            if isinstance(refs, list):
                return refs
        return None

    def _companion_candidates(self, text_path: Path) -> tuple[Path, ...]:
        base_name = text_path.name
        return (
            text_path.parent / f"{base_name}.refs.json.gz",
            text_path.parent / f"{base_name}.refs.json",
            self._companions_dir / f"{base_name}.refs.json.gz",
            self._companions_dir / f"{base_name}.refs.json",
        )

    @staticmethod
    def _occurrence_from_ref(
            work_stem: str,
            text_path: Path,
            content: str,
            ref: dict[str, Any]) -> OtherWorkReferenceOccurrence | None:
        key = reference_key(ref.get("book"), ref.get("chapter"), ref.get("verse"))
        if key is None:
            return None
        try:
            abs_start = int(ref.get("abs_start", ref.get("start", 0)) or 0)
            length = int(ref.get("length", 0) or 0)
        except (TypeError, ValueError, AttributeError):
            return None
        if abs_start < 0 or length <= 0:
            return None
        matched_text = str(ref.get("text", ""))
        return OtherWorkReferenceOccurrence(
            work_stem=work_stem,
            work_path=str(text_path),
            reference_key=key,
            reference_label=reference_label_from_key(key),
            matched_text=matched_text,
            abs_start=abs_start,
            length=length,
            snippet=_make_snippet(content, abs_start, length),
        )


def _first_verse_number(verse: str) -> int:
    match = re.search(r"\d+", verse.replace("–", "-").replace("—", "-"))
    if not match:
        return 0
    return int(match.group(0))


def _make_snippet(content: str, abs_start: int, length: int, radius: int = 55) -> str:
    start = max(0, abs_start - radius)
    end = min(len(content), abs_start + length + radius)
    snippet = re.sub(r"\s+", " ", content[start:end]).strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(content):
        snippet += "…"
    return snippet


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        if not path.exists():
            return None
        if str(path).lower().endswith(".gz"):
            with gzip.open(path, "rt", encoding="utf-8") as f:
                data = json.load(f)
        else:
            with path.open("r", encoding="utf-8") as f:
                data = json.load(f)
    except (OSError, gzip.BadGzipFile, UnicodeError, json.JSONDecodeError, ValueError):
        return None
    return data if isinstance(data, dict) else None