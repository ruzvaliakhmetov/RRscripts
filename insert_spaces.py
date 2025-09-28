# MenuTitle: Insert space glyph...
# -*- coding: utf-8 -*-
from GlyphsApp import *
from AppKit import NSAlert, NSTextField, NSMakeRect

font = Glyphs.font
if not font:
    Message("No font open", "Откройте файл шрифта и запустите скрипт снова.")
    raise SystemExit

# ---------- helpers ----------

def to_int(x):
    # Отсечение дробной части (для положительных чисел int == floor)
    try:
        return int(x)
    except Exception:
        return 0

def get_or_create_glyph(glyph_name, uni_hex=None):
    g = font.glyphs[glyph_name]
    if g is None:
        g = GSGlyph(glyph_name)
        if uni_hex:
            g.unicode = uni_hex  # hex без "U+"
        font.glyphs.append(g)
    return g

def set_width_for_layer(glyph, masterID, width):
    glyph.layers[masterID].width = to_int(width)

def get_layer_width(glyph_name, masterID, fallback=None):
    g = font.glyphs[glyph_name]
    if g is None:
        return fallback
    return to_int(g.layers[masterID].width)

def compute_space_widths(M):
    # space (U+0020): (M/6) + (((M/4)-(M/6))/2) == 5*M/24
    return {
        "space":           to_int((M/6.0) + (((M/4.0) - (M/6.0)) / 2.0)),
        "hairspace":       to_int(M/24.0),           # U+200A
        "thinspace":       to_int((M/24.0) * 3.0),   # U+2009
        "sixperemspace":   to_int(M/6.0),            # U+2006
        "fourperemspace":  to_int(M/4.0),            # U+2005
        "threeperemspace": to_int(M/3.0),            # U+2004
        "enspace":         to_int(M/2.0),            # U+2002
        "emspace":         to_int(M),                # U+2003
    }

def prompt_string(title="Ширина EM SPACE (U+2003)", default="1000", info="Введите ширину M space (em)."):
    alert = NSAlert.alloc().init()
    alert.setMessageText_(title)
    alert.setInformativeText_(info)
    tf = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 0, 240, 24))
    tf.setStringValue_(str(default))
    alert.setAccessoryView_(tf)
    alert.addButtonWithTitle_("OK")
    alert.addButtonWithTitle_("Cancel")
    result = alert.runModal()
    if result == 1000:  # NSAlertFirstButtonReturn
        return tf.stringValue()
    else:
        return None

# ---------- prompt for EM width ----------

default_value = "1000"
answer = prompt_string(default=default_value)
if answer is None:
    print("Отменено пользователем.")
    raise SystemExit

try:
    Mspace = int(float(answer)) if len(answer.strip()) > 0 else int(default_value)
except Exception:
    Mspace = int(default_value)

# ---------- names & unicodes ----------

UNI = {
    "space":             "0020",  # U+0020
    "nbspace":           "00A0",  # U+00A0 NO-BREAK SPACE
    "hairspace":         "200A",  # U+200A
    "thinspace":         "2009",  # U+2009
    "nnbsp":             "202F",  # U+202F NARROW NO-BREAK SPACE
    "sixperemspace":     "2006",  # U+2006
    "fourperemspace":    "2005",  # U+2005
    "threeperemspace":   "2004",  # U+2004
    "enspace":           "2002",  # U+2002
    "emspace":           "2003",  # U+2003
    "figurespace":       "2007",  # U+2007
    "punctuationspace":  "2008",  # U+2008
}

# U+202F: если уже есть 'nnspace', используем его имя; иначе — 'nnbsp'
nnbsp_name = "nnspace" if font.glyphs["nnspace"] else "nnbsp"

# Зафиксируем, был ли обычный пробел ДО создания
space_existed_before = bool(font.glyphs["space"])

# ---------- create / get glyphs ----------

space_g      = get_or_create_glyph("space", UNI["space"])
nbspace_g    = get_or_create_glyph("nbspace", UNI["nbspace"])
hair_g       = get_or_create_glyph("hairspace", UNI["hairspace"])
thin_g       = get_or_create_glyph("thinspace", UNI["thinspace"])
nnbsp_g      = get_or_create_glyph(nnbsp_name, UNI["nnbsp"])
six_g        = get_or_create_glyph("sixperemspace", UNI["sixperemspace"])
four_g       = get_or_create_glyph("fourperemspace", UNI["fourperemspace"])
three_g      = get_or_create_glyph("threeperemspace", UNI["threeperemspace"])
en_g         = get_or_create_glyph("enspace", UNI["enspace"])
em_g         = get_or_create_glyph("emspace", UNI["emspace"])
figure_g     = get_or_create_glyph("figurespace", UNI["figurespace"])
punct_g      = get_or_create_glyph("punctuationspace", UNI["punctuationspace"])

# ---------- assign widths per master ----------

base = compute_space_widths(Mspace)

for master in font.masters:
    mid = master.id

    # space: только если его не было до скрипта
    if not space_existed_before:
        set_width_for_layer(space_g, mid, base["space"])
        current_space_width = base["space"]
    else:
        current_space_width = get_layer_width("space", mid, fallback=base["space"])

    # emspace
    set_width_for_layer(em_g, mid, base["emspace"])

    # hair / thin / narrow no-break (равен thin)
    set_width_for_layer(hair_g, mid, base["hairspace"])
    set_width_for_layer(thin_g, mid, base["thinspace"])
    set_width_for_layer(nnbsp_g, mid, base["thinspace"])

    # 2006/2005/2004/2002
    set_width_for_layer(six_g, mid, base["sixperemspace"])
    set_width_for_layer(four_g, mid, base["fourperemspace"])
    set_width_for_layer(three_g, mid, base["threeperemspace"])
    set_width_for_layer(en_g, mid, base["enspace"])

    # nbspace = обычный пробел
    set_width_for_layer(nbspace_g, mid, current_space_width)

    # figure space = width of zero.tf → zero → обычный пробел
    fig_w = get_layer_width("zero.tf", mid, None)
    if fig_w is None:
        fig_w = get_layer_width("zero", mid, None)
    if fig_w is None:
        fig_w = current_space_width
    set_width_for_layer(figure_g, mid, fig_w)

    # punctuation space = width of period → обычный пробел
    punct_w = get_layer_width("period", mid, current_space_width)
    set_width_for_layer(punct_g, mid, punct_w)

Glyphs.showNotification(
    "Spaces set",
    f"Глифы пробелов созданы/обновлены. EM SPACE = {to_int(Mspace)}."
)
print("✅ Готово. Ширины назначены по всем мастерам.")
