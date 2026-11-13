# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

import sqlite3

from abib.services.commentary_lookup import CommentaryLookup


def _create_gill_db(path, rows: list[tuple[int, int, int, int | None, str]]) -> None:
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE commentary (id, book, chapter, fromverse, toverse, data)")
        connection.executemany(
            "INSERT INTO commentary (book, chapter, fromverse, toverse, data) VALUES (?, ?, ?, ?, ?)",
            rows,
        )


def test_lookup_includes_gill_html_and_mhcc_passage(tmp_path):
    gill_db = tmp_path / "gill.cmt.sqlite"
    _create_gill_db(gill_db, [(43, 3, 16, 16, "<p>For <b>God</b> so loved the world.</p>")])
    mhcc_path = tmp_path / "MHCC.txt"
    text = "__________\n\nJohn\n\nChapter 3\n\nVerses 16-17\nMatthew Henry comments here.\n"
    mhcc_path.write_text(text, encoding="utf-8")

    entries = CommentaryLookup({"MHCC": str(mhcc_path)}, gill_db).lookup((43, 3, 16))

    assert [entry.source for entry in entries] == ["gill", "mhcc"]
    assert entries[0].snippet == "For God so loved the world."
    assert entries[0].label == "Gill"
    assert entries[1].label == "Matthew Henry"
    assert entries[1].snippet == "Matthew Henry comments here."
    assert (entries[1].work_path, entries[1].abs_start, entries[1].length) == (
        str(mhcc_path), text.index("Verses 16-17"), len("Verses 16-17"),
    )


def test_mhcc_chapter_fallback_shows_outline_and_names_heading(tmp_path):
    mhcc_path = tmp_path / "MHCC.txt"
    text = (
        "__________\n\nJohn\n\nChapter 3\n\n   Chapter Outline\n\n"
        "   Christ's discourse with Nicodemus.\n\nVerses 1-8\nFirst passage.\n"
    )
    mhcc_path.write_text(text, encoding="utf-8")

    entries = CommentaryLookup({"MHCC": str(mhcc_path)}, tmp_path / "missing.sqlite").lookup((43, 3, 16))

    assert len(entries) == 1
    assert entries[0].label == "Matthew Henry — Chapter 3"
    assert entries[0].snippet == "Chapter Outline Christ's discourse with Nicodemus."


def test_lookup_uses_gill_range_for_encompassing_entry(tmp_path):
    gill_db = tmp_path / "gill.cmt.sqlite"
    _create_gill_db(gill_db, [(43, 3, 15, 17, "<div>Comments on the whole passage.</div>")])

    entries = CommentaryLookup({}, gill_db).lookup((43, 3, 16))

    assert len(entries) == 1
    assert entries[0].source == "gill"
    assert entries[0].snippet == "Comments on the whole passage."


def test_lookup_treats_null_gill_toverse_as_single_verse(tmp_path):
    gill_db = tmp_path / "gill.cmt.sqlite"
    _create_gill_db(gill_db, [(43, 3, 16, None, "<p>Single verse comment.</p>")])

    entries = CommentaryLookup({}, gill_db).lookup((43, 3, 16))

    assert len(entries) == 1
    assert entries[0].snippet == "Single verse comment."


def test_lookup_omits_unavailable_commentary_sources(tmp_path):
    entries = CommentaryLookup({}, tmp_path / "missing.sqlite").lookup((43, 3, 16))

    assert entries == ()


def test_lookup_uses_chapter_one_for_one_chapter_book(tmp_path):
    gill_db = tmp_path / "gill.cmt.sqlite"
    _create_gill_db(gill_db, [(65, 1, 5, 5, "<p>Jude commentary.</p>")])

    entries = CommentaryLookup({}, gill_db).lookup((65, None, 5))

    assert len(entries) == 1
    assert (entries[0].book, entries[0].chapter, entries[0].verse) == (65, 1, 5)
    assert entries[0].snippet == "Jude commentary."