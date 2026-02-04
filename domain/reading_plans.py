# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Tuple, Optional
from json import load, JSONDecodeError

import fcs
import shared as sh


@dataclass
class DateFile:
    """Represents the Morning/Evening date selection state.

    Fields:
      year: e.g. "Jan 01"
      time_of_day: "AM" or "PM"
      index: integer index used by fcs.get_date_file
    """
    year: str
    time_of_day: str
    index: int


class ReadingPlans:
    """Service encapsulating Spurgeon's Morning & Evening (SME) logic.

    Responsible for:
    - Loading JSON once
    - Maintaining date_file-like state using fcs.get_date_file
    - Returning the SME text and embedded scripture reference
    """

    def __init__(self, sme_json_path: Optional[Path] = None) -> None:
        # Determine JSON path in-app directory by default
        self.sme_json_path = sme_json_path or (sh.base_dir / "morning_evening.json")
        self._sme_data: Dict[str, Dict[str, str]] = {}

        # Initialise the date state using fcs.get_date_file (tuple[str, str, int])
        year, time_of_day, index = fcs.get_date_file()
        self._date = DateFile(year, time_of_day, index)

        self._load_data()

    # ---- Private helpers ----
    def _load_data(self) -> None:
        try:
            with open(self.sme_json_path, "r", encoding="utf-8") as fh:
                self._sme_data = load(fh)
        except FileNotFoundError:
            # Keep empty; callers will get a friendly error text
            self._sme_data = {}
        except JSONDecodeError:
            self._sme_data = {}

    def _advance(self, adjustment: int) -> None:
        # Use fcs.get_date_file to advance based on the current index
        y, tod, idx = fcs.get_date_file(self._date.index, adjustment)
        self._date = DateFile(y, tod, idx)

    # ---- Public API ----
    def get_sme(self, adjustment: int = 0) -> Tuple[str, str]:
        """Return (sme_text, scripture_ref) for the given adjustment.

        adjustment: the existing UI expects increments of 12 (-12 previous, +12 next).
        Returns a pair where first is the display text and second is the scripture ref
        extracted from the first line of the reading.
        """
        # Advance date based on adjustment
        self._advance(adjustment)

        # Fetch reading
        try:
            a: str = self._sme_data[self._date.year][self._date.time_of_day]
        except (KeyError, TypeError):
            # Missing year/time_of_day keys or malformed data structure
            return f"No entry for {self._date.year} in {self._date.time_of_day}.", ""

        # Extract scripture reference between the closing quote and newline of first line
        try:
            # Should be the 2nd '"' at the end of the first line, before the reference
            i: int = a[1:].index('"') + 2
            j: int = a.index('\n')
            sme_ref: str = a[i:j]
        except ValueError:
            sme_ref = ""

        sme_text = f"{self._date.year} — {self._date.time_of_day}\n\n{a}"
        return sme_text, sme_ref

    # Expose the current reference target without text if needed
    def current_ref(self) -> str:
        try:
            a: str = self._sme_data[self._date.year][self._date.time_of_day]
            i: int = a[1:].index('"') + 2
            j: int = a.index('\n')
            return a[i:j]
        except (KeyError, TypeError, ValueError):
            return ""
