# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Read-only access to the OpenBible.info cross-reference dataset.

The dataset ``openbible-crossrefs.sqlite`` is built by
``tools/build_crossrefs_sqlite.py`` and downloaded on demand through
Study → Update Other Works into ``sh.user_crossrefs_dir``.

Schema::

    crossrefs(from_vi INTEGER, to_start INTEGER, to_end INTEGER, votes INTEGER,
              PRIMARY KEY (from_vi, to_start, to_end)) WITHOUT ROWID
    meta(key TEXT PRIMARY KEY, value TEXT)

All positions are Abib's flat verse index, identical to the row used by
``sh.Info``. A connection is opened read-only for each query and closed again,
so the file is never held open: on Windows an open file cannot be replaced or
deleted, which would make a content-sync update or removal fail.

When the file is missing or unreadable, every query returns an empty result.
"""


import sqlite3
from dataclasses import dataclass
from pathlib import Path

from abib.core import shared as sh

DATASET_FILENAME = "openbible-crossrefs.sqlite"
DEFAULT_ATTRIBUTION = "Cross-references: OpenBible.info (CC BY)"
ATTRIBUTION_URL = "https://www.openbible.info/labs/cross-references/"


@dataclass(frozen=True)
class CrossReference:
    """One related verse or verse range for a source verse."""

    to_start: int
    to_end: int
    votes: int


class CrossReferenceService:
    """Read-only lookups of ranked cross-references for a verse."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        if db_path is None:
            db_path = sh.user_crossrefs_dir / DATASET_FILENAME
        self._db_path = Path(db_path)

    @property
    def db_path(self) -> Path:
        return self._db_path

    def _connect(self) -> sqlite3.Connection | None:
        """Open the dataset read-only, or return ``None`` if it is absent."""
        if not self._db_path.is_file():
            return None
        try:
            return sqlite3.connect(f"{self._db_path.resolve().as_uri()}?mode=ro", uri=True)
        except sqlite3.Error:
            return None

    @staticmethod
    def _valid_position(position: object) -> bool:
        return (
            isinstance(position, int)
            and not isinstance(position, bool)
            and 0 <= position <= sh.LAST_VERSE_IN_BIBLE
        )

    def is_available(self) -> bool:
        """Return True when the dataset exists and has the expected table."""
        conn = self._connect()
        if conn is None:
            return False
        try:
            conn.execute("SELECT from_vi, to_start, to_end, votes FROM crossrefs LIMIT 1")
            return True
        except sqlite3.Error:
            return False
        finally:
            conn.close()

    def lookup(self, position: int, min_votes: int | None = None) -> list[CrossReference]:
        """Return cross-references for *position*, strongest first.

        Rows are ordered by votes (highest first), then in Bible order. When
        *min_votes* is given, rows with fewer votes are excluded.
        """
        if not self._valid_position(position):
            return []
        conn = self._connect()
        if conn is None:
            return []
        sql = "SELECT to_start, to_end, votes FROM crossrefs WHERE from_vi = ?"
        params: list[int] = [position]
        if min_votes is not None:
            sql += " AND votes >= ?"
            params.append(int(min_votes))
        sql += " ORDER BY votes DESC, to_start, to_end"
        try:
            rows = conn.execute(sql, params).fetchall()
        except sqlite3.Error:
            return []
        finally:
            conn.close()
        return [CrossReference(int(start), int(end), int(votes)) for start, end, votes in rows]

    def count(self, position: int) -> int:
        """Return the unfiltered number of cross-references for *position*."""
        if not self._valid_position(position):
            return 0
        conn = self._connect()
        if conn is None:
            return 0
        try:
            row = conn.execute(
                "SELECT COUNT(*) FROM crossrefs WHERE from_vi = ?", (position,)
            ).fetchone()
        except sqlite3.Error:
            return 0
        finally:
            conn.close()
        return int(row[0]) if row else 0

    def attribution(self) -> str:
        """Return the dataset's attribution line, or the default credit."""
        conn = self._connect()
        if conn is None:
            return DEFAULT_ATTRIBUTION
        try:
            row = conn.execute("SELECT value FROM meta WHERE key = 'attribution'").fetchone()
        except sqlite3.Error:
            return DEFAULT_ATTRIBUTION
        finally:
            conn.close()
        if row and isinstance(row[0], str) and row[0].strip():
            return row[0].strip()
        return DEFAULT_ATTRIBUTION
