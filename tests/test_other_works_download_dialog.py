# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

from abib.ui.other_works_download_dialog import OtherWorksDownloadDialog


def _available():
    return [
        {"stem": "Foo", "title": "The Foo Book", "downloaded": True},
        {"stem": "Bar", "title": "Bar", "downloaded": False},
        {"stem": "Baz", "title": "Baz", "downloaded": False},
    ]


def test_dialog_preselects_requested_stems(qapp):
    dialog = OtherWorksDownloadDialog(None, _available(), preselected={"Bar"})

    assert dialog.selected_stems() == {"Bar"}


def test_dialog_preselects_downloaded_when_no_preselection(qapp):
    dialog = OtherWorksDownloadDialog(None, _available(), preselected=set())

    # With an explicit empty preselection, nothing is pre-ticked.
    assert dialog.selected_stems() == set()


def test_dialog_defaults_downloaded_ticked_when_preselected_none(qapp):
    dialog = OtherWorksDownloadDialog(None, _available(), preselected=None)

    # No subscription info at all -> installed books start ticked.
    assert dialog.selected_stems() == {"Foo"}


def test_dialog_select_and_deselect_all(qapp):
    dialog = OtherWorksDownloadDialog(None, _available(), preselected=set())

    dialog._set_all(True)
    assert dialog.selected_stems() == {"Foo", "Bar", "Baz"}

    dialog._set_all(False)
    assert dialog.selected_stems() == set()


def test_dialog_handles_empty_catalogue(qapp):
    dialog = OtherWorksDownloadDialog(None, [], preselected=set())

    assert dialog.selected_stems() == set()
