# Build on 64-bit Windows from the repository root.
from pathlib import Path
from PyInstaller.utils.hooks import collect_all
root=Path(SPECPATH)
for name in ('concrete.dds','blankspecular.dds','blankbump.dds'):
    if not (root/'assets'/name).is_file():
        raise SystemExit('First run tools/import_game_assets.py with your game directory.')
datas,binaries,hiddenimports=collect_all('shapely')
datas.append((str(root/'assets'),'assets'))
a=Analysis([str(root/'app.py')],pathex=[str(root)],binaries=binaries,datas=datas,
 hiddenimports=hiddenimports,hookspath=[],hooksconfig={'matplotlib':{'backends':['Agg']}},runtime_hooks=[],
 excludes=['PyQt5','PyQt6','PySide6','scipy','pandas','IPython','torch','tensorflow'],noarchive=False)
pyz=PYZ(a.pure)
exe=EXE(pyz,a.scripts,[],exclude_binaries=True,name='SloganGenerator',debug=False,
 bootloader_ignore_signals=False,strip=False,upx=False,console=False)
coll=COLLECT(exe,a.binaries,a.datas,strip=False,upx=False,name='SloganGenerator')
