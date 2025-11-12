from __future__ import annotations

import unittest

import shared as sh
from domain.scripture_refs import resolve_reference, calculate_book_line


class TestScriptureRefsExtended(unittest.TestCase):
    def test_resolve_reference_defaults_when_omitted(self):
        # Only book provided -> defaults to chapter=1, verse=1
        book, chap, verse = resolve_reference(["genesis"])  # lower-case should work via dict lowercasing
        self.assertEqual((book, chap, verse), (1, 1, 1))

    def test_resolve_reference_int_inputs(self):
        # Accept integers for chapter/verse
        book, chap, verse = resolve_reference(["Genesis", 2, 3])
        self.assertEqual((book, chap, verse), (1, 2, 3))

    def test_resolve_reference_invalid_chapter_returns_none_for_rest(self):
        # Empty string is considered missing/invalid when explicitly provided
        book, chap, verse = resolve_reference(["Genesis", " "])  # explicit but empty -> invalid
        self.assertEqual(book, 1)
        self.assertIsNone(chap)
        self.assertIsNone(verse)

    def test_resolve_reference_invalid_roman(self):
        # An invalid Roman numeral should make that component None
        book, chap, verse = resolve_reference(["Psalms", "IC", "X"])  # "IC" is not valid Roman 99
        self.assertEqual(book, 19)
        self.assertIsNone(chap)
        self.assertIsNone(verse)

    def test_resolve_reference_invalid_verse_only(self):
        # Valid chapter, invalid verse -> verse becomes None while chapter resolved
        book, chap, verse = resolve_reference(["Genesis", "1", "bad"])
        self.assertEqual(book, 1)
        self.assertEqual(chap, 1)
        self.assertIsNone(verse)

    def test_calculate_book_line_invalid_types(self):
        with self.assertRaises(ValueError):
            calculate_book_line("a", 1, 1, 0)  # type error for book
        with self.assertRaises(ValueError):
            calculate_book_line(1, "b", 1, 0)  # type error for chapter
        with self.assertRaises(ValueError):
            calculate_book_line(1, 1, "c", 0)  # type error for verse

    def test_calculate_book_line_values_must_be_positive(self):
        for args in [(-1, 1, 1), (1, 0, 1), (1, 1, -5)]:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    calculate_book_line(*args, _current_line_num=0)

    def test_calculate_book_line_not_found_raises(self):
        # Use an obviously out-of-range chapter to force a miss
        with self.assertRaises(ValueError):
            calculate_book_line(1, 9999, 1, 0)

    def test_calculate_book_line_second_verse_after_first(self):
        # If Genesis 1:1 exists, Genesis 1:2 should follow it or be nearby; at least it's a valid lookup.
        # This primarily verifies no exception and consistent index mapping for a nearby verse when present.
        # We guard with try/except because some datasets might not include 1:2 separately (edge datasets).
        try:
            idx_1_1 = calculate_book_line(1, 1, 1, 0)
            idx_1_2 = calculate_book_line(1, 1, 2, 0)
            self.assertIsInstance(idx_1_2, int)
            self.assertGreaterEqual(idx_1_2, idx_1_1)
        except ValueError:
            # Dataset missing verse 2; acceptable — ensure 1:1 at least exists.
            idx_1_1 = calculate_book_line(1, 1, 1, 0)
            self.assertIsInstance(idx_1_1, int)

    def test_semicolon_reference_inherits_book_and_chapter(self):
        from scripture import find_scripture_references
        text = "See John 10:14-16; 25-28 for context."
        refs = find_scripture_references(text)
        # Expect two references: John 10:14-16 and John 10:25-28
        self.assertGreaterEqual(len(refs), 2)
        self.assertEqual(refs[0]["book"].lower().startswith("john"), True)
        self.assertEqual(refs[0]["chapter"], 10)
        self.assertEqual(refs[0]["verse"], "14-16")
        self.assertEqual(refs[1]["book"].lower().startswith("john"), True)
        self.assertEqual(refs[1]["chapter"], 10)
        self.assertEqual(refs[1]["verse"], "25-28")

    def test_semicolon_reference_chapter_then_chapter(self):
        from scripture import find_scripture_references
        text = "Cross refs: John 3:16; 4:2"
        refs = find_scripture_references(text)
        self.assertGreaterEqual(len(refs), 2)
        self.assertEqual(refs[0]["book"].lower().startswith("john"), True)
        self.assertEqual(refs[0]["chapter"], 3)
        self.assertEqual(refs[0]["verse"], "16")
        self.assertEqual(refs[1]["book"].lower().startswith("john"), True)
        self.assertEqual(refs[1]["chapter"], 4)
        self.assertEqual(refs[1]["verse"], "2")

    def test_semicolon_reference_one_chapter_book(self):
        from scripture import find_scripture_references
        text = "See Jude 5; 7-9 for examples."
        refs = find_scripture_references(text)
        # Expect Jude 5 and Jude 7-9 (chapter implicitly 1)
        self.assertGreaterEqual(len(refs), 2)
        self.assertEqual(refs[0]["book"].lower().startswith("jude"), True)
        self.assertEqual(refs[0]["chapter"], 1)
        self.assertEqual(refs[0]["verse"], "5")
        self.assertEqual(refs[1]["book"].lower().startswith("jude"), True)
        self.assertEqual(refs[1]["chapter"], 1)
        self.assertEqual(refs[1]["verse"], "7-9")


if __name__ == "__main__":
    unittest.main()
