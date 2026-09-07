# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from abib.services.other_works_reference_index import _make_snippet, normalize_text


@dataclass(frozen=True)
class OtherWorkTextSearchOccurrence:
    work_stem: str
    work_path: str
    query: str
    matched_text: str
    abs_start: int
    length: int
    snippet: str


@dataclass(frozen=True)
class OtherWorkTextSearchResults:
    query: str
    occurrences: tuple[OtherWorkTextSearchOccurrence, ...]


class OtherWorksTextSearchService:
    """Search enabled Other Works text files for literal text matches."""

    def __init__(self, other_works_map: dict[str, str], show_work_settings: dict[str, bool] | None = None) -> None:
        self._other_works_map = dict(other_works_map)
        self._show_work_settings = show_work_settings or {}
        self._text_cache: dict[str, str] = {}

    def rebuild(self) -> None:
        self._text_cache.clear()

    def search(self, query: str) -> OtherWorkTextSearchResults:
        normalized_query = normalize_text(query).strip()
        if not normalized_query:
            return OtherWorkTextSearchResults(normalized_query, ())

        occurrences: list[OtherWorkTextSearchOccurrence] = []
        query_pattern = _literal_whitespace_pattern(normalized_query.casefold())
        for work_stem, work_path in self._enabled_works():
            content = self._read_text(work_path)
            if content is None:
                continue
            for abs_start, length in _literal_casefold_spans(content, query_pattern):
                matched_text = content[abs_start:abs_start + length]
                occurrences.append(OtherWorkTextSearchOccurrence(
                    work_stem=work_stem,
                    work_path=str(work_path),
                    query=normalized_query,
                    matched_text=matched_text,
                    abs_start=abs_start,
                    length=length,
                    snippet=_make_snippet(content, abs_start, length),
                ))
        return OtherWorkTextSearchResults(normalized_query, tuple(occurrences))

    def _enabled_works(self) -> tuple[tuple[str, Path], ...]:
        works: list[tuple[str, Path]] = []
        for work_stem, work_path in self._other_works_map.items():
            visible = self._show_work_settings.get(work_stem, True)
            if self._show_work_settings and str(visible).lower() == "false":
                continue
            works.append((work_stem, Path(work_path)))
        return tuple(sorted(works, key=lambda item: item[0].casefold()))

    def _read_text(self, work_path: Path) -> str | None:
        cache_key = str(work_path)
        if cache_key in self._text_cache:
            return self._text_cache[cache_key]
        try:
            content = normalize_text(work_path.read_text(encoding="utf-8", errors="replace"))
        except (OSError, UnicodeError, ValueError):
            return None
        self._text_cache[cache_key] = content
        return content


def _literal_casefold_spans(content: str, query_pattern: re.Pattern[str]) -> tuple[tuple[int, int], ...]:
    if not query_pattern.pattern:
        return ()

    folded_chars: list[str] = []
    folded_to_original: list[int] = []
    for original_index, char in enumerate(content):
        folded = char.casefold()
        folded_chars.append(folded)
        folded_to_original.extend([original_index] * len(folded))
    folded_content = "".join(folded_chars)

    spans: list[tuple[int, int]] = []
    for match in query_pattern.finditer(folded_content):
        match_start = match.start()
        match_end = match.end()
        abs_start = folded_to_original[match_start]
        original_end = folded_to_original[match_end - 1] + 1
        spans.append((abs_start, original_end - abs_start))
    return tuple(spans)


def _literal_whitespace_pattern(query_folded: str) -> re.Pattern[str]:
    tokens = [re.escape(token) for token in query_folded.split() if token]
    return re.compile(r"\s+".join(tokens))