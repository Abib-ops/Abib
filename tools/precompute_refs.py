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
- Normalization matches the app: CRLF/CR are converted to LF before scanning and hashing.
- Output files are named "<source>.refs.json.gz" placed in the output directory.
- Existing companions are reused if content_sha256 and parser_version already match; use --force to rebuild.
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


PARSER_VERSION = "2025-11-21a"
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


def process_one(txt_path: Path, output_dir: Path, force: bool = False) -> tuple[bool, str]:
    """Process a single .txt file. Returns (changed, message)."""
    try:
        raw = txt_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return False, f"ERROR reading {txt_path.name}: {e}"

    content = normalize_text(raw)
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
    payload = build_companion_payload(txt_path, content, refs)
    try:
        write_companion(output_dir, base_name, payload)
    except Exception as e:
        return False, f"ERROR writing companion for {base_name}: {e}"
    return True, f"Wrote: {out_path.name} (refs: {len(payload.get('refs', []))})"


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

    changed = 0
    for p in txt_files:
        did_change, msg = process_one(p, out_dir, force=args.force)
        print(msg)
        if did_change:
            changed += 1

    print(f"\nDone. Processed {len(txt_files)} file(s), updated {changed}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
