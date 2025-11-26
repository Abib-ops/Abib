#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build a precise index for Calvin commentaries, mapping Bible book→chapter→verse
to character offsets within the Calvin text files.

Output: Calvin/calvin_index.json

The index is designed for Abib.py commentary() integration. If present, Abib
will open the correct Calvin volume and jump directly to the nearest verse or
chapter via TextDocumentWindow.goto_char_offset().

Heuristics:
- Normalises all files to LF before scanning; offsets match the app's loader.
- Detects chapter boundaries via headings like:
  "Chapter N", "CHAPTER N", "PSALM N", and also lines like "Genesis 24:1-67".
- Detects verse anchors within a chapter by lines such as
  "Verse N", "VER. N", or leading "N."/"N)" at the start of a paragraph.
- Multi-volume works are supported; the index stores the exact file for each chapter.
  If a verse offset is not found, a chapter-level offset is used as a fallback.

Usage:
  python tools/build_calvin_index.py
  python tools/build_calvin_index.py --calvin "Calvin" --out "Calvin/calvin_index.json"

This script is safe to run multiple times. It overwrites the output file.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

# Allow running from anywhere
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in __import__('sys').path:
    __import__('sys').path.insert(0, str(PROJECT_ROOT))

from roman import fromRoman, InvalidRomanNumeralError  # type: ignore


# The UI book names as used by Abib.nwin (keys expected by Abib.commentary lookup)
UI_BOOKS: List[str] = [
    'Genesis', 'Exodus', 'Leviticus', 'Numbers', 'Deuteronomy',
    'Joshua', 'Judges', 'Ruth', 'I Samuel', 'II Samuel', 'I Kings',
    'II Kings', 'I Chronicles', 'II Chronicles', 'Ezra', 'Nehemiah',
    'Esther', 'Job', 'Psalms', 'Proverbs', 'Ecclesiastes',
    'Song of Solomon', 'Isaiah', 'Jeremiah', 'Lamentations',
    'Ezekiel', 'Daniel', 'Hosea', 'Joel', 'Amos', 'Obadiah', 'Jonah',
    'Micah', 'Nahum', 'Habakkuk', 'Zephaniah', 'Haggai', 'Zechariah',
    'Malachi', 'Matthew', 'Mark', 'Luke', 'John', 'Acts', 'Romans',
    'I Corinthians', 'II Corinthians', 'Galatians', 'Ephesians',
    'Philippians', 'Colossians', 'I Thessalonians',
    'II Thessalonians', 'I Timothy', 'II Timothy', 'Titus',
    'Philemon', 'Hebrews', 'James', 'I Peter', 'II Peter', 'I John',
    'II John', 'III John', 'Jude', 'Revelation'
]


def normalize_text(s: str) -> str:
    return s.replace('\r\n', '\n').replace('\r', '\n')


def ui_to_numeric(book: str) -> str:
    if book.startswith('III '):
        return '3 ' + book[4:]
    if book.startswith('II '):
        return '2 ' + book[3:]
    if book.startswith('I '):
        return '1 ' + book[2:]
    return book


def numeric_to_ui(book: str) -> str:
    if book.startswith('3 '):
        return 'III ' + book[2:]
    if book.startswith('2 '):
        return 'II ' + book[2:]
    if book.startswith('1 '):
        return 'I ' + book[2:]
    return book


def make_book_alt_map() -> Tuple[Dict[str, List[str]], Dict[str, str]]:
    """Return (book_name_variants_map, alt_to_ui_map)."""
    variants: Dict[str, List[str]] = {}
    alt_to_ui: Dict[str, str] = {}
    for ui in UI_BOOKS:
        alts = {ui, ui_to_numeric(ui)}
        variants[ui] = list(alts)
        for a in alts:
            alt_to_ui[a] = ui
    return variants, alt_to_ui


BOOK_VARIANTS, ALT_TO_UI = make_book_alt_map()


def build_patterns() -> Tuple[re.Pattern, re.Pattern, re.Pattern]:
    # Order longer names first to prefer them in alternation
    all_names = sorted({a for v in BOOK_VARIANTS.values() for a in v}, key=lambda s: -len(s))
    # Escape spaces and special chars
    names_pat = '|'.join(re.escape(n) for n in all_names)
    # e.g., "Genesis 24:1-67" or "1 Samuel 3.1"
    book_and_chapter = re.compile(rf"^\s*(?P<book>{names_pat})\s+(?P<chap>[ivxlcdm]+|\d{{1,3}})\s*[:.]\s*(?P<versestart>\d{{1,3}})?", re.IGNORECASE)
    # CHAPTER or PSALM or LECTURE (Roman or Arabic chapter numbers)
    # Note: LECTURE used mainly in Proverbs; treated as a chapter-like boundary.
    chapter_heading = re.compile(r"^\s*(?:CHAPTER|Chapter|PSALM|Psalm|LECTURE|Lecture)\s+(?P<num>[ivxlcdm]+|\d{1,3})\b")
    # Verse lines: "Verse 5" or "VER. 5" or leading "5." or "5)"
    verse_line = re.compile(r"^\s*(?:Verse|VER\.)\s+(?P<v1>\d{1,3})\b|^\s*(?P<v2>\d{1,3})[.)]\s+")
    return book_and_chapter, chapter_heading, verse_line


BOOK_AND_CHAP_RE, CHAPTER_RE, VERSE_RE = build_patterns()


def parse_int_maybe_roman(s: str) -> Optional[int]:
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        try:
            return int(s)
        except ValueError:
            return None
    try:
        return int(fromRoman(s.upper()))
    except (InvalidRomanNumeralError, ValueError):
        return None


def index_file(path: Path) -> Dict[str, Any]:
    """Return a partial index for a single Calvin file.
    Structure: { ui_book: { 'chapters': { str(ch): { 'file': filename, 'offset': int, 'verses': { str(v): int } } } } }
    """
    out: Dict[str, Any] = {}
    try:
        raw = path.read_text(encoding='utf-8', errors='replace')
    except OSError:
        return out
    text = normalize_text(raw)
    lines = text.split('\n')
    # Determine the default book by scanning the first 10k chars for any known name
    default_book: Optional[str] = None
    sample = text[:10000]
    for alt, ui in ALT_TO_UI.items():
        if alt in sample:
            default_book = ui
            break

    cur_book: Optional[str] = default_book
    cur_chapter: Optional[int] = None
    # Prepare for absolute offset tracking
    offset = 0

    def ensure_chapter(bk: str, ch: int, ch_offset: int) -> Dict[str, Any]:
        book_entry = out.setdefault(bk, { 'chapters': {} })
        chs = book_entry['chapters']
        key = str(ch)
        if key not in chs:
            chs[key] = { 'file': path.name, 'offset': ch_offset, 'verses': {} }
        else:
            # If we already have a chapter entry but no offset recorded or this is earlier, keep the earliest
            try:
                if int(chs[key].get('offset', ch_offset)) > ch_offset:
                    chs[key]['offset'] = ch_offset
                    chs[key]['file'] = path.name
            except (TypeError, ValueError):
                chs[key]['offset'] = ch_offset
                chs[key]['file'] = path.name
        return chs[key]

    for ln in lines:
        # Book and chapter explicit line
        m = BOOK_AND_CHAP_RE.match(ln)
        if m:
            braw = m.group('book')
            chap_s = m.group('chap')
            b_ui = ALT_TO_UI.get(braw, braw)
            ch_i = parse_int_maybe_roman(chap_s) or 0
            if ch_i > 0:
                cur_book = b_ui
                cur_chapter = ch_i
                # Record chapter offset
                ensure_chapter(cur_book, cur_chapter, offset)
                # Optional: record the verse start if present
                vstart = m.group('versestart')
                if vstart:
                    try:
                        vi = int(vstart)
                        if vi > 0:
                            ch_entry = ensure_chapter(cur_book, cur_chapter, offset)
                            ch_entry['verses'].setdefault(str(vi), offset)
                    except ValueError:
                        pass
            offset += len(ln) + 1
            continue

        # Chapter-like headings (Chapter/PSALM/LECTURE)
        m2 = CHAPTER_RE.match(ln)
        if m2:
            ch_i = parse_int_maybe_roman(m2.group('num'))
            if ch_i and cur_book:
                cur_chapter = ch_i
                ensure_chapter(cur_book, cur_chapter, offset)
            offset += len(ln) + 1
            continue

        # Verse anchors within an established chapter
        if cur_book and cur_chapter:
            m3 = VERSE_RE.match(ln)
            if m3:
                vs = m3.group('v1') or m3.group('v2')
                try:
                    vi = int(vs)
                    if vi > 0:
                        ch_entry = ensure_chapter(cur_book, cur_chapter, offset)
                        ch_entry['verses'].setdefault(str(vi), offset)
                except (TypeError, ValueError):
                    pass
        offset += len(ln) + 1

    return out


def merge_indices(dst: Dict[str, Any], part: Dict[str, Any]) -> None:
    for bk, bdata in part.items():
        tgt_b = dst.setdefault(bk, { 'chapters': {} })
        tchs = tgt_b['chapters']
        for ch, chdata in bdata.get('chapters', {}).items():
            t_ch = tchs.setdefault(ch, { 'file': chdata.get('file'), 'offset': chdata.get('offset', 0), 'verses': {} })
            # Choose the earliest offset/file for the chapter
            try:
                if int(chdata.get('offset', 0)) < int(t_ch.get('offset', 0)):
                    t_ch['offset'] = int(chdata.get('offset', 0))
                    t_ch['file'] = chdata.get('file')
            except (TypeError, ValueError):
                t_ch['offset'] = chdata.get('offset', 0)
                t_ch['file'] = chdata.get('file')
            # Merge verses preserving the first occurrence
            for vv, voff in chdata.get('verses', {}).items():
                if vv not in t_ch['verses']:
                    t_ch['verses'][vv] = voff


def main() -> int:
    parser = argparse.ArgumentParser(description="Build Calvin commentary verse index")
    parser.add_argument('--calvin', default=str(PROJECT_ROOT / 'Calvin'), help='Calvin directory')
    parser.add_argument('--out', default=str(PROJECT_ROOT / 'Calvin' / 'calvin_index.json'), help='Output JSON path')
    args = parser.parse_args()

    calvin_dir = Path(args.calvin)
    out_path = Path(args.out)
    if not calvin_dir.is_dir():
        print(f"Calvin directory not found: {calvin_dir}")
        return 2

    files = sorted(calvin_dir.glob('calcom*.txt'))
    if not files:
        print("No Calvin commentary files found.")
        return 3

    combined: Dict[str, Any] = {}
    for p in files:
        part = index_file(p)
        merge_indices(combined, part)

    payload = {
        'version': 1,
        'generated_in': str(PROJECT_ROOT),
        'entries': combined,
        'files_indexed': [p.name for p in files],
    }

    try:
        out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    except OSError as e:
        print(f"Error writing index: {e}")
        return 4

    print(f"Wrote: {out_path}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
