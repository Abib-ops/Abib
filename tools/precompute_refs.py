#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Precompute scripture-reference companion files for texts in "Other Works".

This script scans each .txt file in the input directory (default: project_root/Other Works),
finds scripture references using the same parser as the app, and writes a compact,
compressed JSON companion file to the output directory (default: project_root/Other Works companions).

Companion file schema (format = 1):
{
  "format": 1,
  "parser_version": "2025-11-21a",
  "source_file": "Works of Jonathan Edwards Vol II.txt",
  "content_sha256": "<hex of normalised UTF-8 text>",
  "byte_length": 12345678,
  "normalised": "utf8+lf",
  "refs": [
    {"abs_start": 123, "length": 14, "book": "John", "chapter": 3, "verse": "16", "text": "John 3:16"}
    ...
  ]
}

Usage examples:
  python tools/precompute_refs.py
  python tools/precompute_refs.py --input "Other Works" --output "Other Works companions"
  python tools/precompute_refs.py --force

Notes:
- Normalisation matches the app: CRLF/CR are converted to LF before scanning and hashing.
- Output files are named "<source>.refs.json.gz" placed in the output directory.
- Existing companions are reused if content_sha256 and parser_version already match; use --force to rebuild.

Recommended practice: when to bump PARSER_VERSION
Bump the constant whenever any change could alter the produced reference set or their offsets,
even if precompute_refs.py itself didn’t change.

Examples:
•
Modify scripture.find_scripture_references patterns/logic (e.g. the recent no-newline regex change).
•
Change normalisation that affects offsets (e.g. normalize_text policy).
•
Change continuation handling, book normalisation, or mappings that affect book IDs or names.
•
Any change that would alter refs content (text, chapter/verse values, start/length) in the companion files.
You do not need to bump it for:
•
Purely cosmetic refactoring of precompute_refs.py that doesn’t affect output.
•
Input file content changes: those are detected via content_sha256 and will trigger rebuilds even without a version bump.

"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

# Ensure we can import local project modules when run from anywhere
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import scripture  # type: ignore


PARSER_VERSION = "2025-12-23-suppress-chapter-only-v2"
FORMAT_VERSION = 1


def normalize_text(s: str) -> str:
    """Match the app's normalisation so offsets/lengths align exactly."""
    return s.replace("\r\n", "\n").replace("\r", "\n")


def compute_sha256_utf8(text: str) -> str:
    data = text.encode("utf-8", errors="replace")
    return hashlib.sha256(data).hexdigest()


def load_existing_companion(path: Path) -> Dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        with gzip.open(path, "rt", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, gzip.BadGzipFile, UnicodeError, json.JSONDecodeError, ValueError):
        return None


def build_companion_payload(txt_path: Path, content: str, refs: List[Dict[str, Any]]) -> Dict[str, Any]:
    content_hash = compute_sha256_utf8(content)
    try:
        byte_length = txt_path.stat().st_size
    except OSError:
        byte_length = 0
    out_refs: List[Dict[str, Any]] = []
    for r in refs:
        # scripture.find_scripture_references returns 'start' (absolute) and 'length'
        try:
            abs_start = int(r.get("start", 0))
            length = int(r.get("length", 0))
        except (ValueError, TypeError, AttributeError):
            continue
        out_refs.append(
            {
                "abs_start": abs_start,
                "length": length,
                "book": r.get("book"),
                "chapter": r.get("chapter"),
                "verse": r.get("verse"),
                "text": r.get("text", ""),
            }
        )

    payload: Dict[str, Any] = {
        "format": FORMAT_VERSION,
        "parser_version": PARSER_VERSION,
        "source_file": txt_path.name,
        "content_sha256": content_hash,
        "byte_length": byte_length,
        "normalized": "utf8+lf",
        "refs": out_refs,
    }
    return payload


def write_companion(output_dir: Path, base_name: str, payload: Dict[str, Any]) -> Path:
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / f"{base_name}.refs.json.gz"
    with gzip.open(out_path, "wt", encoding="utf-8") as f:
        # Use dumps and write to satisfy type checkers expecting SupportsWrite[str]
        data = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        f.write(data)
    return out_path


def _build_bible_data() -> Dict[str, Any]:
    """Build bible_data structure expected by scripture.lookup_scripture.

    Shape: { CanonicalBookName: { chapter_str: { verse_str: text }}}
    """
    # Lazy imports to avoid hard dependency when the module is imported elsewhere
    from services.data_loader import DataLoader  # type: ignore
    import shared as sh  # type: ignore
    import scripture as _scripture  # type: ignore

    loader = DataLoader(PROJECT_ROOT)
    bible = loader.load_bible()
    KJV = bible.KJV
    can = _scripture.CANONICAL_BOOKS

    bible_data: Dict[str, Dict[str, Dict[str, str]] ] = {}
    # sh.Info aligns 1:1 with KJV after copyright trimming in DataLoader
    for idx, triple in enumerate(sh.Info):
        try:
            book_id, chap_idx, verse_idx = int(triple[0]), int(triple[1]), int(triple[2])
        except (ValueError, TypeError, IndexError):
            continue
        book_name = can.get(book_id + 1)
        if not book_name:
            continue
        chap = str(chap_idx + 1)
        verse = str(verse_idx + 1)
        verse_text = KJV[idx] if 0 <= idx < len(KJV) else ""
        bible_data.setdefault(book_name, {}).setdefault(chap, {})[verse] = verse_text
    return bible_data


def process_one(
    txt_path: Path,
    output_dir: Path,
    force: bool = False,
    bible_data: Dict[str, Any] | None = None,
    csv_rows: List[Dict[str, Any]] | None = None,
) -> tuple[bool, str]:
    """Process a single .txt file. Returns (changed, message)."""
    try:
        raw = txt_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, f"ERROR reading {txt_path.name}: {e}"

    content = normalize_text(raw)
    # Helper to compute 1-based line number from absolute character offset in normalised content
    def _line_from_offset(offset: Any) -> int:
        try:
            pos = int(offset)
        except (TypeError, ValueError):
            return 0
        if pos <= 0:
            return 1 if content else 0
        if pos > len(content):
            pos = len(content)
        # Count newlines up to the offset; lines are 1-based
        return content.count("\n", 0, pos) + 1
    base_name = txt_path.name  # keep extension in base for clarity in the output name
    out_path = output_dir / f"{base_name}.refs.json.gz"

    if out_path.exists() and not force:
        existing = load_existing_companion(out_path)
        if existing and (
            existing.get("format") == FORMAT_VERSION
            and existing.get("parser_version") == PARSER_VERSION
            and existing.get("content_sha256") == compute_sha256_utf8(content)
        ):
            return False, f"Up-to-date: {base_name}"

    # Find references using the shared parser
    refs = scripture.find_scripture_references(content)  # type: ignore

    # Validate refs and collect problems for reporting
    problems: List[Dict[str, Any]] = []
    for r in refs:
        try:
            book = r.get("book")
            chapter = r.get("chapter")
            verses = r.get("verse")
            # Normalisation/lookup check
            from scripture import normalize_book_input  # local import for clarity
            import shared as sh  # type: ignore

            key = normalize_book_input(str(book)) if isinstance(book, str) else None
            book_id = sh.bibledict.get(key) if key else None
            if not book_id:
                prob = {
                    "type": "unknown_book",
                    "book": book,
                    "chapter": chapter,
                    "verse": verses,
                    "pos": r.get("start"),
                    "text": r.get("text", ""),
                }
                problems.append(prob)
                if csv_rows is not None:
                    csv_rows.append({
                        "file": txt_path.name,
                        "type": prob["type"],
                        "book": str(book),
                        "chapter": str(chapter),
                        "verse": str(verses),
                        "line": str(_line_from_offset(r.get("start"))),
                        "message": "Book not recognised",
                        "text": r.get("text", ""),
                    })
                continue

            # Basic chapter validation
            if not isinstance(chapter, int) or chapter <= 0:
                prob = {
                    "type": "invalid_chapter",
                    "book_id": book_id,
                    "book": book,
                    "chapter": chapter,
                    "verse": verses,
                    "pos": r.get("start"),
                    "text": r.get("text", ""),
                }
                problems.append(prob)
                if csv_rows is not None:
                    csv_rows.append({
                        "file": txt_path.name,
                        "type": prob["type"],
                        "book": str(book),
                        "chapter": str(chapter),
                        "verse": str(verses),
                        "line": str(_line_from_offset(r.get("start"))),
                        "message": "Invalid or missing chapter",
                        "text": r.get("text", ""),
                    })
                continue

            # Extract the first verse number if present
            import re as _re
            first_match = _re.search(r"\d+", str(verses) if verses is not None else "")
            if not first_match:
                prob = {
                    "type": "invalid_verse",
                    "book_id": book_id,
                    "book": book,
                    "chapter": chapter,
                    "verse": verses,
                    "pos": r.get("start"),
                    "text": r.get("text", ""),
                }
                problems.append(prob)
                if csv_rows is not None:
                    csv_rows.append({
                        "file": txt_path.name,
                        "type": prob["type"],
                        "book": str(book),
                        "chapter": str(chapter),
                        "verse": str(verses),
                        "line": str(_line_from_offset(r.get("start"))),
                        "message": "Invalid or missing verse",
                        "text": r.get("text", ""),
                    })
                continue

            # Lookup using bible_data if provided
            if bible_data is not None:
                from scripture import lookup_scripture  # type: ignore
                out = lookup_scripture(bible_data, str(book), int(chapter), str(verses))
                out_str = (out or "").strip()
                if out_str == "Scripture not found.":
                    prob = {
                        "type": "scripture_not_found",
                        "book_id": book_id,
                        "book": book,
                        "chapter": chapter,
                        "verse": verses,
                        "pos": r.get("start"),
                        "text": r.get("text", ""),
                    }
                    problems.append(prob)
                    if csv_rows is not None:
                        csv_rows.append({
                            "file": txt_path.name,
                            "type": prob["type"],
                            "book": str(book),
                            "chapter": str(chapter),
                            "verse": str(verses),
                            "line": str(_line_from_offset(r.get("start"))),
                            "message": out_str,
                            "text": r.get("text", ""),
                        })
                else:
                    # Check for partial failures like "Verse N not found". lines
                    missing_lines = [ln for ln in out_str.splitlines() if ln.strip().startswith("Verse ") and ln.strip().endswith("not found.")]
                    if missing_lines:
                        prob = {
                            "type": "verse_missing",
                            "book_id": book_id,
                            "book": book,
                            "chapter": chapter,
                            "verse": verses,
                            "pos": r.get("start"),
                            "text": r.get("text", ""),
                            "details": missing_lines,
                        }
                        problems.append(prob)
                        if csv_rows is not None:
                            csv_rows.append({
                                "file": txt_path.name,
                                "type": prob["type"],
                                "book": str(book),
                                "chapter": str(chapter),
                                "verse": str(verses),
                                "line": str(_line_from_offset(r.get("start"))),
                                "message": "; ".join(missing_lines),
                                "text": r.get("text", ""),
                            })
        except Exception as e:  # extremely defensive to avoid aborting the run
            prob = {
                "type": "exception",
                "error": str(e),
                "ref": {k: r.get(k) for k in ("book", "chapter", "verse", "start", "length", "text")},
            }
            problems.append(prob)
            if csv_rows is not None:
                csv_rows.append({
                    "file": txt_path.name,
                    "type": prob.get("type", "exception"),
                    "book": str(r.get("book")),
                    "chapter": str(r.get("chapter")),
                    "verse": str(r.get("verse")),
                    "line": str(_line_from_offset(r.get("start"))),
                    "message": str(e),
                    "text": r.get("text", ""),
                })

    payload = build_companion_payload(txt_path, content, refs)
    if problems:
        payload["problems"] = problems
    try:
        write_companion(output_dir, base_name, payload)
    except Exception as e:
        return False, f"ERROR writing companion for {base_name}: {e}"
    summary = f"Wrote: {out_path.name} (refs: {len(payload.get('refs', []))}"
    if problems:
        summary += f", problems: {len(problems)}"
    summary += ")"
    return True, summary


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate companion files for Other Works texts")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=str(PROJECT_ROOT / "Other Works"),
        help="Input directory containing .txt files (default: project_root/Other Works)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=str(PROJECT_ROOT / "Other Works companions"),
        help="Output directory for companions (default: project_root/Other Works companions)",
    )
    parser.add_argument(
        "--force",
        "-f",
        action="store_true",
        help="Rebuild companions even if an up-to-date file exists",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Optional path for CSV report of reference problems (defaults to '<output>/scripture_problems.csv')",
    )
    args = parser.parse_args(argv)

    in_dir = Path(args.input).resolve()
    out_dir = Path(args.output).resolve()

    if not in_dir.exists() or not in_dir.is_dir():
        print(f"ERROR: Input directory does not exist: {in_dir}")
        return 2

    txt_files = sorted(p for p in in_dir.glob("*.txt") if p.is_file())
    if not txt_files:
        print(f"No .txt files found in: {in_dir}")
        out_dir.mkdir(parents=True, exist_ok=True)
        return 0

    print(f"Input:  {in_dir}")
    print(f"Output: {out_dir}")
    print(f"Parser: {PARSER_VERSION}\n")

    # Build bible_data once for all lookups
    bible_data = _build_bible_data()

    # Prepare CSV rows collection
    csv_rows: List[Dict[str, Any]] = []

    changed = 0
    for p in txt_files:
        did_change, msg = process_one(p, out_dir, force=args.force, bible_data=bible_data, csv_rows=csv_rows)
        print(msg)
        if did_change:
            changed += 1

    # Write CSV if there are any rows
    if csv_rows:
        csv_path = Path(args.csv) if args.csv else (out_dir / "scripture_problems.csv")
        try:
            # Import locally to avoid altering global imports and preserve minimal change
            from csv_report import write_csv, CSV_FIELDS  # type: ignore
            write_csv(csv_path, csv_rows, fieldnames=CSV_FIELDS)
            print(f"\nProblem report written: {csv_path}")
        except Exception as e:
            print(f"\nERROR writing CSV report: {e}")
    else:
        print("\nNo reference problems detected.")

    print(f"\nDone. Processed {len(txt_files)} file(s), updated {changed}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
