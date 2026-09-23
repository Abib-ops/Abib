# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from abib.ui.search_results import (
    find_highlight_ranges,
    format_reference,
    highlight_result_text,
    highlight_tagged_words,
    result_verse_text,
)


def test_format_reference_handles_normal_and_one_chapter_books():
    info = ((0, 0, 0), (1, 0, 2))
    book_names = ("Genesis", "Jude")

    assert format_reference(0, info, book_names, {1}) == "Genesis 1:1"
    assert format_reference(1, info, book_names, {1}) == "Jude 3"


def test_all_words_result_highlighting_marks_each_word_case_insensitively():
    text = "Come unto me, and I will give you rest for ever."

    assert find_highlight_ranges(text, "rest ever", 3, False) == [(34, 38), (43, 47)]
    html = highlight_result_text(text, "rest ever", 3, False)

    assert html.count("background-color") == 2
    assert ">rest<" in html
    assert ">ever<" in html


def test_result_highlighting_escapes_unmatched_text():
    html = highlight_result_text("rest <ever>", "rest", 2, False)

    assert "&lt;ever&gt;" in html
    assert ">rest<" in html


def test_result_verse_text_uses_bible_line_mapping():
    kjv = ("title line", "Genesis 1:1 text", "heading", "Genesis 1:2 text")
    amap = (1, 3)

    assert result_verse_text(0, kjv, amap) == "Genesis 1:1 text"
    assert result_verse_text(1, kjv, amap) == "Genesis 1:2 text"


def test_result_verse_text_removes_leading_verse_number():
    kjv = ("title line", "2 And the earth was without form", "3 ¶ And God said")
    amap = (1, 2)

    assert result_verse_text(0, kjv, amap) == "And the earth was without form"
    assert result_verse_text(1, kjv, amap) == "¶ And God said"


def test_highlight_tagged_words_marks_only_matching_code():
    text = "In the beginning God created the heaven and the earth."
    tags = [
        ("In", "H0000"),
        ("the", "H0001"),
        ("beginning", "H7225"),
        ("God", "H0430"),
        ("created", "H1254"),
        ("the", "H0001"),
        ("heaven", "H8064"),
        ("and", "H0000"),
        ("the", "H0001"),
        ("earth", "H0776"),
    ]

    html = highlight_tagged_words(text, tags, "H0430")

    # Only the single "God" occurrence is highlighted; the (many) "the" words
    # tagged with a different code are left untouched.
    assert html.count("background-color") == 1
    assert ">God<" in html


def test_highlight_tagged_words_distinguishes_duplicate_surface_by_code():
    # The word "LORD" appears twice; only the first is tagged with the target
    # code, so only the first occurrence must be highlighted.
    text = "the LORD God formed man, and the LORD breathed."
    tags = [
        ("the", "H0001"),
        ("LORD", "H3068"),
        ("God", "H0430"),
        ("formed", "H3335"),
        ("man", "H0120"),
        ("and", "H0000"),
        ("the", "H0001"),
        ("LORD", "H9999"),
        ("breathed", "H5301"),
    ]

    html = highlight_tagged_words(text, tags, "H3068")

    assert html.count("background-color") == 1
    # The highlighted span must be the FIRST "LORD", before "God".
    highlighted_index = html.index("background-color")
    assert html.index("God") > highlighted_index
    assert html.count(">LORD<") == 1


def test_highlight_tagged_words_no_matches_returns_plain_escaped_text():
    html = highlight_tagged_words("rest <ever>", [("rest", "H0001")], "H9999")

    assert "background-color" not in html
    assert "&lt;ever&gt;" in html