"""Shared base geometry and deterministic paint aging for export and preview."""
import math,re
import numpy as np
from PIL import Image, ImageFilter
import mesh

BASE_STYLES=('strip','none','wall','stone')

def options(base_style='strip',weathering=0):
    if base_style not in BASE_STYLES:raise ValueError('Unknown base style.')
    age=float(weathering)
    if not math.isfinite(age) or not 0<=age<=100:raise ValueError('Weathering must be 0–100.')
    return base_style,age

def base_options(value=None):
    value=value or {}
    result={k:float(value.get(k,0) or 0) for k in ('length','depth','height','wall_height','wall_thickness','top_width','top_depth')}
    if any(not math.isfinite(v) or v<0 or v>500 or (0<v<.1) for v in result.values()):
        raise ValueError('Base dimensions: 0 = automatic; 0.1–500 m.')
    return result


def geometry(letters,width,height,depth,base_style='strip',base_size=None,supports=False):
    options(base_style);size=base_options(base_size)
    if base_style=='stone':return stone_geometry(letters,size)
    base_depth=size['depth'] or max(5.,depth+2.)
    if supports and base_style!='wall' and not size['depth']:
        top=max(y for pts,n in letters for x,y,z in pts)-1.2
        base_depth=max(base_depth,2*(depth/2+max(1.,min(12.,top*.45))+.5))
    if base_style=='none':
        shifted=[([(x,y-1.2,z) for x,y,z in pts],n) for pts,n in letters]
        return [],add_supports(shifted,0,base_depth/2-.3) if supports else shifted,base_depth
    length=size['length'] or width+2
    plinth=size['height'] or (.4 if base_style=='wall' else 1.2)
    offset=plinth-(.4 if base_style=='wall' else 1.2)
    letters=[([(x,y+offset,z) for x,y,z in pts],n) for pts,n in letters]
    if base_style=='wall':
        thickness=size['wall_thickness'] or 1.2
        wall_center=depth/2+.05+thickness/2
        base_depth=size['depth'] or max(5.,thickness+2*depth+1)
        foot_length=size['length'] or width+2.5
        length=max(.1,foot_length-.5)
        top=size['wall_height'] or max(y for pts,n in letters for x,y,z in pts)+.6-plinth
        base=mesh.box((-length/2,plinth,depth/2+.05),(length/2,plinth+top,depth/2+.05+thickness))
        base+=mesh.box((-foot_length/2,0,wall_center-base_depth/2),(foot_length/2,plinth,wall_center+base_depth/2))
    else:base=mesh.box((-length/2,0,-base_depth/2),(length/2,plinth,base_depth/2))
    if supports:letters=add_supports(letters,plinth,base_depth/2-.3)
    if base_style=='wall':
        def centered(tris):return [([(x,y,z-wall_center) for x,y,z in pts],n) for pts,n in tris]
        base=centered(base);letters=centered(letters)
    return base,letters,base_depth

def stone_geometry(letters,size):
    from shapely.geometry import Polygon
    from shapely.ops import unary_union
    from shapely import constrained_delaunay_triangles
    source=np.array([pts for pts,n in letters]);lo=source.min(axis=(0,1));hi=source.max(axis=(0,1))
    w,h=hi[0]-lo[0],hi[1]-lo[1]
    height=size['height'] or h+2
    length=size['length'] or (w+2)/.9
    top_width=size['top_width'] or length*.9
    depth=size['depth'] or 2.
    top_depth=size['top_depth'] or depth
    slope=(depth-top_depth)/(2*height)
    front_normal=np.array([0.,slope,-1.]);front_normal/=np.linalg.norm(front_normal)
    front_normal=tuple(front_normal)
    narrow=min(length,top_width)
    margin=min(.7,height*.12,narrow*.05)
    scale=min((narrow-2*margin)/max(w,1e-6),(height-2*margin)/max(h,1e-6))
    center=(lo+hi)/2
    flat=[]
    for pts,n in letters:
        if n==(0,0,-1):
            flat.append(([(float((x-center[0])*scale),float((y-center[1])*scale+height/2),-depth/2) for x,y,z in pts],(0,0,-1)))
    # A single coplanar stone/paint surface: cut the lettering out of the stone
    # face, then fill those regions with the letter material. No offset or sides.
    outline=Polygon([(-length/2,0),(length/2,0),(top_width/2,height),(-top_width/2,height)])
    ink=unary_union([Polygon([(x,y) for x,y,z in pts]) for pts,n in flat])
    face=outline.difference(ink)
    base=[]
    for tri in constrained_delaunay_triangles(face).geoms:
        base.append(([(x,y,-depth/2) for x,y in list(tri.exterior.coords)[:3]],(0,0,-1)))
    for pts,n in mesh.box((-length/2,0,-depth/2),(length/2,height,depth/2))[2:]:
        pts=[(x*(1+(top_width/length-1)*y/height),y,z*(1+(top_depth/depth-1)*y/height)) for x,y,z in pts]
        normal=np.cross(np.array(pts[1])-pts[0],np.array(pts[2])-pts[0]);normal/=np.linalg.norm(normal)
        if np.dot(normal,n)<0:normal=-normal
        base.append((pts,tuple(normal)))
    def on_front(tris):
        return [([(x,y,-depth/2+slope*y) for x,y,z in pts],front_normal if n==(0,0,-1) else n) if n==(0,0,-1) else (pts,n) for pts,n in tris]
    return on_front(base),on_front(flat),max(depth,top_depth)


def stone_texture(age=0,color=None,size=256):
    options(weathering=age)
    color=color or '#bdb4a3'
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('Color must be #RRGGBB.')
    rng=np.random.default_rng(187)
    rgb=np.array(tuple(bytes.fromhex(color[1:])),float)
    speckle=rng.normal(0,7,(size,size,1))
    grains=rng.random((size,size,1))
    pixels=rgb+speckle-np.where(grains<.08,24,0)
    pixels-=float(age)*.3
    return Image.fromarray(np.uint8(np.clip(pixels,0,255))).convert('RGBA')


def steel_beam(start,end,thickness):
    start=np.asarray(start,float);axis=np.asarray(end,float)-start
    length=np.linalg.norm(axis)
    if length<1e-8:return []
    axis/=length
    u=np.array([1.,0,0]) if abs(axis[0])<.9 else np.array([0.,0,1.])
    u-=axis*np.dot(u,axis);u/=np.linalg.norm(u);v=np.cross(axis,u)
    basis=np.column_stack((u,v,axis))
    return [([tuple(start+basis@np.array(p)) for p in pts],tuple(basis@np.array(n)))
            for pts,n in mesh.box((-thickness/2,-thickness/2,0),(thickness/2,thickness/2,length))]


def add_supports(letters,ground,rear_limit=None):
    # Regular sign frame: uniform posts, three level rails, identical rear braces.
    points=np.array([pts for pts,n in letters]);lo=points.min(axis=(0,1));hi=points.max(axis=(0,1))
    x0,y0,_=lo;x1,y1,back=hi;h=y1-y0
    beam=max(.10,min(.4,h*.035));z=back+beam/2-.02
    margin=min((x1-x0)*.12,beam*1.5)
    count=max(2,min(60,math.ceil((x1-x0)/max(1.,h*.65))+1))
    columns=np.linspace(x0+margin,x1-margin,count)
    top=y1+beam*.25;rail_levels=[y0+h*f for f in (.18,.50,.82)]
    rear=back+max(1.,min(12.,h*.45))
    if rear_limit is not None:rear=max(z+beam,rear_limit-beam)
    result=list(letters)
    for x in columns:
        result+=steel_beam((x,ground,z),(x,top,z),beam)
        result+=steel_beam((x,ground+beam*.5,rear),(x,rail_levels[-1],z),beam)
        for foot_z in (z,rear):
            result+=mesh.box((x-beam,ground,foot_z-beam),(x+beam,ground+beam*.2,foot_z+beam))
    for y in rail_levels:
        result+=steel_beam((x0,y,z),(x1,y,z),beam)
    return result


def write_geometry(path,base,letters,letter_count=None):
    if (len(base)+len(letters))*3>=65536:raise ValueError('Model exceeds 65,535 vertices.')
    supports=letters[letter_count:] if letter_count is not None else []
    letters=letters[:letter_count] if letter_count is not None else letters
    node=mesh.node('SloganBase',base,0,letters) if base else mesh.node('SloganBase',letters,1)
    if supports:mesh.write_model(path,[node,mesh.node('SloganSupports',supports,2)],('concrete','red','iron'))
    else:mesh.write_model(path,[node])

def paint(color,age=0,concrete=False,size=256):
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('Color must be #RRGGBB.')
    _,age=options(weathering=age);amount=age/100
    rgb=np.array(tuple(bytes.fromhex(color[1:])),float)
    if not amount:return Image.new('RGBA',(size,size),color)
    rng=np.random.default_rng(55 if concrete else 42)
    def field(grid):
        im=Image.fromarray(rng.integers(0,256,(grid,grid),dtype=np.uint8)).resize((size,size),Image.Resampling.BICUBIC).filter(ImageFilter.GaussianBlur(.6))
        a=np.asarray(im,float);return (a-a.mean())/(a.std()+1e-6)
    coarse=field(14);fine=field(90);damage=field(45)+coarse*.3
    faded=rgb*(1-.3*amount)+np.array([173,149,119])*.3*amount
    result=np.broadcast_to(faded,(size,size,3)).copy()
    result+=coarse[:,:,None]*(3+amount*9)+fine[:,:,None]*2
    if concrete:
        result-=amount*23+np.maximum(coarse,0)[:,:,None]*amount*17
    else:
        limit=2.7-amount*1.8;rust=damage>limit-.2;chip=damage>limit
        result[rust]=np.array([107,61,35])+fine[rust,None]*6
        result[chip]=np.array([57,53,47])+fine[chip,None]*4
    return Image.fromarray(np.uint8(np.clip(result,0,255))).convert('RGBA')

def iron_texture(age=0,size=256):
    _,age=options(weathering=age);amount=age/100
    if not amount:return Image.new('RGBA',(size,size),'#596168')
    rng=np.random.default_rng(73)
    noise=Image.fromarray(rng.integers(0,256,(32,32),dtype=np.uint8)).resize((size,size),Image.Resampling.BICUBIC)
    field=np.asarray(noise,float);field=(field-field.mean())/(field.std()+1e-6)
    fine=rng.normal(0,1,(size,size))
    metal=np.array([89,97,104])*(1-.18*amount)+fine[:,:,None]*2
    oxide=np.array([123,64,31])+field[:,:,None]*10+fine[:,:,None]*5
    coverage=np.clip((field-(2.7-amount*4))*3,0,1)*min(1,amount*4)
    pixels=metal*(1-coverage[:,:,None])+oxide*coverage[:,:,None]
    return Image.fromarray(np.uint8(np.clip(pixels,0,255))).convert('RGBA')


def write_materials(folder,color,weathering,base_color=None,supports=False,base_style='strip'):
    _,age=options(weathering=weathering)
    paint(color,age).save(folder/'red.dds')
    if base_style=='stone':stone_texture(age,base_color).save(folder/'concrete.dds')
    elif age or base_color:paint(base_color or '#b9b7ac',age,True).save(folder/'concrete.dds')
    mtl=(folder/'model.mtl').read_text()
    if supports:
        iron_texture(age).save(folder/'iron.dds')
        iron_spec=.28-(age/100)*.24
        block=f'$SUBMATERIAL iron\n$TEXTURE_MTL 0 iron.dds\n$TEXTURE_MTL 1 blankspecular.dds\n$TEXTURE_MTL 2 blankbump.dds\n$DIFFUSECOLOR 1 1 1 1\n$AMBIENTCOLOR 1 1 1 1\n$SPECULARCOLOR {iron_spec:.3f} {iron_spec:.3f} {iron_spec:.3f} 1\n$SPECULARPOWER 8\n'
        mtl=mtl.replace('$END',block+'$END')
    spec=.15-(age/100)*.12
    (folder/'model.mtl').write_text(mtl.replace('$SPECULARCOLOR 0.15 0.15 0.15 1',f'$SPECULARCOLOR {spec:.3f} {spec:.3f} {spec:.3f} 1'))
