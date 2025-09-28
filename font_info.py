#MenuTitle: Fill Font info
# -*- coding: utf-8 -*-
__doc__ = "Fills the selected Font Info fields with unique values and enables the “Use Typo Metrics” parameter."

from GlyphsApp import Glyphs
import datetime

font = Glyphs.font
if not font:
    print("⚠️ No active font. Open the file and run the script again.")
else:
    # Placeholders that you can change yourself
    placeholders = {
        "designer": "Ruz Valiakhmetov",
        "designerURL": "https://www.valiakhmetov.com",
        "copyright": "Copyright (c) 2025 Ruz Valiakhmetov",
        "sampleText": "The quick brown fox jumps over the lazy dog",
        "license": "License here",
        "description": "Description here",
    }

    # Make values unique between runs (adds a suffix over time)
    add_timestamp_suffix = False  # ← switch to True, if needed
    suffix = (" · " + datetime.datetime.now().strftime("%Y%m%d%H%M%S")) if add_timestamp_suffix else ""

    font.disableUpdateInterface()
    try:
        # Font Info → Font
        font.designer = placeholders["designer"] + suffix
        font.designerURL = placeholders["designerURL"] + suffix
        font.copyright = placeholders["copyright"] + suffix
        font.sampleText = placeholders["sampleText"] + suffix
        font.license = placeholders["license"] + suffix
        font.description = placeholders["description"] + suffix

        # Custom Parameters на уровне шрифта
        font.customParameters["Use Typo Metrics"] = True

        print("✅ Done: data added, “Use Typo Metrics” enabled.")
    except Exception as e:
        print("❌ Error:", e)
    finally:
        font.enableUpdateInterface()
