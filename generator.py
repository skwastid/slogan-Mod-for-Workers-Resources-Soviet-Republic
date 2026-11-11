"""Local font -> fixed 3D slogan monument. No font files are exported."""
from pathlib import Path
import json, shutil, tempfile, uuid, math, re, unicodedata
from fontTools.ttLib import TTFont
from PIL import Image, ImageDraw, ImageFont
import mesh

def generate(text, font, output, height=9., thickness=1., stroke=0., color='#be0f0c'):
    text=unicodedata.normalize('NFC',text.strip())
    if not text or len(text)>40 or any((c.isspace() and c!=' ') or ord(c)<32 for c in text):
        raise ValueError('TEXT: Enter 1–40 characters on one line.')
    if not all(math.isfinite(v) for v in (height,thickness,stroke)) or not (1<=height<=30 and .1<=thickness<=5 and 0<=stroke<=.3):
        raise ValueError('RANGE: Height 1–30m; depth 0.1–5m; weight 0–0.3.')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',color): raise ValueError('COLOR: #RRGGBB')
    font=Path(font).resolve()
    with TTFont(str(font),fontNumber=0) as ft:
        cmap=ft.getBestCmap() or {}
        missing=sorted(set(c for c in text if ord(c) not in cmap))
        if missing: raise ValueError('FONT: '+''.join(missing))
    output=Path(output).resolve();output.mkdir(parents=True,exist_ok=True)
    # Numeric IDs here are local placeholders, never valid Workshop upload IDs.
    ident=str(800000000000+uuid.uuid4().int%100000000000)
    dest=output/ident
    if dest.exists(): raise FileExistsError(dest)
    with tempfile.TemporaryDirectory(prefix='slogan_') as tmp:
        root=Path(tmp)/ident;d=root/'slogan';d.mkdir(parents=True)
        letters,width=mesh.glyph_nodes(text,height,stroke,str(font),thickness)
        if (len(letters)+12)*3>=65536:
            raise ValueError('COMPLEX: Reduce text length or choose a simpler font.')
        depth=max(5.,thickness+2.)
        base=mesh.box((-width/2-1,0,-depth/2),(width/2+1,1.2,depth/2))
        mesh.write_model(d/'model.nmf',[mesh.node('SloganBase',base,0,letters)])
        for name in ['model.mtl','concrete.dds','blankspecular.dds','blankbump.dds','renderconfig.ini']:
            shutil.copy2(mesh.ASSETS/name,d/name)
        Image.new('RGBA',(4,4),color).save(d/'red.dds')
        ini=f'''$NAME_STR "Custom Slogan {ident[-6:]}"
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
        im=Image.new('RGB',(512,512),(235,231,218));draw=ImageDraw.Draw(im)
        f=ImageFont.truetype(str(font),64,index=0)
        box=draw.textbbox((0,0),text,font=f);scale=min(1,460/max(1,box[2]-box[0]))
        f=ImageFont.truetype(str(font),max(6,int(64*scale)),index=0)
        draw.text((256,220),text,font=f,fill=color,anchor='mm')
        draw.rectangle((24,290,488,320),fill=(170,170,165))
        draw.text((30,360),f'{height:g}m / {thickness:g}m',fill=(50,50,50))
        im.save(root/'previewimage.png');im.resize((256,256)).save(d/'imagegui.png')
        (root/'workshopconfig.ini').write_text(f'''$ITEM_ID {ident}
$OWNER_ID 0
$ITEM_TYPE WORKSHOP_ITEMTYPE_BUILDING
$VISIBILITY 2
$OBJECT_BUILDING slogan
$ITEM_NAME "Custom Slogan {ident[-6:]}"
$ITEM_DESC "Locally generated fixed 3D text monument."
$END
''',encoding='ascii')
        (root/'generation.json').write_text(json.dumps(dict(text=text,font=font.name,height=height,thickness=thickness,stroke=stroke,color=color,vertices=(len(letters)+12)*3,local_only=True),ensure_ascii=False,indent=2),encoding='utf8')
        shutil.copytree(root,dest)
    return dest
