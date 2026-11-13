import export_helpers
"""Image masks and fixed-mesh export. No OCR, fonts or network required."""
from pathlib import Path
import io, json, math, re, shutil, tempfile, uuid, zipfile
from collections import deque
import numpy as np
from PIL import Image, ImageFilter, ImageDraw
from shapely import unary_union, constrained_delaunay_triangles
from shapely.geometry import box, Point
import mesh
import model_options

MAX_SIZE = (1600, 1000)

def load_image(path):
    with Image.open(path) as im:
        im.load()
        rgba = im.convert('RGBA')
        image = Image.new('RGBA', rgba.size, 'white')
        image.alpha_composite(rgba)
        image = image.convert('RGB')
    image.thumbnail(MAX_SIZE, Image.Resampling.LANCZOS)
    return image

def clean_components(mask, minimum):
    """Eight-neighbour components; preserve holes and disconnected strokes."""
    a = np.asarray(mask).astype(bool).copy()
    if minimum <= 1:
        return Image.fromarray(a.astype('uint8') * 255)
    seen = np.zeros(a.shape, bool)
    h, w = a.shape
    for y, x in zip(*np.nonzero(a)):
        if seen[y, x]: continue
        queue = deque([(int(x), int(y))]); seen[y, x] = True
        component = []
        while queue:
            px, py = queue.popleft(); component.append((px, py))
            for ny in range(max(0, py-1), min(h, py+2)):
                for nx in range(max(0, px-1), min(w, px+2)):
                    if a[ny, nx] and not seen[ny, nx]:
                        seen[ny, nx] = True; queue.append((nx, ny))
        if len(component) < minimum:
            for px, py in component: a[py, px] = False
    return Image.fromarray(a.astype('uint8') * 255)

def extract(image, dark=True, threshold=145, minimum=12, adaptive=False):
    gray = image.convert('L')
    a = np.asarray(gray, dtype=float)
    if adaptive:
        background = np.asarray(gray.filter(ImageFilter.GaussianBlur(12)), dtype=float)
        delta = max(1, threshold / 8)
        selected = a < background-delta if dark else a > background+delta
    else:
        selected = a < threshold if dark else a >= threshold
    return clean_components(Image.fromarray(selected.astype('uint8')*255), minimum)

def rectify(image, points):
    """Perspective homography: ordered top-left, top-right, bottom-right, bottom-left."""
    from shapely.geometry import Polygon
    poly = Polygon(points)
    if len(points) != 4 or not poly.is_valid or poly.area < 16 or not poly.equals(poly.convex_hull):
        raise ValueError('Select four convex corners in order: TL, TR, BR, BL.')
    p = np.asarray(points, float)
    width = int(max(np.linalg.norm(p[1]-p[0]), np.linalg.norm(p[2]-p[3])))
    height = int(max(np.linalg.norm(p[3]-p[0]), np.linalg.norm(p[2]-p[1])))
    width, height = max(2,width), max(2,height)
    dest = [(0,0),(width,0),(width,height),(0,height)]
    rows=[]; values=[]
    for (x,y),(u,v) in zip(dest,p):
        rows.extend([[x,y,1,0,0,0,-u*x,-u*y],[0,0,0,x,y,1,-v*x,-v*y]])
        values.extend([u,v])
    coeff=np.linalg.solve(rows,values)
    return image.transform((width,height),Image.Transform.PERSPECTIVE,coeff,Image.Resampling.BICUBIC)

def polygons(mask, smooth=.8):
    a=np.asarray(mask)>127; h,w=a.shape
    if not a.any(): raise ValueError('Empty mask: extract or paint some lettering first.')
    runs=[]
    for y,row in enumerate(a):
        edges=np.diff(np.r_[False,row,False].astype('int8'))
        for left,right in zip(np.where(edges==1)[0],np.where(edges==-1)[0]):
            runs.append(box(int(left),h-y-1,int(right),h-y))
        if len(runs)>70000: raise ValueError('Image too noisy: erase background or increase noise removal.')
    shape=unary_union(runs).simplify(float(smooth),preserve_topology=True)
    if shape.is_empty or not shape.is_valid: raise ValueError('Invalid outline.')
    return shape

def extrude(shape,height,depth):
    x0,y0,x1,y1=shape.bounds; scale=height/(y1-y0)
    def point(p,z): return (-(p[0]-(x0+x1)/2)*scale,(p[1]-y0)*scale+1.2,z)
    tris=[]
    parts=list(shape.geoms) if hasattr(shape,'geoms') else [shape]
    for part in parts:
        faces=list(constrained_delaunay_triangles(part).geoms)
        if not math.isclose(sum(t.area for t in faces),part.area,rel_tol=1e-7):
            raise ValueError('Triangulation failed to preserve the outline.')
        for face in faces:
            xy=list(face.exterior.coords)[:3]
            for z,n in [(depth/2,(0,0,1)),(-depth/2,(0,0,-1))]:
                tris.append(([point(p,z) for p in xy],n))
        for ring in [part.exterior,*part.interiors]:
            coords=list(ring.coords)
            for a,b in zip(coords,coords[1:]):
                dx,dy=b[0]-a[0],b[1]-a[1]; length=math.hypot(dx,dy)
                if length<1e-9: continue
                n=np.array([dy,-dx])/length; mid=(np.array(a)+np.array(b))/2
                if part.contains(Point(mid+n*.001)): n=-n
                q=[point(a,-depth/2),point(b,-depth/2),point(b,depth/2),point(a,depth/2)]
                normal=(-n[0],n[1],0)
                tris.extend([(q[:3],normal),([q[0],q[2],q[3]],normal)])
        if (len(tris)+12)*3>=65536:
            raise ValueError('Model exceeds 65,535 vertices: simplify, remove noise or split into lines.')
    return tris,(x1-x0)*scale

def complexity(mask,smooth=.8):
    shape=polygons(mask,smooth); tris,width=extrude(shape,9,1)
    parts=list(shape.geoms) if hasattr(shape,'geoms') else [shape]
    return dict(vertices=(len(tris)+12)*3,components=len(parts),holes=sum(len(p.interiors) for p in parts))

def generate_image(mask,output,height=9.,depth=1.,color='#be0f0c',smooth=.8,base_style='strip',weathering=0,building_name=''):
    base_style,weathering=model_options.options(base_style,weathering)
    if not all(math.isfinite(v) for v in (height,depth,smooth)) or not (1<=height<=30 and .1<=depth<=5 and 0<=smooth<=4):
        raise ValueError('Height 1–30m; depth 0.1–5m; smoothing 0–4px.')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',color): raise ValueError('Color must be #RRGGBB.')
    building_name=export_helpers.name(building_name)
    shape=polygons(mask,smooth); letters,width=extrude(shape,height,depth)
    raw_letters=letters
    output=Path(output).resolve(); output.mkdir(parents=True,exist_ok=True)
    ident=str(800000000000+uuid.uuid4().int%100000000000); destination=output/ident
    with tempfile.TemporaryDirectory(prefix='image_slogan_') as tmp:
        root=Path(tmp)/ident; d=root/'slogan'; d.mkdir(parents=True)
        base_depth=max(5.,depth+2)
        base,letters,base_depth=model_options.geometry(letters,width,height,depth,base_style)
        model_options.write_geometry(d/'model.nmf',base,letters)
        for filename in ['model.mtl','concrete.dds','blankspecular.dds','blankbump.dds','renderconfig.ini']:
            shutil.copy2(mesh.ASSETS/filename,d/filename)
        model_options.write_materials(d,color,weathering)
        (d/'building.ini').write_text(f'''$NAME_STR "{building_name or 'Image Slogan '+ident[-6:]}"
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
0 0 {base_depth/2+2}
0 0 {base_depth/2}
end
''',encoding='utf8')
        export_helpers.thumbnail(root,raw_letters,width,height,depth,base_style,color,weathering)
        (root/'workshopconfig.ini').write_text(f'''$ITEM_ID {ident}
$OWNER_ID 0
$ITEM_TYPE WORKSHOP_ITEMTYPE_BUILDING
$VISIBILITY 2
$OBJECT_BUILDING slogan
$ITEM_NAME "{building_name or 'Image Slogan '+ident[-6:]}"
$ITEM_DESC "Locally generated image silhouette. Placeholder ID, not for uploading."
$END
''',encoding='utf8')
        mask.save(root/'source_mask.png')
        (root/'generation.json').write_text(json.dumps(dict(building_name=building_name,mode='image',height=height,depth=depth,color=color,smoothing=smooth,vertices=(len(letters)+len(base))*3,base_style=base_style,weathering=weathering,local_only=True),indent=2))
        shutil.copytree(root,destination)
    return destination

def save_project(path,image,mask,settings):
    import project_store
    project_store.save(path,dict(kind='image',image=image,mask=mask,settings=settings,layout=None,appearance={}))

def load_project(path):
    import project_store
    state=project_store.load(path)
    if state['kind']!='image' or state['image'].size!=state['mask'].size:raise ValueError('Invalid image project.')
    return state['image'],state['mask'],state['settings']


def extract_color(image,selected,tolerance=55,minimum=12):
    """Euclidean RGB distance (0–442). Keep hue and intensity discrimination explicit."""
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',selected):raise ValueError('Pick a color from the source image first.')
    tol=float(tolerance)
    if not math.isfinite(tol) or not 1<=tol<=255:raise ValueError('Color tolerance: 1–255.')
    rgb=np.array(tuple(bytes.fromhex(selected[1:])),dtype=float)
    a=np.asarray(image.convert('RGB'),dtype=float)
    selected_mask=np.sum((a-rgb)**2,axis=2)<=tol**2
    return clean_components(Image.fromarray(selected_mask.astype('uint8')*255),minimum)
