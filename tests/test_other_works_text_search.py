# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-


from abib.services.other_works_text_search import OtherWorksTextSearchService


def make_service(tmp_path) -> OtherWorksTextSearchService:
    first = tmp_path / "First.txt"
    first.write_text("Alpha mercy. MERCY again.\r\nA tender mercy phrase.", encoding="utf-8")
    second = tmp_path / "Second.txt"
    second.write_text("No match here. A tender Mercy phrase appears too.", encoding="utf-8")
    return OtherWorksTextSearchService(
        {"First": str(first), "Second": str(second)},
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
    service = OtherWorksTextSearchService({"Cats": str(path)})

    results = service.search("as many lives as a cat")

    assert len(results.occurrences) == 1
    occurrence = results.occurrences[0]
    assert occurrence.matched_text == "as many lives\nas a cat"
    assert occurrence.abs_start == 15
    assert occurrence.length == 22


def test_search_includes_every_present_work(tmp_path):
    # There is no per-book visibility toggle any more: every downloaded work
    # is searchable, so a match present in all books is reported for all.
    first = tmp_path / "First.txt"
    first.write_text("First mentions mercy.", encoding="utf-8")
    second = tmp_path / "Second.txt"
    second.write_text("Second mentions mercy.", encoding="utf-8")
    third = tmp_path / "Third.txt"
    third.write_text("Third mentions mercy.", encoding="utf-8")
    service = OtherWorksTextSearchService(
        {"First": str(first), "Second": str(second), "Third": str(third)},
    )

    results = service.search("mercy")

    assert {occ.work_stem for occ in results.occurrences} == {"First", "Second", "Third"}


def test_search_returns_offsets_against_normalized_text(tmp_path):
    path = tmp_path / "First.txt"
    path.write_text(
        "Alpha mercy. MERCY again.\r\nA tender mercy phrase.",
        encoding="utf-8",
        newline="",          # write the \r\n verbatim, no OS translation
    )
    service = OtherWorksTextSearchService({"First": str(path)})

    results = service.search("A tender")
    occurrence = results.occurrences[0]

    assert occurrence.work_stem == "First"
    assert occurrence.abs_start == 26   # \r\n normalized to a single \n
    assert occurrence.length == 8


def test_search_generates_concise_snippets(tmp_path):
    path = tmp_path / "Long.txt"
    path.write_text(f"{'A' * 80}needle{'B' * 80}", encoding="utf-8")
    service = OtherWorksTextSearchService({"Long": str(path)})

    occurrence = service.search("needle").occurrences[0]

    assert occurrence.snippet.startswith("…")
    assert occurrence.snippet.endswith("…")
    assert "needle" in occurrence.snippet


def test_search_returns_empty_results_for_empty_query(tmp_path):
    service = make_service(tmp_path)

    results = service.search("   ")

    assert results.query == ""
    assert results.occurrences == ()


def test_search_finds_hyphenated_name_without_hyphen(tmp_path):
    path = tmp_path / "Names.txt"
    path.write_text("thy land shall be called Hephzi-bah, and Beulah.", encoding="utf-8")
    service = OtherWorksTextSearchService({"Names": str(path)})

    results = service.search("Hephzibah")

    assert [(occ.work_stem, occ.matched_text) for occ in results.occurrences] == [
        ("Names", "Hephzi-bah"),
    ]


def test_search_finds_hyphenated_name_with_hyphen(tmp_path):
    path = tmp_path / "Names.txt"
    path.write_text("thy land shall be called Hephzi-bah, and Beulah.", encoding="utf-8")
    service = OtherWorksTextSearchService({"Names": str(path)})

    results = service.search("Hephzi-bah")

    assert [(occ.work_stem, occ.matched_text) for occ in results.occurrences] == [
        ("Names", "Hephzi-bah"),
    ]


def test_search_case_sensitive_matches_exact_case_only(tmp_path):
    service = make_service(tmp_path)

    results = service.search("mercy", case_sensitive=True)

    assert [(occ.work_stem, occ.matched_text) for occ in results.occurrences] == [
        ("First", "mercy"),
        ("First", "mercy"),
    ]


def test_search_case_sensitive_matches_capitalized_query(tmp_path):
    service = make_service(tmp_path)

    results = service.search("Mercy", case_sensitive=True)

    assert [(occ.work_stem, occ.matched_text) for occ in results.occurrences] == [
        ("Second", "Mercy"),
    ]


def test_search_whole_words_excludes_substring_matches(tmp_path):
    path = tmp_path / "Words.txt"
    path.write_text("mercy is not mercyful nor commercy.", encoding="utf-8")
    service = OtherWorksTextSearchService({"Words": str(path)})

    results = service.search("mercy", whole_words=True)

    assert [(occ.abs_start, occ.matched_text) for occ in results.occurrences] == [
        (0, "mercy"),
    ]


def test_search_whole_words_without_option_includes_substring_matches(tmp_path):
    path = tmp_path / "Words.txt"
    path.write_text("mercy is not mercyful nor commercy.", encoding="utf-8")
    service = OtherWorksTextSearchService({"Words": str(path)})

    results = service.search("mercy")

    assert [occ.matched_text for occ in results.occurrences] == ["mercy", "mercy", "mercy"]


def test_search_whole_words_and_case_sensitive_combined(tmp_path):
    path = tmp_path / "Words.txt"
    path.write_text("Mercy and mercy and mercyful.", encoding="utf-8")
    service = OtherWorksTextSearchService({"Words": str(path)})

    results = service.search("mercy", whole_words=True, case_sensitive=True)

    assert [(occ.abs_start, occ.matched_text) for occ in results.occurrences] == [
        (10, "mercy"),
    ]