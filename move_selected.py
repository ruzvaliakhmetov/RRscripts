# MenuTitle: Move glyphs...
import vanilla
import GlyphsApp

class ShiftGlyphsWindow:
    def __init__(self):
        self.w = vanilla.FloatingWindow((220, 210), "Glyph shift")

        self.w.textX = vanilla.TextBox((15, 15, -15, 20), "X shift:")
        self.w.inputX = vanilla.EditText((15, 35, -15, 24), "0")

        self.w.textY = vanilla.TextBox((15, 70, -15, 20), "Y shift:")
        self.w.inputY = vanilla.EditText((15, 90, -15, 24), "0")

        self.w.onlySelected = vanilla.CheckBox((15, 125, -15, 20), "Selected glyphs only", value=True)

        self.w.shiftButton = vanilla.Button((15, 155, -15, 30), "Move", callback=self.shiftGlyphs)

        self.updateCheckboxState()
        self.w.open()

    def updateCheckboxState(self):
        font = Glyphs.font
        if font and len(font.selectedLayers) == 1 and font.currentTab:  
            # Если открыт один глиф
            self.w.onlySelected.set(True)
            self.w.onlySelected.enable(False)  # Блокируем галочку
        else:
            self.w.onlySelected.enable(True)

    def shiftGlyphs(self, sender):
        try:
            xShift = float(self.w.inputX.get())
            yShift = float(self.w.inputY.get())
        except ValueError:
            Message("Error", "Please enter numeric values.")
            return

        font = Glyphs.font
        masterID = font.selectedFontMaster.id
        onlySelected = self.w.onlySelected.get()

        # Определяем список слоев
        if onlySelected:
            layers = font.selectedLayers
        else:
            layers = [glyph.layers[masterID] for glyph in font.glyphs]

        font.disableUpdateInterface()
        for layer in layers:
            if layer and layer.isMasterLayer:
                layer.applyTransform((1, 0, 0, 1, xShift, yShift))
        font.enableUpdateInterface()

        Glyphs.showNotification(
            "Shift applied",
            f"{ 'Selected' if onlySelected else 'All' } glyphs shifted by X: {xShift}, Y: {yShift}"
        )

ShiftGlyphsWindow()
