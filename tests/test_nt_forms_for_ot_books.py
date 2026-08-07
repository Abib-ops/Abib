# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from abib.core import shared as sh
from abib.core.scripture import normalize_book_input

CASES = {
    # NT/KJV forms used in the New Testament text
    "Jeremias": 24,
    "Osee": 28,
    "Jonas": 32,
    # Latinized/DR/LXX-influenced forms
    "Ezechiel": 26,
    "Abdias": 31,
    "Micheas": 33,
    "Sophonias": 36,
    "Aggeus": 37,
    "Zacharias": 38,
    "Malachias": 39,
    "Josue": 6,
}


def test_nt_forms_for_ot_books_normalize_and_lookup():
    for raw, expected in CASES.items():
        key = normalize_book_input(raw)
        assert sh.bibledict.get(key) == expected, (raw, key, expected)
