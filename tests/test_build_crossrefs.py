# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Tests for the OpenBible cross-reference SQLite builder."""


import hashlib
import importlib
import sqlite3
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOOLS_PATH = PROJECT_ROOT / "tools"
if str(TOOLS_PATH) not in sys.path:
    sys.path.insert(0, str(TOOLS_PATH))

build_crossrefs_sqlite = importlib.import_module("build_crossrefs_sqlite")


def _write_info(tmp_path: Path) -> Path:
    addresses = [
        (0, 0, 0),  # Genesis 1:1
        (0, 0, 1),  # Genesis 1:2
        (0, 1, 0),  # Genesis 2:1
        (1, 0, 0),  # Exodus 1:1
        (42, 2, 15),  # John 3:16
        (42, 2, 16),  # John 3:17
    ]
    info_path = tmp_path / "Info.txt"
    info_path.write_text(
        "# header\n" * 17 + "".join(f"[{b}, {c}, {v}]\n" for b, c, v in addresses),
        encoding="utf-8",
    )
    return info_path


def _source_tsv() -> str:
    return (
        "From Verse\tTo Verse\tVotes\t#www.openbible.info CC-BY fixture\n"
        "Gen.1.1\tGen.1.2\t5\n"
        "Gen.1.1\tGen.1.2\t10\n"
        "Gen.1.1\tGen.1.1-Gen.2.1\t9\n"
        "Gen.1.1\tExod.1.1-Exod.1.1\t-2\n"
        "John.3.16\tJohn.3.17\t4\n"
        "Unknown.1.1\tGen.1.1\t7\n"
        "Gen.99.1\tGen.1.1\t3\n"
        "Exod.1.1\tExod.1.1-Gen.1.1\t3\n"
        "Gen.1.1\tGen.1.2\tnot-a-vote\n"
    )


def test_osis_abbreviations_cover_the_66_canonical_books():
    abbreviations = build_crossrefs_sqlite.OSIS_BOOK_NUMBERS

    assert len(abbreviations) == 66
    assert abbreviations["Gen"] == 0
    assert abbreviations["1Sam"] == 8
    assert abbreviations["Song"] == 21
    assert abbreviations["Phlm"] == 56
    assert abbreviations["3John"] == 63
    assert abbreviations["Rev"] == 65


@pytest.mark.parametrize(
    ("reference", "expected"),
    [
        ("Gen.1.1", (0, 0)),
        ("Gen.1.1-Gen.2.1", (0, 2)),
        ("Gen.1.1-Exod.1.1", (0, 3)),
        ("Unknown.1.1", None),
        ("Gen.99.1", None),
        ("Exod.1.1-Gen.1.1", None),
    ],
)
def test_parse_reference(reference, expected):
    verse_map = {
        (0, 0, 0): 0,
        (0, 1, 0): 2,
        (1, 0, 0): 3,
    }

    assert build_crossrefs_sqlite.parse_reference(reference, verse_map) == expected


def test_build_tsv_skips_invalid_rows_and_keeps_highest_duplicate_vote(tmp_path):
    info_path = _write_info(tmp_path)
    input_path = tmp_path / "cross_references.txt"
    source = _source_tsv().encode("utf-8")
    input_path.write_bytes(source)
    output_path = tmp_path / "openbible-crossrefs.sqlite"

    stats = build_crossrefs_sqlite.build(input_path, output_path, info_path)

    assert stats["rows"] == 4
    assert stats["skipped_rows"] == 4
    with sqlite3.connect(output_path) as connection:
        assert connection.execute(
            "SELECT from_vi, to_start, to_end, votes FROM crossrefs "
            "ORDER BY from_vi, to_start, to_end"
        ).fetchall() == [
            (0, 0, 2, 9),
            (0, 1, 1, 10),
            (0, 3, 3, -2),
            (4, 5, 5, 4),
        ]
        metadata = dict(connection.execute("SELECT key, value FROM meta"))
        assert metadata["schema_version"] == "1"
        assert metadata["source_sha256"] == hashlib.sha256(source).hexdigest()
        assert metadata["rows"] == "4"
        assert metadata["skipped_rows"] == "4"
        assert metadata["attribution"] == build_crossrefs_sqlite.ATTRIBUTION
        assert "CC-BY fixture" in metadata["licence"]
        table_sql = connection.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' AND name='crossrefs'"
        ).fetchone()[0]
        assert "WITHOUT ROWID" in table_sql.upper()


def test_build_reads_cross_references_from_zip(tmp_path):
    info_path = _write_info(tmp_path)
    zip_path = tmp_path / "openbible.zip"
    with zipfile.ZipFile(zip_path, "w") as archive:
        archive.writestr("cross_references.txt", _source_tsv())
    output_path = tmp_path / "crossrefs.sqlite"

    stats = build_crossrefs_sqlite.build(zip_path, output_path, info_path)

    assert stats["rows"] == 4
    assert stats["skipped_rows"] == 4