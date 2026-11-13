# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Build a structural book/chapter/verse-section index for MHCC.txt."""

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any

from project_setup import PROJECT_ROOT

DATA_DIR = PROJECT_ROOT / "src" / "abib" / "data"
DEFAULT_INPUT = DATA_DIR / "Other Works" / "MHCC.txt"
BOOK_RULE_RE = re.compile(r"^\s*_{10,}\s*$")
CHAPTER_RE = re.compile(r"^Chapter\s+(\d+)\s*$", re.IGNORECASE)
SECTION_RE = re.compile(r"^Verses?\s+([\d\s,–—-]+)\s*$", re.IGNORECASE)
VERSE_TOKEN_RE = re.compile(r"(\d+)(?:\s*[-–—]\s*(\d+))?")


def _normalise_book_title(title: str) -> str:
    return re.sub(r"[^a-z0-9]", "", title.casefold())


def _line_text(line: str) -> str:
    return line.rstrip("\r\n")


def _chapter_data(data_path: Path) -> tuple[list[str], dict[str, dict[str, Any]]]:
    try:
        bible_data = json.loads(data_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read Bible data at {data_path}: {exc}") from exc
    if not isinstance(bible_data, dict):
        raise TypeError(f"Bible data must be a JSON object: {data_path}")
    names = list(bible_data)
    return names, bible_data


def _parse_verse_label(label: str) -> tuple[int, int, list[list[int]]] | None:
    match = SECTION_RE.fullmatch(label)
    if match is None:
        return None
    value = match.group(1).strip()
    tokens = re.split(r"\s*,\s*", value)
    ranges: list[list[int]] = []
    for token in tokens:
        token_match = VERSE_TOKEN_RE.fullmatch(token.strip())
        if token_match is None:
            return None
        first = int(token_match.group(1))
        last = int(token_match.group(2) or first)
        if first > last:
            first, last = last, first
        ranges.append([first, last])
    return min(item[0] for item in ranges), max(item[1] for item in ranges), ranges


def _book_titles(lines: list[str], names: list[str]) -> dict[int, tuple[int, str, str]]:
    from abib.core.shared import bibledict
    aliases = {key: value for key, value in bibledict.items()}
    canonical_names = {number: name for number, name in enumerate(names, start=1)}
    candidates: dict[int, tuple[int, str, str]] = {}
    for index, line in enumerate(lines):
        if not BOOK_RULE_RE.fullmatch(_line_text(line)):
            continue
        title_index = index + 1
        while title_index < len(lines) and not _line_text(lines[title_index]).strip():
            title_index += 1
        if title_index >= len(lines):
            continue
        title = _line_text(lines[title_index]).strip()
        number = aliases.get(_normalise_book_title(title))
        if number is not None and number in canonical_names:
            candidates[title_index] = (number, canonical_names[number], title)
    return candidates


def build_index(source_path: Path, bible_path: Path) -> dict[str, Any]:
    try:
        raw_text = source_path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ValueError(f"Could not read source text at {source_path}: {exc}") from exc
    text = raw_text.replace("\r\n", "\n").replace("\r", "\n")
    lines = text.splitlines(keepends=True)
    names, bible_data = _chapter_data(bible_path)
    title_rows = _book_titles(lines, names)
    line_offsets: list[int] = []
    offset = 0
    for line in lines:
        line_offsets.append(offset)
        offset += len(line)

    books: list[dict[str, Any]] = []
    problems: list[dict[str, Any]] = []
    current_book: dict[str, Any] | None = None
    for index, line in enumerate(lines):
        title_info = title_rows.get(index)
        if title_info is not None:
            book_number, book_name, source_title = title_info
            if any(book["book_number"] == book_number for book in books):
                problems.append({
                    "type": "duplicate_book_heading",
                    "book": book_name,
                    "line": index + 1,
                    "message": f"Duplicate heading for {book_name}.",
                })
                current_book = None
                continue
            new_book: dict[str, Any] = {
                "book": book_name,
                "book_number": book_number,
                "heading": source_title,
                "start": line_offsets[index],
                "line": index + 1,
                "chapters": [],
                "_chapter_map": {},
                "_explicit_chapters": set(),
            }
            books.append(new_book)
            current_book = new_book
            continue

        if current_book is None:
            continue
        stripped = _line_text(line).strip()
        chapter_match = CHAPTER_RE.fullmatch(stripped)
        if chapter_match is not None:
            chapter_number = int(chapter_match.group(1))
            chapter_map = current_book["_chapter_map"]
            if chapter_number in chapter_map:
                problems.append({
                    "type": "duplicate_chapter_heading",
                    "book": current_book["book"],
                    "chapter": chapter_number,
                    "line": index + 1,
                    "message": f"Duplicate Chapter {chapter_number} heading.",
                })
                continue
            chapter = {
                "chapter": chapter_number,
                "start": line_offsets[index],
                "line": index + 1,
                "sections": [],
                "_explicit": True,
            }
            chapter_map[chapter_number] = chapter
            current_book["_explicit_chapters"].add(chapter_number)
            current_book["chapters"].append(chapter)
            continue

        section_info = _parse_verse_label(stripped)
        if section_info is None:
            continue
        verse_start, verse_end, verse_ranges = section_info
        chapter_map = current_book["_chapter_map"]
        if not current_book["chapters"]:
            chapter = {
                "chapter": 1,
                "start": line_offsets[index],
                "line": index + 1,
                "sections": [],
                "_explicit": False,
            }
            chapter_map[1] = chapter
            current_book["chapters"].append(chapter)
            problems.append({
                "type": "implicit_chapter_one",
                "book": current_book["book"],
                "chapter": 1,
                "line": index + 1,
                "message": "Verse sections before a Chapter heading were assigned to chapter 1.",
            })
        chapter = current_book["chapters"][-1]
        label = stripped
        chapter["sections"].append({
            "verse_start": verse_start,
            "verse_end": verse_end,
            "verse_ranges": verse_ranges,
            "label": label,
            "start": line_offsets[index],
            "line": index + 1,
        })

        chapter_count = len(bible_data[current_book["book"]])
        if chapter["chapter"] < 1 or chapter["chapter"] > chapter_count:
            problems.append({
                "type": "chapter_out_of_range",
                "book": current_book["book"],
                "chapter": chapter["chapter"],
                "line": index + 1,
                "message": f"Chapter is outside the Bible data range of 1-{chapter_count}.",
            })
            continue
        chapter_verses = bible_data[current_book["book"]][str(chapter["chapter"])]
        max_verse = len(chapter_verses)
        if verse_end > max_verse:
            problems.append({
                "type": "verse_out_of_range",
                "book": current_book["book"],
                "chapter": chapter["chapter"],
                "verse_start": verse_start,
                "verse_end": verse_end,
                "line": index + 1,
                "message": f"Verse section exceeds the chapter's final verse ({max_verse}).",
            })

    for book_index, book in enumerate(books):
        book_end = books[book_index + 1]["start"] if book_index + 1 < len(books) else len(text)
        book["end"] = book_end
        expected_chapters = len(bible_data[book["book"]])
        explicit_chapters = book.pop("_explicit_chapters")
        book.pop("_chapter_map")
        missing_chapters = [n for n in range(1, expected_chapters + 1) if n not in explicit_chapters]
        for missing in missing_chapters:
            problems.append({
                "type": "missing_chapter_heading",
                "book": book["book"],
                "chapter": missing,
                "message": f"No explicit Chapter {missing} heading found in the text.",
            })
        chapters = sorted(book["chapters"], key=lambda item: (item["chapter"], item["start"]))
        for chapter in chapters:
            later_starts = [item["start"] for item in chapters if item["start"] > chapter["start"]]
            chapter["end"] = min(later_starts) if later_starts else book_end
            chapter.pop("_explicit")
            sections = chapter["sections"]
            for section_index, section in enumerate(sections):
                section["end"] = sections[section_index + 1]["start"] if section_index + 1 < len(sections) else chapter["end"]
        book["chapters"] = chapters
        book["chapter_count"] = expected_chapters
        book["explicit_chapter_headings"] = len(explicit_chapters)
        book["missing_chapter_headings"] = missing_chapters

    found_numbers = {book["book_number"] for book in books}
    for number, name in enumerate(names, start=1):
        if number not in found_numbers:
            problems.append({
                "type": "missing_book_heading",
                "book": name,
                "book_number": number,
                "message": f"No book heading found for {name}.",
            })

    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "format": 1,
        "source_file": source_path.name,
        "content_sha256": digest,
        "normalised": "utf8+lf",
        "character_length": len(text),
        "books": books,
        "problems": problems,
    }


def _default_output(input_path: Path) -> Path:
    if input_path.resolve() == DEFAULT_INPUT.resolve():
        directory = DATA_DIR / "Other Works companions"
    elif input_path.parent.name.casefold() == "other works":
        directory = input_path.parent.parent / "Other Works companions"
    else:
        directory = input_path.parent
    return directory / f"{input_path.name}.index.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Index book, chapter and verse headings in MHCC.txt")
    parser.add_argument("--input", "-i", type=Path, default=DEFAULT_INPUT, help="MHCC.txt input file")
    parser.add_argument("--output", "-o", type=Path, default=None, help="Output JSON index path")
    args = parser.parse_args(argv)

    input_path = args.input.expanduser().resolve()
    output_path = (args.output.expanduser().resolve() if args.output else _default_output(input_path))
    bible_path = DATA_DIR / "bible_data.json"
    if not input_path.is_file():
        print(f"ERROR: Input text file does not exist: {input_path}")
        return 2
    try:
        payload = build_index(input_path, bible_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"ERROR: {exc}")
        return 2

    section_count = sum(len(chapter["sections"]) for book in payload["books"] for chapter in book["chapters"])
    print(f"Wrote {output_path}")
    print(f"Indexed {len(payload['books'])} books, "
          f"{sum(len(book['chapters']) for book in payload['books'])} chapters, "
          f"and {section_count} verse sections.")
    print(f"Reported {len(payload['problems'])} validation issue(s).")
    for problem in payload["problems"]:
        where = f"{problem.get('book', '')}"
        if "chapter" in problem:
            where += f" chapter {problem['chapter']}"
        if "line" in problem:
            where += f" line {problem['line']}"
        print(f"- {where}: {problem['message']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())