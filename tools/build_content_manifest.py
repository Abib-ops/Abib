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

"""Rebuild the Abib-OtherWorks manifest without invoking git."""


import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

DATASET_PATH = "Cross References/openbible-crossrefs.sqlite"
DATASET_TITLE = "Cross References (OpenBible.info)"


def _existing_titles(manifest_path: Path) -> dict[str, str]:
    if not manifest_path.exists():
        return {}
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(f"Could not read existing manifest {manifest_path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("files"), list):
        raise TypeError(f"Existing manifest has an invalid structure: {manifest_path}")
    titles: dict[str, str] = {}
    for entry in data["files"]:
        if not isinstance(entry, dict):
            continue
        path, title = entry.get("path"), entry.get("title")
        if isinstance(path, str) and isinstance(title, str) and title.strip():
            titles[path] = title
    return titles


def _file_entry(path: str, data: bytes, titles: dict[str, str]) -> dict[str, Any]:
    entry: dict[str, Any] = {
        "path": path,
        "sha256": hashlib.sha256(data).hexdigest(),
        "size": len(data),
    }
    title = titles.get(path)
    if title:
        entry["title"] = title
    return entry


def build_manifest(repo_path: Path) -> dict[str, Any]:
    """Normalize content files and rebuild the repository's manifest."""
    repo_path = repo_path.expanduser().resolve()
    manifest_path = repo_path / "manifest.json"
    titles = _existing_titles(manifest_path)
    entries: list[dict[str, Any]] = []

    works_dir = repo_path / "Other Works"
    if works_dir.is_dir():
        for path in sorted(works_dir.glob("*.txt")):
            if not path.is_file():
                continue
            original = path.read_bytes()
            data = original.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            if data != original:
                path.write_bytes(data)
            entries.append(_file_entry(f"Other Works/{path.name}", data, titles))

    companions_dir = repo_path / "Other Works companions"
    if companions_dir.is_dir():
        for path in sorted(companions_dir.glob("*.refs.json.gz")):
            if path.is_file():
                entries.append(_file_entry(
                    f"Other Works companions/{path.name}", path.read_bytes(), titles
                ))

    crossrefs_dir = repo_path / "Cross References"
    if crossrefs_dir.is_dir():
        for path in sorted(crossrefs_dir.glob("*.sqlite")):
            if not path.is_file():
                continue
            relative_path = f"Cross References/{path.name}"
            entry = _file_entry(relative_path, path.read_bytes(), titles)
            if relative_path == DATASET_PATH:
                entry["title"] = DATASET_TITLE
            entries.append(entry)

    entries.sort(key=lambda entry: str(entry["path"]))
    manifest: dict[str, Any] = {
        "content_version": datetime.now().strftime("%Y.%m.%d.%H%M%S"),
        "files": entries,
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Rebuild manifest.json for an Abib-OtherWorks repository."
    )
    parser.add_argument("--repo", type=Path, required=True, help="Content repository root.")
    args = parser.parse_args(argv)
    try:
        manifest = build_manifest(args.repo)
    except (OSError, TypeError, ValueError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    print(f"Wrote {args.repo.expanduser().resolve() / 'manifest.json'}")
    print(f"Indexed {len(manifest['files']):,} content files.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())