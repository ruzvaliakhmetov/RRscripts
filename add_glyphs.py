# MenuTitle: Create Glyphs from Paragraphs...
# -*- coding: utf-8 -*-

import re
from GlyphsApp import Glyphs, GSGlyph
from vanilla import Window, TextBox, TextEditor, Button

ALLOWED_RE = re.compile(r"[A-Za-z0-9-]")

def sanitize_to_glyph_name(s: str) -> str:
    cleaned = []
    for ch in s:
        if ALLOWED_RE.match(ch):
            cleaned.append(ch)
        else:
            cleaned.append("-")
    name = "".join(cleaned)
    name = re.sub(r"-{2,}", "-", name)  # Collapse consecutive hyphens
    name = name.strip("-")              # Trim leading/trailing hyphens
    if not name.startswith("_"):
        name = "_" + name if name else "_"
    return name

def unique_name(font, base_name: str) -> str:
    name = base_name
    i = 1
    while font.glyphs[name] is not None:
        name = f"{base_name}-{i}"
        i += 1
    return name

def clear_meta(glyph):
    # Очистить Script/Category/Subcategory
    for attr in ("script", "category", "subCategory"):
        try:
            setattr(glyph, attr, None)
        except Exception:
            setattr(glyph, attr, "")

class ParagraphGlyphsUI(object):
    def __init__(self):
        self.w = Window((600, 460), "Create Glyphs from Paragraphs")
        self.w.label = TextBox((15, 12, -15, 20), "Each non-empty line becomes a separate glyph.")
        self.w.input = TextEditor(
            (15, 40, -15, -60),
            text="",
            callback=None
        )
        self.w.makeButton = Button(
            (-200, -40, -15, 24),
            "Create glyphs",
            callback=self.make_glyphs,
        )
        self.w.open()
        self.w.makeKey()

    def make_glyphs(self, sender):
        font = Glyphs.font
        if not font:
            Glyphs.showNotification(
                "Create Glyphs from Paragraphs",
                "Open a font before running the script."
            )
            return

        raw = self.w.input.get()
        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        if not lines:
            Glyphs.showNotification("Create Glyphs from Paragraphs", "No text found. Paste text.")
            return

        created = []
        font.disableUpdateInterface()
        try:
            for line in lines:
                name = sanitize_to_glyph_name(line).rstrip("-")
                if name == "_":
                    name = "_glyph"
                name = unique_name(font, name)

                glyph = GSGlyph(name)
                font.glyphs.append(glyph)

                # Clear auto-detected fields
                clear_meta(glyph)

                created.append(name)
        finally:
            font.enableUpdateInterface()

        msg = "Glyphs created: %d\n" % len(created)
        if created:
            msg += "• " + "\n• ".join(created[:20])
            if len(created) > 20:
                msg += f"\n… and {len(created)-20} more"
        Glyphs.showNotification("Create Glyphs from Paragraphs", msg)

ParagraphGlyphsUI()
