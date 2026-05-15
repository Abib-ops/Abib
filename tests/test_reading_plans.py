# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

import unittest

from abib.domain.reading_plans import ReadingPlans


class TestReadingPlans(unittest.TestCase):
    def test_get_devotional_entry_returns_text_and_ref(self):
        rp = ReadingPlans()
        text, ref = rp.get_devotional_entry(0)
        # Should always return strings; content depends on JSON and date
        self.assertIsInstance(text, str)
        self.assertIsInstance(ref, str)
        self.assertGreater(len(text), 0)
        # ref may be empty if parsing failed, but it must be a string

    def test_get_devotional_reference_is_string(self):
        rp = ReadingPlans()
        ref = rp.get_devotional_reference()
        self.assertIsInstance(ref, str)


if __name__ == "__main__":
    unittest.main()
