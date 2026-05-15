# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from abib.core import shared as sh
from abib.core.scripture import find_scripture_references, normalize_book_input


def _book_id(ref):
    return sh.bibledict.get(normalize_book_input(ref["book"]))


def test_naves_line_does_not_bleed_into_next_dash_item():
    # Mirrors the AARON excerpt where the next line starts with a dash
    text = (
        "AARON\n"
        "          -Lineage of Ex 6:16-20; Jos 21:4,10; 1Ch 6:2,3; 23:13\n\n"
        "          -Marriage of Ex 6:23\n"
    )
    refs = find_scripture_references(text)

    # Ensure we captured the 1 Chronicles references, including the continuation 23:13
    # and that it did not consume the leading dash from the next line.
    one_chron_refs = [r for r in refs if _book_id(r) == 13]
    assert any(r["chapter"] == 6 and r["verse"].startswith("2") for r in one_chron_refs)

    # Find the continuation 23:13 and confirm no hyphen bled in.
    cont = [r for r in one_chron_refs if r["chapter"] == 23 and r["verse"] == "13"]
    assert cont, f"Expected 1 Chronicles 23:13 in refs: {one_chron_refs}"
    assert all("-" not in r["text"] for r in cont), cont


def test_naves_abel_item_does_not_bleed_dash_number():
    # Mirrors the ABEL excerpt where a new dash-numbered item starts on the next line
    text = (
        "ABEL\n"
        "          -1. Son of Adam. History of Ge 4:1-15,25\n\n"
        "          .References to the death of Mt 23:35; Lu 11:51; Heb 11:4; 12:24;\n"
        "          1Jo 3:12\n\n"
        "          -2. A stone 1Sa 6:18\n"
    )
    refs = find_scripture_references(text)
    one_john = [r for r in refs if _book_id(r) == 62 and r["chapter"] == 3 and r["verse"] == "12"]
    assert one_john, f"Expected to find 1 John 3:12, got: {refs}"
    # The matched text should not include the dash beginning the next line
    assert all("-" not in r["text"] for r in one_john), one_john


def test_cross_line_break_between_book_and_chapter_still_matches():
    # A legitimate wrap between book and chapter should still be detected
    text = "John\n3:16"
    refs = find_scripture_references(text)
    john_316 = [r for r in refs if _book_id(r) == 43 and r["chapter"] == 3 and r["verse"] == "16"]
    assert john_316, f"Expected John 3:16 across a newline, got: {refs}"
