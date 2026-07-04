# MenuTitle: [test] Remove Glyphs Settings...
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs
import vanilla


PARAM_NAME = "Remove Glyphs"
DEFAULT_LANGUAGE_TAG = "dflt"


class RemoveGlyphsSettings(object):

    def __init__(self):
        self.font = Glyphs.font

        if not self.font:
            Glyphs.showMacroWindow()
            print("No font open.")
            return

        self.instances = [i for i in self.font.instances if i.active]

        if not self.instances:
            Glyphs.showMacroWindow()
            print("No active export instances found.")
            return

        self.scripts = self.collectScripts()

        if not self.scripts:
            Glyphs.showMacroWindow()
            print("No glyph scripts found in this font.")
            return

        self.selectedInstanceIndex = 0
        self.currentCheckboxStates = {}
        self.isDirty = False
        self.scriptCheckboxes = {}

        self.w = vanilla.FloatingWindow(
            (620, 430),
            "Remove glyphs settings",
            minSize=(520, 320),
            maxSize=(900, 700),
        )

        margin = 16
        listTop = 58
        buttonWidth = 90
        buttonHeight = 28

        self.w.instancesLabel = vanilla.TextBox(
            (margin, margin, 220, 22),
            "Instances",
            sizeStyle="regular",
        )

        self.w.scriptsLabel = vanilla.TextBox(
            (300, margin, 220, 22),
            "Scripts to keep",
            sizeStyle="regular",
        )

        instanceNames = [self.instanceDisplayName(i) for i in self.instances]

        self.w.instancesList = vanilla.List(
            (margin, listTop, 250, -margin),
            instanceNames,
            selectionCallback=self.instanceSelectionChanged,
        )

        buttonSpacing = 8
        closeBottom = margin
        applyBottom = closeBottom + buttonHeight + buttonSpacing

        self.w.scriptsBox = vanilla.Group(
            (300, listTop, -margin, -(applyBottom + buttonHeight + 12))
        )

        self.w.applyButton = vanilla.Button(
            (-margin - buttonWidth, -(applyBottom + buttonHeight), buttonWidth, buttonHeight),
            "Apply",
            callback=self.applyCallback,
        )
        self.w.applyButton.enable(False)

        self.w.revertButton = vanilla.Button(
            (
                -margin - buttonWidth * 2 - buttonSpacing,
                -(applyBottom + buttonHeight),
                buttonWidth,
                buttonHeight,
            ),
            "Revert",
            callback=self.revertCallback,
        )
        self.w.revertButton.enable(False)

        self.w.closeButton = vanilla.Button(
            (-margin - buttonWidth, -(closeBottom + buttonHeight), buttonWidth, buttonHeight),
            "Close",
            callback=self.closeCallback,
        )

        # Keep keyboard focus on the instances list so its selection
        # stays highlighted in the accent color instead of inactive gray.
        self.stopStealingFocus(self.w.applyButton)
        self.stopStealingFocus(self.w.revertButton)
        self.stopStealingFocus(self.w.closeButton)

        self.buildScriptCheckboxes()

        self.w.instancesList.setSelection([0])
        self.loadInstanceState()

        self.w.open()
        self.focusInstancesList()

    # -------------------------
    # Collect data
    # -------------------------

    def collectScripts(self):
        scripts = set()

        for glyph in self.font.glyphs:
            script = glyph.script
            if script:
                scripts.add(script)

        return sorted(scripts)

    # -------------------------
    # Instance naming
    # -------------------------

    def instanceDisplayName(self, instance):
        familyName = self.localizedFamilyNameForInstance(instance)
        styleName = self.styleNameForInstance(instance)

        if familyName and styleName:
            return "%s %s" % (familyName, styleName)

        if familyName:
            return familyName

        if styleName:
            return styleName

        if instance.name:
            return instance.name

        return "Unnamed instance"

    def styleNameForInstance(self, instance):
        # Usually this is what Glyphs shows as Style Name.
        if instance.name:
            return instance.name

        if hasattr(instance, "styleName") and instance.styleName:
            return instance.styleName

        return None

    def propertyValueAsString(self, prop):
        # propertyForName_languageTag_ returns a property object,
        # not the string itself. Extract .value if present.
        if prop is None:
            return None

        value = getattr(prop, "value", None)
        if value:
            return str(value)

        if isinstance(prop, str) and prop:
            return prop

        return None

    def localizedFamilyNameForInstance(self, instance):
        # 1. Try Glyphs 3 property API:
        # Localized Family Names = familyNames
        try:
            prop = instance.propertyForName_languageTag_("familyNames", DEFAULT_LANGUAGE_TAG)
            value = self.propertyValueAsString(prop)
            if value:
                return value
        except Exception:
            pass

        # 2. Try scanning properties manually.
        try:
            for prop in instance.properties:
                if prop.name == "familyNames":
                    if getattr(prop, "languageTag", None) in (DEFAULT_LANGUAGE_TAG, None, ""):
                        if prop.value:
                            return str(prop.value)
        except Exception:
            pass

        # 3. Fallback to font-level family name.
        try:
            prop = self.font.propertyForName_languageTag_("familyNames", DEFAULT_LANGUAGE_TAG)
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

        return None

    # -------------------------
    # UI
    # -------------------------

    def stopStealingFocus(self, control):
        # Controls that refuse first responder status don't pull
        # keyboard focus away from the instances list when clicked,
        # so the list selection keeps its accent color.
        try:
            control.getNSButton().setRefusesFirstResponder_(True)
        except Exception:
            pass

    def focusInstancesList(self):
        # vanilla.FloatingWindow creates an NSPanel with
        # becomesKeyOnlyIfNeeded enabled, so the panel never becomes
        # the key window and the list selection is always drawn in
        # inactive gray. Undo that so selection gets the accent color.
        try:
            panel = self.w.getNSWindow()
            panel.setBecomesKeyOnlyIfNeeded_(False)
            panel.makeKeyWindow()
        except Exception:
            pass

        try:
            tableView = self.w.instancesList.getNSTableView()
            self.w.getNSWindow().makeFirstResponder_(tableView)
        except Exception:
            pass

    def buildScriptCheckboxes(self):
        y = 0

        for script in self.scripts:
            checkbox = vanilla.CheckBox(
                (0, y, -0, 24),
                self.prettyScriptName(script),
                value=False,
                callback=self.checkboxChanged,
            )
            self.stopStealingFocus(checkbox)

            setattr(self.w.scriptsBox, "checkbox_%s" % self.safeAttributeName(script), checkbox)
            self.scriptCheckboxes[script] = checkbox

            y += 28

    def safeAttributeName(self, text):
        safe = []
        for char in text:
            if char.isalnum() or char == "_":
                safe.append(char)
            else:
                safe.append("_")
        return "".join(safe)

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

    def instanceSelectionChanged(self, sender):
        selection = sender.getSelection()

        if not selection:
            return

        newIndex = selection[0]

        if self.isDirty:
            self.w.instancesList.setSelection([self.selectedInstanceIndex])
            Glyphs.showNotification(
                "Remove glyphs settings",
                "Apply current changes before selecting another instance.",
            )
            return

        self.selectedInstanceIndex = newIndex
        self.loadInstanceState()

    def checkboxChanged(self, sender):
        self.updateDirtyState()

    def setApplyEnabled(self, value):
        self.w.applyButton.enable(bool(value))
        self.w.revertButton.enable(bool(value))

    def revertCallback(self, sender):
        # Restore checkboxes to the last loaded/applied state
        # of the selected instance.
        for script, checkbox in self.scriptCheckboxes.items():
            checkbox.set(bool(self.currentCheckboxStates.get(script)))

        self.isDirty = False
        self.setApplyEnabled(False)
        self.focusInstancesList()

    # -------------------------
    # Remove Glyphs parsing
    # -------------------------

    def selectedInstance(self):
        return self.instances[self.selectedInstanceIndex]

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
            # Glyphs usually stores Remove Glyphs as a list (NSArray).
            # Iterate it directly instead of str()-ing the whole thing,
            # which would produce plist junk like ( "script=latin" ).
            try:
                rawLines = [str(item) for item in value]
            except TypeError:
                rawLines = str(value).splitlines()

        return self.normalizeLines(rawLines)

    def cleanToken(self, token):
        token = str(token).strip()

        # Strip plist leftovers: trailing commas / semicolons.
        while token and token[-1] in (",", ";"):
            token = token[:-1].strip()

        # Strip wrapping quotes: "script=latin" -> script=latin
        if len(token) >= 2 and token[0] == token[-1] and token[0] in ('"', "'"):
            token = token[1:-1].strip()

        # Drop pure plist delimiters.
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

            # Support accidental multi-line / comma-separated values a little better.
            for part in line.replace(",", "\n").splitlines():
                part = self.cleanToken(part)
                if part and part not in seen:
                    seen.add(part)
                    lines.append(part)

        return lines

    def getRemovedScripts(self, instance):
        lines = self.getRemoveGlyphsLines(instance)
        removedScripts = set()

        for line in lines:
            line = line.strip()

            if line.startswith("script="):
                script = line.split("=", 1)[1].strip()

                if script:
                    removedScripts.add(script)

        return removedScripts

    def loadInstanceState(self):
        instance = self.selectedInstance()
        removedScripts = self.getRemovedScripts(instance)

        self.currentCheckboxStates = {}

        for script, checkbox in self.scriptCheckboxes.items():
            # Checked = keep.
            # If script is already in Remove Glyphs, checkbox must be off.
            shouldKeep = script not in removedScripts

            checkbox.set(shouldKeep)
            self.currentCheckboxStates[script] = shouldKeep

        self.isDirty = False
        self.setApplyEnabled(False)

    def updateDirtyState(self):
        dirty = False

        for script, checkbox in self.scriptCheckboxes.items():
            currentValue = bool(checkbox.get())
            originalValue = bool(self.currentCheckboxStates.get(script))

            if currentValue != originalValue:
                dirty = True
                break

        self.isDirty = dirty
        self.setApplyEnabled(dirty)

    # -------------------------
    # Apply
    # -------------------------

    def applyCallback(self, sender):
        instance = self.selectedInstance()

        scriptsToRemove = []

        for script, checkbox in self.scriptCheckboxes.items():
            keepScript = bool(checkbox.get())

            if not keepScript:
                scriptsToRemove.append("script=%s" % script)

        oldLines = self.getRemoveGlyphsLines(instance)

        # Preserve manual non-script rules:
        # unicode=...
        # note=...
        # category=...
        # subCategory=...
        # production=...
        preservedLines = [
            line for line in oldLines
            if not line.strip().startswith("script=")
        ]

        newLines = []
        seen = set()
        for line in preservedLines + sorted(scriptsToRemove):
            if line not in seen:
                seen.add(line)
                newLines.append(line)

        self.setRemoveGlyphsParameter(instance, newLines)

        self.currentCheckboxStates = {
            script: bool(checkbox.get())
            for script, checkbox in self.scriptCheckboxes.items()
        }

        self.isDirty = False
        self.setApplyEnabled(False)

        Glyphs.showNotification(
            "Remove glyphs settings",
            "Updated Remove Glyphs for %s." % self.instanceDisplayName(instance),
        )

        self.focusInstancesList()

    def setRemoveGlyphsParameter(self, instance, lines):
        # Store as a list of lines - this is the native format
        # for the Remove Glyphs parameter in Glyphs 3.
        value = list(lines)

        parameter = self.getRemoveGlyphsParameter(instance)

        if parameter:
            parameter.value = value
        else:
            instance.customParameters[PARAM_NAME] = value

    def closeCallback(self, sender):
        self.w.close()


RemoveGlyphsSettings()
