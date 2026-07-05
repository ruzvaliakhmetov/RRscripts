# MenuTitle: Set Vertical Metrics (Google Fonts Strategy)
# -*- coding: utf-8 -*-
from __future__ import division

__doc__ = """
Sets vertical metrics using the Google Fonts strategy:
typo = hhea = design metrics covering the tallest cap diacritics and deepest
descenders, all line gaps = 0, win = font bounding box, Use Typo Metrics ON.
The same values are applied to ALL masters, as required by the GF spec.
Shows a summary window with the applied values.
"""

import math
import vanilla
from GlyphsApp import Glyphs

# Round metrics outwards to multiples of this value
GRID = 10

# GF expects the typo/hhea span to be around 120-130% of UPM
GF_RATIO_MIN = 1.2
GF_RATIO_MAX = 1.3

# Glyphs measured for typoAscender/hheaAscender.
# GF spec: must be equal to or higher than the tallest cap diacritics,
# e.g. Abreveacute. Extend this list for your scripts.
ASCENDER_SAMPLE = (
	"Abreveacute", "Abrevehookabove", "Acircumflexacute",
	"Aacute", "Aring", "Adieresis", "Ecircumflex",
	"Ntilde", "Ohungarumlaut", "Scaron", "Zcaron",
)

# Glyphs measured for typoDescender/hheaDescender.
# GF spec: lower than the deepest descender of the primary script.
DESCENDER_SAMPLE = (
	"g", "j", "p", "q", "y",
)

# Display order, matching the report window
PARAM_ORDER = (
	"hheaAscender",
	"hheaDescender",
	"hheaLineGap",
	"typoAscender",
	"typoDescender",
	"typoLineGap",
	"winAscent",
	"winDescent",
)


def roundUp(value, grid=GRID):
	return int(math.ceil(value / grid) * grid)


def roundDown(value, grid=GRID):
	return int(math.floor(value / grid) * grid)


def layerExtremes(font, master, glyphNames=None):
	"""
	Returns (yMin, yMax) for the given master.
	If glyphNames is None, measures all exporting glyphs (= font bbox).
	"""
	yMin, yMax = None, None
	if glyphNames is None:
		glyphs = [g for g in font.glyphs if g.export]
	else:
		glyphs = [font.glyphs[name] for name in glyphNames if font.glyphs[name]]

	for glyph in glyphs:
		layer = glyph.layers[master.id]
		if layer is None:
			continue
		bounds = layer.bounds
		if bounds.size.height == 0:
			continue
		bottom = bounds.origin.y
		top = bounds.origin.y + bounds.size.height
		if yMin is None or bottom < yMin:
			yMin = bottom
		if yMax is None or top > yMax:
			yMax = top
	return yMin, yMax


def calculateFamilyMetrics(font):
	"""
	Measures across ALL masters and returns one shared metrics dict,
	as GF requires identical vertical metrics on every master.
	"""
	bboxMin, bboxMax = None, None
	sampleTop, sampleBottom = None, None
	designAscender, designDescender = None, None

	for master in font.masters:
		# Font bounding box for win values
		mMin, mMax = layerExtremes(font, master)
		if mMin is not None:
			if bboxMin is None or mMin < bboxMin:
				bboxMin = mMin
			if bboxMax is None or mMax > bboxMax:
				bboxMax = mMax

		# Tallest cap diacritics for typo/hhea ascender
		_, sMax = layerExtremes(font, master, ASCENDER_SAMPLE)
		if sMax is not None and (sampleTop is None or sMax > sampleTop):
			sampleTop = sMax

		# Deepest descenders for typo/hhea descender
		sMin, _ = layerExtremes(font, master, DESCENDER_SAMPLE)
		if sMin is not None and (sampleBottom is None or sMin < sampleBottom):
			sampleBottom = sMin

		# Design metrics as fallback / lower bound
		if designAscender is None or master.ascender > designAscender:
			designAscender = master.ascender
		if designDescender is None or master.descender < designDescender:
			designDescender = master.descender

	if bboxMax is None:
		bboxMin, bboxMax = designDescender, designAscender
	if sampleTop is None:
		sampleTop = designAscender
	if sampleBottom is None:
		sampleBottom = designDescender

	typoAscender = roundUp(max(sampleTop, designAscender))
	typoDescender = roundDown(min(sampleBottom, designDescender))  # negative
	winAscent = roundUp(bboxMax)
	winDescent = roundUp(abs(bboxMin))  # positive value

	return {
		"typoAscender": typoAscender,
		"typoDescender": typoDescender,
		"typoLineGap": 0,
		"hheaAscender": typoAscender,
		"hheaDescender": typoDescender,
		"hheaLineGap": 0,
		"winAscent": winAscent,
		"winDescent": winDescent,
	}


def applyMetrics(master, metrics):
	for key, value in metrics.items():
		master.customParameters[key] = value


class MetricsReportWindow:
	rowHeight = 26
	margin = 20

	def __init__(self, metrics, footnotes=()):
		height = (
			self.margin + 44
			+ self.rowHeight * len(PARAM_ORDER) + 10
			+ (self.rowHeight - 6) * len(footnotes)
			+ self.margin - 10
		)

		self.w = vanilla.FloatingWindow(
			(360, height),
			"Vertical Metrics",
		)

		y = self.margin
		self.w.header = vanilla.TextBox(
			(self.margin, y, -self.margin, 40),
			"The following metrics were applied:",
			alignment="center",
			sizeStyle="regular",
		)
		y += 44

		for j, key in enumerate(PARAM_ORDER):
			setattr(
				self.w,
				"label%i" % j,
				vanilla.TextBox(
					(self.margin, y, 150, self.rowHeight),
					key,
					alignment="right",
				),
			)
			setattr(
				self.w,
				"value%i" % j,
				vanilla.TextBox(
					(self.margin + 160, y, -self.margin, self.rowHeight),
					str(metrics[key]),
					alignment="left",
				),
			)
			y += self.rowHeight
		y += 10

		for k, footnote in enumerate(footnotes):
			setattr(
				self.w,
				"footnote%i" % k,
				vanilla.TextBox(
					(self.margin, y, -self.margin, self.rowHeight),
					footnote,
					alignment="center",
					sizeStyle="small",
				),
			)
			y += self.rowHeight - 6

		self.w.open()
		self.w.makeKey()


def main():
	font = Glyphs.font
	if font is None:
		Glyphs.showMacroWindow()
		print("No font open.")
		return

	metrics = calculateFamilyMetrics(font)

	# Same values on every master (required by the GF spec)
	for master in font.masters:
		applyMetrics(master, metrics)

	# Use Typo Metrics (fsSelection bit 7) is required by GF
	font.customParameters["Use Typo Metrics"] = True

	# Sanity check: typo/hhea span should be ~120-130% of UPM
	span = metrics["typoAscender"] + abs(metrics["typoDescender"])
	ratio = span / font.upm
	footnotes = ["Same values on all masters · Use Typo Metrics: ON"]
	if ratio < GF_RATIO_MIN:
		footnotes.append("Warning: typo span %i%% of UPM (GF: 120-130%%)" % round(ratio * 100))
	elif ratio > GF_RATIO_MAX:
		footnotes.append("Warning: typo span %i%% of UPM, too loose" % round(ratio * 100))

	# Log to Macro window as well
	print("Applied vertical metrics (Google Fonts Strategy):")
	for key in PARAM_ORDER:
		print("  %-14s %6i" % (key, metrics[key]))
	print("\nApplied to all %i masters. Use Typo Metrics: ON" % len(font.masters))
	print("Typo span: %i units = %i%% of UPM (%i)" % (span, round(ratio * 100), font.upm))

	MetricsReportWindow(metrics, footnotes)


main()