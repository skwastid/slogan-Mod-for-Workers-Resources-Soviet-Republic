"""Local font -> fixed 3D slogan monument. No font files are exported."""
from pathlib import Path
import json, shutil, tempfile, uuid, math, re, unicodedata
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
import mesh
import model_options, typography, export_helpers

def generate(text, font, output, height=9., thickness=1., stroke=0., color='#be0f0c',base_style='strip',weathering=0,building_name='',direction='horizontal',line_spacing=1.3,base_size=None,base_color=None,supports=False):
    base_style,weathering=model_options.options(base_style,weathering)
    base_size=model_options.base_options(base_size)
    supports=bool(supports) and base_style!='stone'
    text=typography.normalize(text)
    building_name=export_helpers.name(building_name)
    if not all(math.isfinite(v) for v in (height,thickness,stroke)) or not (1<=height<=30 and .1<=thickness<=5 and 0<=stroke<=.3):
        raise ValueError('RANGE: Height 1–30m; depth 0.1–5m; weight 0–0.3.')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',color): raise ValueError('COLOR: #RRGGBB')
    font=Path(font).resolve()
    with TTFont(str(font),fontNumber=0) as ft:
        cmap=ft.getBestCmap() or {}
        missing=sorted(set(c for c in text if not c.isspace() and ord(c) not in cmap))
        if missing: raise ValueError('FONT: '+''.join(missing))
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    # Numeric IDs here are local placeholders, never valid Workshop upload IDs.
    ident=str(800000000000+uuid.uuid4().int%100000000000)
    dest=output/ident
    if dest.exists(): raise FileExistsError(dest)
    with tempfile.TemporaryDirectory(prefix='slogan_') as tmp:
        root=Path(tmp)/ident;d=root/'slogan';d.mkdir(parents=True)
        letters,width=typography.glyph_mesh(text,str(font),height,thickness,stroke,direction,line_spacing)
        raw_letters=letters
        if (len(letters)+12)*3>=65536:
            raise ValueError('COMPLEX: Reduce text length or choose a simpler font.')
        depth=max(5.,thickness+2.)
        base,letters,depth=model_options.geometry(letters,width,height,thickness,base_style,base_size,supports)
        model_options.write_geometry(d/'model.nmf',base,letters,len(raw_letters))
        for name in ['model.mtl','concrete.dds','blankspecular.dds','blankbump.dds','renderconfig.ini']:
            shutil.copy2(mesh.ASSETS/name,d/name)
        model_options.write_materials(d,color,weathering,base_color,supports,base_style)
        ini=f'''$NAME_STR "{building_name or 'Custom Slogan '+ident[-6:]}"
$TYPE_MONUMENT
$MONUMENT_GOVERNMENT_LOYALTY_RADIUS 150
$MONUMENT_GOVERNMENT_LOYALTY_STRENGTH 1.0
$COST_WORK SOVIET_CONSTRUCTION_GROUNDWORKS 1.0
$COST_WORK_BUILDING_NODE SloganBase
$COST_WORK_VEHICLE_STATION_ACCORDING_NODE SloganBase
$COST_RESOURCE_AUTO ground_asphalt 1.0
$COST_WORK SOVIET_CONSTRUCTION_SKELETON_CASTING 1.0
$COST_WORK_BUILDING_KEYWORD $Slogan
$COST_RESOURCE_AUTO wall_concrete 0.8
$CONNECTION_PEDESTRIAN
0 0 {depth/2+2}
0 0 {depth/2}
end
'''
        (d/'building.ini').write_text(ini,encoding='utf8')
        export_helpers.thumbnail(root,raw_letters,width,height,thickness,base_style,color,weathering,base_size,base_color,supports)
        (root/'workshopconfig.ini').write_text(f'''$ITEM_ID {ident}
$OWNER_ID 0
$ITEM_TYPE WORKSHOP_ITEMTYPE_BUILDING
$VISIBILITY 2
$OBJECT_BUILDING slogan
$ITEM_NAME "{building_name or 'Custom Slogan '+ident[-6:]}"
$ITEM_DESC "Locally generated fixed 3D text monument."
$END
''',encoding='utf8')
        (root/'generation.json').write_text(json.dumps(dict(building_name=building_name,direction=direction,line_spacing=line_spacing,text=text,font=font.name,height=height,thickness=thickness,stroke=stroke,color=color,vertices=(len(letters)+len(base))*3,base_style=base_style,weathering=weathering,base_size=base_size,base_color=base_color,supports=bool(supports),local_only=True),ensure_ascii=False,indent=2),encoding='utf8')
        shutil.copytree(root,dest)
    return dest
