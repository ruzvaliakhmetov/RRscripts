#MenuTitle: Clear Selected Glyphs
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs, Message

font = Glyphs.font

if not font:
    Message("No font open", "Open a font first.")
else:
    selected_layers = font.selectedLayers

    if not selected_layers:
        Message("No glyphs selected", "Select glyphs in Font View first.")
    else:
        # Get unique glyphs from selected layers
        selected_glyphs = []
        seen = set()

        for layer in selected_layers:
            glyph = layer.parent
            if glyph and glyph.name not in seen:
                selected_glyphs.append(glyph)
                seen.add(glyph.name)

        font.disableUpdateInterface()

        try:
            for glyph in selected_glyphs:
                glyph.beginUndo()

                try:
                    for layer in glyph.layers:
                        # Preserve advance width
                        width = layer.width

                        # Removes paths, components, anchors, hints, guides, etc.
                        layer.clear()

                        # Restore width after clearing
                        layer.width = width

                finally:
                    glyph.endUndo()

            print("Cleared contents of %i glyph(s)." % len(selected_glyphs))

        finally:
            font.enableUpdateInterface()