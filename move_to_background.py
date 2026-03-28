# MenuTitle: Move All Shapes to Background
# -*- coding: utf-8 -*-
from GlyphsApp import Glyphs

Font = Glyphs.font
if not Font:
    raise SystemExit()

# ---- helpers for undo, совместимы с разными версиями ----
def begin_undo(font):
    try:
        font.beginUndo()
    except Exception:
        font.undoManager().beginUndoGrouping()

def end_undo(font):
    try:
        font.endUndo()
    except Exception:
        font.undoManager().endUndoGrouping()
# ---------------------------------------------------------

Font.disableUpdateInterface()
begin_undo(Font)

try:
    for glyph in Font.glyphs:
        for layer in glyph.layers:
            # Только реальные слои (мастеры и спецслои)
            if not (layer.isMasterLayer or layer.isSpecialLayer):
                continue

            bg = layer.background
            if bg is None:
                continue

            # очистить фон (чтобы не накапливать)
            try:
                bg.shapes = []
            except Exception:
                for s in list(bg.shapes):
                    bg.removeShape_(s)

            # скопировать все формы в фон
            for s in layer.shapes:
                bg.shapes.append(s.copy())

            # скопировать хинты в фон
            try:
                bg.hints = [h.copy() for h in layer.hints]
            except Exception:
                for h in list(bg.hints):
                    bg.removeHint_(h)
                for h in layer.hints:
                    bg.addHint_(h.copy())

            # если нужны гайды в фоне, раскомментируйте:
            # try:
            #     bg.guides = [g.copy() for g in layer.guides]
            # except Exception:
            #     for g in list(bg.guides):
            #         bg.removeGuide_(g)
            #     for g in layer.guides:
            #         bg.addGuide_(g.copy())

            # очистить передний план
            for s in list(layer.shapes)[::-1]:
                layer.removeShape_(s)
            for h in list(layer.hints)[::-1]:
                layer.removeHint_(h)

finally:
    end_undo(Font)
    Font.enableUpdateInterface()
