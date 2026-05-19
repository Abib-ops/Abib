# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

# check_refs.py
# Run from the Abib repo root: C:\Projects\Abib

import json
from pathlib import Path

# Ensure we can import local project modules when run from anywhere
from project_setup import PROJECT_ROOT

from abib.core import scripture

# Path to the target file
data_dir = PROJECT_ROOT / "src" / "abib" / "data"
NAME = "Call to the Unconverted.txt"
TARGET = data_dir / "Other Works" / NAME
print(f"Target file: {TARGET}")
if not TARGET.is_file():
    raise FileNotFoundError(
        f"Target file not found: {TARGET}. "
        "Place the target file in the 'Other Works' folder."
    )

# Load bible_data.json (canonical book -> chapter(str) -> verse(str) -> text)
BIBLE_JSON = data_dir / "bible_data.json"
if not BIBLE_JSON.is_file():
    raise FileNotFoundError(f"bible_data.json not found at {BIBLE_JSON}.")

with BIBLE_JSON.open("r", encoding="utf-8") as f:
    bible_data = json.load(f)

text = TARGET.read_text(encoding="utf-8", errors="ignore")

# Find references
refs = scripture.find_scripture_references(text)

problems = []
for r in refs:
    book = r["book"]
    chap = r["chapter"]
    vers = r["verse"]
    looked_up = scripture.lookup_scripture(bible_data, book, chap, vers)
    # The lookup returns either verse lines or friendly error messages.
    if "Scripture not found." in looked_up:
        problems.append({
            "kind": "book-not-found",
            "book": book, "chapter": chap, "verses": vers,
            "span": (r["start"], r["length"]),
			"text": r["text"],
        })
    elif any(line.startswith("Verse ") and line.endswith(" not found.") for line in looked_up.splitlines()):
        missing = [line for line in looked_up.splitlines() if line.startswith("Verse ") and line.endswith(" not found.")]
        problems.append({
            "kind": "verse-not-found",
            "book": book, "chapter": chap, "verses": vers,
            "missing": missing,
            "span": (r["start"], r["length"]),
            "text": r["text"],
        })

print(f"Total references detected: {len(refs)}")
print(f"Problems found: {len(problems)}")

# Emit a concise report file (CSV-like)
out = Path(rf"integrity_report_{NAME}")
with out.open("w", encoding="utf-8") as f:
    f.write("kind\tbook\tchapter\tverses\tmissing_or_info\tstart\tlength\tref_text\n")
    for p in problems:
        info = ", ".join(p.get("missing", [])) if p["kind"] == "verse-not-found" else ""
        f.write(
            f"{p['kind']}\t{p['book']}\t{p['chapter']}\t{p['verses']}\t{info}\t{p['span'][0]}\t{p['span'][1]}\t{p['text']}\n"
        )

print(f"Wrote: {out}")
