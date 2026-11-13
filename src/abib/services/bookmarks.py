# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

"""Persistent per-user bookmarks for Bible verses."""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from abib.core import shared as sh


@dataclass(frozen=True)
class Bookmark:
    position: int
    note: str
    created: str


class BookmarkStore:
    """Store one note-bearing bookmark per Bible verse in a JSON file."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path) if path is not None else Path(sh.user_settings_dir) / "bookmarks.json"

    def all(self) -> list[Bookmark]:
        """Return valid bookmarks ordered by Bible position."""
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return []
        except OSError:
            return []
        except (UnicodeError, json.JSONDecodeError):
            self._preserve_corrupt_file()
            return []

        if not isinstance(data, dict) or not isinstance(data.get("bookmarks"), list):
            self._preserve_corrupt_file()
            return []

        bookmarks: dict[int, Bookmark] = {}
        for item in data["bookmarks"]:
            if not isinstance(item, dict):
                continue
            position = item.get("position")
            note = item.get("note")
            created = item.get("created")
            if (
                isinstance(position, bool)
                or not isinstance(position, int)
                or not 0 <= position <= sh.LAST_VERSE_IN_BIBLE
                or not isinstance(note, str)
                or not isinstance(created, str)
            ):
                continue
            bookmarks[position] = Bookmark(position, note, created)

        return sorted(bookmarks.values(), key=lambda bookmark: bookmark.position)

    def get(self, position: int) -> Bookmark | None:
        """Return the bookmark for a verse, if one exists."""
        return next((bookmark for bookmark in self.all() if bookmark.position == position), None)

    def set(self, position: int, note: str) -> Bookmark:
        """Add or update a verse bookmark and atomically persist the store."""
        if isinstance(position, bool) or not isinstance(position, int) or not 0 <= position <= sh.LAST_VERSE_IN_BIBLE:
            raise ValueError("Bookmark position is outside the Bible")
        if not isinstance(note, str):
            raise TypeError("Bookmark note must be text")

        bookmarks = {bookmark.position: bookmark for bookmark in self.all()}
        existing = bookmarks.get(position)
        bookmark = Bookmark(
            position=position,
            note=note,
            created=existing.created if existing else datetime.now(UTC).isoformat(),
        )
        bookmarks[position] = bookmark
        self._write(sorted(bookmarks.values(), key=lambda item: item.position))
        return bookmark

    def remove(self, position: int) -> bool:
        """Remove a verse bookmark; return whether one existed."""
        bookmarks = self.all()
        remaining = [bookmark for bookmark in bookmarks if bookmark.position != position]
        if len(remaining) == len(bookmarks):
            return False
        self._write(remaining)
        return True

    def _preserve_corrupt_file(self) -> None:
        if not self.path.exists():
            return
        backup = self.path.with_name(f"{self.path.name}.bak")
        suffix = 1
        while backup.exists():
            backup = self.path.with_name(f"{self.path.name}.bak.{suffix}")
            suffix += 1
        try:
            self.path.replace(backup)
        except OSError:
            # Leave the original untouched when it cannot be moved; callers can
            # still read an empty list without risking an implicit overwrite.
            return

    def _write(self, bookmarks: list[Bookmark]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=self.path.parent,
                prefix=f"{self.path.name}.",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(
                    {"bookmarks": [bookmark.__dict__ for bookmark in bookmarks]},
                    temporary_file,
                    ensure_ascii=False,
                    indent=2,
                )
                temporary_file.write("\n")
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            temporary_path.replace(self.path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()