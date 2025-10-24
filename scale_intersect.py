# MenuTitle: Scale Objects Intersecting Background...
# -*- coding: utf-8 -*-

from GlyphsApp import *
from AppKit import (
    NSBezierPath, NSAffineTransform, NSPoint,
    NSAlert, NSTextField, NSButton, NSSwitchButton,
    NSMakeRect, NSView, NSApp
)

# ---------- helpers ----------

def elem_at(path, i):
    """Кросс-версионный доступ к elementAtIndex_associatedPoints_."""
    try:
        et, pts = path.elementAtIndex_associatedPoints_(i)
    except TypeError:
        et, pts = path.elementAtIndex_associatedPoints_(i, None)
    return et, pts

def bezierPathFromBackgroundLayer(bg_layer):
    bp = NSBezierPath.alloc().init()
    for sh in bg_layer.shapes:
        cls = sh.__class__.__name__
        if cls == "GSPath":
            bp.appendBezierPath_(sh.bezierPath)  # свойство
        elif cls == "GSComponent":
            try:
                bp.appendBezierPath_(sh.bezierPath)
            except Exception:
                decomp = sh.decomposedLayer()
                if decomp:
                    for p in decomp.paths:
                        bp.appendBezierPath_(p.bezierPath)
    return bp

def flattenPath(nsBezierPath):
    """Список отрезков [(p0, p1), ...] после flatten()."""
    flat = nsBezierPath.bezierPathByFlatteningPath()
    segs, prev = [], None
    if flat is None:
        return segs
    count = flat.elementCount()
    for i in range(count):
        et, pts = elem_at(flat, i)
        # 0=MoveTo, 1=LineTo, 3=ClosePath
        if et == 0:
            prev = pts[0]
        elif et == 1:
            cur = pts[0]
            if prev is not None:
                segs.append((prev, cur))
            prev = cur
        elif et == 3:
            prev = None
    return segs

def segmentsIntersect(p, p2, q, q2):
    x1, y1 = p.x,  p.y
    x2, y2 = p2.x, p2.y
    x3, y3 = q.x,  q.y
    x4, y4 = q2.x, q2.y

    def orient(ax, ay, bx, by, cx, cy):
        return (bx-ax)*(cy-ay) - (by-ay)*(cx-ax)

    def onseg(ax, ay, bx, by, px, py):
        eps = 1e-9
        return (min(ax, bx)-eps <= px <= max(ax, bx)+eps and
                min(ay, by)-eps <= py <= max(ay, by)+eps)

    o1 = orient(x1,y1,x2,y2,x3,y3)
    o2 = orient(x1,y1,x2,y2,x4,y4)
    o3 = orient(x3,y3,x4,y4,x1,y1)
    o4 = orient(x3,y3,x4,y4,x2,y2)

    if (o1*o2 < 0) and (o3*o4 < 0):
        return True
    if abs(o1) < 1e-9 and onseg(x1,y1,x2,y2,x3,y3): return True
    if abs(o2) < 1e-9 and onseg(x1,y1,x2,y2,x4,y4): return True
    if abs(o3) < 1e-9 and onseg(x3,y3,x4,y4,x1,y1): return True
    if abs(o4) < 1e-9 and onseg(x3,y3,x4,y4,x2,y2): return True
    return False

def pathIntersectsFill(pathBezier, fillBezier):
    """Частичное ИЛИ полное попадание (или касание границы)."""
    # Узлы внутри заливки
    count = pathBezier.elementCount()
    for i in range(count):
        et, pts = elem_at(pathBezier, i)
        if et in (0, 1) and fillBezier.containsPoint_(pts[0]):
            return True
    # Пересечение границ
    segsA = flattenPath(pathBezier)
    segsB = flattenPath(fillBezier)
    if not segsA or not segsB:
        return False
    for a0, a1 in segsA:
        for b0, b1 in segsB:
            if segmentsIntersect(a0, a1, b0, b1):
                return True
    return False

def pathFullyInsideFill(pathBezier, fillBezier):
    """Истинно, если весь контур строго внутри заливки (без касания/пересечения)."""
    # 1) Никаких пересечений границ
    segsA = flattenPath(pathBezier)
    segsB = flattenPath(fillBezier)
    for a0, a1 in segsA:
        for b0, b1 in segsB:
            if segmentsIntersect(a0, a1, b0, b1):
                return False
    # 2) Все вершины flatten-пути лежат внутри заливки
    flat = pathBezier.bezierPathByFlatteningPath()
    if flat is None:
        return False
    count = flat.elementCount()
    for i in range(count):
        et, pts = elem_at(flat, i)
        if et in (0, 1):  # moveTo / lineTo
            if not fillBezier.containsPoint_(pts[0]):
                return False
    return True

def scalePathAroundCenter(gsPath, factor):
    b = gsPath.bounds
    cx = b.origin.x + 0.5 * b.size.width
    cy = b.origin.y + 0.5 * b.size.height
    t = NSAffineTransform.transform()
    t.translateXBy_yBy_(cx, cy)
    t.scaleBy_(factor)
    t.translateXBy_yBy_(-cx, -cy)
    for n in gsPath.nodes:
        p2 = t.transformPoint_(NSPoint(n.x, n.y))
        n.x, n.y = p2.x, p2.y

# ---------- modal prompt (percent + checkbox) ----------

def promptPercentAndMode(default_percent="10", default_full_inside=False):
    alert = NSAlert.alloc().init()
    alert.setMessageText_("Scale intersecting with background")
    alert.setInformativeText_("Increase by, % (negative shrinks).")

    # accessory view: stack textfield + checkbox
    container = NSView.alloc().initWithFrame_(NSMakeRect(0, 0, 260, 54))

    field = NSTextField.alloc().initWithFrame_(NSMakeRect(0, 30, 120, 24))
    field.setStringValue_(default_percent)

    checkbox = NSButton.alloc().initWithFrame_(NSMakeRect(0, 4, 240, 22))
    checkbox.setButtonType_(NSSwitchButton)
    checkbox.setTitle_("Only if fully inside")
    checkbox.setState_(1 if default_full_inside else 0)

    container.addSubview_(field)
    container.addSubview_(checkbox)

    alert.setAccessoryView_(container)
    alert.addButtonWithTitle_("OK")
    alert.addButtonWithTitle_("Cancel")

    NSApp.activateIgnoringOtherApps_(True)
    alert.window().setInitialFirstResponder_(field)
    resp = alert.runModal()
    if resp != 1000:
        return None, None

    try:
        s = field.stringValue().strip().replace(",", ".")
        v = float(s)
        if v <= -100.0:
            Message("Invalid value", "Percentage must be greater than -100.")
            return None, None
    except Exception:
        Message("Invalid value", "Please enter a number like 10 or 5.5.")
        return None, None

    full_inside = bool(checkbox.state())
    return v, full_inside

# ---------- main ----------

def main():
    f = Glyphs.font
    if not f:
        Message("No font open", "Open a font and try again.")
        return
    layer = f.selectedLayers[0] if f.selectedLayers else None
    if not layer:
        Message("No active layer", "Select a glyph and a layer.")
        return

    bg = layer.background
    if not bg or len(bg.shapes) == 0:
        Message("Background is empty", "Background layer contains no shapes.")
        return

    percent, require_full = promptPercentAndMode("10", False)
    if percent is None:
        return

    factor = 1.0 + percent / 100.0
    bgBezier = bezierPathFromBackgroundLayer(bg)

    layer.beginChanges()
    changed = False
    try:
        for p in list(layer.paths):
            if not p.closed:
                continue
            pb = p.bezierPath  # свойство
            if require_full:
                hit = pathFullyInsideFill(pb, bgBezier)
            else:
                hit = pathIntersectsFill(pb, bgBezier)
            if hit:
                scalePathAroundCenter(p, factor)
                changed = True
        if changed:
            layer.syncMetrics()
    finally:
        layer.endChanges()

    Glyphs.showNotification(
        "Scale Intersecting",
        "{} {:+.2f}% to {} paths.".format(
            "Applied",
            percent,
            "fully-inside" if require_full else "intersecting"
        )
    )

if __name__ == "__main__":
    main()