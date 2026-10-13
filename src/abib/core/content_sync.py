# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

################################################################################
## Content sync service for the optional "Other Works" library.
##
## Mirrors the structure and the ``requests.exceptions.RequestException``
## handling of ``updater.py``. The bulk of the Other Works texts (and their
## precomputed ".refs.json.gz" companions) live in a separate GitHub content
## repo (``Abib-ops/Abib-OtherWorks``) and are downloaded on demand into the
## writable per-user directory (``%APPDATA%\\Abib`` on Windows). Only the
## bundled seed book (Pilgrim's Progress) ships with the installer.
##
## A ``manifest.json`` at the repo root lists every file with a ``content_version``
## (fast "nothing changed" check) and per-file ``sha256`` (download only
## new/changed files). Downloads are written to a temp name, verified against
## the manifest ``sha256`` and then atomically ``os.replace``d into place so a
## partial/corrupt download can never clobber a good copy.
################################################################################

import hashlib
import json
import os
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from PySide6.QtCore import QObject, QThread, Signal

from abib.core import shared as sh

# Paths and URLs
CONTENT_RAW_BASE = "https://raw.githubusercontent.com/Abib-ops/Abib-OtherWorks/main"
CONTENT_MANIFEST_URL = f"{CONTENT_RAW_BASE}/manifest.json"

# Local copy of the last-synced manifest.
LOCAL_MANIFEST_PATH: Path = sh.user_settings_dir / "content_manifest.json"

# Network timeout (matches updater.py's short timeout).
REQUEST_TIMEOUT = 4

# Stems that must never be removed by a sync deletion (the bundled seed book
# guarantees a usable offline/first-run experience and the ``last_other_work``
# fallback, so it can never be stripped away).
PROTECTED_STEMS: frozenset[str] = frozenset({"Pilgrims-Progress"})


def fetch_remote_manifest() -> dict[str, Any] | None:
    """Fetch and parse the remote ``manifest.json``.

    Returns the parsed manifest dict, or ``None`` on any network/format
    problem (so callers can fail silently when offline).
    """
    try:
        response = requests.get(CONTENT_MANIFEST_URL, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.RequestException:
        # Offline or server unreachable — fail silently.
        return None
    except ValueError:
        # Malformed JSON.
        return None

    if not isinstance(data, dict):
        return None
    if not isinstance(data.get("files"), list):
        return None
    return data


def load_local_manifest() -> dict[str, Any]:
    """Load the locally stored manifest, or an empty manifest if absent."""
    try:
        text = LOCAL_MANIFEST_PATH.read_text(encoding="utf-8")
        data = json.loads(text)
    except (OSError, ValueError):
        return {"content_version": "", "files": []}
    if not isinstance(data, dict):
        return {"content_version": "", "files": []}
    if not isinstance(data.get("files"), list):
        data["files"] = []
    return data


def _manifest_files_by_path(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Index a manifest's ``files`` list by their ``path`` (ignoring bad rows)."""
    result: dict[str, dict[str, Any]] = {}
    for entry in manifest.get("files", []):
        if not isinstance(entry, dict):
            continue
        path = entry.get("path")
        if isinstance(path, str) and path:
            result[path] = entry
    return result


def _target_path(rel_path: str) -> Path:
    """Map a manifest ``path`` (e.g. ``Other Works/Foo.txt``) to its local file.

    The manifest paths use the spaced ``Other Works`` / ``Other Works
    companions`` folder names which line up exactly with the user directories
    under ``user_settings_dir``.
    """
    return sh.user_settings_dir / Path(rel_path)


def _stem_of(rel_path: str) -> str:
    """Return the work stem for a manifest path.

    ``Other Works/Foo.txt`` -> ``Foo``;
    ``Other Works companions/Foo.txt.refs.json.gz`` -> ``Foo``.
    """
    name = Path(rel_path).name
    if name.endswith(".txt.refs.json.gz"):
        return name[: -len(".txt.refs.json.gz")]
    if name.endswith(".txt.refs.json"):
        return name[: -len(".txt.refs.json")]
    return Path(name).stem


def _sha256_of_file(path: Path) -> str:
    """Return the lowercase hex SHA-256 of a file, or "" if unreadable."""
    try:
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                h.update(chunk)
        return h.hexdigest()
    except OSError:
        return ""


def _normalise_selection(selected_stems: Iterable[str] | None) -> set[str] | None:
    """Return a set of selected stems, or ``None`` meaning "all titles".

    ``None`` keeps the original all-or-nothing behaviour (used by callers that
    want the whole catalogue). A concrete (possibly empty) iterable restricts
    the sync to those stems only; an empty set therefore means "nothing".
    """
    if selected_stems is None:
        return None
    return {str(s) for s in selected_stems}


def list_available(remote: dict[str, Any]) -> list[dict[str, Any]]:
    """List the optional books offered by the remote manifest.

    Returns one entry per *text* file (companions are grouped under the same
    stem) as a dict with ``stem``, ``title`` (human-readable, falling back to
    the stem) and ``downloaded`` (whether the text already exists locally).
    The list is sorted by title (case-insensitively) for stable display.
    """
    books: list[dict[str, Any]] = []
    for path, entry in _manifest_files_by_path(remote).items():
        name = Path(path).name
        if not name.endswith(".txt"):
            continue
        stem = _stem_of(path)
        if stem in PROTECTED_STEMS:
            # The bundled seed book is never an optional download.
            continue
        title = str(entry.get("title") or "").strip() or stem
        downloaded = _target_path(path).is_file()
        books.append({"stem": stem, "title": title, "downloaded": downloaded})
    books.sort(key=lambda b: str(b["title"]).casefold())
    return books


def compute_download_list(
    remote: dict[str, Any],
    selected_stems: Iterable[str] | None = None,
) -> list[dict[str, Any]]:
    """Build the list of files that are new or whose ``sha256`` differs locally.

    A file is downloaded when it is missing on disk or its on-disk SHA-256
    does not match the manifest entry. When ``selected_stems`` is given, only
    files belonging to those stems (plus any protected seed) are considered,
    so the user downloads just the books they chose.
    """
    selection = _normalise_selection(selected_stems)
    to_download: list[dict[str, Any]] = []
    for path, entry in _manifest_files_by_path(remote).items():
        if selection is not None:
            stem = _stem_of(path)
            if stem not in selection and stem not in PROTECTED_STEMS:
                continue
        expected = str(entry.get("sha256", "")).lower()
        target = _target_path(path)
        if not target.is_file():
            to_download.append(entry)
            continue
        if expected and _sha256_of_file(target) != expected:
            to_download.append(entry)
    return to_download


def compute_deletions(
    remote: dict[str, Any],
    selected_stems: Iterable[str] | None = None,
) -> list[Path]:
    """Find local user-dir works/companions that should be removed.

    Without ``selected_stems`` a file is removed only when it is no longer
    listed in the manifest (withdrawn upstream). With ``selected_stems`` a file
    is also removed when its stem is not in the selection (the user
    unsubscribed from that book).

    The bundled seed book (and anything else in ``PROTECTED_STEMS``) is never
    returned, so a sync can never strip the app back to an empty library.
    """
    selection = _normalise_selection(selected_stems)
    remote_paths = set(_manifest_files_by_path(remote).keys())
    deletions: list[Path] = []
    for directory, pattern in (
        (sh.user_other_works_dir, "*.txt"),
        (sh.user_companions_dir, "*.refs.json.gz"),
    ):
        if not directory.exists():
            continue
        for p in directory.glob(pattern):
            if not p.is_file():
                continue
            rel = f"{directory.name}/{p.name}"
            stem = _stem_of(rel)
            if stem in PROTECTED_STEMS:
                continue
            if selection is not None and stem not in selection:
                # User unsubscribed from this book.
                deletions.append(p)
                continue
            if rel in remote_paths:
                continue
            # Withdrawn upstream.
            deletions.append(p)
    return deletions


def _download_file(entry: dict[str, Any]) -> bool:
    """Download a single manifest entry atomically, verifying its SHA-256.

    Writes to a temp name in the target directory and ``os.replace``s on
    success so a partial/corrupt download never overwrites a good copy.
    """
    rel_path = str(entry.get("path", ""))
    if not rel_path:
        return False
    expected = str(entry.get("sha256", "")).lower()
    target = _target_path(rel_path)

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
    except OSError:
        return False

    url = f"{CONTENT_RAW_BASE}/{quote(rel_path)}"
    tmp = target.with_name(target.name + ".part")
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, stream=True)
        response.raise_for_status()
        h = hashlib.sha256()
        with open(tmp, "wb") as out:
            for chunk in response.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                out.write(chunk)
                h.update(chunk)
    except requests.exceptions.RequestException:
        _safe_unlink(tmp)
        return False
    except OSError:
        _safe_unlink(tmp)
        return False

    if expected and h.hexdigest() != expected:
        # Verification failed — discard and keep any existing good copy.
        _safe_unlink(tmp)
        return False

    try:
        os.replace(tmp, target)
    except OSError:
        _safe_unlink(tmp)
        return False
    return True


def _safe_unlink(path: Path) -> None:
    try:
        path.unlink()
    except OSError:
        pass


def _write_local_manifest(manifest: dict[str, Any]) -> None:
    try:
        sh.user_settings_dir.mkdir(parents=True, exist_ok=True)
        LOCAL_MANIFEST_PATH.write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def _is_text_book(rel_path: str) -> bool:
    """Return True if a manifest path is a book *text* file (not a companion).

    Companions end with ``.txt.refs.json.gz`` / ``.txt.refs.json``; only the
    plain ``.txt`` books are counted for download progress so the number the
    user sees reflects books, never the hidden companion index files.
    """
    name = Path(rel_path).name
    if name.endswith((".txt.refs.json.gz", ".txt.refs.json")):
        return False
    return name.endswith(".txt")


def sync_content(
    force: bool = False,
    selected_stems: Iterable[str] | None = None,
    progress_callback: Callable[[int, int], None] | None = None,
) -> dict[str, Any]:
    """Synchronise the Other Works content from the remote repo.

    Steps:
      1. Fetch the remote manifest (fail silently when offline).
      2. Fast exit if ``content_version`` matches the local manifest
         (unless ``force``).
      3. Download only new/changed files (per-file SHA-256 diff), atomically.
      4. Remove local works no longer listed (never the protected seed book).
      5. On full success, persist the fetched manifest.

    When ``selected_stems`` is given, only those books are downloaded/kept and
    any other (non-protected) local works are removed, so the user controls
    exactly which titles are present. ``None`` syncs the whole catalogue.

    ``progress_callback`` (if given) is called as ``(done, total)`` where both
    counts refer to *book text files only* (companion index files are never
    counted), so a progress bar reflects books, not hidden companions.

    Returns a small summary dict with ``status`` and ``added`` / ``updated`` /
    ``removed`` (all files) plus ``added_books`` / ``updated_books`` /
    ``removed_books`` (book text files only, excluding companions) counts for
    UI feedback.
    """
    summary: dict[str, Any] = {
        "status": "ok",
        "added": 0,
        "updated": 0,
        "removed": 0,
        "added_books": 0,
        "updated_books": 0,
        "removed_books": 0,
        "message": "",
    }

    remote = fetch_remote_manifest()
    if remote is None:
        summary["status"] = "offline"
        summary["message"] = "Could not reach the content server."
        return summary

    local = load_local_manifest()
    remote_version = str(remote.get("content_version", ""))
    local_version = str(local.get("content_version", ""))

    if not force and remote_version and remote_version == local_version:
        summary["status"] = "unchanged"
        summary["message"] = "Other Works are already up to date."
        return summary

    # Ensure the user directories exist before writing into them.
    try:
        sh.user_other_works_dir.mkdir(parents=True, exist_ok=True)
        sh.user_companions_dir.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        summary["status"] = "error"
        summary["message"] = f"Could not create content folders: {exc}"
        return summary

    to_download = compute_download_list(remote, selected_stems)
    # Count only book text files for progress — never the companions.
    total_books = sum(1 for e in to_download if _is_text_book(str(e.get("path", ""))))
    done_books = 0
    if progress_callback is not None:
        try:
            progress_callback(done_books, total_books)
        except (RuntimeError, AttributeError, TypeError, ValueError):
            # Progress reporting must never break a sync.
            pass
    all_ok = True
    for entry in to_download:
        rel_path = str(entry.get("path", ""))
        is_book = _is_text_book(rel_path)
        existed = _target_path(rel_path).is_file()
        if _download_file(entry):
            if existed:
                summary["updated"] += 1
                if is_book:
                    summary["updated_books"] += 1
            else:
                summary["added"] += 1
                if is_book:
                    summary["added_books"] += 1
        else:
            all_ok = False
        if is_book:
            done_books += 1
            if progress_callback is not None:
                try:
                    progress_callback(done_books, total_books)
                except (RuntimeError, AttributeError, TypeError, ValueError):
                    # Progress reporting must never break a sync.
                    pass

    for path in compute_deletions(remote, selected_stems):
        try:
            path.unlink()
            summary["removed"] += 1
            if _is_text_book(str(path.name)):
                summary["removed_books"] += 1
        except OSError:
            all_ok = False

    if all_ok:
        # Only persist the manifest when everything succeeded, so a failed
        # file is retried on the next sync (its SHA won't match).
        _write_local_manifest(remote)
    else:
        summary["status"] = "partial"
        summary["message"] = "Some files could not be updated; will retry later."

    return summary


class ContentSyncWorker(QObject):
    """Runs :func:`sync_content` off the UI thread.

    Emits :pyattr:`progress` as ``(done, total)`` book counts (companions are
    never counted) during the download, and :pyattr:`finished` with the summary
    dict (or an empty dict on an unexpected error) so the UI can show a progress
    bar and refresh the Other Works list without blocking startup.
    """

    progress = Signal(int, int)
    finished = Signal(dict)

    def __init__(self, force: bool = False, selected_stems: Iterable[str] | None = None) -> None:
        super().__init__()
        self._force = force
        self._selected_stems = None if selected_stems is None else set(selected_stems)

    def _emit_progress(self, done: int, total: int) -> None:
        self.progress.emit(int(done), int(total))

    def run(self) -> None:
        try:
            result = sync_content(
                force=self._force,
                selected_stems=self._selected_stems,
                progress_callback=self._emit_progress,
            )
        except (OSError, ValueError, RuntimeError, AttributeError, TypeError,
                requests.exceptions.RequestException):
            # Never let a background worker crash the app.
            result = {"status": "error", "added": 0, "updated": 0, "removed": 0,
                      "message": "Unexpected error during content sync."}
        self.finished.emit(result)


def start_background_sync(
    parent: QObject | None = None,
    force: bool = False,
    selected_stems: Iterable[str] | None = None,
    autostart: bool = True,
) -> tuple[QThread, ContentSyncWorker]:
    """Start a background content sync on a ``QThread``.

    Returns the ``(thread, worker)`` pair. The caller should keep a reference
    to both (e.g. on ``self``) until the thread finishes, and may connect to
    ``worker.finished`` to refresh the UI. The thread cleans itself up on
    completion. ``selected_stems`` restricts the sync to the user's chosen
    books (see :func:`sync_content`).

    When ``autostart`` is ``False`` the thread is created and wired up but not
    started, so the caller can connect additional slots to ``worker.progress``
    / ``worker.finished`` *before* calling ``thread.start()``. This avoids a
    race where the worker emits its first progress (or even finishes) before
    the GUI has connected, leaving the progress bar stuck and the Other Works
    list un-refreshed.
    """
    thread = QThread(parent)
    worker = ContentSyncWorker(force=force, selected_stems=selected_stems)
    worker.moveToThread(thread)
    thread.started.connect(worker.run)
    worker.finished.connect(thread.quit)
    worker.finished.connect(worker.deleteLater)
    thread.finished.connect(thread.deleteLater)
    if autostart:
        thread.start()
    return thread, worker
