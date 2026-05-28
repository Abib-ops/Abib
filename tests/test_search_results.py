# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from abib.ui.search_results import find_highlight_ranges, format_reference, highlight_result_text, result_verse_text


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