from __future__ import annotations

import csv
from pathlib import Path
from typing import List, Dict, Any, Iterable, Sequence


# Standard CSV columns used by tools that emit line-based text diagnostics
CSV_FIELDS: List[str] = [
    "file",
    "type",
    "book",
    "chapter",
    "verse",
    "line",
    "message",
    "text",
]


def write_csv(csv_path: Path, rows: Iterable[Dict[str, Any]], fieldnames: Sequence[str] | None = None) -> None:
    """Write rows to csv_path with a header.

    - Ensures parent directory exists.
    - Uses CSV_FIELDS by default but allows overriding via fieldnames.
    """
    header = list(fieldnames) if fieldnames is not None else CSV_FIELDS
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
