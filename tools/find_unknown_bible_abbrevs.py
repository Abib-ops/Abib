#!/usr/bin/env python3

# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""
Tool: find_unknown_bible_abbrevs.py

Purpose:
    Scan the "Other Works" corpus for Scripture references and report any
    book abbreviations not present in shared.py's `bibledict`.

What's new:
    - Supports older dotted/roman formats such as "Book. iii. 16.", or
      "1 Cor. xiii. 4–7." in addition to modern forms like "Jn 3:16".
    - Normalises the captured book token (lowercase, remove spaces/periods,
      convert leading roman I/II/III → 1/2/3) before checking against
      `bibledict`.

Usage:
    PowerShell (from project root):
        python .\find_unknown_bible_abbrevs.py
        python .\find_unknown_bible_abbrevs.py "C:\\Path\\To\\Other Works"

Output:
    Writes unknown_bible_abbreviations.csv in the project root with columns:
      normalized_key, raw_forms, count, example_file, line, snippet
"""

from __future__ import annotations

import re
import sys
import csv
from pathlib import Path

# Ensure the project root is on sys.path when run from tools/
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Try to import bibledict from shared.py in the same project
try:
    from shared import bibledict
except Exception as e:
    print(f"Error importing bibledict from shared.py: {e}")
    print("Ensure this script is placed next to shared.py or adjust sys.path accordingly.")
    sys.exit(1)


# ----- Configuration -----
BASE_DIR = Path(__file__).resolve().parents[1]
# Default folder to scan
OTHER_WORKS_DIR = BASE_DIR / "Other Works"

# File extensions to include
INCLUDE_EXTS = {".txt", ".md", ".rst", ".markdown", ".csv", ".htm", ".html"}

# Output report path
OUTPUT_CSV = BASE_DIR / "unknown_bible_abbreviations.csv"


# Build a normalised key set from bibledict for fast membership testing
KNOWN = {k.lower() for k in bibledict.keys()}


# Regex to catch modern-style references: Book token followed by chapter/verse
# Examples: "Jn 3:16", "1 Cor. 13", "REV 21:1-5"
BOOK_TOKEN = r"(?:(?:[1-3]|i{1,3})\s*)?[A-Za-z][A-Za-z\.]{0,23}"

MODERN_LOOKAHEAD = (
    r"(?=\s*\d{1,3}"  # chapter
    r"(?::\d{1,3})?"   # optional :verse
    r"(?:[\-–]\d{1,3}(?::\d{1,3})?)?"  # optional range
    r")"
)

BOOK_REF_MODERN = re.compile(rf"\b({BOOK_TOKEN})\s*{MODERN_LOOKAHEAD}")


# Regex to catch the older dotted/roman format: "Book. roman_chapter. decimal_verse." (range optional)
# Examples: "Jn. iii. 16.", "1 Cor. xiii. 4–7.", "Rev. xxi. 1-5."
ROMAN = r"[ivxlcdmIVXLCDM]{1,8}"
DIGITS = r"\d{1,3}"
OLD_PATTERN = (
    rf"\b({BOOK_TOKEN})\.?"       # capture Book (allow an optional trailing dot right after token)
    rf"\s*\.\s*{ROMAN}\s*\."      # dot, roman chapter, dot
    rf"\s*{DIGITS}"               # arabic verse
    rf"(?:\s*[\-–]\s*{DIGITS})?"  # optional verse range
    rf"\s*\."                     # trailing dot
)
BOOK_REF_OLD = re.compile(OLD_PATTERN)


ROMAN_LEADING_MAP = {"i": "1", "ii": "2", "iii": "3"}

# Exclusions to reduce false positives that are not book abbreviations
EXCLUDED_NORMALS = {
    # structural words
    "chapter", "chap", "ch",
    "verse", "ver", "vs", "v",
    # pagination
    "p", "pp", "page", "pages",
    # volumes/sections
    "vol", "vols", "volume", "volum", "sect", "section",
    # general words seen near refs
    "book", "bk",
}

# Common roman numerals that often appear as chapter numbers in old styles
ROMAN_EXCLUDE = {
    "i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x",
    "xi", "xii", "xiii", "xiv", "xv", "xvi", "xvii", "xviii", "xix", "xx",
}


def normalize_book_token(token: str) -> str:
    """Normalise a captured book token to the style used in shared.bibledict keys.
    - lowercase
    - strip periods and spaces
    - convert leading roman numerals i/ii/iii to 1/2/3
    """
    # Work with a version that still preserves spaces for roman handling
    t0 = token.strip().lower()
    # Remove the trailing dot that sometimes goes with abbreviations (e.g. "Jn.")
    if t0.endswith('.'):
        t0 = t0[:-1]
    # Prefer converting leading roman numerals only when separated by a space
    m_roman = re.match(r"^(i{1,3})\s+(.*)$", t0)
    if m_roman:
        lead, rest = m_roman.groups()
        t0 = f"{ROMAN_LEADING_MAP.get(lead, lead)} {rest}"
    else:
        # Also support arabic 1-3 with or without a space (e.g. "1 Cor" or "1Cor")
        m_arabic = re.match(r"^([1-3])\s*(.*)$", t0)
        if m_arabic:
            lead, rest = m_arabic.groups()
            t0 = f"{lead}{rest}"

    # Finally, strip periods and spaces to create the normalised key
    t = t0.replace('.', '').replace(' ', '')
    return t


def is_excluded(norm: str) -> bool:
    """Return True if the token should be ignored as a non-book abbreviation."""
    if not norm:
        return True
    # Already known is not excluded here; this helper is used only for unknowns
    # Skip common non-book tokens
    if norm in EXCLUDED_NORMALS:
        return True
    # Skip pure digits (line/section numbers)
    if norm.isdigit():
        return True
    # Skip common roman numerals that likely denote chapters in old style refs
    if norm in ROMAN_EXCLUDE:
        return True
    # Skip single letters (e.g. p.) unless they are known book keys (handled elsewhere)
    if len(norm) == 1:
        return True
    return False


def iter_text_files(root: Path):
    if not root.exists():
        return
    for p in root.rglob("*"):
        if p.is_file() and p.suffix.lower() in INCLUDE_EXTS:
            yield p


def scan_line_for_unknowns(line: str):
    """Yield (norm, raw_token, span_start, span_end) for each unknown book token found in the line."""
    # Check modern references
    for m in BOOK_REF_MODERN.finditer(line):
        raw = m.group(1)
        norm = normalize_book_token(raw)
        if norm not in KNOWN and not is_excluded(norm):
            yield norm, raw, m.start(), m.end()

    # Check old dotted/roman references
    for m in BOOK_REF_OLD.finditer(line):
        raw = m.group(1)
        norm = normalize_book_token(raw)
        if norm not in KNOWN and not is_excluded(norm):
            yield norm, raw, m.start(), m.end()


def scan_file(path: Path):
    """Return a list of (unknown_key, raw_token, line_no, snippet) for unknown book tokens in a file."""
    results = []
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        try:
            text = path.read_text(encoding="latin-1", errors="replace")
        except OSError:
            return results

    for i, line in enumerate(text.splitlines(), 1):
        for norm, raw, s, ea in scan_line_for_unknowns(line):
            start = max(0, s - 40)
            end = min(len(line), ea + 40)
            snippet = line[start:end].strip()
            results.append((norm, raw, i, snippet))
    return results


def main():
    if len(sys.argv) > 1:
        root = Path(sys.argv[1])
    else:
        root = OTHER_WORKS_DIR

    if not root.exists():
        print(f"Directory not found: {root}")
        print("Usage: python find_unknown_bible_abbrevs.py <path-to-Other-Works-dir>")
        sys.exit(2)

    unknown_map: dict[str, dict] = {}

    for f in iter_text_files(root):
        findings = scan_file(f)
        for norm, raw, line_no, snippet in findings:
            bucket = unknown_map.setdefault(norm, {"raw": set(), "count": 0, "examples": []})
            bucket["raw"].add(raw)
            bucket["count"] += 1
            if len(bucket["examples"]) < 10:
                bucket["examples"].append((str(f), line_no, snippet))

    if not unknown_map:
        print("No unknown book abbreviations found.")
        return

    with OUTPUT_CSV.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.writer(fh)
        writer.writerow(["normalized_key", "raw_forms", "count", "example_file", "line", "snippet"])
        for norm, data in sorted(unknown_map.items(), key=lambda kv: (-kv[1]["count"], kv[0])):
            raw_forms = "; ".join(sorted(data["raw"]))
            if data["examples"]:
                for file_path, line_no, snippet in data["examples"]:
                    writer.writerow([norm, raw_forms, data["count"], file_path, line_no, snippet])
            else:
                writer.writerow([norm, raw_forms, data["count"], "", "", ""]) 

    print(f"Report written to: {OUTPUT_CSV.resolve()}")


if __name__ == "__main__":
    main()
