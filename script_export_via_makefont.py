#MenuTitle: Script Export via Fontmake...
# -*- coding: utf-8 -*-

from __future__ import print_function

import os
import re
import glob
import shlex
import shutil
import tempfile
import subprocess

from AppKit import NSOpenPanel
try:
    from AppKit import NSModalResponseOK
    OK_RESPONSE = NSModalResponseOK
except Exception:
    from AppKit import NSOKButton
    OK_RESPONSE = NSOKButton

from GlyphsApp import Glyphs, Message, GSCustomParameter
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

KEEP_GLYPHS_PARAMETER_NAME = "Keep Glyphs"
REMOVE_GLYPHS_PARAMETER_NAME = "Remove Glyphs"

# These scripts are always kept:
# punctuation, figures, combining marks, shared signs, etc.
DO_NOT_REMOVE_SCRIPTS = set([
    "",
    "common",
    "inherited",
    "unknown",
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


def build_env():
    env = os.environ.copy()

    extra_paths = [
        "/opt/homebrew/bin",
        "/usr/local/bin",
        os.path.expanduser("~/.local/bin"),  # pipx usually puts fontmake here
        "/usr/bin",
        "/bin",
        "/usr/sbin",
        "/sbin",
    ]

    extra_paths += glob.glob(os.path.expanduser("~/Library/Python/*/bin"))
    extra_paths += glob.glob("/Library/Frameworks/Python.framework/Versions/*/bin")

    current_path = env.get("PATH", "")
    env["PATH"] = ":".join(extra_paths + [current_path])

    return env


def fontmake_command_base(env):
    found = shutil.which("fontmake", path=env.get("PATH", ""))
    if found:
        return [found]

    python3 = shutil.which("python3", path=env.get("PATH", ""))
    if python3:
        return [python3, "-m", "fontmake"]

    return None


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


# ------------------------------------------------------------
# Glyphs / custom parameter helpers
# ------------------------------------------------------------

def delete_custom_parameter(target, name):
    try:
        for i in range(len(target.customParameters) - 1, -1, -1):
            if target.customParameters[i].name == name:
                del target.customParameters[i]
    except Exception as e:
        print("Could not delete custom parameter %s:" % name)
        print(e)


def add_list_custom_parameter(target, name, values):
    delete_custom_parameter(target, name)

    try:
        parameter = GSCustomParameter(name, values)
        target.customParameters.append(parameter)
    except Exception as e:
        print("Could not add list custom parameter %s as list:" % name)
        print(e)

        try:
            target.customParameters[name] = "\n".join(values)
        except Exception as e2:
            print("Could not add custom parameter %s as string:" % name)
            print(e2)


def glyph_export_value(glyph):
    try:
        return bool(glyph.export)
    except Exception:
        return not glyph.name.startswith("_")


def glyph_script_value(glyph):
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

    return normalize_script(script)


def build_keep_and_remove_glyph_lists(font, selected_scripts):
    keep_glyph_names = []
    remove_glyph_names = []

    selected_scripts = set([normalize_script(script) for script in selected_scripts])

    for glyph in font.glyphs:
        originally_exports = glyph_export_value(glyph)

        # Preserve existing non-exporting glyphs.
        if not originally_exports:
            continue

        script = glyph_script_value(glyph)

        # Keep Common / Inherited / Unknown:
        # punctuation, figures, combining marks, shared symbols, etc.
        if script in DO_NOT_REMOVE_SCRIPTS:
            keep_glyph_names.append(glyph.name)
            continue

        if script in selected_scripts:
            keep_glyph_names.append(glyph.name)
        else:
            remove_glyph_names.append(glyph.name)

    return keep_glyph_names, remove_glyph_names


def apply_script_subset_to_temp_font(font, selected_scripts):
    keep_glyph_names, remove_glyph_names = build_keep_and_remove_glyph_lists(font, selected_scripts)
    keep_set = set(keep_glyph_names)

    for glyph in font.glyphs:
        if glyph_export_value(glyph) and glyph.name not in keep_set:
            try:
                glyph.export = False
            except Exception as e:
                print("Could not set glyph.export = False for %s:" % glyph.name)
                print(e)

    # Remove conflicting parameters from the temporary copy.
    delete_custom_parameter(font, REMOVE_GLYPHS_PARAMETER_NAME)
    delete_custom_parameter(font, KEEP_GLYPHS_PARAMETER_NAME)

    # Add Keep Glyphs globally as fallback.
    add_list_custom_parameter(font, KEEP_GLYPHS_PARAMETER_NAME, keep_glyph_names)

    # Add Keep Glyphs to exportable instances too.
    for instance in font.instances:
        try:
            if hasattr(instance, "active") and not instance.active:
                continue
        except Exception:
            pass

        try:
            if hasattr(instance, "exports") and not instance.exports:
                continue
        except Exception:
            pass

        delete_custom_parameter(instance, REMOVE_GLYPHS_PARAMETER_NAME)
        delete_custom_parameter(instance, KEEP_GLYPHS_PARAMETER_NAME)
        add_list_custom_parameter(instance, KEEP_GLYPHS_PARAMETER_NAME, keep_glyph_names)

    return keep_glyph_names, remove_glyph_names


def save_temp_glyphs_copy(original_font, selected_scripts):
    temp_dir = tempfile.mkdtemp(prefix="glyphs-fontmake-export-")
    family_name = safe_file_name(original_font.familyName)
    temp_path = os.path.join(temp_dir, "%s.subset.glyphs" % family_name)

    temp_font = original_font.copy()
    keep_glyph_names, remove_glyph_names = apply_script_subset_to_temp_font(temp_font, selected_scripts)

    temp_font.save(temp_path)

    return temp_dir, temp_path, keep_glyph_names, remove_glyph_names


# ------------------------------------------------------------
# Fontmake helpers
# ------------------------------------------------------------

def exportable_instances(font):
    instances = []

    for instance in font.instances:
        exports = True

        try:
            exports = bool(instance.exports)
        except Exception:
            try:
                exports = bool(instance.active)
            except Exception:
                exports = True

        if exports:
            instances.append(instance)

    return instances


def find_exported_fonts(output_dir, extension):
    found = []

    for root, dirs, files in os.walk(output_dir):
        for file_name in files:
            if file_name.lower().endswith("." + extension.lower()):
                found.append(os.path.join(root, file_name))

    return sorted(found)


def run_fontmake(original_font, output_kind, selected_scripts):
    output_dir = choose_output_folder()
    if not output_dir:
        return

    env = build_env()
    command_base = fontmake_command_base(env)

    if not command_base:
        alert(
            "fontmake not found",
            "Could not find fontmake.\n\nIf you installed it with pipx, make sure ~/.local/bin is available, or reinstall with:\n\npipx install fontmake"
        )
        return

    temp_dir, temp_glyphs_path, keep_glyph_names, remove_glyph_names = save_temp_glyphs_copy(
        original_font,
        selected_scripts
    )

    instances = exportable_instances(original_font)

    cmd = command_base + [
        "-g", temp_glyphs_path,
        "-o", output_kind,
        "--subset",
        "--output-dir", output_dir,
        "--master-dir", "{tmp}",
        "--instance-dir", "{tmp}",
    ]

    if instances:
        cmd.append("-i")
        export_mode = "instances"
    else:
        cmd.append("-M")
        export_mode = "masters as instances"

    Glyphs.clearLog()
    Glyphs.showMacroWindow()

    print("Fontmake Script Export")
    print("----------------------")
    print("Keep scripts:")
    print(", ".join(sorted(selected_scripts)))
    print("")
    print("Export format:")
    print(output_kind)
    print("")
    print("Export mode:")
    print(export_mode)
    print("")
    print("Keep Glyphs:")
    print("%s glyph(s)" % len(keep_glyph_names))
    print("")
    print("Glyphs marked as non-exporting:")
    print("%s glyph(s)" % len(remove_glyph_names))
    print("")

    if remove_glyph_names:
        print("Removed glyphs preview:")
        print(", ".join(remove_glyph_names[:100]))
        if len(remove_glyph_names) > 100:
            print("... and %s more" % (len(remove_glyph_names) - 100))
        print("")

    print("Temporary source:")
    print(temp_glyphs_path)
    print("")
    print("Output folder:")
    print(output_dir)
    print("")
    print("Command:")
    print(" ".join(shlex.quote(part) for part in cmd))
    print("")

    process = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=output_dir,
        env=env,
        text=True
    )

    stdout, stderr = process.communicate()

    if stdout:
        print("STDOUT:")
        print(stdout)

    if stderr:
        print("STDERR:")
        print(stderr)

    exported_fonts = find_exported_fonts(output_dir, output_kind)

    if process.returncode == 0 and exported_fonts:
        print("")
        print("Exported fonts:")
        for path in exported_fonts:
            print(path)

        message = "Export finished. %s font(s) exported." % len(exported_fonts)
        print("")
        print(message)

        try:
            Glyphs.showNotification("Fontmake export finished", message)
        except Exception:
            pass

    elif process.returncode == 0 and not exported_fonts:
        alert(
            "Fontmake finished, but no fonts were exported",
            "fontmake returned exit code 0, but no .%s files were found in the selected folder.\n\nOpen Macro Panel for details." % output_kind
        )

    else:
        alert(
            "Fontmake export failed",
            "fontmake returned exit code %s.\n\nOpen Macro Panel for details." % process.returncode
        )


# ------------------------------------------------------------
# UI
# ------------------------------------------------------------

class FontmakeScriptExportWindow(object):

    def __init__(self):
        width = 300
        height = 300

        self.w = FloatingWindow(
            (width, height),
            "Fontmake Script Export",
            minSize=(width, height),
            maxSize=(width, height),
        )

        self.w.note = TextBox(
            (16, 14, -16, 34),
            "Checked scripts will be kept.\nAll other scripts will be excluded.",
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

        run_fontmake(font, output_kind, selected)

    def export_ttf_callback(self, sender):
        self.export("ttf")

    def export_otf_callback(self, sender):
        self.export("otf")


Glyphs.fontmakeScriptExportWindow = FontmakeScriptExportWindow()