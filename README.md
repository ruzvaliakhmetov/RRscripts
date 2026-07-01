# RR Scripts

Small Python scripts for [Glyphs 3](https://glyphsapp.com/) and type design workflows.

This repository is a personal collection of small utilities, experiments and helper scripts that automate repetitive tasks in Glyphs. Most scripts were made for practical use while working on fonts, outlines, spacing, SVG export and variable font testing.

The scripts are provided as-is. Some of them are polished enough for regular use, while others are experimental and may need small adjustments for a specific workflow.

## Scripts

| Script                                               | Description                                                                                                                                       |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| `add_glyphs.py`                                      | Creates new glyphs from pasted text lines. Each non-empty line becomes a separate glyph name.                                                     |
| `clear_selected.py`                                  | Clears the contents of selected glyphs on all layers while preserving their advance widths.                                                       |
| `expand_outlines_for_selected_glyphs_master.py`      | Expands outlines for selected glyphs in the current master only.                                                                                  |
| `expand_outlines_for_selected_glyphs_all_masters.py` | Expands outlines for selected glyphs across all masters.                                                                                          |
| `export_SVG.py`                                      | Exports selected glyphs as SVG files with a 1000 × 1000 px artboard and selectable stroke line join / line cap settings.                          |
| `export_variable_ttf_via_makefont.py`                | Exports a variable TTF through `fontmake` instead of the native Glyphs export. Useful for testing fontmake output and getting clearer error logs. |
| `font_info.py`                                       | Fills selected Font Info fields with placeholder values and enables the `Use Typo Metrics` custom parameter.                                      |
| `insert_spaces.py`                                   | Creates or updates common space glyphs and assigns their widths across masters.                                                                   |
| `move_selected.py`                                   | Moves selected glyphs, or all glyphs in the current master, by a specified X/Y offset.                                                            |
| `move_to_background.py`                              | Moves all foreground shapes and hints to the background layer.                                                                                    |
| `scale_intersect.py`                                 | Scales paths that intersect with shapes in the background layer.                                                                                  |
| `script_export_native.py`                            | Exports selected scripts through the native Glyphs export. Checked scripts are kept; all other scripts are added to `Remove Glyphs`.              |
| `script_export_via_makefont.py`                      | Exports selected scripts through `fontmake`. Useful for script-specific OTF/TTF exports and clearer build logs outside the native Glyphs export.   |


## Requirements

The fontmake-based export scripts additionally require `fontmake` to be installed and available on your system.

For example, using `pipx`:

```bash
pipx install fontmake
```

If Glyphs cannot find `fontmake`, the script checks common install locations such as:

```text
~/.local/bin/fontmake
/opt/homebrew/bin/fontmake
/usr/local/bin/fontmake
```

## Notes

These scripts are primarily made for my own type design practice. They may assume a specific workflow, file structure or naming convention.

Before running scripts that modify many glyphs or layers, it is recommended to save a copy of your Glyphs file.

## AI-assisted development

Many scripts in this repository were created, modified or debugged with the help of AI tools, including ChatGPT and similar systems.

The scripts are still reviewed and tested manually for my own workflow, but they should be treated as practical utilities rather than polished software products.

## License

This project is licensed under the MIT License.

You are free to use, copy, modify, merge, publish, distribute, sublicense and/or sell copies of the scripts, as long as the original license notice is included.

See the [LICENSE](LICENSE) file for details.

