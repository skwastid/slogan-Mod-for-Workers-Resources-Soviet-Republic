"""Install only newly generated local projects, without overwriting user mods."""
from pathlib import Path
import os,re,json,shutil,uuid,hashlib

def valid_game(path):
    p=Path(path)
    return (p/'media_soviet').is_dir() and any((p/n).is_file() for n in ['SOVIET.exe','SOVIET64.exe','SovietRepublic.exe'])

def detect_game():
    candidates=[Path('D:/App/steam/steamapps/common/SovietRepublic')]
    steam=[]
    try:
        import winreg
        for hive,key,value in [(winreg.HKEY_CURRENT_USER,r'Software\Valve\Steam','SteamPath'),(winreg.HKEY_LOCAL_MACHINE,r'SOFTWARE\WOW6432Node\Valve\Steam','InstallPath')]:
            try:
                with winreg.OpenKey(hive,key) as k:steam.append(Path(winreg.QueryValueEx(k,value)[0]))
            except OSError:pass
    except ImportError:pass
    for key in ['ProgramFiles(x86)','ProgramFiles']:
        if os.environ.get(key):steam.append(Path(os.environ[key])/'Steam')
    for location in steam:
        libraries=[location];vdf=location/'steamapps/libraryfolders.vdf'
        if vdf.is_file():
            for raw in re.findall(r'"path"\s+"([^"]+)"',vdf.read_text(encoding='utf8',errors='replace')):libraries.append(Path(raw.replace('\\\\','\\')))
        candidates.extend(p/'steamapps/common/SovietRepublic' for p in libraries)
    return next((str(p) for p in candidates if valid_game(p)),'')

def install(project,game):
    project=Path(project).resolve();game=Path(game).resolve()
    if not valid_game(game):raise ValueError('Select the SovietRepublic game folder containing SOVIET64.exe and media_soviet.')
    if not re.fullmatch(r'8\d{11}',project.name):raise ValueError('Only local generated project IDs can be installed.')
    meta=json.loads((project/'generation.json').read_text(encoding='utf8'))
    if meta.get('local_only') is not True:raise ValueError('Not a locally generated building.')
    cfg=(project/'workshopconfig.ini').read_text(encoding='utf8')
    if f'$ITEM_ID {project.name}' not in cfg or '$OBJECT_BUILDING slogan' not in cfg:raise ValueError('Invalid building configuration.')
    for name in ['slogan/model.nmf','slogan/model.mtl','slogan/building.ini','slogan/renderconfig.ini']:
        if not (project/name).is_file():raise ValueError('Incomplete generated project: '+name)
    files=list(project.rglob('*'))
    if any(p.is_symlink() for p in files):raise ValueError('Symbolic links are not allowed in generated projects.')
    parent=game/'media_soviet/workshop_wip';parent.mkdir(parents=True,exist_ok=True)
    if parent.resolve()!=parent:raise ValueError('The local Workshop path must not redirect to another location.')
    dest=parent/project.name
    if dest.exists():raise FileExistsError('Already installed. Existing buildings are never overwritten.')
    staging=parent/('.slogan-import-'+uuid.uuid4().hex)
    try:
        shutil.copytree(project,staging)
        for file in files:
            if file.is_file():
                copied=staging/file.relative_to(project)
                if hashlib.sha256(file.read_bytes()).digest()!=hashlib.sha256(copied.read_bytes()).digest():raise IOError('Copy verification failed.')
        staging.rename(dest)
    finally:
        if staging.exists() and staging.parent.resolve()==parent:shutil.rmtree(staging)
    return dest
