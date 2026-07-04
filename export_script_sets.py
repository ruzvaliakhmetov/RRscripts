# MenuTitle: [test] Export Script Sets...
# -*- coding: utf-8 -*-
#
# Exports every active static instance once per script set.
#
# A script set is: base scripts (Latin, Cyrillic, Greek) + one extra
# script. The base-only set is called "LGC". For each set the script
# builds a temporary copy of every instance, fills its Remove Glyphs
# parameter so only the set's scripts survive, optionally appends the
# set name to the family name, and generates the font file.
#
# Output structure:
#   Destination/OTF/LGC/...
#   Destination/OTF/Armenian/...
#   Destination/TTF/LGC/...
#   ...

import os

from GlyphsApp import Glyphs, OTF, TTF, GetFolder
import vanilla

try:
    from GlyphsApp import INSTANCETYPEVARIABLE
except ImportError:
    INSTANCETYPEVARIABLE = None


PARAM_NAME = "Remove Glyphs"
DEFAULT_LANGUAGE_TAG = "dflt"

BASE_SCRIPTS = ("latin", "cyrillic", "greek")
BASE_SET_NAME = "LGC"


class ExportScriptSets(object):

    def __init__(self):
        self.font = Glyphs.font

        if not self.font:
            Glyphs.showMacroWindow()
            print("No font open.")
            return

        self.instances = self.collectInstances()

        if not self.instances:
            Glyphs.showMacroWindow()
            print("No active static export instances found.")
            return

        self.scripts = self.collectScripts()

        if not self.scripts:
            Glyphs.showMacroWindow()
            print("No glyph scripts found in this font.")
            return

        self.extraScripts = sorted(
            s for s in self.scripts if s not in BASE_SCRIPTS
        )

        # (setName, setScript). setScript is None for the base LGC set.
        self.sets = [(BASE_SET_NAME, None)]
        self.sets += [(self.prettyScriptName(s), s) for s in self.extraScripts]

        self.destinationPath = None
        self.setCheckboxes = {}

        self.buildUI()

    # -------------------------
    # Collect data
    # -------------------------

    def collectInstances(self):
        instances = []

        for instance in self.font.instances:
            if not instance.active:
                continue

            # Skip variable font settings, this script exports statics.
            if INSTANCETYPEVARIABLE is not None:
                try:
                    if instance.type == INSTANCETYPEVARIABLE:
                        continue
                except Exception:
                    pass

            instances.append(instance)

        return instances

    def collectScripts(self):
        scripts = set()

        for glyph in self.font.glyphs:
            script = glyph.script
            if script:
                scripts.add(script)

        return sorted(scripts)

    def prettyScriptName(self, script):
        special = {
            "latin": "Latin",
            "greek": "Greek",
            "cyrillic": "Cyrillic",
            "arabic": "Arabic",
            "armenian": "Armenian",
            "hebrew": "Hebrew",
            "georgian": "Georgian",
            "thai": "Thai",
            "devanagari": "Devanagari",
        }

        if script in special:
            return special[script]

        result = ""
        for char in script:
            if char.isupper():
                result += " "
            result += char

        return result[:1].upper() + result[1:]

    # -------------------------
    # UI
    # -------------------------

    def buildUI(self):
        margin = 16
        lineHeight = 24
        y = margin

        setsHeight = lineHeight * len(self.sets)
        windowHeight = (
            22 + 8 + setsHeight          # sets label + checkboxes
            + 16 + 22 + 8 + lineHeight   # formats
            + 16 + lineHeight            # family name option
            + 16 + 28                    # destination row
            + 16 + 28                    # export button
            + 22                         # status line
            + margin * 2
        )
        windowHeight = max(windowHeight, 360)

        self.w = vanilla.FloatingWindow(
            (420, windowHeight),
            "Export script sets",
        )

        self.w.setsLabel = vanilla.TextBox(
            (margin, y, -margin, 22),
            "Script sets to export",
        )
        y += 30

        for setName, setScript in self.sets:
            checkbox = vanilla.CheckBox(
                (margin + 8, y, -margin, lineHeight),
                setName,
                value=True,
            )
            self.setCheckboxes[setName] = checkbox
            setattr(self.w, "setCheckbox_%s" % self.safeAttributeName(setName), checkbox)
            y += lineHeight

        y += 16

        self.w.formatsLabel = vanilla.TextBox(
            (margin, y, -margin, 22),
            "Formats",
        )
        y += 30

        self.w.otfCheckbox = vanilla.CheckBox(
            (margin + 8, y, 100, lineHeight),
            "OTF",
            value=True,
        )
        self.w.ttfCheckbox = vanilla.CheckBox(
            (margin + 120, y, 100, lineHeight),
            "TTF",
            value=True,
        )
        y += lineHeight + 16

        self.w.renameCheckbox = vanilla.CheckBox(
            (margin, y, -margin, lineHeight),
            "Append set name to family name (MyFont Armenian)",
            value=True,
        )
        y += lineHeight + 16

        self.w.chooseFolderButton = vanilla.Button(
            (margin, y, 110, 28),
            "Choose folder...",
            callback=self.chooseFolderCallback,
        )
        self.w.folderLabel = vanilla.TextBox(
            (margin + 122, y + 5, -margin, 22),
            "No folder selected",
            sizeStyle="small",
        )
        y += 28 + 16

        self.w.exportButton = vanilla.Button(
            (-margin - 90, y, 90, 28),
            "Export",
            callback=self.exportCallback,
        )

        self.w.status = vanilla.TextBox(
            (margin, y + 5, -margin - 100, 22),
            "",
            sizeStyle="small",
        )

        self.w.open()

    def safeAttributeName(self, text):
        safe = []
        for char in text:
            if char.isalnum() or char == "_":
                safe.append(char)
            else:
                safe.append("_")
        return "".join(safe)

    def chooseFolderCallback(self, sender):
        folder = GetFolder(message="Choose export destination")

        if folder:
            self.destinationPath = str(folder)
            self.w.folderLabel.set(self.compactPath(self.destinationPath))

    def compactPath(self, path):
        home = os.path.expanduser("~")
        if path.startswith(home):
            return "~" + path[len(home):]
        return path

    # -------------------------
    # Remove Glyphs helpers
    # -------------------------

    def getRemoveGlyphsParameter(self, instance):
        for parameter in instance.customParameters:
            if parameter.name == PARAM_NAME:
                return parameter

        return None

    def getRemoveGlyphsLines(self, instance):
        parameter = self.getRemoveGlyphsParameter(instance)

        if not parameter:
            return []

        value = parameter.value

        if value is None:
            return []

        if isinstance(value, str):
            rawLines = value.splitlines()
        else:
            try:
                rawLines = [str(item) for item in value]
            except TypeError:
                rawLines = str(value).splitlines()

        return self.normalizeLines(rawLines)

    def cleanToken(self, token):
        token = str(token).strip()

        while token and token[-1] in (",", ";"):
            token = token[:-1].strip()

        if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
            token = token[1:-1].strip()

        if token in ("(", ")", "{", "}"):
            return ""

        return token

    def normalizeLines(self, rawLines):
        lines = []
        seen = set()

        for rawLine in rawLines:
            line = self.cleanToken(rawLine)

            if not line:
                continue

            for part in line.replace(",", "\n").splitlines():
                part = self.cleanToken(part)
                if part and part not in seen:
                    seen.add(part)
                    lines.append(part)

        return lines

    # -------------------------
    # Naming helpers
    # -------------------------

    def propertyValueAsString(self, prop):
        if prop is None:
            return None

        value = getattr(prop, "value", None)
        if value:
            return str(value)

        if isinstance(prop, str) and prop:
            return prop

        return None

    def baseFamilyName(self, instance):
        # Prefer an existing per-instance family override, then the font.
        try:
            prop = instance.propertyForName_languageTag_("familyNames", DEFAULT_LANGUAGE_TAG)
            value = self.propertyValueAsString(prop)
            if value:
                return value
        except Exception:
            pass

        try:
            if self.font.familyName:
                return self.font.familyName
        except Exception:
            pass

        return "Untitled"

    def setInstanceFamilyName(self, instance, name):
        try:
            instance.setProperty_value_languageTag_("familyNames", name, None)
            return
        except Exception:
            pass

        try:
            instance.customParameters["familyName"] = name
        except Exception:
            print("Could not set family name %s" % name)

    def setInstanceProperty(self, instance, propertyName, value):
        try:
            instance.setProperty_value_languageTag_(propertyName, value, None)
            return True
        except Exception:
            return False

    def applySetNaming(self, exportInstance, originalInstance, setName):
        # Explicit Full Names / Font Name overrides on the original
        # instance would otherwise survive the family rename and cause
        # name clashes between sets (e.g. every set exporting
        # MyFont-Medium). Rewrite the whole naming trio consistently.
        styleName = originalInstance.name or "Regular"
        familyName = "%s %s" % (self.baseFamilyName(originalInstance), setName)

        self.setInstanceFamilyName(exportInstance, familyName)

        fullName = "%s %s" % (familyName, styleName)
        self.setInstanceProperty(exportInstance, "fullNames", fullName)

        postscriptName = "%s-%s" % (
            familyName.replace(" ", ""),
            styleName.replace(" ", ""),
        )

        if not self.setInstanceProperty(exportInstance, "postscriptFontName", postscriptName):
            try:
                exportInstance.fontName = postscriptName
            except Exception:
                print("Could not set font name %s" % postscriptName)

    # -------------------------
    # Export
    # -------------------------

    def exportCallback(self, sender):
        formats = []

        if self.w.otfCheckbox.get():
            formats.append(("OTF", OTF))

        if self.w.ttfCheckbox.get():
            formats.append(("TTF", TTF))

        if not formats:
            self.w.status.set("Select at least one format.")
            return

        selectedSets = [
            (setName, setScript)
            for setName, setScript in self.sets
            if self.setCheckboxes[setName].get()
        ]

        if not selectedSets:
            self.w.status.set("Select at least one script set.")
            return

        destination = self.destinationPath

        if not destination:
            folder = GetFolder(message="Choose export destination")
            if not folder:
                self.w.status.set("Export cancelled.")
                return
            destination = str(folder)
            self.destinationPath = destination
            self.w.folderLabel.set(self.compactPath(destination))

        self.w.exportButton.enable(False)
        self.w.status.set("Exporting...")

        Glyphs.showMacroWindow()
        print("Export script sets")
        print("Destination: %s" % destination)

        exportedCount = 0
        errorCount = 0

        try:
            for formatName, formatConstant in formats:
                for setName, setScript in selectedSets:
                    folder = os.path.join(destination, formatName, setName)
                    os.makedirs(folder, exist_ok=True)

                    print("\n%s / %s" % (formatName, setName))

                    for instance in self.instances:
                        ok = self.exportInstance(
                            instance, setName, setScript, folder, formatConstant
                        )

                        if ok:
                            exportedCount += 1
                        else:
                            errorCount += 1
        finally:
            self.w.exportButton.enable(True)

        summary = "Done: %d exported" % exportedCount
        if errorCount:
            summary += ", %d failed (see Macro window)" % errorCount

        self.w.status.set(summary)
        print("\n%s" % summary)

    def exportInstance(self, instance, setName, setScript, folder, formatConstant):
        try:
            exportInstance = instance.copy()
        except Exception as error:
            print("  Could not copy instance %s: %s" % (instance.name, error))
            return False

        try:
            exportInstance.font = self.font
        except Exception:
            try:
                exportInstance.setFont_(self.font)
            except Exception as error:
                print("  Could not attach instance %s: %s" % (instance.name, error))
                return False

        # Build Remove Glyphs: keep base scripts + the set script,
        # remove every other script. Manual non-script rules of the
        # original instance are preserved.
        keepScripts = set(BASE_SCRIPTS)
        if setScript:
            keepScripts.add(setScript)

        scriptsToRemove = sorted(
            s for s in self.scripts if s not in keepScripts
        )

        manualLines = [
            line for line in self.getRemoveGlyphsLines(instance)
            if not line.strip().startswith("script=")
        ]

        removeLines = manualLines + ["script=%s" % s for s in scriptsToRemove]
        exportInstance.customParameters[PARAM_NAME] = removeLines

        # Family name: "MyFont" for LGC, "MyFont Armenian" for sets.
        # Full Names and Font Name are rewritten too, so explicit
        # overrides from the original instance can't leak through.
        if self.w.renameCheckbox.get() and setScript:
            self.applySetNaming(exportInstance, instance, setName)

        try:
            result = exportInstance.generate(
                Format=formatConstant,
                FontPath=folder,
                RemoveOverlap=True,
            )
        except Exception as error:
            print("  %s: ERROR %s" % (instance.name, error))
            return False

        if result is True:
            print("  %s: OK" % instance.name)
            return True

        print("  %s: %s" % (instance.name, result))
        return False


ExportScriptSets()
