# Abib
# Copyright (C) 2003–2026 <Contributors>
# SPDX-License-Identifier: GPL-3.0-or-later

# -*- coding: utf-8 -*-

"""Build the tiny "Abib Italic h" font from Noto Sans Math.

The KJB text marks an italic 'h' with U+1D4BD MATHEMATICAL SCRIPT SMALL H
(the Mathematical Italic block has no 'h'; its proper italic h is U+210E).
Abib's search and highlighting code depends on that exact character, so it is
kept in the text and only its *appearance* is changed: this font maps
U+1D4BD to Noto Sans Math's italic h glyph, so it matches the other
Mathematical Italic letters drawn by Noto Sans Math.

Usage (fontTools is only needed to build the font, not to run Abib):
    uv run --no-project --with fonttools python tools/build_italic_h_font.py
"""

import sys
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._c_m_a_p import CmapSubtable

FAMILY = "Abib Italic h"
POSTSCRIPT_NAME = "AbibItalich-Regular"
PLANCK_H = 0x210E  # Italic h used by Mathematical Italic fonts
SCRIPT_H = 0x1D4BD  # The italic h used in the KJB text

font_dir = Path(__file__).resolve().parents[1] / "src" / "abib" / "font"
source_path = font_dir / "NotoSansMath-Regular.ttf"
target_path = font_dir / "AbibItalicH.ttf"


def build(source: Path = source_path, target: Path = target_path) -> None:
    font = TTFont(str(source))
    options = subset.Options()
    options.layout_features = []
    options.drop_tables += ["MATH", "GSUB", "GPOS", "GDEF"]
    options.name_IDs = ["*"]
    options.notdef_outline = True
    subsetter = subset.Subsetter(options)
    subsetter.populate(unicodes=[PLANCK_H])
    subsetter.subset(font)

    glyph = font.getBestCmap()[PLANCK_H]
    bmp = CmapSubtable.newSubtable(4)
    bmp.platformID, bmp.platEncID, bmp.language = 3, 1, 0
    bmp.cmap = {PLANCK_H: glyph}
    full = CmapSubtable.newSubtable(12)
    full.platformID, full.platEncID, full.language = 3, 10, 0
    full.cmap = {PLANCK_H: glyph, SCRIPT_H: glyph}
    font["cmap"].tables = [bmp, full]

    names = font["name"]
    for name_id in (16, 17, 21, 22):
        names.removeNames(nameID=name_id)
    for name_id, value in (
        (1, FAMILY),
        (2, "Regular"),
        (3, f"{POSTSCRIPT_NAME};derived from Noto Sans Math"),
        (4, FAMILY),
        (6, POSTSCRIPT_NAME),
    ):
        names.setName(value, name_id, 3, 1, 0x409)
        names.setName(value, name_id, 1, 0, 0)

    font.save(str(target))
    print(f"Wrote {target} ({target.stat().st_size} bytes)")


if __name__ == "__main__":
    build(*(Path(arg) for arg in sys.argv[1:3]))
