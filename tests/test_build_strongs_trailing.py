# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Tests for the trailing-text handling in ``tools/build_strongs_sqlite.py``.

Regression guard for the bug where the final word(s) of a verse that appear
after the last Strong's tag (e.g. "any" in Proverbs 30:30,
"... for<S>6440</S> any;") were silently dropped from ``strongs.sqlite``.
"""

from __future__ import annotations

import importlib
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_PATH = PROJECT_ROOT / "tools"
if str(TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLS_PATH))

build_strongs_sqlite = importlib.import_module("build_strongs_sqlite")


def _write_kjv(tmp_path: Path, text: str) -> Path:
    data = {
        "books": [
            {
                "name": "Genesis",
                "chapters": [
                    {"chapter": 1, "verses": [{"verse": 1, "text": text}]}
                ],
            }
        ]
    }
    p = tmp_path / "kjv.json"
    p.write_text(json.dumps(data), encoding="utf-8")
    return p


def test_trailing_text_after_last_tag_is_captured(tmp_path):
    kjv = _write_kjv(tmp_path, "for<S>6440</S> any;")
    rows = list(build_strongs_sqlite.iter_word_tags(kjv, {(0, 0, 0): 0}))
    assert rows == [
        (0, 0, "for", "H6440"),
        (0, 1, "any;", ""),
    ]


def test_no_trailing_text_produces_no_extra_row(tmp_path):
    kjv = _write_kjv(tmp_path, "beginning<S>7225</S>")
    rows = list(build_strongs_sqlite.iter_word_tags(kjv, {(0, 0, 0): 0}))
    assert rows == [(0, 0, "beginning", "H7225")]


def test_trailing_whitespace_only_is_ignored(tmp_path):
    kjv = _write_kjv(tmp_path, "God<S>430</S>   ")
    rows = list(build_strongs_sqlite.iter_word_tags(kjv, {(0, 0, 0): 0}))
    assert rows == [(0, 0, "God", "H0430")]


def test_proverbs_30_30_correction_is_registered():
    # Proverbs 30:30 (0-based 19,29,29): the trailing word "any" is corrected
    # to H3605 (כֹּל, kol), which the Bolls source omits.
    assert build_strongs_sqlite.TRAILING_TAG_CORRECTIONS[(19, 29, 29)] == "H3605"


def test_trailing_correction_applied_to_trailing_word(tmp_path, monkeypatch):
    # Add a correction for the Genesis test verse and confirm the trailing
    # word receives it instead of an empty code.
    monkeypatch.setitem(
        build_strongs_sqlite.TRAILING_TAG_CORRECTIONS, (0, 0, 0), "H3605"
    )
    kjv = _write_kjv(tmp_path, "for<S>6440</S> any;")
    rows = list(build_strongs_sqlite.iter_word_tags(kjv, {(0, 0, 0): 0}))
    assert rows == [
        (0, 0, "for", "H6440"),
        (0, 1, "any;", "H3605"),
    ]
