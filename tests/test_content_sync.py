# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

import hashlib
import json
import re

import pytest
import requests

from abib.core import content_sync as cs
from abib.core import shared as sh
from tools.build_content_manifest import build_manifest


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture()
def user_dirs(tmp_path, monkeypatch):
    """Point all user directories at a temporary location."""
    settings_dir = tmp_path / "Abib"
    other = settings_dir / "Other Works"
    comps = settings_dir / "Other Works companions"
    crossrefs = settings_dir / "Cross References"
    monkeypatch.setattr(sh, "user_settings_dir", settings_dir)
    monkeypatch.setattr(sh, "user_other_works_dir", other)
    monkeypatch.setattr(sh, "user_companions_dir", comps)
    monkeypatch.setattr(sh, "user_crossrefs_dir", crossrefs, raising=False)
    monkeypatch.setattr(cs, "LOCAL_MANIFEST_PATH", settings_dir / "content_manifest.json")
    return settings_dir, other, comps


class _FakeResponse:
    def __init__(self, content: bytes):
        self._content = content

    @staticmethod
    def raise_for_status():
        return None

    def iter_content(self, chunk_size=65536):
        for i in range(0, len(self._content), chunk_size):
            yield self._content[i:i + chunk_size]


def _make_fake_get(files: dict[str, bytes], manifest: dict):
    """Return a fake requests.get serving the manifest and file contents."""
    def fake_get(url, timeout=None, stream=False):
        _ = (timeout, stream)  # Accept requests.get's signature; unused in the fake.
        if url == cs.CONTENT_MANIFEST_URL:
            resp = _FakeResponse(b"")
            resp.json = lambda: manifest  # type: ignore[attr-defined]
            return resp
        # Decode the raw file URL back to a repo-relative path.
        from urllib.parse import unquote
        rel = unquote(url[len(cs.CONTENT_RAW_BASE) + 1:])
        if rel in files:
            return _FakeResponse(files[rel])
        raise requests.exceptions.HTTPError(f"404 {rel}")
    return fake_get


def _manifest(entries: dict[str, bytes], version: str = "2026.01.01") -> dict:
    return {
        "content_version": version,
        "files": [
            {"path": p, "sha256": _sha256(c), "size": len(c)}
            for p, c in entries.items()
        ],
    }


def test_stem_of_handles_companions():
    assert cs._stem_of("Other Works/Foo.txt") == "Foo"
    assert cs._stem_of("Other Works companions/Foo.txt.refs.json.gz") == "Foo"


def test_sha256_of_file(tmp_path):
    p = tmp_path / "a.txt"
    p.write_bytes(b"hello")
    assert cs._sha256_of_file(p) == _sha256(b"hello")
    assert cs._sha256_of_file(tmp_path / "missing.txt") == ""


def test_offline_returns_offline_status(user_dirs, monkeypatch):
    def boom(*_a, **_k):
        raise requests.exceptions.ConnectionError("no network")
    monkeypatch.setattr("requests.get", boom)
    result = cs.sync_content()
    assert result["status"] == "offline"


def test_initial_download_adds_files(user_dirs, monkeypatch):
    settings_dir, other, comps = user_dirs
    files = {
        "Other Works/Foo.txt": b"foo text",
        "Other Works companions/Foo.txt.refs.json.gz": b"\x1f\x8bfoo",
    }
    manifest = _manifest(files)
    monkeypatch.setattr("requests.get", _make_fake_get(files, manifest))

    result = cs.sync_content()

    assert result["status"] == "ok"
    assert result["added"] == 2
    assert result["updated"] == 0
    # Book-only count excludes the companion: one book, not two files.
    assert result["added_books"] == 1
    assert result["updated_books"] == 0
    assert (other / "Foo.txt").read_bytes() == b"foo text"
    assert (comps / "Foo.txt.refs.json.gz").is_file()
    # Local manifest persisted.
    assert (settings_dir / "content_manifest.json").is_file()


def test_unchanged_version_fast_exit(user_dirs, monkeypatch):
    settings_dir, _, _ = user_dirs
    files = {"Other Works/Foo.txt": b"foo text"}
    manifest = _manifest(files, version="2026.05.05")
    # Pre-seed a local manifest with the same version.
    settings_dir.mkdir(parents=True, exist_ok=True)
    (settings_dir / "content_manifest.json").write_text(json.dumps(manifest))
    monkeypatch.setattr("requests.get", _make_fake_get(files, manifest))

    result = cs.sync_content()

    assert result["status"] == "unchanged"
    assert result["added"] == 0


def test_only_changed_file_redownloaded(user_dirs, monkeypatch):
    _settings_dir, other, _ = user_dirs
    v1 = {"Other Works/Foo.txt": b"foo v1", "Other Works/Bar.txt": b"bar"}
    monkeypatch.setattr("requests.get", _make_fake_get(v1, _manifest(v1, "1")))
    cs.sync_content()

    # Change Foo only, bump version.
    v2 = {"Other Works/Foo.txt": b"foo v2 changed", "Other Works/Bar.txt": b"bar"}
    monkeypatch.setattr("requests.get", _make_fake_get(v2, _manifest(v2, "2")))
    result = cs.sync_content()

    assert result["updated"] == 1  # only Foo
    assert result["added"] == 0
    assert (other / "Foo.txt").read_bytes() == b"foo v2 changed"


def test_corrupt_download_is_discarded(user_dirs, monkeypatch):
    settings_dir, other, _ = user_dirs
    files = {"Other Works/Foo.txt": b"real content"}
    # Manifest declares a wrong sha256 so verification fails.
    bad_manifest = {
        "content_version": "9",
        "files": [{"path": "Other Works/Foo.txt", "sha256": "deadbeef", "size": 12}],
    }
    monkeypatch.setattr("requests.get", _make_fake_get(files, bad_manifest))

    result = cs.sync_content()

    assert result["status"] == "partial"
    assert not (other / "Foo.txt").exists()
    assert not (other / "Foo.txt.part").exists()
    # Manifest NOT persisted on partial failure.
    assert not (settings_dir / "content_manifest.json").exists()


def test_list_available_reports_titles_and_downloaded(user_dirs):
    _settings_dir, other, _ = user_dirs
    other.mkdir(parents=True, exist_ok=True)
    (other / "Foo.txt").write_bytes(b"foo")  # already downloaded
    remote = {
        "content_version": "1",
        "files": [
            {"path": "Other Works/Foo.txt", "sha256": "a", "title": "The Foo Book"},
            {"path": "Other Works/Bar.txt", "sha256": "b"},  # no title -> stem
            {"path": "Other Works companions/Foo.txt.refs.json.gz", "sha256": "c"},
            {"path": "Other Works/Pilgrims-Progress.txt", "sha256": "d"},  # seed excluded
        ],
    }

    books = cs.list_available(remote)

    # Companions and the protected seed are not listed; sorted by title.
    assert [b["stem"] for b in books] == ["Bar", "Foo"]
    foo = next(b for b in books if b["stem"] == "Foo")
    bar = next(b for b in books if b["stem"] == "Bar")
    assert foo["title"] == "The Foo Book"
    assert foo["downloaded"] is True
    assert bar["title"] == "Bar"  # falls back to stem
    assert bar["downloaded"] is False


def test_list_available_includes_cross_reference_dataset(user_dirs):
    settings_dir, _other, _comps = user_dirs
    crossrefs_dir = settings_dir / "Cross References"
    crossrefs_dir.mkdir(parents=True)
    (crossrefs_dir / "openbible-crossrefs.sqlite").write_bytes(b"sqlite")
    remote = _manifest({
        "Cross References/openbible-crossrefs.sqlite": b"sqlite",
    })
    remote["files"][0]["title"] = "Cross References (OpenBible.info)"

    available = cs.list_available(remote)

    assert available == [
        {
            "stem": "openbible-crossrefs",
            "title": "Cross References (OpenBible.info)",
            "downloaded": True,
            "kind": "dataset",
        }
    ]


def test_download_list_respects_selection(user_dirs):
    remote = _manifest({
        "Other Works/Foo.txt": b"foo",
        "Other Works companions/Foo.txt.refs.json.gz": b"foo-c",
        "Other Works/Bar.txt": b"bar",
    })

    # Only Foo selected -> Foo text + companion, Bar excluded.
    to_download = cs.compute_download_list(remote, selected_stems={"Foo"})
    paths = {e["path"] for e in to_download}
    assert paths == {"Other Works/Foo.txt", "Other Works companions/Foo.txt.refs.json.gz"}

    # Empty selection -> nothing.
    assert cs.compute_download_list(remote, selected_stems=set()) == []

    # None -> everything (backward compatible).
    assert len(cs.compute_download_list(remote, selected_stems=None)) == 3


def test_download_list_includes_selected_dataset(user_dirs):
    dataset_path = "Cross References/openbible-crossrefs.sqlite"
    remote = _manifest({
        dataset_path: b"cross-reference data",
        "Other Works/Foo.txt": b"foo",
    })

    assert [entry["path"] for entry in cs.compute_download_list(
        remote, selected_stems={"openbible-crossrefs"}
    )] == [dataset_path]


def test_dataset_sync_counts_progress_and_downloads_to_crossrefs_dir(user_dirs, monkeypatch):
    settings_dir, _other, _comps = user_dirs
    dataset_path = "Cross References/openbible-crossrefs.sqlite"
    files = {dataset_path: b"cross-reference data"}
    manifest = _manifest(files)
    manifest["files"][0]["title"] = "Cross References (OpenBible.info)"
    monkeypatch.setattr("requests.get", _make_fake_get(files, manifest))
    events: list[tuple[int, int]] = []

    result = cs.sync_content(
        selected_stems={"openbible-crossrefs"},
        progress_callback=lambda done, total: events.append((done, total)),
    )

    assert result["status"] == "ok"
    assert result["added"] == 1
    assert result["added_books"] == 1
    assert events == [(0, 1), (1, 1)]
    assert (settings_dir / dataset_path).read_bytes() == files[dataset_path]


def test_deletions_include_unselected_and_withdrawn_datasets(user_dirs):
    settings_dir, _other, _comps = user_dirs
    crossrefs_dir = settings_dir / "Cross References"
    crossrefs_dir.mkdir(parents=True)
    dataset = crossrefs_dir / "openbible-crossrefs.sqlite"
    dataset.write_bytes(b"old data")
    dataset_path = "Cross References/openbible-crossrefs.sqlite"

    assert cs.compute_deletions(_manifest({}), selected_stems=None) == [dataset]
    assert cs.compute_deletions(
        _manifest({dataset_path: b"old data"}), selected_stems=set()
    ) == [dataset]


def test_withdrawing_dataset_increments_removed_title_count(user_dirs, monkeypatch):
    settings_dir, _other, _comps = user_dirs
    crossrefs_dir = settings_dir / "Cross References"
    crossrefs_dir.mkdir(parents=True)
    dataset_path = "Cross References/openbible-crossrefs.sqlite"
    dataset = crossrefs_dir / "openbible-crossrefs.sqlite"
    dataset.write_bytes(b"old data")
    files = {dataset_path: b"old data"}
    monkeypatch.setattr("requests.get", _make_fake_get(files, _manifest(files)))

    result = cs.sync_content(selected_stems=set())

    assert result["removed"] == 1
    assert result["removed_books"] == 1
    assert not dataset.exists()


def test_sync_with_selection_downloads_only_selected(user_dirs, monkeypatch):
    _settings_dir, other, comps = user_dirs
    files = {
        "Other Works/Foo.txt": b"foo text",
        "Other Works companions/Foo.txt.refs.json.gz": b"foo-c",
        "Other Works/Bar.txt": b"bar text",
    }
    monkeypatch.setattr("requests.get", _make_fake_get(files, _manifest(files)))

    result = cs.sync_content(selected_stems={"Foo"})

    assert result["status"] == "ok"
    assert (other / "Foo.txt").is_file()
    assert (comps / "Foo.txt.refs.json.gz").is_file()
    assert not (other / "Bar.txt").exists()


def test_is_text_book_excludes_companions():
    assert cs._is_text_book("Other Works/Foo.txt") is True
    assert cs._is_text_book("Other Works companions/Foo.txt.refs.json.gz") is False
    assert cs._is_text_book("Other Works companions/Foo.txt.refs.json") is False
    assert cs._is_text_book("Cross References/openbible-crossrefs.sqlite") is True


def test_build_manifest_normalizes_files_preserves_titles_and_lists_dataset(tmp_path):
    repo = tmp_path / "Abib-OtherWorks"
    works = repo / "Other Works"
    companions = repo / "Other Works companions"
    crossrefs = repo / "Cross References"
    works.mkdir(parents=True)
    companions.mkdir()
    crossrefs.mkdir()

    text_path = works / "MHCC.txt"
    text_path.write_bytes(b"line one\r\nline two\r")
    companion_path = companions / "MHCC.txt.refs.json.gz"
    companion_data = b"compressed companion"
    companion_path.write_bytes(companion_data)
    dataset_path = crossrefs / "openbible-crossrefs.sqlite"
    dataset_data = b"sqlite database bytes"
    dataset_path.write_bytes(dataset_data)
    (repo / "manifest.json").write_text(json.dumps({
        "content_version": "old",
        "files": [
            {"path": "Other Works/MHCC.txt", "title": "Matthew Henry"},
            {
                "path": "Other Works companions/MHCC.txt.refs.json.gz",
                "title": "MHCC companion title",
            },
            {
                "path": "Cross References/openbible-crossrefs.sqlite",
                "title": "Old dataset title",
            },
            {"path": "Other Works/withdrawn.txt", "title": "Withdrawn"},
        ],
    }), encoding="utf-8")

    manifest = build_manifest(repo)

    assert re.fullmatch(r"\d{4}\.\d{2}\.\d{2}\.\d{6}", manifest["content_version"])
    assert text_path.read_bytes() == b"line one\nline two\n"
    entries = {entry["path"]: entry for entry in manifest["files"]}
    assert set(entries) == {
        "Other Works/MHCC.txt",
        "Other Works companions/MHCC.txt.refs.json.gz",
        "Cross References/openbible-crossrefs.sqlite",
    }
    text = entries["Other Works/MHCC.txt"]
    assert text["title"] == "Matthew Henry"
    assert text["sha256"] == _sha256(b"line one\nline two\n")
    assert text["size"] == len(b"line one\nline two\n")
    companion = entries["Other Works companions/MHCC.txt.refs.json.gz"]
    assert companion["title"] == "MHCC companion title"
    assert companion["sha256"] == _sha256(companion_data)
    dataset = entries["Cross References/openbible-crossrefs.sqlite"]
    assert dataset["title"] == "Cross References (OpenBible.info)"
    assert dataset["sha256"] == _sha256(dataset_data)
    assert dataset["size"] == len(dataset_data)
    assert json.loads((repo / "manifest.json").read_text(encoding="utf-8")) == manifest


def test_progress_callback_counts_books_not_companions(user_dirs, monkeypatch):
    _settings_dir, _other, _comps = user_dirs
    files = {
        "Other Works/Foo.txt": b"foo text",
        "Other Works companions/Foo.txt.refs.json.gz": b"foo-c",
        "Other Works/Bar.txt": b"bar text",
        "Other Works companions/Bar.txt.refs.json.gz": b"bar-c",
    }
    monkeypatch.setattr("requests.get", _make_fake_get(files, _manifest(files)))

    events: list[tuple[int, int]] = []
    result = cs.sync_content(progress_callback=lambda done, total: events.append((done, total)))

    assert result["status"] == "ok"
    # Two books downloaded, four files total; progress totals must be 2 (books
    # only), never 4 (which would include the companions).
    assert events[0] == (0, 2)
    assert events[-1] == (2, 2)
    assert all(total == 2 for _done, total in events)
    # The final book count matches the number of .txt books.
    assert events[-1][0] == 2


def test_deletion_removes_unsubscribed_book(user_dirs):
    _settings_dir, other, _comps = user_dirs
    other.mkdir(parents=True, exist_ok=True)
    (other / "Foo.txt").write_bytes(b"foo")
    (other / "Bar.txt").write_bytes(b"bar")
    (other / "Pilgrims-Progress.txt").write_bytes(b"seed")

    # Both Foo and Bar are in the manifest, but the user only subscribed to Foo.
    remote = _manifest({"Other Works/Foo.txt": b"foo", "Other Works/Bar.txt": b"bar"})
    deletions = cs.compute_deletions(remote, selected_stems={"Foo"})
    names = {p.name for p in deletions}

    assert "Bar.txt" in names  # unsubscribed -> removed
    assert "Foo.txt" not in names  # subscribed -> kept
    assert "Pilgrims-Progress.txt" not in names  # protected seed


def test_deletion_removes_withdrawn_but_guards_seed(user_dirs, monkeypatch):
    _settings_dir, other, comps = user_dirs
    other.mkdir(parents=True, exist_ok=True)
    comps.mkdir(parents=True, exist_ok=True)
    # Pre-existing user files: one withdrawn, plus the protected seed.
    (other / "Withdrawn.txt").write_bytes(b"old")
    (other / "Pilgrims-Progress.txt").write_bytes(b"seed")

    remote = _manifest({"Other Works/Keep.txt": b"keep"}, "7")
    deletions = cs.compute_deletions(remote)
    names = {p.name for p in deletions}

    assert "Withdrawn.txt" in names
    assert "Pilgrims-Progress.txt" not in names

