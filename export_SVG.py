#MenuTitle: Export Selected Glyphs to SVG...
# -*- coding: utf-8 -*-

from GlyphsApp import *
from vanilla import FloatingWindow, TextBox, RadioGroup, EditText, Button
import os
import re
import xml.sax.saxutils as xml_escape


ARTBOARD_SIZE = 1000


def clean_file_name(name):
    name = str(name)
    name = re.sub(r'[\\/:*?"<>|]+', "_", name)
    name = name.strip()
    if not name:
        name = "glyph"
    return name


def fmt(value):
    value = round(float(value), 3)
    if value == int(value):
        return str(int(value))
    return ("%.3f" % value).rstrip("0").rstrip(".")


def get_layer_master(font, layer):
    try:
        if layer.master:
            return layer.master
    except:
        pass

    master_id = None

    try:
        master_id = layer.associatedMasterId
    except:
        pass

    if not master_id:
        try:
            master_id = layer.layerId
        except:
            pass

    if master_id:
        try:
            for master in font.masters:
                if master.id == master_id:
                    return master
        except:
            pass

    return font.selectedFontMaster


def get_glyph_name(layer):
    try:
        return layer.parent.name
    except:
        pass

    try:
        return layer.glyph.name
    except:
        pass

    return "glyph"


def node_xy(node):
    try:
        return node.x, node.y
    except:
        return node.position.x, node.position.y


def svg_xy(node, ascender, scale):
    x, y = node_xy(node)

    # Glyphs: Y goes up from baseline.
    # SVG: Y goes down from top.
    # With typical metrics ascender 800 / descender -200,
    # baseline becomes y=800 on a 1000px artboard.
    return x * scale, (ascender - y) * scale


def is_offcurve(node):
    return node.type == OFFCURVE


def segment_to_svg(controls, end_node, ascender, scale):
    ex, ey = svg_xy(end_node, ascender, scale)

    if len(controls) == 0:
        return "L %s %s" % (fmt(ex), fmt(ey))

    if len(controls) == 1:
        cx, cy = svg_xy(controls[0], ascender, scale)
        return "Q %s %s %s %s" % (
            fmt(cx), fmt(cy),
            fmt(ex), fmt(ey)
        )

    c1x, c1y = svg_xy(controls[-2], ascender, scale)
    c2x, c2y = svg_xy(controls[-1], ascender, scale)

    return "C %s %s %s %s %s %s" % (
        fmt(c1x), fmt(c1y),
        fmt(c2x), fmt(c2y),
        fmt(ex), fmt(ey)
    )


def path_to_svg_d(path, ascender, scale):
    nodes = list(path.nodes)

    if not nodes:
        return ""

    start_index = None

    for i, node in enumerate(nodes):
        if not is_offcurve(node):
            start_index = i
            break

    if start_index is None:
        return ""

    nodes = nodes[start_index:] + nodes[:start_index]
    start_node = nodes[0]

    sx, sy = svg_xy(start_node, ascender, scale)
    d = ["M %s %s" % (fmt(sx), fmt(sy))]

    controls = []

    for node in nodes[1:]:
        if is_offcurve(node):
            controls.append(node)
        else:
            d.append(segment_to_svg(controls, node, ascender, scale))
            controls = []

    if path.closed:
        if controls:
            d.append(segment_to_svg(controls, start_node, ascender, scale))

        d.append("Z")

    return " ".join(d)


def decomposed_layer(layer):
    try:
        return layer.copyDecomposedLayer()
    except:
        pass

    layer_copy = layer.copy()

    try:
        layer_copy.decomposeComponents()
    except:
        pass

    return layer_copy


def export_layer_to_svg(layer, folder, linejoin, linecap, stroke_width):
    font = Glyphs.font
    master = get_layer_master(font, layer)

    upm = font.upm or ARTBOARD_SIZE
    scale = float(ARTBOARD_SIZE) / float(upm)

    ascender = master.ascender
    glyph_name = get_glyph_name(layer)

    layer_copy = decomposed_layer(layer)

    path_data = []

    for path in layer_copy.paths:
        d = path_to_svg_d(path, ascender, scale)
        if d:
            path_data.append(d)

    full_path_data = " ".join(path_data)

    safe_title = xml_escape.escape(glyph_name)
    safe_path_data = xml_escape.escape(full_path_data)

    svg = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     width="{size}px"
     height="{size}px"
     viewBox="0 0 {size} {size}">
  <title>{title}</title>
  <path d="{path_data}"
        fill="none"
        stroke="#000000"
        stroke-width="{stroke_width}"
        stroke-linecap="{linecap}"
        stroke-linejoin="{linejoin}"
        stroke-miterlimit="4"/>
</svg>
'''.format(
        size=ARTBOARD_SIZE,
        title=safe_title,
        path_data=safe_path_data,
        stroke_width=fmt(stroke_width),
        linecap=linecap,
        linejoin=linejoin
    )

    file_name = clean_file_name(glyph_name) + ".svg"
    file_path = os.path.join(folder, file_name)

    counter = 2
    base_name = clean_file_name(glyph_name)

    while os.path.exists(file_path):
        file_name = "%s_%s.svg" % (base_name, counter)
        file_path = os.path.join(folder, file_name)
        counter += 1

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(svg)

    return file_path


class ExportSelectedGlyphsToSVG(object):

    def __init__(self):
        self.w = FloatingWindow((380, 205), "Export Selected Glyphs to SVG")

        self.w.info = TextBox(
            (15, 14, -15, 34),
            "Exports selected glyphs as stroked SVG paths.\nArtboard: 1000 × 1000 px."
        )

        self.w.join_label = TextBox((15, 58, 90, 20), "Line join")

        self.w.join = RadioGroup(
            (105, 54, -15, 22),
            ["round", "miter", "bevel"],
            isVertical=False
        )
        self.w.join.set(0)

        self.w.cap_label = TextBox((15, 92, 90, 20), "Line cap")

        self.w.cap = RadioGroup(
            (105, 88, -15, 22),
            ["butt", "round", "square"],
            isVertical=False
        )
        self.w.cap.set(0)

        self.w.stroke_label = TextBox((15, 126, 90, 20), "Stroke width")

        self.w.stroke_width = EditText(
            (105, 122, 70, 22),
            "100"
        )

        self.w.export_button = Button(
            (15, 162, -15, 24),
            "Choose Folder and Export",
            callback=self.export_callback
        )

        self.w.open()

    def export_callback(self, sender):
        font = Glyphs.font

        if not font:
            Message(
                "No Font Open",
                "Open a Glyphs file first."
            )
            return

        layers = font.selectedLayers

        if not layers:
            Message(
                "Nothing Selected",
                "Select one or more glyphs/layers first."
            )
            return

        join_options = ["round", "miter", "bevel"]
        linejoin = join_options[self.w.join.get()]

        cap_options = ["butt", "round", "square"]
        linecap = cap_options[self.w.cap.get()]

        try:
            stroke_width = float(self.w.stroke_width.get())
        except:
            Message(
                "Invalid Stroke Width",
                "Stroke width must be a number."
            )
            return

        if stroke_width <= 0:
            Message(
                "Invalid Stroke Width",
                "Stroke width must be greater than 0."
            )
            return

        folder = GetFolder(message="Choose SVG export folder")

        if not folder:
            return

        if isinstance(folder, (list, tuple)):
            folder = folder[0]

        exported = []
        seen = set()

        for layer in layers:
            glyph_name = get_glyph_name(layer)

            try:
                layer_id = layer.layerId
            except:
                layer_id = id(layer)

            key = (glyph_name, layer_id)

            if key in seen:
                continue

            seen.add(key)

            file_path = export_layer_to_svg(
                layer,
                folder,
                linejoin,
                linecap,
                stroke_width
            )

            exported.append(file_path)

        Glyphs.showNotification(
            "SVG export complete",
            "%s SVG file(s) exported." % len(exported)
        )

        self.w.close()


ExportSelectedGlyphsToSVG()
