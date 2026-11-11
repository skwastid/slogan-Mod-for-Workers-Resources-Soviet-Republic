# Slogan Mod for Workers & Resources: Soviet Republic

[简体中文](README.md)

Create fixed 3D slogan monuments from fonts installed on your computer.

## Download

Download the Windows x64 portable ZIP from [Releases](https://github.com/skwastid/slogan-Mod-for-Workers-Resources-Soviet-Republic/releases), extract the entire archive, and run `SloganGenerator.exe`. Python is not required. Keep the `_internal` folder next to the executable.

Choose an interface language, enter text, select an installed font, adjust height/depth/color/extra weight, and generate a building. Copy the generated numeric folder to the game's `media_soviet/workshop_wip` folder and restart the game. Find `Custom Slogan` in the mod building menu.

## Features

18 interface languages; installed-font discovery; optional TTF/OTF/TTC import; 1–40 characters including spaces; adjustable 1–30m height and 0.1–5m depth; color and extra weight; live flat font preview; missing-glyph and vertex-limit checks.

Text is embedded in the mesh and cannot be edited with the in-game T_ button. The preview is not an in-game 3D render. TTC uses its first font. Complex script shaping, arbitrary combining marks and color emoji are not supported. Character coverage depends on the selected font.

## Development

Windows x64, Python 3.11+ with tkinter, and an installed copy of the game are required.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python tools/import_game_assets.py "D:\SteamLibrary\steamapps\common\SovietRepublic"
python app.py
```

Replace the example game path. Game textures are imported locally and ignored by Git.

```powershell
python -m pip install -r requirements-build.txt
.\build.ps1
```

Output: `dist/SloganGenerator-v0.3-windows-x64.zip`. Prefer a clean virtual environment for builds. The current Release is the previously validated portable build; this repository organizes its source paths and build/import scripts for development.

## Workshop and licensing

Generated project IDs are local placeholders. Create a real Workshop item through the game before uploading; preserve its ITEM_ID and OWNER_ID. The generator never uploads automatically.

No system fonts are bundled. Check the font license before publicly distributing generated glyph models. See [third-party notices](THIRD_PARTY_NOTICES.md). A project-wide open-source license has not yet been selected.

## Credits

Created with assistance from GPT-6 Astra.
