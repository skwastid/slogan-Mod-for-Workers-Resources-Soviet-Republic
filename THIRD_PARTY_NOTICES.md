# Third-party materials

- Python dependencies retain their respective licenses: NumPy, Pillow, Matplotlib, Shapely/GEOS, FontTools, Tk/Tcl and their dependencies. PyInstaller uses its own license and bootloader exception.
- `assets/*.dds` are game-owned textures imported from a locally installed copy of Workers & Resources: Soviet Republic. They are excluded from this Git repository. They are not relicensed by this project.
- `assets/template.nmf` is the project's small base-mesh template. The exporter reuses its static NMF node header to maintain game compatibility; generated geometry replaces the template geometry.
- No system font files are distributed. Generated models contain glyph outlines; public distribution of those models must comply with the selected font's license.
- A project-wide open-source license has not yet been selected. Public availability alone does not grant unrestricted redistribution rights.
