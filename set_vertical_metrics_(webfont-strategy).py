# MenuTitle: Set Vertical Metrics (Webfont Strategy)
# -*- coding: utf-8 -*-
from __future__ import division

__doc__ = """
Sets vertical metrics for all masters using the Webfont Strategy (2019)
from the Glyphs vertical metrics tutorial:
win = font bounding box (nothing gets clipped), typo = hhea = design metrics
including important diacritics, typoLineGap = hheaLineGap = percentage of the
typo span, plus the font-level Use Typo Metrics parameter.
Shows a summary window with the applied values.
"""

import math
import vanilla
from GlyphsApp import Glyphs

# Line gap as a fraction of (typoAscender + |typoDescender|).
# The tutorial recommends 10-20%.
LINEGAP_RATIO = 0.1

# Round metrics outwards to multiples of this value
GRID = 10

# Glyphs measured for typoAscender/hheaAscender (top extremes incl. diacritics).
# Extend this list for your scripts, e.g. Cyrillic caps with diacritics.
ASCENDER_SAMPLE = (
	"Aacute", "Aring", "Adieresis", "Ecircumflex",
	"Ntilde", "Ohungarumlaut", "Scaron", "Zcaron",
)

# Glyphs measured for typoDescender/hheaDescender (bottom extremes).
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


def calculateMetrics(font, master):
	# 1-2: win = font bounding box, rounded outwards
	bboxMin, bboxMax = layerExtremes(font, master)
	if bboxMin is None:
		bboxMin, bboxMax = master.descender, master.ascender

	winAscent = roundUp(bboxMax)
	winDescent = roundUp(abs(bboxMin))  # positive value

	# 3: typoAscender = hheaAscender = top of important cap diacritics
	sampleMin, sampleMax = layerExtremes(font, master, ASCENDER_SAMPLE)
	if sampleMax is None:
		sampleMax = master.ascender
	typoAscender = roundUp(max(sampleMax, master.ascender))

	# 4: typoDescender = hheaDescender = full depth of descenders
	sampleMin, sampleMax = layerExtremes(font, master, DESCENDER_SAMPLE)
	if sampleMin is None:
		sampleMin = master.descender
	typoDescender = roundDown(min(sampleMin, master.descender))  # negative

	# 5: line gap = percentage of the typo span
	lineGap = roundUp((typoAscender + abs(typoDescender)) * LINEGAP_RATIO)

	return {
		"typoAscender": typoAscender,
		"typoDescender": typoDescender,
		"typoLineGap": lineGap,
		"hheaAscender": typoAscender,
		"hheaDescender": typoDescender,
		"hheaLineGap": lineGap,
		"winAscent": winAscent,
		"winDescent": winDescent,
	}


def applyMetrics(master, metrics):
	for key, value in metrics.items():
		master.customParameters[key] = value


class MetricsReportWindow:
	rowHeight = 26
	margin = 20

	def __init__(self, results, footnote=None):
		# results: list of (masterName, metricsDict)
		showMasterNames = len(results) > 1

		height = self.margin + 44  # header
		for _ in results:
			if showMasterNames:
				height += self.rowHeight + 6
			height += self.rowHeight * len(PARAM_ORDER) + 10
		if footnote:
			height += self.rowHeight + 6
		height += self.margin - 10

		self.w = vanilla.FloatingWindow(
			(320, height),
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

		for i, (masterName, metrics) in enumerate(results):
			if showMasterNames:
				setattr(
					self.w,
					"masterName%i" % i,
					vanilla.TextBox(
						(self.margin, y, -self.margin, self.rowHeight),
						masterName,
						alignment="center",
					),
				)
				y += self.rowHeight + 6

			for j, key in enumerate(PARAM_ORDER):
				setattr(
					self.w,
					"label%i_%i" % (i, j),
					vanilla.TextBox(
						(self.margin, y, 150, self.rowHeight),
						key,
						alignment="right",
					),
				)
				setattr(
					self.w,
					"value%i_%i" % (i, j),
					vanilla.TextBox(
						(self.margin + 160, y, -self.margin, self.rowHeight),
						str(metrics[key]),
						alignment="left",
					),
				)
				y += self.rowHeight
			y += 10

		if footnote:
			self.w.footnote = vanilla.TextBox(
				(self.margin, y, -self.margin, self.rowHeight),
				footnote,
				alignment="center",
				sizeStyle="small",
			)

		self.w.open()
		self.w.makeKey()


def main():
	font = Glyphs.font
	if font is None:
		Glyphs.showMacroWindow()
		print("No font open.")
		return

	results = []
	for master in font.masters:
		metrics = calculateMetrics(font, master)
		applyMetrics(master, metrics)
		results.append((master.name, metrics))

	# 6: font-level Use Typo Metrics (fsSelection bit 7)
	font.customParameters["Use Typo Metrics"] = True

	# Log to Macro window as well
	print("Applied vertical metrics (Webfont Strategy, line gap = %i%%):" % round(LINEGAP_RATIO * 100))
	for masterName, metrics in results:
		print("\nMaster: %s" % masterName)
		for key in PARAM_ORDER:
			print("  %-14s %6i" % (key, metrics[key]))
	print("\nUse Typo Metrics: ON")

	MetricsReportWindow(results, footnote="Use Typo Metrics: ON")


main()
