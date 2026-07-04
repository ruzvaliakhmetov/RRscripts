# MenuTitle: [test] Export Families to Folders...
# -*- coding: utf-8 -*-
#
# Companion to "Remove Glyphs Settings..." for setups where instances
# are already multiplied per script (MyFont Medium, MyFont Arabic
# Medium, ...) with Localized Family Names overrides and their own
# Remove Glyphs parameters.
#
# This script does NOT modify anything. It groups active static
# instances by their (resolved) family name and exports each group
# into its own folder:
#
#   Destination/OTF/LGC/...       <- base family ("MyFont")
#   Destination/OTF/Arabic/...    <- "MyFont Arabic"
#   Destination/TTF/LGC/...
#   ...
#
# Folder naming: the base font family name maps to "LGC"; a family
# name starting with the base name maps to its suffix ("MyFont
# Arabic" -> "Arabic"); anything else keeps its full family name.

import os

from GlyphsApp import Glyphs, OTF, TTF, GetFolder
import vanilla

try:
    from GlyphsApp import INSTANCETYPEVARIABLE
except ImportError:
    INSTANCETYPEVARIABLE = None


DEFAULT_LANGUAGE_TAG = "dflt"
BASE_SET_NAME = "LGC"


class ExportFamiliesToFolders(object):

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

        # {folderName: [instance, ...]}
        self.groups = self.groupInstances()
        self.groupNames = self.sortedGroupNames()

        self.destinationPath = None
        self.groupCheckboxes = {}

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

    def propertyValueAsString(self, prop):
        if prop is None:
            return None

        value = getattr(prop, "value", None)
        if value:
            return str(value)

        if isinstance(prop, str) and prop:
            return prop

        return None

    def instanceFamilyName(self, instance):
        try:
            prop = instance.propertyForName_languageTag_("familyNames", DEFAULT_LANGUAGE_TAG)
            value = self.propertyValueAsString(prop)
            if value:
                return value
        except Exception:
            pass

        try:
            for prop in instance.properties:
                if prop.name == "familyNames":
                    if getattr(prop, "languageTag", None) in (DEFAULT_LANGUAGE_TAG, None, ""):
                        if prop.value:
                            return str(prop.value)
        except Exception:
            pass

        try:
            if self.font.familyName:
                return self.font.familyName
        except Exception:
            pass

        return "Untitled"

    def baseFontFamilyName(self):
        try:
            if self.font.familyName:
                return str(self.font.familyName)
        except Exception:
            pass

        return "Untitled"

    def folderNameForFamily(self, familyName):
        base = self.baseFontFamilyName()

        if familyName == base:
            return BASE_SET_NAME

        prefix = base + " "
        if familyName.startswith(prefix):
            suffix = familyName[len(prefix):].strip()
            if suffix:
                return suffix

        return familyName

    def groupInstances(self):
        groups = {}

        for instance in self.instances:
            familyName = self.instanceFamilyName(instance)
            folderName = self.folderNameForFamily(familyName)
            groups.setdefault(folderName, []).append(instance)

        return groups

    def sortedGroupNames(self):
        names = sorted(self.groups.keys())

        # LGC always comes first.
        if BASE_SET_NAME in names:
            names.remove(BASE_SET_NAME)
            names.insert(0, BASE_SET_NAME)

        return names

    # -------------------------
    # UI
    # -------------------------

    def buildUI(self):
        margin = 16
        lineHeight = 24
        y = margin

        groupsHeight = lineHeight * len(self.groupNames)
        windowHeight = (
            22 + 8 + groupsHeight        # groups label + checkboxes
            + 16 + 22 + 8 + lineHeight   # formats
            + 16 + 28                    # destination row
            + 16 + 28                    # export button
            + 22                         # status line
            + margin * 2
        )
        windowHeight = max(windowHeight, 320)

        self.w = vanilla.FloatingWindow(
            (420, windowHeight),
            "Export families to folders",
        )

        self.w.groupsLabel = vanilla.TextBox(
            (margin, y, -margin, 22),
            "Families to export",
        )
        y += 30

        for groupName in self.groupNames:
            count = len(self.groups[groupName])
            label = "%s (%d instance%s)" % (
                groupName, count, "" if count == 1 else "s"
            )

            checkbox = vanilla.CheckBox(
                (margin + 8, y, -margin, lineHeight),
                label,
                value=True,
            )
            self.groupCheckboxes[groupName] = checkbox
            setattr(self.w, "groupCheckbox_%s" % self.safeAttributeName(groupName), checkbox)
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

        selectedGroups = [
            name for name in self.groupNames
            if self.groupCheckboxes[name].get()
        ]

        if not selectedGroups:
            self.w.status.set("Select at least one family.")
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
        print("Export families to folders")
        print("Destination: %s" % destination)

        exportedCount = 0
        errorCount = 0

        try:
            for formatName, formatConstant in formats:
                for groupName in selectedGroups:
                    folder = os.path.join(destination, formatName, groupName)
                    os.makedirs(folder, exist_ok=True)

                    print("\n%s / %s" % (formatName, groupName))

                    for instance in self.groups[groupName]:
                        ok = self.exportInstance(instance, folder, formatConstant)

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

    def exportInstance(self, instance, folder, formatConstant):
        try:
            result = instance.generate(
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


ExportFamiliesToFolders()
