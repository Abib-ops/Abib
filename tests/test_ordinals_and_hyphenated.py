# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from abib.core import shared as sh
from abib.core.scripture import find_scripture_references, normalize_book_input


def test_normalize_book_input_suffix_ordinals():
    assert normalize_book_input("1st John") == "1john"
    assert normalize_book_input("2nd Timothy") == "2timothy"
    assert normalize_book_input("3rd Jn") == "3jn"


def test_normalize_book_input_written_out_and_hyphenated():
    assert normalize_book_input("Second Kings") == "2kings"
    assert normalize_book_input("First Peter") == "1peter"
    assert normalize_book_input("1-Jn") == "1jn"


def _book_id(ref):
    # Helper to convert the raw book text to a book id via normalisation and bibledict
    return sh.bibledict.get(normalize_book_input(ref["book"]))


def test_find_refs_suffix_ordinals():
    text = "Some text 1st John 3:16 in a sentence."
    refs = find_scripture_references(text)
    assert len(refs) >= 1
    r = refs[0]
    assert _book_id(r) == 62  # 1 John
    assert r["chapter"] == 3
    assert r["verse"] == "16"


def test_find_refs_hyphenated_and_compact():
    text = "Also 1-John 4:8 and later 3rdJn 1:4 appear."
    refs = find_scripture_references(text)
    # Expect two references captured in order
    assert len(refs) >= 2
    r1, r2 = refs[0], refs[1]
    assert _book_id(r1) == 62  # 1 John
    assert r1["chapter"] == 4 and r1["verse"] == "8"
    assert _book_id(r2) == 64  # 3 John
    assert r2["chapter"] == 1 and r2["verse"] == "4"


def test_find_refs_written_out_ordinals():
    text = "We read in Second Corinthians 5:17 and in First Peter 2:9."
    refs = find_scripture_references(text)
    # Two references expected
    assert len(refs) >= 2
    r1, r2 = refs[0], refs[1]
    assert _book_id(r1) == 47  # 2 Corinthians
    assert r1["chapter"] == 5 and r1["verse"] == "17"
    assert _book_id(r2) == 60  # 1 Peter
    assert r2["chapter"] == 2 and r2["verse"] == "9"
