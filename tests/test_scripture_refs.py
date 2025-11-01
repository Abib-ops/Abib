from __future__ import annotations

import unittest

import shared as sh
from domain.scripture_refs import resolve_reference, calculate_book_line


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


if __name__ == "__main__":
    unittest.main()
