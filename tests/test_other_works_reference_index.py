# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Any

from abib.services.other_works_reference_index import (
    OtherWorksReferenceIndex,
    compute_sha256_utf8,
    normalize_text,
    reference_key,
    reference_label_from_key,
)


def write_work(tmp_path: Path, name: str, text: str) -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def write_companion(path: Path, content: str, refs: list[dict[str, Any]]) -> None:
    payload = {
        "format": 1,
        "content_sha256": compute_sha256_utf8(normalize_text(content)),
        "refs": refs,
    }
    with gzip.open(path, "wt", encoding="utf-8") as f:
        json.dump(payload, f)


def test_reference_key_normalizes_aliases_and_one_chapter_labels():
    john_key = reference_key("Jn", 3, "16-18")
    jude_key = reference_key("Jude", 1, "5")

    assert john_key == (43, 3, 16)
    assert john_key is not None
    assert reference_label_from_key(john_key) == "John 3:16"
    assert jude_key == (65, 1, 5)
    assert jude_key is not None
    assert reference_label_from_key(jude_key) == "Jude 5"


def test_lookup_groups_enabled_work_occurrences_from_fallback_scan(tmp_path):
    first = write_work(tmp_path, "First.txt", "Alpha John 3:16 text.")
    second = write_work(tmp_path, "Second.txt", "Beta Jn. 3:16 and Jude 5 text.")
    hidden = write_work(tmp_path, "Hidden.txt", "Hidden John 3:16 text.")
    service = OtherWorksReferenceIndex(
        {"First": str(first), "Second": str(second), "Hidden": str(hidden)},
        {"First": True, "Second": True, "Hidden": False},
        tmp_path / "companions",
    )

    group = service.lookup("John 3:16")

    assert group is not None
    assert group.reference_label == "John 3:16"
    assert [occ.work_stem for occ in group.occurrences] == ["First", "Second"]
    assert all("John 3:16" in occ.snippet or "Jn. 3:16" in occ.snippet for occ in group.occurrences)


def test_valid_companion_records_are_used(tmp_path):
    work = write_work(tmp_path, "Companion.txt", "No live reference here.")
    companion = tmp_path / "Companion.txt.refs.json.gz"
    write_companion(
        companion,
        "No live reference here.",
        [{"abs_start": 3, "length": 9, "book": "John", "chapter": 3, "verse": "16", "text": "John 3:16"}],
    )
    service = OtherWorksReferenceIndex({"Companion": str(work)}, {"Companion": True}, tmp_path / "unused")

    group = service.lookup("John 3:16")

    assert group is not None
    assert group.occurrences[0].abs_start == 3
    assert group.occurrences[0].matched_text == "John 3:16"


def test_stale_companion_falls_back_to_runtime_scan(tmp_path):
    work = write_work(tmp_path, "Stale.txt", "Runtime text has Jude 5.")
    stale_payload = {
        "format": 1,
        "content_sha256": "stale",
        "refs": [{"abs_start": 0, "length": 9, "book": "John", "chapter": 3, "verse": "16", "text": "John 3:16"}],
    }
    with gzip.open(tmp_path / "Stale.txt.refs.json.gz", "wt", encoding="utf-8") as f:
        json.dump(stale_payload, f)
    service = OtherWorksReferenceIndex({"Stale": str(work)}, {"Stale": True}, tmp_path / "unused")

    assert service.lookup("John 3:16") is None
    group = service.lookup("Jude 5")
    assert group is not None
    assert group.occurrences[0].matched_text == "Jude 5"