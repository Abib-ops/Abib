# Copyright 2026 Andrew Kingston
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

"""Build ``strongs.sqlite`` for Abib's Strong's-number / original-language lookup.

This is a one-off, developer-only generator (it is *not* shipped inside the
running application). It consumes the source datasets kept in the external
``bible-llm-reference`` workspace and emits a read-only SQLite database that
mirrors the conventions of Abib's existing ``gill.cmt.sqlite`` file.

Sources (see ``--reference`` / defaults below):
  * ``kjv.json``            - Bolls Bible "KJV (1769) with Strong's Numbers".
                              Each translated word is followed by ``<S>N</S>``
                              tags (bare numbers; ``<sup>...</sup>`` footnotes
                              are ignored). OT books get an ``H`` prefix, NT
                              books a ``G`` prefix.
  * strongs-hebrew-dictionary.js / strongs-greek-dictionary.js
                              - Open Scriptures Strong's dictionaries
                              (CC-BY-SA), wrapped as JS ``var ... = {...};``.

Output schema (``strongs.sqlite``):
  word_tags(verse_index INTEGER, word_pos INTEGER, surface TEXT, strongs TEXT)
  strongs_dict(strongs TEXT PRIMARY KEY, lemma, translit, pronunciation,
               short_def, long_def, language)
  meta(key TEXT PRIMARY KEY, value TEXT)

``verse_index`` is Abib's flat global verse index (0..31100), identical to the
position used by ``sh.Info`` and computed from ``Info.txt``. Strong's codes are
normalised to ``H%04d`` / ``G%04d`` (e.g. ``430`` -> ``H0430``).

Usage (from the project root):
    python tools/build_strongs_sqlite.py
    python tools/build_strongs_sqlite.py --reference C:\\Projects\\bible-llm-reference
    python tools/build_strongs_sqlite.py --output some\\other\\strongs.sqlite
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

from project_setup import SRC_PATH

DEFAULT_REFERENCE = Path(r"C:\Projects\bible-llm-reference")

# Number of leading (comment) lines in Info.txt before verse rows begin.
# Matches abib.core.shared, which parses ``Inf[17:]``.
INFO_HEADER_LINES = 17

# OT books (1..39) use Hebrew (H) Strong's numbers, NT books (40..66) Greek (G).
LAST_OT_BOOK = 39
# Abib only contains the 66 canonical books. The Bolls kjv.json lists these
# first, in order, followed by apocryphal/deuterocanonical books (67..81) which
# Abib does not include; those are skipped.
CANONICAL_BOOK_COUNT = 66

# Expected canonical book names (in order) as they appear in kjv.json, used to
# guard against the source being reordered or apocrypha being interspersed.
CANONICAL_BOOK_NAMES = (
    "Genesis", "Exodus", "Leviticus", "Numbers", "Deuteronomy", "Joshua",
    "Judges", "Ruth", "1 Samuel", "2 Samuel", "1 Kings", "2 Kings",
    "1 Chronicles", "2 Chronicles", "Ezra", "Nehemiah", "Esther", "Job",
    "Psalms", "Proverbs", "Ecclesiastes", "Song of Solomon", "Isaiah",
    "Jeremiah", "Lamentations", "Ezekiel", "Daniel", "Hosea", "Joel", "Amos",
    "Obadiah", "Jonah", "Micah", "Nahum", "Habakkuk", "Zephaniah", "Haggai",
    "Zechariah", "Malachi", "Matthew", "Mark", "Luke", "John", "Acts",
    "Romans", "1 Corinthians", "2 Corinthians", "Galatians", "Ephesians",
    "Philippians", "Colossians", "1 Thessalonians", "2 Thessalonians",
    "1 Timothy", "2 Timothy", "Titus", "Philemon", "Hebrews", "James",
    "1 Peter", "2 Peter", "1 John", "2 John", "3 John", "Jude", "Revelation",
)

# Known upstream tagging omissions in the Bolls kjv.json, corrected here.
#
# The Bolls source occasionally drops the Strong's tag from the final word of a
# verse, so that word survives only as a trailing surface-only row (see
# ``iter_word_tags``).  Where the correct number is well attested by other
# Strong's-tagged KJV editions, it is supplied here so the trailing word is
# tagged like any other.
#
# Keyed by the 0-based ``(book0, chapter0, verse0)`` verse address (matching
# ``Info.txt``) -> the Strong's code for the verse's trailing untagged text.
TRAILING_TAG_CORRECTIONS: dict[tuple[int, int, int], str] = {
    # Proverbs 30:30 "... turneth not away for<S>6440</S> any;" -> "any" = H3605
    # (כֹּל, kol, "all/any"), which Bolls omits.
    (19, 29, 29): "H3605",
}

# Matches a single Strong's tag such as ``<S>430</S>``.
_S_TAG = re.compile(r"<S>(\d+)</S>")
# Editorial footnotes embedded in the Bolls text, e.g. ``<sup>...</sup>``.
_SUP = re.compile(r"<sup>.*?</sup>", re.DOTALL)
# Any residual angle-bracket markup left over after the passes above.
_ANY_TAG = re.compile(r"<[^>]+>")


def build_verse_index_map(info_path: Path) -> dict[tuple[int, int, int], int]:
    """Return {(book0, chapter0, verse0): verse_index} from Info.txt.

    ``verse_index`` is the 0-based row position, exactly as ``sh.Info`` is built.
    Entries in Info.txt are 0-based ``[book0, chapter0, verse0]``.
    """
    lines = info_path.read_text(encoding="utf-8").splitlines()
    rows = lines[INFO_HEADER_LINES:]
    mapping: dict[tuple[int, int, int], int] = {}
    for idx, line in enumerate(rows):
        line = line.strip()
        if not line:
            continue
        inner = line.strip("[]")
        parts = [p.strip() for p in inner.split(",")]
        if len(parts) != 3:
            continue
        try:
            b0, c0, v0 = (int(parts[0]), int(parts[1]), int(parts[2]))
        except ValueError:
            continue
        mapping[(b0, c0, v0)] = idx
    return mapping


def _strip_js_wrapper(text: str) -> str:
    """Strip the Open Scriptures ``var x = {...};`` (CommonJS) wrapper -> JSON."""
    text = re.sub(r"^/\*\*.*?\*/\s*", "", text, flags=re.DOTALL)
    text = re.sub(r"^var\s+\w+\s*=\s*", "", text.strip())
    text = re.sub(r";\s*module\.exports.*$", "", text, flags=re.DOTALL)
    text = re.sub(r";\s*$", "", text)
    return text


def _normalise_code(raw_key: str) -> str | None:
    """Normalise a dictionary key like ``H1`` / ``G1615`` to ``H0001`` / ``G1615``."""
    m = re.match(r"^([HG])0*(\d+)$", raw_key.strip(), re.IGNORECASE)
    if not m:
        return None
    letter = m.group(1).upper()
    return f"{letter}{int(m.group(2)):04d}"


def load_dictionary(js_path: Path, language: str) -> dict[str, dict]:
    """Load an Open Scriptures Strong's dictionary .js file into a dict of rows."""
    raw = json.loads(_strip_js_wrapper(js_path.read_text(encoding="utf-8")))
    out: dict[str, dict] = {}
    for key, entry in raw.items():
        code = _normalise_code(key)
        if code is None:
            continue
        lemma = (entry.get("lemma") or "").strip()
        # Hebrew uses ``xlit`` for the transliteration; Greek uses ``translit``.
        translit = (entry.get("xlit") or entry.get("translit") or "").strip()
        pron = (entry.get("pron") or "").strip()
        short_def = (entry.get("strongs_def") or "").strip()
        derivation = (entry.get("derivation") or "").strip()
        kjv_def = (entry.get("kjv_def") or "").strip()
        long_parts = [p for p in (derivation, kjv_def) if p]
        long_def = "  ".join(long_parts)
        out[code] = {
            "strongs": code,
            "lemma": lemma,
            "translit": translit,
            "pronunciation": pron,
            "short_def": short_def,
            "long_def": long_def,
            "language": language,
        }
    return out


def iter_word_tags(kjv_path: Path, verse_map: dict[tuple[int, int, int], int]):
    """Yield (verse_index, word_pos, surface, strongs) rows from kjv.json.

    Also returns a small stats dict via the generator's ``return`` value.
    """
    data = json.loads(kjv_path.read_text(encoding="utf-8"))
    tag_rows = 0
    verses_seen = 0
    verses_unmapped = 0

    for book_num, book in enumerate(data.get("books", []), start=1):
        # Abib has no apocrypha; only the 66 canonical books (listed first).
        if book_num > CANONICAL_BOOK_COUNT:
            break
        name = str(book.get("name", ""))
        expected = CANONICAL_BOOK_NAMES[book_num - 1]
        if name != expected:
            raise SystemExit(
                f"Error: unexpected book order in kjv.json: position {book_num} "
                f"is {name!r} but expected {expected!r}. The canonical books must "
                f"appear first, in order.")
        letter = "H" if book_num <= LAST_OT_BOOK else "G"
        for chapter in book.get("chapters", []):
            c0 = int(chapter.get("chapter", 0)) - 1
            for verse in chapter.get("verses", []):
                verses_seen += 1
                v0 = int(verse.get("verse", 0)) - 1
                b0 = book_num - 1
                vi = verse_map.get((b0, c0, v0))
                if vi is None:
                    verses_unmapped += 1
                    continue
                text = _SUP.sub("", verse.get("text", ""))
                word_pos = 0
                last_end = 0
                for m in _S_TAG.finditer(text):
                    chunk = text[last_end:m.start()]
                    last_end = m.end()
                    surface = _ANY_TAG.sub("", chunk).strip()
                    strongs = f"{letter}{int(m.group(1)):04d}"
                    yield vi, word_pos, surface, strongs
                    word_pos += 1
                    tag_rows += 1
                # Capture any trailing text after the final Strong's tag (e.g.
                # the word "any" in Proverbs 30:30, "... for<S>6440</S> any;").
                # Without this such trailing words are silently dropped. It is
                # stored as a surface-only row with an empty Strong's code, so
                # the reader can still show the word while it never matches a
                # Strong's-number search.
                trailing = _ANY_TAG.sub("", text[last_end:]).strip()
                if trailing:
                    # Supply a known-missing Strong's number for the trailing
                    # word where the upstream source omitted it (see
                    # TRAILING_TAG_CORRECTIONS); otherwise leave the code empty.
                    correction = TRAILING_TAG_CORRECTIONS.get((b0, c0, v0), "")
                    yield vi, word_pos, trailing, correction
                    word_pos += 1
                    tag_rows += 1

    return {
        "tag_rows": tag_rows,
        "verses_seen": verses_seen,
        "verses_unmapped": verses_unmapped,
    }


def build(reference: Path, output: Path, info_path: Path) -> None:
    kjv_path = reference / "kjv.json"
    heb_path = reference / "strongs_data" / "hebrew" / "strongs-hebrew-dictionary.js"
    grk_path = reference / "strongs_data" / "greek" / "strongs-greek-dictionary.js"

    for p in (kjv_path, heb_path, grk_path, info_path):
        if not p.exists():
            raise SystemExit(f"Error: required source not found: {p}")

    print(f"Reading verse index from {info_path}...")
    verse_map = build_verse_index_map(info_path)
    print(f"  {len(verse_map):,} verse positions loaded.")

    print("Loading Strong's dictionaries...")
    strongs_dict = load_dictionary(heb_path, "hebrew")
    grk = load_dictionary(grk_path, "greek")
    strongs_dict.update(grk)
    print(f"  {len(strongs_dict):,} dictionary entries "
          f"(Hebrew + Greek) loaded.")

    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists():
        output.unlink()

    print(f"Writing {output}...")
    conn = sqlite3.connect(str(output))
    try:
        cur = conn.cursor()
        cur.execute("PRAGMA journal_mode=OFF")
        cur.execute("PRAGMA synchronous=OFF")
        cur.executescript(
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
            CREATE TABLE meta (
                key   TEXT PRIMARY KEY,
                value TEXT
            );
            """
        )

        cur.executemany(
            "INSERT INTO strongs_dict "
            "(strongs, lemma, translit, pronunciation, short_def, long_def, language) "
            "VALUES (:strongs, :lemma, :translit, :pronunciation, :short_def, "
            ":long_def, :language)",
            list(strongs_dict.values()),
        )

        gen = iter_word_tags(kjv_path, verse_map)
        stats: dict[str, int] = {}

        def _drain():
            # Wrap the generator so we can capture its StopIteration.value (stats).
            nonlocal stats
            while True:
                try:
                    yield next(gen)
                except StopIteration as stop:
                    if isinstance(stop.value, dict):
                        stats = stop.value
                    return

        cur.executemany(
            "INSERT INTO word_tags (verse_index, word_pos, surface, strongs) "
            "VALUES (?, ?, ?, ?)",
            _drain(),
        )

        cur.executescript(
            """
            CREATE INDEX idx_word_tags_verse ON word_tags(verse_index);
            CREATE INDEX idx_word_tags_strongs ON word_tags(strongs);
            """
        )

        cur.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [
                ("schema_version", "1"),
                ("source_text", "Bolls Bible KJV (1769) with Strong's Numbers"),
                ("source_dictionary",
                 "Open Scriptures Strong's Hebrew & Greek (CC-BY-SA)"),
                ("dictionary_entries", str(len(strongs_dict))),
                ("word_tags", str(stats.get("tag_rows", 0))),
            ],
        )

        conn.commit()

        # Optimise the read-only artefact for shipping.
        cur.execute("VACUUM")
        conn.commit()
    finally:
        conn.close()

    print("Done.")
    print(f"  word_tags rows      : {stats.get('tag_rows', 0):,}")
    print(f"  verses processed    : {stats.get('verses_seen', 0):,}")
    print(f"  verses unmapped     : {stats.get('verses_unmapped', 0):,}")
    print(f"  dictionary entries  : {len(strongs_dict):,}")
    size_mb = output.stat().st_size / (1024 * 1024)
    print(f"  output size         : {size_mb:.1f} MB -> {output}")


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate strongs.sqlite for Abib from the "
                    "bible-llm-reference datasets.")
    parser.add_argument(
        "--reference", type=Path, default=DEFAULT_REFERENCE,
        help=f"Path to the bible-llm-reference workspace "
             f"(default: {DEFAULT_REFERENCE}).")
    parser.add_argument(
        "--output", type=Path,
        default=SRC_PATH / "abib" / "data" / "strongs.sqlite",
        help="Destination .sqlite path "
             "(default: src/abib/data/strongs.sqlite).")
    parser.add_argument(
        "--info", type=Path,
        default=SRC_PATH / "abib" / "data" / "Info.txt",
        help="Path to Abib's Info.txt (default: src/abib/data/Info.txt).")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    build(args.reference, args.output, args.info)


if __name__ == "__main__":
    main()
