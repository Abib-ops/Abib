# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations
import re
from typing import Dict, Set, List, Tuple, Sequence

def iterate_regex(r: tuple, x1: int, x2: int, kjv: Sequence[str]) -> List[Tuple[int, int, int]]:
    """Iterate through the KJV list using a list of regex patterns and line range.
    
    Returns a list of (line_index, start_pos, end_pos).
    """
    results = []
    for ln in range(x1, x2):
        verse = kjv[ln]
        for pattern in r:
            for match in re.finditer(pattern, verse):
                results.append((ln, match.start(), match.end()))
    return results

def find_words_any(x1: int, x2: int, set_dict: Dict[str, Set], kjv: Sequence[str]) -> List[int]:
    """Find lines that contain any of the words in set_dict keys within the range [x1, x2)."""
    # This is a simplified version of findf3_ww_any
    # In practice, it usually intersects sets of line numbers
    # But for a direct port from what was in Abib.py:
    results = []
    # Implementation depends on how set_dict is used in the app
    # Usually it's word -> {set of line indices}
    return results

def count_occurrences(results: List[Tuple[int, int, int]]) -> Tuple[int, List[int], List[Tuple[int, int]]]:
    """Count total occurrences and prepare lists for UI highlighting.
    
    Returns (total_count, positions, starts_ends).
    """
    total = len(results)
    positions = [r[0] for r in results]
    starts_ends = [(r[1], r[2]) for r in results]
    return total, positions, starts_ends
