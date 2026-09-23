# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from typing import Any

import pytest

from abib.services import strongs_service as ss
from abib.services.strongs_service import StrongsEntry, StrongsService, WordTag


def _build_db(path) -> None:
    """Create a tiny strongs.sqlite mirroring the real schema."""
    conn = sqlite3.connect(path)
    try:
        conn.executescript(
            """
            CREATE TABLE word_tags (
                verse_index INTEGER NOT NULL,
                word_pos    INTEGER NOT NULL,
                surface     TEXT,
                strongs     TEXT NOT NULL
            );
            CREATE TABLE strongs_dict (
                strongs       TEXT PRIMARY KEY,
                lemma         TEXT,
                translit      TEXT,
                pronunciation TEXT,
                short_def     TEXT,
                long_def      TEXT,
                language      TEXT
            );
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
            """
        )
        # Genesis 1:1 (verse_index 0): "In the beginning God created ..."
        conn.executemany(
            "INSERT INTO word_tags (verse_index, word_pos, surface, strongs) "
            "VALUES (?, ?, ?, ?)",
            [
                (0, 0, "In the beginning", "H7225"),
                (0, 1, "God", "H0430"),
                (0, 2, "created", "H1254"),
                # "God" (H0430) also occurs in a later verse (index 5).
                (5, 0, "God", "H0430"),
                # A Greek tag in the NT (John 1:1, arbitrary index).
                (26046, 3, "Word", "G3056"),
            ],
        )
        conn.executemany(
            "INSERT INTO strongs_dict "
            "(strongs, lemma, translit, pronunciation, short_def, long_def, "
            "language) VALUES (?, ?, ?, ?, ?, ?, ?)",
            [
                ("H0430", "אֱלֹהִים", "ʼĕlôhîym", "el-o-heem'",
                 "gods, supreme God", "plural of H0433", "hebrew"),
                ("G3056", "λόγος", "lógos", "log'-os",
                 "something said, the Word", "from G3004", "greek"),
            ],
        )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture()
def service(tmp_path) -> Generator[StrongsService, Any, None]:
    db_path = tmp_path / "strongs.sqlite"
    _build_db(db_path)
    svc = StrongsService(db_path)
    yield svc
    svc.close()


def test_normalise_code():
    assert ss.normalise_code("H430") == "H0430"
    assert ss.normalise_code("h0430") == "H0430"
    assert ss.normalise_code("  G3056  ") == "G3056"
    assert ss.normalise_code("g3") == "G0003"
    assert ss.normalise_code("H12345") == "H12345"
    assert ss.normalise_code("430") is None
    assert ss.normalise_code("strongs:H430") is None
    assert ss.normalise_code("") is None
    assert ss.normalise_code(None) is None  # type: ignore[arg-type]


def test_is_available_true(service: StrongsService):
    assert service.is_available() is True


def test_get_tags_for_verse(service: StrongsService):
    tags = service.get_tags_for_verse(0)
    assert tags == [
        WordTag(0, 0, "In the beginning", "H7225"),
        WordTag(0, 1, "God", "H0430"),
        WordTag(0, 2, "created", "H1254"),
    ]
    # A verse with no tags returns an empty list, not an error.
    assert service.get_tags_for_verse(999) == []
    # A value that is not an integer is handled gracefully.
    assert service.get_tags_for_verse("nope") == []  # type: ignore[arg-type]


def test_tag_at(service: StrongsService):
    assert service.tag_at(0, 1) == WordTag(0, 1, "God", "H0430")
    assert service.tag_at(0, 99) is None
    assert service.tag_at("x", 0) is None  # type: ignore[arg-type]


def test_lookup_strongs(service: StrongsService):
    entry = service.lookup_strongs("H430")  # accepts un-padded form
    assert isinstance(entry, StrongsEntry)
    assert entry.strongs == "H0430"
    assert entry.lemma == "אֱלֹהִים"
    assert entry.translit == "ʼĕlôhîym"
    assert entry.language == "hebrew"

    greek = service.lookup_strongs("G3056")
    assert greek is not None
    assert greek.lemma == "λόγος"

    assert service.lookup_strongs("H9999") is None
    assert service.lookup_strongs("not-a-code") is None


def test_find_verses_by_strongs(service: StrongsService):
    assert service.find_verses_by_strongs("H0430") == [0, 5]
    assert service.find_verses_by_strongs("h430") == [0, 5]
    assert service.find_verses_by_strongs("G3056") == [26046]
    assert service.find_verses_by_strongs("H9999") == []
    assert service.find_verses_by_strongs("bad") == []


def test_count_occurrences(service: StrongsService):
    assert service.count_occurrences("H0430") == 2
    assert service.count_occurrences("H7225") == 1
    assert service.count_occurrences("H9999") == 0
    assert service.count_occurrences("bad") == 0


def test_missing_db_degrades_gracefully(tmp_path):
    svc = StrongsService(tmp_path / "does_not_exist.sqlite")
    assert svc.is_available() is False
    assert svc.get_tags_for_verse(0) == []
    assert svc.tag_at(0, 0) is None
    assert svc.lookup_strongs("H0430") is None
    assert svc.find_verses_by_strongs("H0430") == []
    assert svc.count_occurrences("H0430") == 0
    svc.close()


def test_default_path_uses_shared_cwd(tmp_path, monkeypatch):
    db_path = tmp_path / "strongs.sqlite"
    _build_db(db_path)
    monkeypatch.setattr(ss.sh, "str_cwd", str(tmp_path))
    svc = StrongsService()
    try:
        assert svc.is_available() is True
        assert svc.lookup_strongs("H0430") is not None
    finally:
        svc.close()
