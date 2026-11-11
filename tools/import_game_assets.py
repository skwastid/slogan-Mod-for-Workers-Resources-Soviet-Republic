"""Copy required textures from the user's own installed game."""
from pathlib import Path
import argparse,shutil
p=argparse.ArgumentParser();p.add_argument('game_directory',type=Path);a=p.parse_args()
media=a.game_directory/'media_soviet'
assets=Path(__file__).resolve().parents[1]/'assets'
sources={'concrete.dds':media/'buildings/monument_conrete.dds','blankspecular.dds':media/'blankspecular.dds','blankbump.dds':media/'blankbump.dds'}
missing=[str(x) for x in sources.values() if not x.is_file()]
if missing:p.error('Missing game assets: '+', '.join(missing))
for name,source in sources.items():shutil.copy2(source,assets/name)
print('Imported 3 textures. They are ignored by Git.')
