#MenuTitle: Export Variable TTF via fontmake...
# -*- coding: utf-8 -*-

from GlyphsApp import Glyphs
from AppKit import NSOpenPanel
import os
import subprocess
import tempfile
import shutil
import glob
import traceback


# If True, adds -f to fontmake.
# Useful when you have nested components.
FLATTEN_COMPONENTS = False

# If True, keeps temporary .glyphs file when export fails.
# Useful for debugging fontmake output.
KEEP_TEMP_ON_ERROR = True


def find_fontmake():
    """
    Glyphs.app does not always inherit the same PATH as Terminal.
    So we check the most likely locations explicitly.
    """
    candidates = [
        os.path.expanduser("~/.local/bin/fontmake"),  # default pipx binary location
        "/opt/homebrew/bin/fontmake",                 # Apple Silicon Homebrew
        "/usr/local/bin/fontmake",                    # Intel Homebrew
    ]

    for path in candidates:
        if os.path.isfile(path) and os.access(path, os.X_OK):
            return path

    # Fallback: ask shell environment.
    try:
        result = subprocess.run(
            ["/bin/zsh", "-lc", "command -v fontmake"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        found = result.stdout.strip()
        if found and os.path.isfile(found):
            return found
    except Exception:
        pass

    return None


def choose_export_folder():
    panel = NSOpenPanel.openPanel()
    panel.setCanChooseFiles_(False)
    panel.setCanChooseDirectories_(True)
    panel.setAllowsMultipleSelection_(False)
    panel.setCanCreateDirectories_(True)
    panel.setPrompt_("Export")

    if panel.runModal() == 1:
        return panel.URL().path()
    return None


def clean_name(name):
    allowed = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_"
    cleaned = "".join(c if c in allowed else "_" for c in name)
    return cleaned or "Untitled"


def important_lines(log_text):
    """
    Extract potentially useful lines from fontmake output.
    This is not perfect, but it makes long tracebacks easier to scan.
    """
    keywords = [
        "error",
        "exception",
        "traceback",
        "incompatible",
        "compatib",
        "glyph",
        "master",
        "contour",
        "point",
        "interpol",
        "varlib",
        "cu2qu",
        "fontmake",
    ]

    lines = []
    for line in log_text.splitlines():
        low = line.lower()
        if any(k in low for k in keywords):
            lines.append(line)

    if not lines:
        return ""

    # Avoid flooding the beginning of the Macro Window.
    return "\n".join(lines[-80:])


def show_header(title):
    print("\n" + "=" * 72)
    print(title)
    print("=" * 72 + "\n")


def main():
    Glyphs.clearLog()
    Glyphs.showMacroWindow()

    font = Glyphs.font
    if font is None:
        print("No font is open.")
        Glyphs.showNotification("fontmake export failed", "No font is open.")
        return

    fontmake_path = find_fontmake()
    if not fontmake_path:
        print("Could not find fontmake.")
        print("")
        print("Try this in Terminal:")
        print("    pipx ensurepath")
        print("    exec zsh")
        print("    command -v fontmake")
        print("")
        print("If command -v fontmake returns a path, add it to find_fontmake() candidates.")
        Glyphs.showNotification("fontmake export failed", "Could not find fontmake.")
        return

    export_dir = choose_export_folder()
    if not export_dir:
        print("Export cancelled.")
        return

    family_name = clean_name(font.familyName or "Untitled")
    temp_root = tempfile.mkdtemp(prefix="glyphs_fontmake_")
    temp_glyphs_path = os.path.join(temp_root, family_name + ".glyphs")

    show_header("Export Variable TTF via fontmake")

    print("fontmake:")
    print("  " + fontmake_path)
    print("")
    print("Export folder:")
    print("  " + export_dir)
    print("")
    print("Temporary source:")
    print("  " + temp_glyphs_path)
    print("")

    try:
        # Save a copy, without changing the path of the currently open document.
        # Glyphs 3 API supports save(path, formatVersion=3, makeCopy=False).
        font.save(temp_glyphs_path, makeCopy=True)

        cmd = [
            fontmake_path,
            temp_glyphs_path,
            "-o",
            "variable",
            "--output-dir",
            export_dir,
        ]

        if FLATTEN_COMPONENTS:
            cmd.append("-f")

        print("Command:")
        print("  " + " ".join('"%s"' % x if " " in x else x for x in cmd))
        print("")

        env = os.environ.copy()

        # Help subprocess find Homebrew/pipx tools even when Glyphs has a poor PATH.
        extra_paths = [
            os.path.expanduser("~/.local/bin"),
            "/opt/homebrew/bin",
            "/usr/local/bin",
            "/usr/bin",
            "/bin",
        ]
        env["PATH"] = ":".join(extra_paths + [env.get("PATH", "")])

        result = subprocess.run(
            cmd,
            cwd=temp_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env=env,
        )

        full_log = ""
        if result.stdout:
            full_log += result.stdout
        if result.stderr:
            full_log += "\n" + result.stderr

        print("Exit code:")
        print("  " + str(result.returncode))
        print("")

        if result.returncode == 0:
            show_header("Success")

            ttf_files = []
            ttf_files += glob.glob(os.path.join(export_dir, "*.ttf"))
            ttf_files += glob.glob(os.path.join(export_dir, "variable_ttf", "*.ttf"))

            if ttf_files:
                print("Generated TTF file(s):")
                for path in ttf_files:
                    print("  " + path)
            else:
                print("fontmake finished successfully, but I could not find .ttf files in:")
                print("  " + export_dir)

            if full_log.strip():
                show_header("fontmake log")
                print(full_log)

            Glyphs.showNotification("fontmake export complete", "Variable TTF exported.")
            subprocess.call(["open", export_dir])

            shutil.rmtree(temp_root, ignore_errors=True)

        else:
            show_header("fontmake failed")

            summary = important_lines(full_log)
            if summary:
                print("Important lines:")
                print(summary)
                print("")

            print("Full fontmake log:")
            print(full_log if full_log.strip() else "(No output from fontmake.)")

            if KEEP_TEMP_ON_ERROR:
                print("")
                print("Temporary files kept for debugging:")
                print("  " + temp_root)
            else:
                shutil.rmtree(temp_root, ignore_errors=True)

            Glyphs.showNotification("fontmake export failed", "See Macro Window.")

    except Exception:
        show_header("Script error")
        print(traceback.format_exc())

        if KEEP_TEMP_ON_ERROR:
            print("")
            print("Temporary files kept for debugging:")
            print("  " + temp_root)
        else:
            shutil.rmtree(temp_root, ignore_errors=True)

        Glyphs.showNotification("fontmake script error", "See Macro Window.")


main()