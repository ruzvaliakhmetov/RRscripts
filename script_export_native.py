#MenuTitle: Script Export Native...
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import re
import glob
import tempfile
import xml.etree.ElementTree as ET

from AppKit import NSOpenPanel
try:
    from AppKit import NSModalResponseOK
    OK_RESPONSE = NSModalResponseOK
except Exception:
    from AppKit import NSOKButton
    OK_RESPONSE = NSOKButton

from Foundation import NSBundle

from GlyphsApp import Glyphs, Message, GSCustomParameter, GSInstance
from GlyphsApp import OTF, TTF, PLAIN

try:
    from GlyphsApp import INSTANCETYPESINGLE, INSTANCETYPEVARIABLE
except Exception:
    INSTANCETYPESINGLE = 0
    INSTANCETYPEVARIABLE = 1

from vanilla import FloatingWindow, TextBox, CheckBox, Button, HorizontalLine


# ------------------------------------------------------------
# Settings
# ------------------------------------------------------------

KEEP_SCRIPT_OPTIONS = [
    ("Latin", "latin"),
    ("Cyrillic", "cyrillic"),
    ("Georgian", "georgian"),
    ("Armenian", "armenian"),
    ("Greek", "greek"),
    ("Arabic", "arabic"),
    ("Hebrew", "hebrew"),
]

REMOVE_GLYPHS_PARAMETER_NAME = "Remove Glyphs"

# Do not remove punctuation, figures, combining marks, shared signs, etc.
DO_NOT_REMOVE_SCRIPTS = set([
    "",
    "common",
    "inherited",
    "unknown",
    None,
])

FALLBACK_SCRIPT_VALUES = set([
    "adlam", "alchemical", "arabic", "armenian", "avestan",
    "balinese", "bamum", "batak", "bengali", "black letter",
    "bopomofo", "brahmi", "braille", "buginese", "canadian",
    "chakma", "cham", "cherokee", "chorasmian", "coptic",
    "cyrillic", "dentistry", "deseret", "devanagari", "divesakuru",
    "elbasan", "elymaic", "ethiopic", "georgian", "glagolitic",
    "gothic", "greek", "gujarati", "gurmukhi", "han", "hangul",
    "hebrew", "javanese", "kana", "kannada", "kawi", "kayahli",
    "khmer", "khojki", "lao", "latin", "lepcha", "lue",
    "mahjong", "malayalam", "mandaic", "math", "mongolian",
    "musical", "myanmar", "nko", "nyiakeng puachue hmong",
    "ogham", "old georgian", "oriya", "osage", "osmanya",
    "pahawh hmong", "phaistosDisc", "rovas", "runic",
    "samaritan", "shavian", "sinhala", "syriac", "tagalog",
    "tamil", "telugu", "thaana", "thai", "tham", "tibet",
    "tifinagh", "vai", "yezidi", "yi",
])


# ------------------------------------------------------------
# Small helpers
# ------------------------------------------------------------

def alert(title, message):
    try:
        Message(title=title, message=message)
    except Exception:
        print("%s\n%s" % (title, message))


def safe_file_name(name):
    name = name or "font"
    name = re.sub(r"[^\w\-. ]+", "_", name, flags=re.UNICODE)
    name = name.strip(" .")
    return name or "font"


def normalize_script(script):
    if script is None:
        return ""
    return str(script).strip().lower()


def choose_output_folder():
    panel = NSOpenPanel.openPanel()
    panel.setTitle_("Choose export folder")
    panel.setPrompt_("Export")
    panel.setCanChooseFiles_(False)
    panel.setCanChooseDirectories_(True)
    panel.setAllowsMultipleSelection_(False)
    panel.setCanCreateDirectories_(True)

    result = panel.runModal()
    if result == OK_RESPONSE:
        return panel.URL().path()

    return None


def find_exported_fonts(output_dir, extension):
    found = []

    for root, dirs, files in os.walk(output_dir):
        for file_name in files:
            if file_name.lower().endswith("." + extension.lower()):
                found.append(os.path.join(root, file_name))

    return sorted(found)


# ------------------------------------------------------------
# GlyphData script discovery
# ------------------------------------------------------------

def glyphdata_xml_paths():
    paths = []

    try:
        app_path = str(NSBundle.mainBundle().bundlePath())
        pattern = os.path.join(
            app_path,
            "Contents",
            "Frameworks",
            "GlyphsCore.framework",
            "Versions",
            "A",
            "Resources",
            "GlyphData*.xml"
        )
        paths += glob.glob(pattern)
    except Exception:
        pass

    paths += glob.glob(os.path.expanduser("~/Library/Application Support/Glyphs/Info/GlyphData*.xml"))
    paths += glob.glob(os.path.expanduser("~/Library/Application Support/Glyphs 3/Info/GlyphData*.xml"))

    seen = set()
    unique_paths = []

    for path in paths:
        if path not in seen and os.path.exists(path):
            unique_paths.append(path)
            seen.add(path)

    return unique_paths


def scripts_from_glyphdata_xml():
    scripts = set()

    for path in glyphdata_xml_paths():
        try:
            tree = ET.parse(path)
            root = tree.getroot()

            for element in root.iter():
                script = element.attrib.get("script")
                if script:
                    scripts.add(script)

        except Exception as e:
            print("Could not read GlyphData XML:")
            print(path)
            print(e)

    return scripts


def scripts_from_current_font(font):
    scripts = set()

    for glyph in font.glyphs:
        script = None

        try:
            script = glyph.script
        except Exception:
            pass

        if not script:
            try:
                info = Glyphs.glyphInfoForName(glyph.name)
                if info:
                    script = info.script
            except Exception:
                pass

        if script:
            scripts.add(script)

    return scripts


def all_supported_scripts(font):
    scripts = scripts_from_glyphdata_xml()
    scripts.update(scripts_from_current_font(font))

    if not scripts:
        scripts = set(FALLBACK_SCRIPT_VALUES)

    clean_scripts = set()

    for script in scripts:
        normalized = normalize_script(script)
        if normalized not in DO_NOT_REMOVE_SCRIPTS:
            clean_scripts.add(script)

    return clean_scripts


# ------------------------------------------------------------
# Custom parameter helpers
# ------------------------------------------------------------

def delete_custom_parameter(target, name):
    try:
        for i in range(len(target.customParameters) - 1, -1, -1):
            if target.customParameters[i].name == name:
                del target.customParameters[i]
    except Exception as e:
        print("Could not delete custom parameter %s:" % name)
        print(e)


def add_remove_glyphs_parameter(target, remove_glyphs_lines):
    delete_custom_parameter(target, REMOVE_GLYPHS_PARAMETER_NAME)

    try:
        parameter = GSCustomParameter(REMOVE_GLYPHS_PARAMETER_NAME, remove_glyphs_lines)
        target.customParameters.append(parameter)
    except Exception as e:
        print("Could not add Remove Glyphs as list:")
        print(e)

        try:
            target.customParameters[REMOVE_GLYPHS_PARAMETER_NAME] = "\n".join(remove_glyphs_lines)
        except Exception as e2:
            print("Could not add Remove Glyphs as string:")
            print(e2)


def remove_glyphs_lines_for_selected_scripts(font, selected_scripts):
    selected_normalized = set([normalize_script(script) for script in selected_scripts])

    remove_scripts = []

    for script in all_supported_scripts(font):
        normalized = normalize_script(script)

        if normalized in DO_NOT_REMOVE_SCRIPTS:
            continue

        if normalized not in selected_normalized:
            remove_scripts.append(script)

    lines = []
    for script in sorted(remove_scripts, key=lambda item: normalize_script(item)):
        lines.append("script=%s" % script)

    return lines


def apply_remove_glyphs_to_font_and_instances(font, selected_scripts):
    remove_glyphs_lines = remove_glyphs_lines_for_selected_scripts(font, selected_scripts)

    add_remove_glyphs_parameter(font, remove_glyphs_lines)

    for instance in font.instances:
        if is_exportable_static_instance(instance):
            add_remove_glyphs_parameter(instance, remove_glyphs_lines)

    return remove_glyphs_lines


# ------------------------------------------------------------
# Instance helpers
# ------------------------------------------------------------

def instance_exports(instance):
    try:
        return bool(instance.exports)
    except Exception:
        try:
            return bool(instance.active)
        except Exception:
            return True


def is_variable_instance(instance):
    try:
        return instance.type == INSTANCETYPEVARIABLE
    except Exception:
        return False


def is_exportable_static_instance(instance):
    if not instance_exports(instance):
        return False

    if is_variable_instance(instance):
        return False

    return True


def exportable_static_instances(font):
    return [instance for instance in font.instances if is_exportable_static_instance(instance)]


def make_fallback_instances_from_masters(font):
    created_instances = []

    if font.instances:
        return created_instances

    for master in font.masters:
        instance = GSInstance()

        try:
            instance.name = master.name or "Regular"
        except Exception:
            instance.name = "Regular"

        try:
            instance.type = INSTANCETYPESINGLE
        except Exception:
            pass

        try:
            instance.exports = True
        except Exception:
            pass

        try:
            instance.axes = list(master.axes)
        except Exception:
            pass

        try:
            instance.weightClass = 400
        except Exception:
            pass

        try:
            instance.widthClass = 5
        except Exception:
            pass

        font.instances.append(instance)
        created_instances.append(instance)

    return created_instances


def prepare_temp_font(original_font, selected_scripts):
    temp_font = original_font.copy()

    make_fallback_instances_from_masters(temp_font)

    remove_glyphs_lines = apply_remove_glyphs_to_font_and_instances(
        temp_font,
        selected_scripts
    )

    return temp_font, remove_glyphs_lines


# ------------------------------------------------------------
# Native export
# ------------------------------------------------------------

def native_export(original_font, output_kind, selected_scripts):
    output_dir = choose_output_folder()
    if not output_dir:
        return

    if output_kind == "otf":
        format_constant = OTF
        extension = "otf"
    else:
        format_constant = TTF
        extension = "ttf"

    temp_font, remove_glyphs_lines = prepare_temp_font(original_font, selected_scripts)
    instances = exportable_static_instances(temp_font)

    Glyphs.clearLog()
    Glyphs.showMacroWindow()

    print("Native Script Export")
    print("--------------------")
    print("Keep scripts:")
    print(", ".join(sorted(selected_scripts)))
    print("")
    print("Export format:")
    print(output_kind.upper())
    print("")
    print("Export mode:")
    if original_font.instances:
        print("existing exportable static instances")
    else:
        print("temporary instances from masters")
    print("")
    print("Remove Glyphs parameter:")
    print("%s line(s)" % len(remove_glyphs_lines))
    print("")

    for line in remove_glyphs_lines:
        print(line)

    print("")
    print("Output folder:")
    print(output_dir)
    print("")

    if not instances:
        alert(
            "No exportable instances",
            "No exportable static instances were found or created."
        )
        return

    results = []
    errors = []

    before_export = set(find_exported_fonts(output_dir, extension))

    for instance in instances:
        print("Exporting instance:")
        print(instance.name)

        try:
            result = instance.generate(
                Format=format_constant,
                FontPath=output_dir,
                AutoHint=False,
                RemoveOverlap=True,
                UseSubroutines=True,
                UseProductionNames=True,
                Containers=[PLAIN],
                DecomposeSmartStuff=True,
            )

            results.append((instance.name, result))

            print("Result:")
            print(result)

            try:
                if instance.lastExportedFilePath:
                    print("Last exported file:")
                    print(instance.lastExportedFilePath)
            except Exception:
                pass

            print("")

        except Exception as e:
            errors.append((instance.name, e))
            print("ERROR:")
            print(e)
            print("")

    after_export = set(find_exported_fonts(output_dir, extension))
    new_fonts = sorted(list(after_export.difference(before_export)))

    if new_fonts:
        print("Exported fonts:")
        for path in new_fonts:
            print(path)
        print("")

        message = "Export finished. %s font(s) exported." % len(new_fonts)

        try:
            Glyphs.showNotification("Native export finished", message)
        except Exception:
            pass

        print(message)

    elif errors:
        error_text = "\n".join(["%s: %s" % (name, error) for name, error in errors])
        alert(
            "Native export failed",
            "Glyphs reported errors during export.\n\n%s\n\nOpen Macro Panel for details." % error_text
        )

    else:
        alert(
            "Native export finished, but no new fonts were detected",
            "Glyphs did not report a hard error, but no new .%s files were detected in the selected folder.\n\nOpen Macro Panel for details." % extension
        )


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------

class NativeScriptExportWindow(object):

    def __init__(self):
        width = 300
        height = 300

        self.w = FloatingWindow(
            (width, height),
            "Native Script Export",
            minSize=(width, height),
            maxSize=(width, height),
        )

        self.w.note = TextBox(
            (16, 14, -16, 34),
            "Checked scripts will be kept.\nAll other scripts go to Remove Glyphs.",
            sizeStyle="small"
        )

        self.checkboxes = {}

        y = 58
        for label, script in KEEP_SCRIPT_OPTIONS:
            self.checkboxes[script] = CheckBox(
                (18, y, -18, 22),
                label,
                value=True,
                sizeStyle="regular"
            )
            setattr(self.w, "check_%s" % script, self.checkboxes[script])
            y += 26

        self.w.line = HorizontalLine((16, -58, -16, 1))

        self.w.exportTTF = Button(
            (16, -44, 126, 28),
            "Export TTF",
            callback=self.export_ttf_callback
        )

        self.w.exportOTF = Button(
            (-142, -44, 126, 28),
            "Export OTF",
            callback=self.export_otf_callback
        )

        self.w.open()

    def selected_scripts(self):
        selected = set()

        for label, script in KEEP_SCRIPT_OPTIONS:
            if self.checkboxes[script].get():
                selected.add(script)

        return selected

    def current_font(self):
        font = Glyphs.font
        if not font:
            alert("No font open", "Open a Glyphs file first.")
            return None
        return font

    def export(self, output_kind):
        font = self.current_font()
        if not font:
            return

        selected = self.selected_scripts()
        if not selected:
            alert(
                "No scripts selected",
                "Select at least one script to keep."
            )
            return

        native_export(font, output_kind, selected)

    def export_ttf_callback(self, sender):
        self.export("ttf")

    def export_otf_callback(self, sender):
        self.export("otf")


Glyphs.nativeScriptExportWindow = NativeScriptExportWindow()