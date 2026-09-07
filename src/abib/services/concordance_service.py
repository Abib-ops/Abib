# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from abib.ui.search_results import format_reference, result_verse_text

DEFAULT_STOP_WORDS = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any",
    "are", "as", "at", "be", "because", "been", "before", "being", "below", "between", "both",
    "but", "by", "can", "did", "do", "does", "doing", "down", "during", "each", "few", "for",
    "from", "further", "had", "has", "have", "having", "he", "her", "here", "hers", "herself",
    "him", "himself", "his", "how", "i", "if", "in", "into", "is", "it", "its", "itself", "me",
    "more", "most", "my", "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or",
    "other", "our", "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so",
    "some", "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "we", "were", "what", "when", "where", "which", "while", "who", "whom", "why",
    "will", "with", "you", "your", "yours", "yourself", "yourselves",
})

TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)?")


@dataclass(frozen=True)
class ConcordanceHit:
    position: int
    reference: str
    verse_text: str


@dataclass(frozen=True)
class ConcordanceEntry:
    term: str
    count: int
    hits: tuple[ConcordanceHit, ...]


def normalize_term(term: str) -> str:
    """Return the concordance key for a word or phrase."""
    return " ".join(match.group(0).casefold() for match in TOKEN_RE.finditer(term))


class ConcordanceService:
    """Build and query a Bible-only concordance from loaded Scripture data."""

    def __init__(
            self,
            kjv: Sequence[str],
            amap: Sequence[int | str],
            info: Sequence[Sequence[int]],
            book_names: Sequence[str],
            one_chapter_books: Iterable[int],
            stop_words: Iterable[str] = DEFAULT_STOP_WORDS) -> None:
        self._kjv = kjv
        self._amap = amap
        self._info = info
        self._book_names = book_names
        self._one_chapter_books = set(one_chapter_books)
        self._stop_words = {normalize_term(word) for word in stop_words if normalize_term(word)}
        self._entries: dict[str, ConcordanceEntry] | None = None

    def entries(self) -> tuple[ConcordanceEntry, ...]:
        """Return all concordance entries alphabetically."""
        self._ensure_index()
        assert self._entries is not None
        return tuple(self._entries[term] for term in sorted(self._entries))

    def get_entry(self, term: str) -> ConcordanceEntry | None:
        """Return a built word entry or an on-demand phrase entry."""
        normalized = normalize_term(term)
        if not normalized:
            return None
        if " " in normalized:
            return self.lookup_phrase(normalized)
        self._ensure_index()
        assert self._entries is not None
        return self._entries.get(normalized)

    def lookup_phrase(self, phrase: str) -> ConcordanceEntry | None:
        """Find verses containing a case-folded whole-word phrase."""
        normalized = normalize_term(phrase)
        if not normalized:
            return None

        pattern_text = r"\b" + r"\s+".join(re.escape(part) for part in normalized.split()) + r"\b"
        pattern = re.compile(pattern_text, re.IGNORECASE)
        hits: list[ConcordanceHit] = []
        for position in range(len(self._amap)):
            try:
                verse_text = result_verse_text(position, self._kjv, self._amap)
            except (IndexError, TypeError, ValueError):
                continue
            for _match in pattern.finditer(verse_text):
                hits.append(self._make_hit(position, verse_text))
        if not hits:
            return None
        return ConcordanceEntry(normalized, len(hits), tuple(hits))

    def matching_entries(self, filter_text: str = "") -> tuple[ConcordanceEntry, ...]:
        """Return entries whose term contains the case-folded filter text."""
        normalized = normalize_term(filter_text)
        entries = self.entries()
        if not normalized:
            return entries
        return tuple(entry for entry in entries if normalized in entry.term)

    def _ensure_index(self) -> None:
        if self._entries is not None:
            return

        hits_by_term: dict[str, list[ConcordanceHit]] = defaultdict(list)
        for position in range(len(self._amap)):
            try:
                verse_text = result_verse_text(position, self._kjv, self._amap)
            except (IndexError, TypeError, ValueError):
                continue
            hit = self._make_hit(position, verse_text)
            for match in TOKEN_RE.finditer(verse_text):
                term = match.group(0).casefold()
                if term in self._stop_words:
                    continue
                hits_by_term[term].append(hit)

        self._entries = {
            term: ConcordanceEntry(term, len(hits), tuple(hits))
            for term, hits in hits_by_term.items()
        }

    def _make_hit(self, position: int, verse_text: str) -> ConcordanceHit:
        reference = format_reference(position, self._info, self._book_names, self._one_chapter_books)
        return ConcordanceHit(position, reference, verse_text)