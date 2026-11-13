# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from abib.services.mhcc_index import MhccIndex


def _write_mhcc(path, text: str, newline: str = "\n") -> None:
    path.write_bytes(text.replace("\n", newline).encode("utf-8"))


def test_lookup_matches_verse_range_and_comma_range(tmp_path):
    text = "__________\n\nGenesis\n\nChapter 1\n\nVerses 1-3\nFirst passage.\n\nVerses 5, 7-8\nSecond passage.\n"
    path = tmp_path / "MHCC.txt"
    _write_mhcc(path, text)

    index = MhccIndex(path)

    first = index.lookup(1, 1, 2)
    comma_range = index.lookup(1, 1, 7)

    assert first is not None
    assert (first.label, first.kind, first.start, first.length) == (
        "Verses 1-3", "section", text.index("Verses 1-3"), len("Verses 1-3"),
    )
    assert comma_range is not None
    assert comma_range.label == "Verses 5, 7-8"


def test_lookup_falls_back_to_chapter_when_verse_has_no_section(tmp_path):
    text = "__________\n\nGenesis\n\nChapter 1\n\nVerses 1-3\nFirst passage.\n"
    path = tmp_path / "MHCC.txt"
    _write_mhcc(path, text)

    passage = MhccIndex(path).lookup(1, 1, 4)

    assert passage is not None
    assert (passage.label, passage.kind, passage.start) == ("Chapter 1", "chapter", text.index("Chapter 1"))


def test_lookup_falls_back_to_book_for_unheaded_chapter_one(tmp_path):
    text = "__________\n\n2 Chronicles\n\nAn introduction without a chapter heading.\n"
    path = tmp_path / "MHCC.txt"
    _write_mhcc(path, text)

    passage = MhccIndex(path).lookup(14, 1, 1)

    assert passage is not None
    assert (passage.label, passage.kind, passage.start) == ("2 Chronicles", "book", text.index("2 Chronicles"))


def test_unheaded_sections_belong_to_chapter_one(tmp_path):
    text = "__________\n\n2 Kings\n\nVerses 1-3\nFirst chapter.\n\nChapter 2\n\nVerses 1-2\nSecond chapter.\n"
    path = tmp_path / "MHCC.txt"
    _write_mhcc(path, text)

    index = MhccIndex(path)
    section = index.lookup(12, 1, 2)
    chapter_fallback = index.lookup(12, 1, 4)

    assert section is not None and section.label == "Verses 1-3"
    assert chapter_fallback is not None
    assert (chapter_fallback.label, chapter_fallback.kind, chapter_fallback.start) == (
        "Chapter 1", "chapter", text.index("Verses 1-3"),
    )


def test_lookup_returns_none_for_unknown_book_or_chapter(tmp_path):
    path = tmp_path / "MHCC.txt"
    _write_mhcc(path, "__________\n\nGenesis\n\nChapter 1\n")
    index = MhccIndex(path)

    assert index.lookup(67, 1, 1) is None
    assert index.lookup(1, 2, 1) is None
    assert index.lookup(1, 999, 1) is None


def test_crlf_and_lf_offsets_are_identical(tmp_path):
    text = "__________\n\nGenesis\n\nChapter 1\n\nVerses 1-3\nPassage.\n"
    lf_path = tmp_path / "lf.txt"
    crlf_path = tmp_path / "crlf.txt"
    _write_mhcc(lf_path, text)
    _write_mhcc(crlf_path, text, "\r\n")

    lf_passage = MhccIndex(lf_path).lookup(1, 1, 1)
    crlf_passage = MhccIndex(crlf_path).lookup(1, 1, 1)

    assert lf_passage is not None and crlf_passage is not None
    assert lf_passage.start == crlf_passage.start == text.index("Verses 1-3")


def test_index_cache_refreshes_when_source_changes(tmp_path):
    text = "__________\n\nGenesis\n\nChapter 1\n\nVerses 1-3\nPassage.\n"
    path = tmp_path / "MHCC.txt"
    _write_mhcc(path, text)
    index = MhccIndex(path)
    before = index.lookup(1, 1, 1)
    assert before is not None

    updated = text.replace("Chapter 1\n", "Chapter 1\nNew introductory text.\n")
    _write_mhcc(path, updated)
    after = index.lookup(1, 1, 1)

    assert after is not None
    assert after.start == updated.index("Verses 1-3")
    assert after.start > before.start