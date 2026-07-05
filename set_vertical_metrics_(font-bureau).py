# MenuTitle: Set Vertical Metrics (120% Strategy)
# -*- coding: utf-8 -*-
from __future__ import division

__doc__ = """
Sets vertical metrics for all masters using the Font Bureau strategy:
typo metrics = design metrics (ascender/descender), win & hhea metrics =
design metrics x multiplier, typoLineGap = the difference between the two,
hheaLineGap = 0. Shows a summary window with the applied values.
"""

import vanilla
from GlyphsApp import Glyphs

# 1.2 = 120% leading
MULTIPLIER = 1.2

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


def calculateMetrics(master):
	primaryAscender = int(round(master.ascender))
	primaryDescender = int(round(master.descender))  # negative

	secondaryAscender = int(round(primaryAscender * MULTIPLIER))
	secondaryDescender = int(round(abs(primaryDescender) * MULTIPLIER))  # positive

	typoLineGap = (secondaryAscender + secondaryDescender) - (
		primaryAscender + abs(primaryDescender)
	)

	return {
		"typoAscender": primaryAscender,
		"typoDescender": primaryDescender,
		"typoLineGap": typoLineGap,
		"winAscent": secondaryAscender,
		"winDescent": secondaryDescender,  # stored as a positive value
		"hheaAscender": secondaryAscender,
		"hheaDescender": -secondaryDescender,  # negative
		"hheaLineGap": 0,
	}


def applyMetrics(master, metrics):
	for key, value in metrics.items():
		master.customParameters[key] = value


class MetricsReportWindow:
	rowHeight = 26
	margin = 20

	def __init__(self, results):
		# results: list of (masterName, metricsDict)
		showMasterNames = len(results) > 1

		height = self.margin + 44  # header
		for _ in results:
			if showMasterNames:
				height += self.rowHeight + 6
			height += self.rowHeight * len(PARAM_ORDER) + 10
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
		metrics = calculateMetrics(master)
		applyMetrics(master, metrics)
		results.append((master.name, metrics))

	# Log to Macro window as well
	print("Applied vertical metrics (multiplier = %s):" % MULTIPLIER)
	for masterName, metrics in results:
		print("\nMaster: %s" % masterName)
		for key in PARAM_ORDER:
			print("  %-14s %6i" % (key, metrics[key]))

	MetricsReportWindow(results)


main()
