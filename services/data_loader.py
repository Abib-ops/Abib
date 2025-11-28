from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Tuple
from json import load, JSONDecodeError

import shared as sh
import fcs


@dataclass
class BibleData:
    KJV: Tuple[str, ...]
    KJB_PCE_LASTLINE: int
    EOTNOC: str
    Amap: List[Any]
    Ps119: List[int]
    P119: List[Any]
    book_bounds: List[int]
    starts_with_italics: List[int]


@dataclass
class SearchData:
    Rnew: Tuple[str, ...]
    Rdic: Dict[int, str]
    Rlow: Tuple[str, ...]
    Ldic: Dict[int, str]
    Rstp: Tuple[str, ...]
    Rlsp: Tuple[str, ...]
    stripped_dict: Dict[str, Any]
    strpd_low_dict: Dict[str, Any]
    set_dict: Dict[str, Any]
    set_lowdict: Dict[str, Any]


@dataclass
class SmeData:
    data: Dict[str, Dict[str, str]]
    date_file: tuple


class DataLoader:
    """Centralises loading of Bible text, indexes, and SME metadata.

    Provides explicit, cacheable load methods so app bootstrap can stay thin and
    other modules may reuse this logic later (e.g., for tests).
    """

    def __init__(self, base_dir: Path | None = None) -> None:
        self.base_dir = base_dir or sh.base_dir
        self._bible: BibleData | None = None
        self._search: SearchData | None = None
        self._sme: SmeData | None = None

    # ---- Bible ----
    def load_bible(self) -> BibleData:
        if self._bible is not None:
            return self._bible

        # KJV text and copyright trimming
        KJB_PCE_LASTLINE = 36199
        file_path = str(self.base_dir / "KJB_PCE.txt")
        KJV = fcs.readio('', file_path, KJB_PCE_LASTLINE)

        EOTNOC = '****END OF THE NOTICE OF COPYRIGHT****\n'
        try:
            i_ = KJV.index(EOTNOC)
        except ValueError as e:
            raise SystemExit('Failed to find copyright marker; reinstall may resolve.') from e
        KJV = tuple(KJV[i_ + 1:])

        # Amap
        amap_path = str(self.base_dir / "Amap.txt")
        Amap_raw = sh.readfile('', amap_path, sh.EOF_AMAP)
        Amap = Amap_raw[17:]

        # Psalm 119 helpers
        Ps119: List[int] = [
            15907, 15915, 15923, 15931, 15939, 15947, 15955, 15963, 15971, 15979,
            15987, 15995, 16003, 16011, 16019, 16027, 16035, 16043, 16051, 16059,
            16067
        ]
        P119: List[Any] = [Amap[_] for _ in Ps119]

        # Precomputed bounds/flags used by syntax/highlighting (kept for parity)
        # Compute book start bounds (0-based verse indices) for all 66 books from Info,
        # then append a sentinel (LAST_VERSE_IN_BIBLE + 1). This avoids hard-coded
        # mistakes and guarantees strict monotonicity and correctness across all books.
        book_bounds: List[int] = [sh.LAST_VERSE_IN_BIBLE + 1] * sh.BOOKS_IN_THE_BIBLE
        try:
            # shared.Info is a tuple of per-verse metadata; index 0 is the 0-based book id
            for idx in range(sh.LAST_VERSE_IN_BIBLE + 1):
                b = sh.Info[idx][0]
                if 0 <= b < sh.BOOKS_IN_THE_BIBLE and idx < book_bounds[b]:
                    book_bounds[b] = idx
            # Validate none are left at default; if any remain, we fall back to a simple increasing fill
            last_seen = 0
            for i in range(sh.BOOKS_IN_THE_BIBLE):
                if book_bounds[i] == sh.LAST_VERSE_IN_BIBLE + 1:
                    book_bounds[i] = last_seen
                last_seen = book_bounds[i]
        except Exception:
            # On any unexpected issue, fall back to the original hard-coded Psalms start and an even split
            # (still monotonic). This is a defensive fallback and should not normally trigger.
            book_bounds = [0] + [i * (sh.LAST_VERSE_IN_BIBLE // (sh.BOOKS_IN_THE_BIBLE - 1)) for i in range(1, sh.BOOKS_IN_THE_BIBLE)]
        # Append sentinel end bound
        book_bounds.append(sh.LAST_VERSE_IN_BIBLE + 1)
        starts_with_italics = [6203, 13009, 14972, 15412, 22195, 28117]

        self._bible = BibleData(
            KJV=KJV,
            KJB_PCE_LASTLINE=KJB_PCE_LASTLINE,
            EOTNOC=EOTNOC,
            Amap=Amap,
            Ps119=Ps119,
            P119=P119,
            book_bounds=book_bounds,
            starts_with_italics=starts_with_italics,
        )
        return self._bible

    # ---- Search ----
    def load_search(self) -> SearchData:
        if self._search is not None:
            return self._search

        Rnew = tuple(fcs.readio('', str(self.base_dir / "PCE-find.txt"), sh.EOF_BIBLE_TEXT))
        Rdic = dict(enumerate(Rnew))

        Rlow = tuple(fcs.readio('', str(self.base_dir / "PCE-lower.txt"), sh.EOF_BIBLE_TEXT))
        Ldic = dict(enumerate(Rlow))

        Rstp = tuple(fcs.readio('', str(self.base_dir / "PCE-stripped.txt"), sh.EOF_BIBLE_TEXT))
        Rlsp = tuple(fcs.readio('', str(self.base_dir / "PCE-stripped_lower.txt"), sh.EOF_BIBLE_TEXT))

        with open(self.base_dir / "stripped_dict.txt", encoding="utf-8") as f:
            stripped_dict: Dict[str, Any] = load(f)
        with open(self.base_dir / "strpd_low_dict.txt", encoding="utf-8") as f:
            strpd_low_dict: Dict[str, Any] = load(f)

        set_dict = fcs.load_list_set_dict(str(self.base_dir / "list_dict.json"), stripped_dict)
        set_lowdict = fcs.load_list_set_dict(str(self.base_dir / "list_lowdict.json"), strpd_low_dict)

        self._search = SearchData(
            Rnew=Rnew,
            Rdic=Rdic,
            Rlow=Rlow,
            Ldic=Ldic,
            Rstp=Rstp,
            Rlsp=Rlsp,
            stripped_dict=stripped_dict,
            strpd_low_dict=strpd_low_dict,
            set_dict=set_dict,
            set_lowdict=set_lowdict,
        )
        return self._search

    # ---- SME (legacy compatibility) ----
    def load_sme(self) -> SmeData:
        if self._sme is not None:
            return self._sme
        data: Dict[str, Dict[str, str]] = {}
        sme_path = self.base_dir / "morning_evening.json"
        try:
            with open(sme_path, "r", encoding="utf-8") as fh:
                data = load(fh)
        except FileNotFoundError:
            data = {}
        except JSONDecodeError:
            data = {}
        date_file = fcs.get_date_file()
        self._sme = SmeData(data=data, date_file=date_file)
        return self._sme

    # Convenience to load everything eagerly (optional)
    def load_all(self) -> tuple[BibleData, SearchData, SmeData]:
        return self.load_bible(), self.load_search(), self.load_sme()
