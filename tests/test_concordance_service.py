# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from abib.services.concordance_service import ConcordanceService, normalize_term


def make_service() -> ConcordanceService:
    kjv = (
        "In the beginning God created the heaven and the earth.",
        "And God said, Let there be light: and there was light.",
        "The LORD is my shepherd; the Lord is good.",
    )
    amap = (0, 1, 2)
    info = ((0, 0, 0), (0, 0, 1), (1, 0, 2))
    book_names = ("Genesis", "Psalms")
    return ConcordanceService(kjv, amap, info, book_names, set())


def make_hyphen_service() -> ConcordanceService:
    kjv = (
        "but thou shalt be called Hephzi-bah, and thy land Beulah.",
    )
    amap = (0,)
    info = ((0, 61, 3),)
    book_names = ("Isaiah",)
    return ConcordanceService(kjv, amap, info, book_names, set())


def test_normalize_term_case_folds_words_and_phrases():
    assert normalize_term("  The LORD's Mercies! ") == "the lord's mercies"


def test_entries_group_case_variants_and_count_occurrences():
    entry = make_service().get_entry("lord")

    assert entry is not None
    assert entry.term == "lord"
    assert entry.count == 2
    assert [hit.reference for hit in entry.hits] == ["Psalms 1:3", "Psalms 1:3"]


def test_stop_words_are_excluded_from_word_index():
    service = make_service()

    assert service.get_entry("the") is None
    assert all(entry.term != "the" for entry in service.entries())


def test_phrase_lookup_uses_same_hit_model():
    entry = make_service().get_entry("God said")

    assert entry is not None
    assert entry.term == "god said"
    assert entry.count == 1
    assert entry.hits[0].position == 1
    assert entry.hits[0].reference == "Genesis 1:2"
    assert "God said" in entry.hits[0].verse_text


def test_matching_entries_filters_alphabetical_entries():
    entries = make_service().matching_entries("lig")

    assert [entry.term for entry in entries] == ["light"]


def test_normalize_term_collapses_hyphenated_names():
    assert normalize_term("Hephzi-bah") == "hephzibah"


def test_hyphenated_name_found_without_hyphen():
    entry = make_hyphen_service().get_entry("Hephzibah")

    assert entry is not None
    assert entry.term == "hephzibah"
    assert entry.count == 1
    assert "Hephzi-bah" in entry.hits[0].verse_text


def test_hyphenated_name_found_with_hyphen():
    entry = make_hyphen_service().get_entry("Hephzi-bah")

    assert entry is not None
    assert entry.term == "hephzibah"
    assert entry.count == 1
    assert "Hephzi-bah" in entry.hits[0].verse_text