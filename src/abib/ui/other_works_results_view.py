# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-
from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Sequence
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem


def group_by_work(occurrences: Sequence[Any]) -> dict[str, tuple[Any, ...]]:
    grouped: dict[str, list[Any]] = defaultdict(list)
    for occurrence in occurrences:
        grouped[occurrence.work_stem].append(occurrence)
    return {work: tuple(items) for work, items in grouped.items()}


def populate_results_tree(
        tree: QTreeWidget,
        summary_label: QLabel,
        occurrences: Sequence[Any],
        summary_prefix: str,
        row_columns: Callable[[Any], list[str]],
) -> None:
    noun = "occurrence" if len(occurrences) == 1 else "occurrences"
    summary_label.setText(f"{summary_prefix}: {len(occurrences)} {noun} found.")
    for work_stem, group in group_by_work(occurrences).items():
        parent = QTreeWidgetItem([f"{work_stem} ({len(group)})", "", ""])
        parent.setFirstColumnSpanned(True)
        tree.addTopLevelItem(parent)
        for occurrence in group:
            item = QTreeWidgetItem(row_columns(occurrence))
            item.setData(0, Qt.ItemDataRole.UserRole, occurrence)
            parent.addChild(item)
        parent.setExpanded(True)
    tree.resizeColumnToContents(0)
    tree.resizeColumnToContents(1)
