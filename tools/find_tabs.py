# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Dict, Any
import sys

# Ensure we can import project-root modules when run from tools/
THIS_FILE = Path(__file__).resolve()
PROJECT_ROOT = THIS_FILE.parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import csv_report


def normalize_text(s: str) -> str:
    """Normalise line endings to LF only to keep offsets/lines consistent."""
    return s.replace("\r\n", "\n").replace("\r", "\n")


def scan_tabs(text: str) -> List[Dict[str, Any]]:
    """Return a list of dicts describing each tab character position.

    Each dict contains: line (1-based), column (1-based), abs_index (0-based),
    and context (a short snippet of the line with the tab marked as \t).
    """
    rows: List[Dict[str, Any]] = []
    line_no = 1
    col_no = 1
    abs_index = 0
    # Pre-split lines for context extraction while keeping indices aligned to the normalised text
    lines = text.split("\n")
    # Build starting absolute index of each line for efficient context lookup
    line_starts: List[int] = []
    cur = 0
    for i, ln in enumerate(lines):
        line_starts.append(cur)
        # +1 for the newline character except for the last line if text doesn't end with \n
        cur += len(ln)
        if i < len(lines) - 1:
            cur += 1

    # Iterate once through text to capture line/column/index
    for ch in text:
        if ch == "\t":
            # Extract context: the full line containing the tab
            # Find the line index via binary search on line_starts (linear scan here is fine too)
            # We keep a simple running line/column, so we can use those directly.
            line_idx = line_no - 1
            context = lines[line_idx] if 0 <= line_idx < len(lines) else ""
            rows.append(
                {
                    "line": line_no,
                    "column": col_no,
                    "abs_index": abs_index,
                    "context": context,
                }
            )
        if ch == "\n":
            line_no += 1
            col_no = 1
        else:
            col_no += 1
        abs_index += 1
    return rows


def process_path(path: Path) -> List[Dict[str, Any]]:
    """Scan a file path for tabs and return CSV rows with file info."""
    try:
        raw = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [
            {
                "file": path.name,
                "type": "error",
                "line": "",
                "column": "",
                "message": f"Failed to read file: {e}",
                "context": "",
            }
        ]

    content = normalize_text(raw)
    findings = scan_tabs(content)
    rows: List[Dict[str, Any]] = []
    for f in findings:
        rows.append(
            {
                "file": path.name,
                "type": "tab",
                "book": "",
                "chapter": "",
                "verse": "",
                "line": str(f["line"]),
                "message": f"Tab at column {f['column']}",
                "text": f["context"],
            }
        )
    if not findings:
        rows.append(
            {
                "file": path.name,
                "type": "ok",
                "book": "",
                "chapter": "",
                "verse": "",
                "line": "",
                "message": "No tabs found",
                "text": "",
            }
        )
    return rows


def _write_csv(csv_path: Path, rows: List[Dict[str, Any]]) -> None:
    """Write rows to csv_path using the shared csv_report fields."""
    csv_report.write_csv(csv_path, rows, fieldnames=csv_report.CSV_FIELDS)


def main(argv: List[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Scan text files for tab characters and export a CSV report.")
    parser.add_argument(
        "--input",
        "-i",
        type=str,
        default=None,
        help="Path to a .txt file or a directory containing .txt files (if omitted, you'll be prompted)",
    )
    parser.add_argument(
        "--csv",
        type=str,
        default=None,
        help="Optional path to write the CSV report. If not provided: for a directory, '<dir>/tabs_report.csv'; for a file, '<file>.tabs.csv'",
    )
    args = parser.parse_args(argv)

    # If no input provided on the command line, ask the user interactively
    user_input = args.input
    if not user_input:
        try:
            user_input = input("Enter path to a .txt file or a directory of .txt files: ").strip()
        except EOFError:
            user_input = ""
        # Strip surrounding quotes if the user pasted a quoted path
        if user_input.startswith(('"', "'")) and user_input.endswith(('"', "'")) and len(user_input) >= 2:
            user_input = user_input[1:-1]

    if not user_input:
        print("ERROR: No input path provided.")
        return 2

    in_path = Path(user_input).expanduser().resolve()
    if not in_path.exists():
        print(f"ERROR: Input path does not exist: {in_path}")
        return 2

    default_csv: Path
    if in_path.is_dir():
        files: List[Path] = sorted(p for p in in_path.glob("*.txt") if p.is_file())
        default_csv = in_path / "tabs_report.csv"
    else:
        if in_path.suffix.lower() != ".txt":
            print(f"WARNING: Input file does not have .txt extension: {in_path.name}")
        files: List[Path] = [in_path]
        default_csv = in_path.with_suffix(in_path.suffix + ".tabs.csv")

    if not files:
        print("No .txt files to scan.")
        # Still write an empty CSV header to the default path for consistency
        csv_path = Path(args.csv) if args.csv else default_csv
        try:
            _write_csv(csv_path, [])
            print(f"Report written: {csv_path} (no files)")
        except Exception as e:
            print(f"ERROR writing CSV: {e}")
            return 1
        return 0

    all_rows: List[Dict[str, Any]] = []
    total_tabs = 0
    for p in files:
        rows = process_path(p)
        all_rows.extend(rows)
        total_tabs += sum(1 for r in rows if r.get("type") == "tab")

    csv_path = Path(args.csv) if args.csv else default_csv
    try:
        _write_csv(csv_path, all_rows)
        print(f"Report written: {csv_path}")
        print(f"Scanned {len(files)} file(s). Tabs found: {total_tabs}.")
    except Exception as e:
        print(f"ERROR writing CSV: {e}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
