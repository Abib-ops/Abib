# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations
from typing import List, Tuple, Sequence, Dict, Set
from abib.domain import search as search_domain

class BibleSearchService:
    """Service to coordinate Bible searches and result state."""
    
    def __init__(self, kjv_data: Sequence[str], set_dict: Dict[str, Set]) -> None:
        self.kjv_data = kjv_data
        self.set_dict = set_dict
        
        # Search state
        self.last_results: List[Tuple[int, int, int]] = []
        self.occurrence_index: int = 0
        self.occurrences_total: int = 0
        self.search_key: str = ""

    def run_regex_search(self, patterns: tuple, start_line: int, end_line: int) -> int:
        """Run regex search and update state. Returns total found."""
        self.last_results = search_domain.iterate_regex(patterns, start_line, end_line, self.kjv_data)
        self.occurrences_total = len(self.last_results)
        self.occurrence_index = 0
        return self.occurrences_total

    def get_current_result(self) -> Tuple[int, int, int] | None:
        """Get current (line, start, end) based on occurrence_index."""
        if 0 <= self.occurrence_index < self.occurrences_total:
            return self.last_results[self.occurrence_index]
        return None

    def next_occurrence(self) -> bool:
        """Advance index. Returns True if wrapped or advanced."""
        if self.occurrences_total == 0:
            return False
        self.occurrence_index = (self.occurrence_index + 1) % self.occurrences_total
        return True

    def reset(self) -> None:
        """Clear results and state."""
        self.last_results = []
        self.occurrence_index = 0
        self.occurrences_total = 0
        self.search_key = ""
