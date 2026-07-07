#MenuTitle: Compare Glyph Sets of Open Fonts
# -*- coding: utf-8 -*-
__doc__="""
Compares the glyph sets of all open fonts and prints the differences to the Macro window.
Nice and production names are treated as the same glyph, suffixes (.ss01, .alt, .001, ...)
are preserved as distinct variants, and unicode-less duplicates are matched via their base name.
"""

import os
from GlyphsApp import Glyphs


def splitSuffix(name):
	"""Split a glyph name into base and suffix. Leading dot (.notdef) is not a suffix separator."""
	start = 1 if name.startswith(".") else 0
	dot = name.find(".", start)
	if dot == -1:
		return name, ""
	return name[:dot], name[dot + 1:]


def normalizeBase(baseName):
	"""Return (identityString, canonicalDisplayName) for a base glyph name."""
	nice = Glyphs.niceGlyphName(baseName) or baseName
	info = Glyphs.glyphInfoForName(nice)
	if info:
		if info.name:
			nice = info.name
		if info.unicode:
			return "U+%s" % info.unicode, nice
	return "name:%s" % nice, nice


def glyphKey(glyph):
	"""Return ((identity, suffix), canonicalDisplayName) for a glyph."""
	base, suffix = splitSuffix(glyph.name)
	unicodes = glyph.unicodes
	if unicodes and len(unicodes) > 0:
		unis = sorted([str(u).upper() for u in unicodes])
		identity = "U+%s" % "+".join(unis)
		display = base
		info = Glyphs.glyphInfoForUnicode(unis[0])
		if info and info.name:
			display = info.name
	else:
		identity, display = normalizeBase(base)
	if suffix:
		display = "%s.%s" % (display, suffix)
	return (identity, suffix), display


fonts = Glyphs.fonts
Glyphs.clearLog()
Glyphs.showMacroWindow()

if len(fonts) < 2:
	print("Open at least two fonts to compare.")
else:
	# key -> {"display": canonical name, "names": {fontIndex: [actual glyph names]}}
	registry = {}
	for fi, font in enumerate(fonts):
		for glyph in font.glyphs:
			key, display = glyphKey(glyph)
			entry = registry.setdefault(key, {"display": display, "names": {}})
			entry["names"].setdefault(fi, []).append(glyph.name)

	allIndexes = set(range(len(fonts)))

	def fontLabel(fi):
		return "[%d]" % (fi + 1)

	print("Comparing %d fonts:" % len(fonts))
	for fi, font in enumerate(fonts):
		label = font.familyName or "Untitled"
		if font.filepath:
			label += "  (%s)" % os.path.basename(font.filepath)
		print("  %s %s — %d glyphs" % (fontLabel(fi), label, len(font.glyphs)))
	print()

	shared = []
	diffs = []
	for key, entry in registry.items():
		if set(entry["names"].keys()) == allIndexes:
			shared.append((key, entry))
		else:
			diffs.append((key, entry))

	print("Shared by all fonts: %d glyph identities" % len(shared))
	print("Different:           %d glyph identities" % len(diffs))
	print()

	for fi in range(len(fonts)):
		onlyHere = sum(1 for k, e in diffs if set(e["names"].keys()) == {fi})
		missingHere = sum(1 for k, e in diffs if fi not in e["names"])
		print("  %s only here: %d,  missing here: %d" % (fontLabel(fi), onlyHere, missingHere))
	print()

	if diffs:
		print("=" * 64)
		print("DIFFERENCES")
		print("=" * 64)
		width = max(len(e["display"]) for k, e in diffs) + 2
		for key, entry in sorted(diffs, key=lambda t: t[1]["display"].lower()):
			present = sorted(entry["names"].keys())
			absent = sorted(allIndexes - set(present))
			if len(present) == 1:
				where = "only in %s" % fontLabel(present[0])
			elif len(absent) == 1:
				where = "missing from %s" % fontLabel(absent[0])
			else:
				where = "in %s — not in %s" % (
					" ".join(fontLabel(i) for i in present),
					" ".join(fontLabel(i) for i in absent),
				)
			line = entry["display"].ljust(width) + where
			# Show actual names where they differ from the canonical one
			aliases = []
			for fi in present:
				for actualName in entry["names"][fi]:
					if actualName != entry["display"]:
						aliases.append("%s as '%s'" % (fontLabel(fi), actualName))
			if aliases:
				line += "   (%s)" % ", ".join(aliases)
			print(line)
		print()

	# Glyphs present in every font but under different names
	renamed = []
	for key, entry in shared:
		nameSet = set()
		for names in entry["names"].values():
			nameSet.update(names)
		if len(nameSet) > 1:
			renamed.append(entry)
	if renamed:
		print("=" * 64)
		print("SAME GLYPH, DIFFERENT NAMES (present in all fonts)")
		print("=" * 64)
		for entry in sorted(renamed, key=lambda e: e["display"].lower()):
			parts = []
			for fi in sorted(entry["names"].keys()):
				parts.append("%s %s" % (fontLabel(fi), ", ".join(entry["names"][fi])))
			print("%s   →   %s" % (entry["display"], "   ".join(parts)))
	print()
	print("Done.")
