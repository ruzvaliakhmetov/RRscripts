# MenuTitle: Expand Outline for Selected Glyphs (All Masters)

from GlyphsApp import Glyphs, Message

font = Glyphs.font

if not font:
    Message("No font open", "Open a font first.")
else:
    # 1) Selection from Font View
    selectedGlyphs = [g for g in font.glyphs if g.selected]

    # 2) Fallback: selection from current Edit tab
    if not selectedGlyphs:
        seen = set()
        selectedGlyphs = []
        for layer in font.selectedLayers:
            glyph = layer.parent
            if glyph and glyph.name not in seen:
                selectedGlyphs.append(glyph)
                seen.add(glyph.name)

    if not selectedGlyphs:
        Message("Nothing selected", "Select one or more glyphs in Font View or in an Edit tab.")
    else:
        Glyphs.clearLog()
        Glyphs.showMacroWindow()

        processedNames = []

        font.disableUpdateInterface()
        try:
            for glyph in selectedGlyphs:
                glyph.beginUndo()
                try:
                    for layer in glyph.layers:
                        if layer and len(layer.shapes) > 0:
                            layer.flattenOutlines()
                    processedNames.append(glyph.name)
                finally:
                    glyph.endUndo()
        finally:
            font.enableUpdateInterface()

        print("Expanded outlines in %i glyph(s):" % len(processedNames))
        print(", ".join(processedNames))

        Glyphs.showNotification(
            "Expand Outline finished",
            "Processed %i glyph(s)." % len(processedNames)
        )