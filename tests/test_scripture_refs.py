# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

import shared as sh
from domain.scripture_refs import resolve_reference, calculate_book_line
import scripture


class TestScriptureRefs(unittest.TestCase):
    def test_resolve_reference_basic(self):
        book, chap, verse = resolve_reference(["Genesis", "1", "1"])
        self.assertEqual((book, chap, verse), (1, 1, 1))

    def test_resolve_reference_roman(self):
        # Psalms CXIX:XXII -> Psalm 119:22
        book, chap, verse = resolve_reference(["Psalms", "CXIX", "XXII"])
        self.assertEqual((book, chap, verse), (19, 119, 22))

    def test_resolve_reference_invalid_book(self):
        book, chap, verse = resolve_reference(["NotABook"])  # invalid
        self.assertIsNone(book)
        self.assertIsNone(chap)
        self.assertIsNone(verse)

    def test_calculate_book_line_invalid_raises(self):
        with self.assertRaises(ValueError):
            calculate_book_line(0, 1, 1, 0)

    def test_calculate_book_line_genesis_1_1_matches_info_index(self):
        # Expected: the first entry [0,0,0] in sh.Info
        expected_index = sh.Info.index([0, 0, 0])
        idx = calculate_book_line(1, 1, 1, expected_index)
        self.assertEqual(idx, expected_index)

    def test_open_ended_range_resolves_first_verse(self):
        # Deuteronomy 32:29-- should resolve to book 5, chapter 32, verse 29
        book, chap, verse = resolve_reference(["Deuteronomy", "32", "29--"])
        self.assertEqual((book, chap, verse), (5, 32, 29))
        # And calculate a valid line without raising
        idx = calculate_book_line(book, chap, verse, 0)
        self.assertIsInstance(idx, int)

    def test_list_with_open_ended_first_unit(self):
        # Also handle lists; we take the very first verse number for navigation
        book, chap, verse = resolve_reference(["Deuteronomy", "32", "29--, 31-33"]) 
        self.assertEqual((book, chap, verse), (5, 32, 29))

    def test_lookup_scripture_open_ended_range_is_discarded(self):
        # Minimal in-memory bible data for Deuteronomy 32
        bible_data = {
            "Deuteronomy": {
                "32": {
                    "28": "For they are a nation void of counsel...",
                    "29": "O that they were wise, that they understood this...",
                    "30": "How should one chase a thousand...",
                }
            }
        }
        # A dangling range like 29-- should be treated as just verse 29 (hyphen discarded)
        txt = scripture.lookup_scripture(bible_data, "Deuteronomy", 32, "29--")
        self.assertIn("29 O that they were wise", txt)
        self.assertNotIn("30 How should one chase a thousand", txt)
        self.assertNotIn("28 For they are a nation", txt)


if __name__ == "__main__":
    unittest.main()
