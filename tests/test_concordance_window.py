# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from unittest.mock import MagicMock

from abib.services.concordance_service import ConcordanceService
from abib.ui.concordance_window import ConcordanceWindow


def make_window() -> ConcordanceWindow:
    service = ConcordanceService(
        (
            "God is light, and in him is no darkness at all.",
            "The LORD is good, a strong hold in the day of trouble.",
        ),
        (0, 1),
        ((0, 0, 0), (1, 0, 0)),
        ("I John", "Nahum"),
        set(),
    )
    settings_service = MagicMock()
    settings_service.get_window_geometry.return_value = (100, 100, 640, 500)
    return ConcordanceWindow(service, settings_service=settings_service)


def test_window_lists_entries_and_filters_words(qapp):
    window = make_window()

    assert window.entry_list.count() > 0

    window.filter_edit.setText("lig")

    assert window.entry_list.count() == 1
    assert window.entry_list.item(0).text() == "light (1)"
    assert window.reference_list.item(0).text().startswith("I John 1:1")


def test_window_supports_typed_phrase_lookup(qapp):
    window = make_window()

    window.filter_edit.setText("strong hold")


    assert window.entry_list.count() == 1
    assert window.entry_list.item(0).text() == "strong hold (1)"
    assert window.reference_list.item(0).text().startswith("Nahum 1:1")


def test_window_emits_position_and_term_when_reference_activates(qapp):
    window = make_window()
    activations: list[tuple[int, str]] = []
    window.referenceActivated.connect(lambda pos, term: activations.append((pos, term)))

    window.filter_edit.setText("lord")
    window._activate_reference(window.reference_list.item(0))

    assert activations == [(1, "lord")]