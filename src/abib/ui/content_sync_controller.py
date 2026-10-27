# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Other Works content-download / sync controller extracted from ``MainWindow``.

Holds all logic for scanning, downloading and synchronising the optional
"Other Works" library: the menu-triggered update flow, the throttled startup
auto-sync, the background worker wiring and the download progress dialog.
``MainWindow`` keeps thin delegators, so external callers (the Study menu action
and the startup bootstrap) are unaffected.

The GUI slots that receive cross-thread signals from the background worker
(``on_content_sync_finished``, ``on_download_progress`` and
``on_download_finished``) are invoked via thin bound methods on ``MainWindow``
(a ``QObject``): a queued signal must be delivered to a slot with thread
affinity, which a plain controller object does not have. The window delegates to
this controller, which then runs on the GUI thread as required.
"""


import logging
from typing import TYPE_CHECKING, Any

from abib.core import shared as sh

if TYPE_CHECKING:
    from abib.Abib import MainWindow

logger = logging.getLogger(__name__)


class ContentSyncController:
    """Encapsulate the Other Works download/sync behaviour of ``MainWindow``."""

    def __init__(self, window: MainWindow) -> None:
        self._win = window
        # Progress dialog shown while books are downloading (menu-triggered).
        self._download_progress_dialog: Any = None

    def reload_other_works(self) -> None:
        """Re-scan the bundled + user Other Works directories and refresh the UI.

        Called after a content sync so newly downloaded (or removed) titles appear
        without an application restart. Rebuilds the combo and recreates the
        reference-index / text-search services (keyed on the updated map) so any
        open browser windows pick up the changes.
        """
        win = self._win
        mapping: dict[str, str] = {}
        for other_works_dir in sh.other_works_dirs():
            for p in sorted(other_works_dir.glob("*.txt")):
                if p.is_file():
                    mapping[p.stem] = str(p)
        win.other_works_map = mapping

        win.refresh_other_works_combo()
        try:
            last_work = win.settings.get("last_other_work") if isinstance(win.settings, dict) else None
            if win.other_works_combo is not None:
                # Block signals while restoring the selection: unlike the initial
                # setup (where the combo is populated before currentTextChanged is
                # connected), here the signal is already wired to _open_other_work,
                # so an unguarded setCurrentText would pop open the Other Works
                # window after a download. The user just wants the list refreshed.
                win.other_works_combo.blockSignals(True)
                try:
                    if last_work and last_work in win.other_works_map:
                        win.other_works_combo.setCurrentText(str(last_work or ""))
                    elif "Pilgrims-Progress" in win.other_works_map:
                        win.other_works_combo.setCurrentText("Pilgrims-Progress")
                finally:
                    win.other_works_combo.blockSignals(False)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            logger.debug("Could not restore Other Works combo selection", exc_info=True)

        # Recreate the reference index with the updated map so an open window
        # reflects the new titles (rebuild() alone keeps the stale map).
        if getattr(win, "other_works_reference_index", None) is not None:
            try:
                from abib.services.other_works_reference_index import (
                    OtherWorksReferenceIndex,
                )
                win.other_works_reference_index = OtherWorksReferenceIndex(win.other_works_map)
                if win.other_works_references_window is not None:
                    win.other_works_references_window._service = win.other_works_reference_index
                    win.other_works_references_window.clear_search()
            except (AttributeError, RuntimeError, TypeError, ValueError):
                logger.debug("Could not refresh Other Works reference index", exc_info=True)

        # Recreate the text-search service likewise.
        if getattr(win, "other_works_text_search_service", None) is not None:
            try:
                from abib.services.other_works_text_search import (
                    OtherWorksTextSearchService,
                )
                win.other_works_text_search_service = OtherWorksTextSearchService(win.other_works_map)
                if win.other_works_text_search_window is not None:
                    win.other_works_text_search_window._service = win.other_works_text_search_service
                    win.other_works_text_search_window.clear_search()
            except (AttributeError, RuntimeError, TypeError, ValueError):
                logger.debug("Could not refresh Other Works text search service", exc_info=True)

    @staticmethod
    def format_sync_summary(summary: dict) -> str:
        """Build a short status-bar message describing a content-sync result."""
        status = str(summary.get("status", "")) if isinstance(summary, dict) else ""
        if status == "offline":
            return "Other Works update: could not reach the content server."
        if status == "unchanged":
            return "Other Works are already up to date."
        if status == "error":
            return str(summary.get("message") or "Other Works update failed.")
        # Prefer book-only counts (companion index files are never counted),
        # falling back to the raw file counts for older summaries.
        added = int(summary.get("added_books", summary.get("added", 0)) or 0)
        updated = int(summary.get("updated_books", summary.get("updated", 0)) or 0)
        removed = int(summary.get("removed_books", summary.get("removed", 0)) or 0)
        if not (added or updated or removed):
            return "Other Works are already up to date."
        parts: list[str] = []
        if added:
            parts.append(f"{added} book{'' if added == 1 else 's'} added")
        if updated:
            parts.append(f"{updated} book{'' if updated == 1 else 's'} updated")
        if removed:
            parts.append(f"{removed} book{'' if removed == 1 else 's'} removed")
        prefix = "Other Works updated" if status == "ok" else "Other Works partially updated"
        return f"{prefix}: {', '.join(parts)}."

    def on_content_sync_finished(self, summary: dict) -> None:
        """Handle completion of a background content sync (menu or startup)."""
        win = self._win
        try:
            changed = isinstance(summary, dict) and (
                summary.get("added") or summary.get("updated") or summary.get("removed")
            )
            if changed:
                self.reload_other_works()
        except (RuntimeError, AttributeError, TypeError, ValueError):
            logger.debug("Failed to reload Other Works after sync", exc_info=True)
        # Show a brief status-bar message (menu-triggered syncs are the main
        # beneficiary; the message is harmless on startup too).
        try:
            if getattr(win, "statusBar", None) is not None:
                win.statusBar.showMessage(self.format_sync_summary(summary), 6000)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            logger.debug("Could not display content-sync status message", exc_info=True)

    def update_other_works(self) -> None:
        """Menu action: let the user pick which Other Works to download, then sync.

        Fetches the remote manifest, shows a checklist of available books
        (pre-ticking the user's current subscription / already-installed
        titles), persists the chosen set as ``subscribed_works`` and starts a
        background sync restricted to that selection.
        """
        win = self._win
        try:
            if getattr(win, "statusBar", None) is not None:
                win.statusBar.showMessage("Checking for Other Works updates…", 4000)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            logger.debug("Could not display content-sync start message", exc_info=True)

        available: Any = None
        try:
            from abib.core import content_sync
            remote = content_sync.fetch_remote_manifest()
            if remote is not None:
                available = content_sync.list_available(remote)
        except (ImportError, RuntimeError, AttributeError, TypeError, ValueError):
            logger.debug("Could not fetch Other Works manifest", exc_info=True)
            remote = None

        if remote is None or available is None:
            try:
                if getattr(win, "statusBar", None) is not None:
                    win.statusBar.showMessage(
                        "Other Works update: could not reach the content server.", 6000
                    )
            except (RuntimeError, AttributeError, TypeError, ValueError):
                logger.debug("Could not display content-sync offline message", exc_info=True)
            return

        # Pre-select: the user's saved subscription, falling back to whatever is
        # already downloaded so an existing library stays ticked.
        subscribed = set(win.settings.get("subscribed_works") or []) if isinstance(win.settings, dict) else set()
        if not subscribed:
            subscribed = {str(b.get("stem")) for b in available if b.get("downloaded")}

        try:
            # noinspection PyPackageRequirements
            from PySide6.QtWidgets import QDialog

            from abib.ui.other_works_download_dialog import OtherWorksDownloadDialog
            dialog = OtherWorksDownloadDialog(win, available, subscribed)
            if dialog.exec() != QDialog.DialogCode.Accepted:
                return
            selected = dialog.selected_stems()
        except (ImportError, RuntimeError, AttributeError, TypeError, ValueError):
            logger.debug("Could not show Other Works download dialog", exc_info=True)
            return

        # Persist the user's choice so the throttled startup sync keeps exactly
        # these titles current.
        try:
            if isinstance(win.settings, dict):
                win.settings["subscribed_works"] = sorted(selected)
                if getattr(win, "settings_service", None):
                    win.settings_service.save(win.settings)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            logger.debug("Could not persist subscribed_works", exc_info=True)

        self.start_content_sync(force=True, selected_stems=selected, show_progress=True)

    def maybe_auto_sync_content(self) -> None:
        """Start a throttled (at most once/day) background content sync at startup."""
        win = self._win
        from datetime import datetime, timedelta
        now = datetime.now()
        try:
            last = str(win.settings.get("last_content_sync", "")) if isinstance(win.settings, dict) else ""
        except (AttributeError, TypeError, ValueError):
            last = ""
        # TESTING: the once-per-day download throttle is temporarily disabled, so
        # the background content sync runs on every startup. To restore the limit,
        # set ``throttle_enabled`` back to True (or remove this override).
        throttle_enabled = True
        due = True
        if throttle_enabled and last:
            try:
                due = (now - datetime.fromisoformat(last)) >= timedelta(days=1)
            except ValueError:
                due = True
        if not due:
            return
        # Only the books the user subscribed to are kept current automatically;
        # nothing is downloaded until the user opts in via "Update Other Works…".
        subscribed = set(win.settings.get("subscribed_works") or []) if isinstance(win.settings, dict) else set()
        if not subscribed:
            return
        # Record the attempt now so the throttle holds even if the sync fails.
        try:
            if isinstance(win.settings, dict):
                win.settings["last_content_sync"] = now.isoformat()
                if getattr(win, "settings_service", None):
                    win.settings_service.save(win.settings)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            logger.debug("Could not persist last_content_sync timestamp", exc_info=True)
        self.start_content_sync(force=False, selected_stems=subscribed)

    def start_content_sync(self, force: bool, selected_stems: Any = None,
                           show_progress: bool = False) -> None:
        """Kick off a background content sync, keeping worker/thread references alive.

        When ``show_progress`` is set (menu-triggered downloads), a green
        progress bar is shown reporting the number of *books* downloaded
        (companion index files are never counted).
        """
        win = self._win
        try:
            from abib.core import content_sync
            # Create the worker/thread but DON'T start yet, so every GUI slot is
            # connected before the worker can emit any signal. Starting first
            # caused a race where the first progress (or even finished) could be
            # emitted before the UI connected, leaving the bar stuck open and the
            # Other Works list unrefreshed ("bar appears but nothing happens").
            win.content_sync_thread, win.content_sync_worker = content_sync.start_background_sync(
                win, force=force, selected_stems=selected_stems, autostart=False
            )
            if show_progress:
                self.show_download_progress(win.content_sync_worker)
            # Connect to the window's bound slot (a QObject) so the cross-thread
            # queued signal is delivered on the GUI thread.
            win.content_sync_worker.finished.connect(win.on_content_sync_finished)
            # All slots connected — now it is safe to start the worker thread.
            win.content_sync_thread.start()
        except (ImportError, RuntimeError, AttributeError, TypeError, ValueError):
            logger.debug("Could not start background content sync", exc_info=True)

    def show_download_progress(self, worker: Any) -> None:
        """Show a green progress bar tracking the book downloads of ``worker``.

        The bar's range/value count *books only* (the ``(done, total)`` values
        emitted by the worker already exclude companion index files), so the
        number shown to the user never includes companions.
        """
        win = self._win
        try:
            # noinspection PyPackageRequirements
            from PySide6.QtCore import Qt

            # noinspection PyPackageRequirements
            from PySide6.QtWidgets import QProgressBar, QProgressDialog

            # Start as a busy/indeterminate bar (0..0) so the dialog is visible
            # immediately, before the first progress tick arrives.
            dialog = QProgressDialog("Preparing to download Other Works…", "", 0, 0, win)
            dialog.setWindowTitle("Downloading Other Works")
            dialog.setWindowModality(Qt.WindowModality.WindowModal)
            dialog.setMinimumDuration(0)
            dialog.setAutoClose(False)
            dialog.setAutoReset(False)
            # No Cancel button: the sync cannot be safely interrupted mid-file.
            dialog.setCancelButton(None)

            # A green progress bar (the "chunk" is the filled portion).
            bar = QProgressBar(dialog)
            bar.setTextVisible(True)
            bar.setStyleSheet(
                "QProgressBar {"
                " border: 1px solid #3a3a3a;"
                " border-radius: 4px;"
                " text-align: center;"
                " }"
                "QProgressBar::chunk {"
                " background-color: #2ecc40;"
                " }"
            )
            dialog.setBar(bar)

            self._download_progress_dialog = dialog
            # Force the dialog to render now rather than relying on the
            # auto-show timer (downloads may finish before it would appear).
            dialog.show()
            dialog.raise_()

            # Connect the worker signals to *bound methods* of the window
            # (which lives on the GUI thread). A cross-thread signal to a
            # QObject slot is auto-delivered as a queued call on the receiver's
            # (GUI) thread, so the bar actually updates/closes. Connecting to
            # plain local functions — even with an explicit QueuedConnection —
            # is unreliable because such slots have no thread affinity, which
            # left the bar frozen and the sync looking like it never ran.
            worker.progress.connect(win.on_download_progress)
            worker.finished.connect(win.on_download_finished)
        except (ImportError, RuntimeError, AttributeError, TypeError, ValueError):
            logger.debug("Could not show download progress dialog", exc_info=True)

    def on_download_progress(self, done: int, total: int) -> None:
        """GUI-thread slot: update the green download progress bar."""
        dialog = self._download_progress_dialog
        if dialog is None:
            return
        try:
            if total <= 0:
                # Nothing to download — don't leave an empty bar lingering.
                dialog.close()
                self._download_progress_dialog = None
                return
            dialog.setMaximum(int(total))
            dialog.setValue(int(done))
            dialog.setLabelText(
                f"Downloading Other Works… {int(done)} of {int(total)} book"
                f"{'' if total == 1 else 's'}"
            )
        except (RuntimeError, AttributeError, TypeError, ValueError):
            logger.debug("Could not update download progress", exc_info=True)

    def on_download_finished(self, _summary: dict) -> None:
        """GUI-thread slot: close the download progress bar when done."""
        dialog = self._download_progress_dialog
        if dialog is not None:
            try:
                dialog.close()
            except (RuntimeError, AttributeError, TypeError, ValueError):
                logger.debug("Could not close download progress dialog", exc_info=True)
        self._download_progress_dialog = None
