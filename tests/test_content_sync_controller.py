# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Unit tests for the status-bar message formatting extracted into
``ContentSyncController.format_sync_summary``.

The method is a pure function (no Qt/window state), so it can be exercised
directly — one of the benefits of moving the Other Works download/sync logic out
of ``MainWindow``.
"""

from abib.ui.content_sync_controller import ContentSyncController

fmt = ContentSyncController.format_sync_summary


def test_offline_status():
    assert fmt({"status": "offline"}) == (
        "Other Works update: could not reach the content server."
    )


def test_unchanged_status():
    assert fmt({"status": "unchanged"}) == "Other Works are already up to date."


def test_error_status_uses_message():
    assert fmt({"status": "error", "message": "boom"}) == "boom"


def test_error_status_default_message():
    assert fmt({"status": "error"}) == "Other Works update failed."


def test_no_changes_reported_as_up_to_date():
    assert fmt({"status": "ok", "added": 0, "updated": 0, "removed": 0}) == (
        "Other Works are already up to date."
    )


def test_counts_use_book_only_values_and_singular_plural():
    msg = fmt({
        "status": "ok",
        "added_books": 1,
        "updated_books": 2,
        "removed_books": 0,
        # Raw file counts should be ignored in favour of the *_books values.
        "added": 9,
        "updated": 9,
    })
    assert msg == "Other Works updated: 1 book added, 2 books updated."


def test_partial_status_prefix():
    msg = fmt({"status": "partial", "added_books": 3})
    assert msg == "Other Works partially updated: 3 books added."


def test_falls_back_to_raw_counts_for_old_summaries():
    msg = fmt({"status": "ok", "added": 1, "updated": 0, "removed": 1})
    assert msg == "Other Works updated: 1 book added, 1 book removed."
