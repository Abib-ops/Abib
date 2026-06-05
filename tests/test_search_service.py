# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from types import SimpleNamespace
from typing import TYPE_CHECKING, cast

from abib.core.fcs import any_of_the_words_lookup
from abib.services.search_service import findf3_ww_all, findf3_ww_any

if TYPE_CHECKING:
    from abib.Abib import MainWindow


def test_all_words_counts_matching_verses_not_individual_words():
    r_list = [
        "rest and ever rest",
        "rest only",
        "ever only",
        "ever rest rest ever",
        "neither word",
    ]
    lookup = {
        "rest": {0, 1, 3},
        "ever": {0, 2, 3},
    }
    win = cast("MainWindow", cast(object, SimpleNamespace(key="rest ever")))

    findf3_ww_all(0, len(r_list) - 1, 2, lookup, r_list, win)

    assert win.occurs == [0, 3]
    assert win.occurring == 2
    assert len(win.occur[0]) == 3
    assert len(win.occur[1]) == 4


def test_any_words_counts_matching_verses_not_individual_words():
    r_list = [
        "rest and ever rest",
        "rest only",
        "ever only ever",
        "ever rest rest ever",
        "neither word",
    ]
    lookup = {
        "rest": {0, 1, 3},
        "ever": {0, 2, 3},
    }
    win = cast("MainWindow", cast(object, SimpleNamespace(key="rest ever")))

    findf3_ww_any(0, len(r_list) - 1, lookup, r_list, win)

    assert win.occurs == [3, 0, 2, 1]
    assert win.occurring == 4
    assert [len(spans) for spans in win.occur] == [4, 3, 2, 1]


def test_any_words_lookup_ignores_common_words():
    lookup = {
        "the": {0, 1, 2, 3},
        "and": {0, 2},
        "covenant": {1},
        "mercy": {2},
    }

    count, key = any_of_the_words_lookup("the covenant and mercy", lookup)

    assert count == 2
    assert key == "covenant mercy"


def test_any_words_lookup_rejects_all_common_words():
    lookup = {
        "the": {0, 1, 2, 3},
        "and": {0, 2},
        "of": {1, 3},
    }

    count, key = any_of_the_words_lookup("the and of", lookup)

    assert count == 0
    assert key == ""