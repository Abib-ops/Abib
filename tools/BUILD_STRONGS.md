# Building `strongs.sqlite`

`build_strongs_sqlite.py` is a **developer-only, one-off generator** for the
Strong's-number / original-language lookup data used by Abib. It is *not* part
of the shipped application (just like the generator for `gill.cmt.sqlite`).

It reads the source datasets from the external **`bible-llm-reference`**
workspace and emits a read-only SQLite database that follows the same
conventions as Abib's existing `gill.cmt.sqlite`.

## Sources

Kept in the external workspace (default `C:\Projects\bible-llm-reference`):

| File                                               | What it is                                                                                                                                                                                                                                                         | License                |
| -------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------- |
| `kjv.json`                                         | Bolls Bible "KJV (1769) with Strong's Numbers". Each translated word is followed by `<S>N</S>` tags; `<sup>...</sup>` footnotes are ignored. It lists the 66 canonical books first, then apocryphal books (which Abib does not use and which the generator skips). | Public domain KJV text |
| `strongs_data/hebrew/strongs-hebrew-dictionary.js` | Open Scriptures *Strong's Hebrew Dictionary*                                                                                                                                                                                                                       | CC-BY-SA               |
| `strongs_data/greek/strongs-greek-dictionary.js`   | Open Scriptures *Strong's Greek Dictionary*                                                                                                                                                                                                                        | CC-BY-SA               |

The verse numbering is aligned to Abib's flat global verse index using
`src/abib/data/Info.txt` (0-based `[book, chapter, verse]` rows), so the output
is directly compatible with `abib.core.shared.Info` / `sh.Info`.

## Output

By default, the database is written to `src/abib/data/strongs.sqlite` — the same
folder Abib loads runtime data from via `sh.str_cwd` (mirroring
`gill.cmt.sqlite`). Runtime code should therefore open it as
`Path(sh.str_cwd) / "strongs.sqlite"`.

### Schema

```sql
word_tags(
    verse_index INTEGER NOT NULL,  -- global verse index (0..31100), matches sh.Info
    word_pos    INTEGER NOT NULL,  -- 0-based Strong's-tag position within the verse
    surface     TEXT,              -- the KJV word/phrase the tag applies to
    strongs     TEXT NOT NULL      -- normalised code, e.g. 'H0430', 'G3056'
);
strongs_dict(
    strongs       TEXT PRIMARY KEY, -- 'H0430'
    lemma         TEXT,             -- original-script word (e.g. אֱלֹהִים / λόγος)
    translit      TEXT,             -- transliteration
    pronunciation TEXT,             -- Hebrew only (Greek dict has none)
    short_def     TEXT,             -- Strong's concise definition
    long_def      TEXT,             -- derivation + KJV renderings
    language      TEXT              -- 'hebrew' | 'greek'
);
meta(key TEXT PRIMARY KEY, value TEXT);  -- provenance / row counts

-- Indexes
idx_word_tags_verse   ON word_tags(verse_index);   -- verse -> its tags
idx_word_tags_strongs ON word_tags(strongs);       -- 'find all occurrences'
```

Strong's codes are normalised to `H%04d` / `G%04d` (OT books 1–39 → `H`,
NT books 40–66 → `G`). E.g. the bare `430` in Genesis becomes `H0430`.

## Usage

Run from the `tools/` directory (so `project_setup.py` is importable):

```powershell
cd C:\Projects\Abib\tools
python build_strongs_sqlite.py
```

Options:

```powershell
# Point at a different reference workspace
python build_strongs_sqlite.py --reference C:\Projects\bible-llm-reference

# Write somewhere else
python build_strongs_sqlite.py --output C:\some\path\strongs.sqlite

# Use a different Info.txt
python build_strongs_sqlite.py --info ..\src\abib\data\Info.txt
```

## Expected result (current data)

```
verse positions loaded : 31,102
dictionary entries     : 14,197  (Hebrew + Greek)
word_tags rows         : 351,675
verses processed       : 31,207
verses unmapped        : 105     (apocryphal additions inside Esther; expected)
output size            : ~21 MB
```

Spot-checks: Genesis 1:1 "God" → `H0430` (אֱלֹהִים, *ʼĕlôhîym*), which occurs
2,606 times; `G3056` → λόγος (*lógos*).

The 105 "unmapped" verses are apocryphal additions embedded in the Bolls
*Esther*; Abib does not contain them, so they are correctly dropped.

## Notes for shipping

- Add `strongs.sqlite` to `Abib.spec` and `64Bit_for_Abib.iss` next to
  `gill.cmt.sqlite` so it is bundled from `src/abib/data`.
- Add attribution for the Bolls KJV Strong's text and the Open Scriptures
  (CC-BY-SA) dictionaries to `HELP.txt` / `README.txt`.
- The bulky source inputs stay in the external `bible-llm-reference` workspace
  (outside version control); only this generator + README are committed.
