# MenuTitle: Collect Placed Images
# -*- coding: utf-8 -*-
"""Copy all placed images into an Images folder beside the current .glyphs file.

Images are not relinked or moved. The report counts unique referenced files,
not the number of layers where those files are placed.
"""

import filecmp
import os
import shutil
from urllib.parse import unquote, urlparse

from GlyphsApp import Glyphs


def to_local_path(value, font_folder):
    """Make a stored image path absolute (Glyphs may store relative paths)."""
    if not value:
        return None
    value = str(value)
    if value.startswith("file://"):
        value = unquote(urlparse(value).path)
    value = os.path.expanduser(value)
    if not os.path.isabs(value):
        value = os.path.join(font_folder, value)
    return os.path.normpath(value)


def paths_for_image(image, font_folder):
    """Try the image path first, then the original file URL if available."""
    candidates = []

    try:
        path = to_local_path(image.path, font_folder)
        if path:
            candidates.append(path)
    except Exception:
        pass

    # A stored NSURL can sometimes resolve even when the imagePath is stale.
    try:
        url = image.imageURL
        if callable(url):
            url = url()
        if url:
            path_value = url.path
            if callable(path_value):
                path_value = path_value()
            path = to_local_path(path_value, font_folder)
            if path and path not in candidates:
                candidates.append(path)
    except Exception:
        pass

    return candidates


def placed_images(font):
    """Scan every glyph/layer, including images on the background layer."""
    for glyph in font.glyphs:
        for layer in glyph.layers:
            for place, target_layer in (("layer", layer), ("background", layer.background)):
                if target_layer is None:
                    continue
                image = target_layer.backgroundImage
                if image is not None:
                    yield glyph.name, layer.name, place, image


def main():
    font = Glyphs.font
    if font is None:
        print("No font is open.")
        return

    if not font.filepath:
        Glyphs.showMacroWindow()
        print("Save the .glyphs file first, then run the script again.")
        return

    font_folder = os.path.dirname(os.path.abspath(os.path.expanduser(str(font.filepath))))
    images_folder = os.path.join(font_folder, "Images")

    Glyphs.clearLog()
    Glyphs.showMacroWindow()
    print("Collect Placed Images")
    print("Font: {}".format(font.filepath))
    print("Destination: {}\n".format(images_folder))

    unique = {}
    no_path = []
    placements = 0

    for glyph_name, layer_name, place, image in placed_images(font):
        placements += 1
        location = "{} / {} ({})".format(glyph_name, layer_name, place)
        candidates = paths_for_image(image, font_folder)

        if not candidates:
            no_path.append(location)
            continue

        # Same source referenced by multiple layers must be counted once.
        key = os.path.normcase(os.path.realpath(candidates[0]))
        if key not in unique:
            unique[key] = (candidates, location)

    if not unique and not no_path:
        print("No placed images found.")
        return

    os.makedirs(images_folder, exist_ok=True)

    copied = 0
    already = 0
    missing = len(no_path)
    errors = 0
    collisions = []

    for location in no_path:
        print("MISSING: {} — no image path stored".format(location))

    for candidates, location in unique.values():
        # Prefer an existing source; the stored path can sometimes be outdated.
        source = next((p for p in candidates if os.path.isfile(p)), None)
        reference = candidates[0]
        filename = os.path.basename(source or reference)

        if not filename:
            missing += 1
            print("MISSING: {} — empty filename".format(location))
            continue

        target = os.path.join(images_folder, filename)

        # Existing files are never overwritten (even when the source is missing).
        if os.path.isfile(target):
            already += 1
            print("ALREADY EXISTS: {}".format(filename))
            if source is not None:
                try:
                    if not os.path.samefile(source, target) and not filecmp.cmp(source, target, shallow=False):
                        collisions.append(filename)
                except OSError:
                    pass
            else:
                print("  WARNING: source path not found: {}".format(reference))
            continue

        if os.path.exists(target):
            errors += 1
            print("ERROR: '{}' already exists but is not a file".format(target))
            continue

        if source is None:
            missing += 1
            print("MISSING: {} — {}".format(location, reference))
            continue

        try:
            shutil.copy2(source, target)
            copied += 1
            print("COPIED: {}".format(filename))
        except OSError as error:
            errors += 1
            print("COPY ERROR: {} — {}".format(filename, error))

    print("\n" + "=" * 42)
    print("Image placements in layers: {}".format(placements))
    print("Unique referenced images: {}".format(len(unique) + len(no_path)))
    print("Missing: {}".format(missing))
    print("Copied: {}".format(copied))
    print("Already in Images: {}".format(already))
    if errors:
        print("Copy errors: {}".format(errors))
    if collisions:
        print("\nWARNING: identical filenames but different file contents:")
        for name in sorted(set(collisions)):
            print("  {} (existing file in Images was not overwritten)".format(name))
    print("\nImage paths in the .glyphs file were not changed.")

    Glyphs.showNotification(
        "Collect Placed Images",
        "Copied: {} · Already there: {} · Missing: {}".format(copied, already, missing),
    )


main()
