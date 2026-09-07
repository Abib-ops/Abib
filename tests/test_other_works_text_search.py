# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from abib.services.other_works_text_search import OtherWorksTextSearchService


def make_service(tmp_path, show_work_settings: dict[str, bool] | None = None) -> OtherWorksTextSearchService:
    first = tmp_path / "First.txt"
    first.write_text("Alpha mercy. MERCY again.\r\nA tender mercy phrase.", encoding="utf-8")
    second = tmp_path / "Second.txt"
    second.write_text("No match here. A tender Mercy phrase appears too.", encoding="utf-8")
    hidden = tmp_path / "Hidden.txt"
    hidden.write_text("Hidden mercy should not appear.", encoding="utf-8")
    return OtherWorksTextSearchService(
        {"First": str(first), "Second": str(second), "Hidden": str(hidden)},
        show_work_settings if show_work_settings is not None else {"First": True, "Second": True, "Hidden": False},
    )


def test_search_finds_case_insensitive_matches_and_preserves_original_text(tmp_path):
    service = make_service(tmp_path)

    results = service.search("mercy")

    assert results.query == "mercy"
    assert [(occ.work_stem, occ.matched_text) for occ in results.occurrences] == [
        ("First", "mercy"),
        ("First", "MERCY"),
        ("First", "mercy"),
        ("Second", "Mercy"),
    ]


def test_search_finds_phrase_matches(tmp_path):
    service = make_service(tmp_path)

    results = service.search("tender mercy phrase")

    assert [(occ.work_stem, occ.matched_text) for occ in results.occurrences] == [
        ("First", "tender mercy phrase"),
        ("Second", "tender Mercy phrase"),
    ]


def test_search_finds_phrase_matches_across_crlf_like_reader_search(tmp_path):
    path = tmp_path / "Cats.txt"
    path.write_text("A saying about as many lives\r\nas a cat is here.", encoding="utf-8", newline="")
    service = OtherWorksTextSearchService({"Cats": str(path)}, {"Cats": True})

    results = service.search("as many lives as a cat")

    assert len(results.occurrences) == 1
    occurrence = results.occurrences[0]
    assert occurrence.matched_text == "as many lives\nas a cat"
    assert occurrence.abs_start == 15
    assert occurrence.length == 22


def test_search_excludes_disabled_works(tmp_path):
    service = make_service(tmp_path)

    results = service.search("hidden mercy")

    assert results.occurrences == ()


def test_search_returns_offsets_against_normalized_text(tmp_path):
    service = make_service(tmp_path, {"First": True})

    results = service.search("A tender")
    occurrence = results.occurrences[0]

    assert occurrence.work_stem == "First"
    assert occurrence.abs_start == 27
    assert occurrence.length == 8


def test_search_generates_concise_snippets(tmp_path):
    path = tmp_path / "Long.txt"
    path.write_text(f"{'A' * 80}needle{'B' * 80}", encoding="utf-8")
    service = OtherWorksTextSearchService({"Long": str(path)}, {"Long": True})

    occurrence = service.search("needle").occurrences[0]

    assert occurrence.snippet.startswith("…")
    assert occurrence.snippet.endswith("…")
    assert "needle" in occurrence.snippet


def test_search_returns_empty_results_for_empty_query(tmp_path):
    service = make_service(tmp_path)

    results = service.search("   ")

    assert results.query == ""
    assert results.occurrences == ()