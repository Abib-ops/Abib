from __future__ import annotations

import unittest

from domain.reading_plans import ReadingPlans


class TestReadingPlans(unittest.TestCase):
    def test_get_sme_returns_text_and_ref(self):
        rp = ReadingPlans()
        text, ref = rp.get_sme(0)
        # Should always return strings; content depends on JSON and date
        self.assertIsInstance(text, str)
        self.assertIsInstance(ref, str)
        self.assertGreater(len(text), 0)
        # ref may be empty if parsing failed, but it must be a string

    def test_current_ref_is_string(self):
        rp = ReadingPlans()
        ref = rp.current_ref()
        self.assertIsInstance(ref, str)


if __name__ == "__main__":
    unittest.main()
