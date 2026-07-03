#MenuTitle: Get Scripts in Macro
# -*- coding: utf-8 -*-
font = Glyphs.font

scripts = sorted(set(
    glyph.script for glyph in font.glyphs
    if glyph.script
))

for script in scripts:
    print(f"script={script}")