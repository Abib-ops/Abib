# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

#
# This file is part of Abib Bible Reader.
#
# Abib is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# any later version.
#
# Abib is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Abib.  If not, see <https://www.gnu.org/licenses/>.

"""Build Abib's indexed OpenBible.info cross-reference SQLite dataset."""


import argparse
import csv
import hashlib
import io
import sqlite3
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

from build_strongs_sqlite import build_verse_index_map
from project_setup import PROJECT_ROOT, SRC_PATH

DATASET_FILENAME = "openbible-crossrefs.sqlite"
SOURCE_URL = "https://www.openbible.info/labs/cross-references/"
LICENCE = "Creative Commons Attribution (CC BY; version not specified)"
ATTRIBUTION = "Cross-references: OpenBible.info (CC BY)"
DEFAULT_OUTPUT = PROJECT_ROOT / "Cross References" / DATASET_FILENAME
DEFAULT_INFO = SRC_PATH / "abib" / "data" / "Info.txt"

OSIS_BOOK_NUMBERS: dict[str, int] = {
    "Gen": 0,
    "Exod": 1,
    "Lev": 2,
    "Num": 3,
    "Deut": 4,
    "Josh": 5,
    "Judg": 6,
    "Ruth": 7,
    "1Sam": 8,
    "2Sam": 9,
    "1Kgs": 10,
    "2Kgs": 11,
    "1Chr": 12,
    "2Chr": 13,
    "Ezra": 14,
    "Neh": 15,
    "Esth": 16,
    "Job": 17,
    "Ps": 18,
    "Prov": 19,
    "Eccl": 20,
    "Song": 21,
    "Isa": 22,
    "Jer": 23,
    "Lam": 24,
    "Ezek": 25,
    "Dan": 26,
    "Hos": 27,
    "Joel": 28,
    "Amos": 29,
    "Obad": 30,
    "Jonah": 31,
    "Mic": 32,
    "Nah": 33,
    "Hab": 34,
    "Zeph": 35,
    "Hag": 36,
    "Zech": 37,
    "Mal": 38,
    "Matt": 39,
    "Mark": 40,
    "Luke": 41,
    "John": 42,
    "Acts": 43,
    "Rom": 44,
    "1Cor": 45,
    "2Cor": 46,
    "Gal": 47,
    "Eph": 48,
    "Phil": 49,
    "Col": 50,
    "1Thess": 51,
    "2Thess": 52,
    "1Tim": 53,
    "2Tim": 54,
    "Titus": 55,
    "Phlm": 56,
    "Heb": 57,
    "James": 58,
    "1Pet": 59,
    "2Pet": 60,
    "1John": 61,
    "2John": 62,
    "3John": 63,
    "Jude": 64,
    "Rev": 65,
}


def _verse_position(
    reference: str,
    verse_map: dict[tuple[int, int, int], int],
) -> int | None:
    """Resolve one OSIS ``Book.chapter.verse`` reference to an Abib position."""
    parts = reference.strip().split(".")
    if len(parts) != 3:
        return None
    book_number = OSIS_BOOK_NUMBERS.get(parts[0])
    if book_number is None:
        return None
    try:
        chapter, verse = int(parts[1]), int(parts[2])
    except ValueError:
        return None
    if chapter < 1 or verse < 1:
        return None
    return verse_map.get((book_number, chapter - 1, verse - 1))


def parse_reference(
    reference: str,
    verse_map: dict[tuple[int, int, int], int],
) -> tuple[int, int] | None:
    """Return the Abib positions at both ends of an OSIS verse or range."""
    endpoints = reference.strip().split("-")
    if len(endpoints) not in (1, 2):
        return None
    start = _verse_position(endpoints[0], verse_map)
    end = _verse_position(endpoints[-1], verse_map)
    if start is None or end is None or end < start:
        return None
    return start, end


def _read_source(input_path: Path) -> tuple[bytes, str]:
    """Read a plain TSV or the cross_references.txt member of an OpenBible zip."""
    if input_path.suffix.casefold() != ".zip":
        return input_path.read_bytes(), input_path.name

    with zipfile.ZipFile(input_path) as archive:
        members = [
            name for name in archive.namelist()
            if Path(name).name.casefold() == "cross_references.txt"
        ]
        if len(members) != 1:
            raise ValueError(
                "Zip must contain exactly one cross_references.txt file."
            )
        member = members[0]
        return archive.read(member), member


def _parse_rows(
    source_text: str,
    verse_map: dict[tuple[int, int, int], int],
) -> tuple[dict[tuple[int, int, int], int], int]:
    """Return unique cross-reference rows and the number of rejected data rows."""
    rows: dict[tuple[int, int, int], int] = {}
    skipped_rows = 0
    reader = csv.reader(io.StringIO(source_text, newline=""), delimiter="\t")
    for row_number, row in enumerate(reader):
        if row_number == 0 and row and row[0].strip().casefold() == "from verse":
            continue
        if len(row) != 3:
            skipped_rows += 1
            continue
        from_position = _verse_position(row[0], verse_map)
        target = parse_reference(row[1], verse_map)
        try:
            votes = int(row[2].strip())
        except ValueError:
            votes = None
        if from_position is None or target is None or votes is None:
            skipped_rows += 1
            continue
        key = (from_position, target[0], target[1])
        if key not in rows or votes > rows[key]:
            rows[key] = votes
    return rows, skipped_rows


def _source_licence_notice(source_text: str) -> str:
    """Return the optional licence notice appended to the TSV header."""
    first_line = source_text.splitlines()[0] if source_text.splitlines() else ""
    header = next(csv.reader([first_line], delimiter="\t"), [])
    if not header or header[0].strip().casefold() != "from verse":
        return ""
    notice = "\t".join(header[3:]).strip()
    if notice and "cc-by" not in notice.casefold():
        raise ValueError(f"Unexpected source licence notice: {notice}")
    return notice


def _write_database(
    output_path: Path,
    rows: dict[tuple[int, int, int], int],
    skipped_rows: int,
    source_name: str,
    source_sha256: str,
    source_licence_notice: str,
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(output_path) as connection:
        connection.executescript(
            """
            PRAGMA journal_mode=OFF;
            PRAGMA synchronous=OFF;
            CREATE TABLE crossrefs (
                from_vi  INTEGER NOT NULL,
                to_start INTEGER NOT NULL,
                to_end   INTEGER NOT NULL,
                votes    INTEGER NOT NULL,
                PRIMARY KEY (from_vi, to_start, to_end)
            ) WITHOUT ROWID;
            CREATE TABLE meta (key TEXT PRIMARY KEY, value TEXT);
            """
        )
        connection.executemany(
            "INSERT INTO crossrefs (from_vi, to_start, to_end, votes) "
            "VALUES (?, ?, ?, ?)",
            [(*key, votes) for key, votes in rows.items()],
        )
        built_utc = datetime.now(UTC).isoformat(timespec="seconds")
        metadata = {
            "schema_version": "1",
            "source": f"OpenBible.info {source_name}",
            "source_url": SOURCE_URL,
            "licence": (
                f"{LICENCE}; source header: {source_licence_notice}"
                if source_licence_notice else LICENCE
            ),
            "attribution": ATTRIBUTION,
            "source_sha256": source_sha256,
            "rows": str(len(rows)),
            "skipped_rows": str(skipped_rows),
            "built_utc": built_utc,
        }
        connection.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            metadata.items(),
        )
        connection.commit()
        connection.execute("VACUUM")


def build(input_path: Path, output_path: Path, info_path: Path) -> dict[str, int]:
    """Convert source cross-references into SQLite and return build counts."""
    source_bytes, source_name = _read_source(input_path)
    source_text = source_bytes.decode("utf-8-sig")
    source_licence_notice = _source_licence_notice(source_text)
    verse_map = build_verse_index_map(info_path)
    rows, skipped_rows = _parse_rows(source_text, verse_map)
    _write_database(
        output_path,
        rows,
        skipped_rows,
        source_name,
        hashlib.sha256(source_bytes).hexdigest(),
        source_licence_notice,
    )
    stats = {"rows": len(rows), "skipped_rows": skipped_rows}
    print(f"Cross-reference rows : {stats['rows']:,}")
    print(f"Skipped rows          : {stats['skipped_rows']:,}")
    print(f"Output size           : {output_path.stat().st_size:,} bytes -> {output_path}")
    return stats


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build openbible-crossrefs.sqlite from OpenBible.info TSV data."
    )
    parser.add_argument(
        "--input", type=Path, required=True,
        help="OpenBible cross_references.zip or plain TSV file.",
    )
    parser.add_argument(
        "--output", type=Path, default=DEFAULT_OUTPUT,
        help=f"Destination SQLite file (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--info", type=Path, default=DEFAULT_INFO,
        help=f"Path to Abib's Info.txt (default: {DEFAULT_INFO}).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        build(args.input, args.output, args.info)
    except (OSError, UnicodeError, ValueError, sqlite3.Error) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())