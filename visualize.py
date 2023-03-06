import FreeCAD, Draft, Arch, importOBJ, FreeCADGui

doc = FreeCAD.ActiveDocument

for obj in doc.Objects:
    if obj.Label.startswith("mywindow"):
        obj.ViewObject.Transparency = 80
        obj.ViewObject.ShapeColor = (0.0, 0.0, 1.0)
    elif obj.Label.startswith("mywall"):
        obj.ViewObject.DisplayMode = "Shaded"

FreeCADGui.SendMsgToActiveView("ViewFit")
