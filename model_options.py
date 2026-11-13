"""Shared base geometry and deterministic paint aging for export and preview."""
import math,re
import numpy as np
from PIL import Image, ImageFilter
import mesh

BASE_STYLES=('strip','none','wall')

def options(base_style='strip',weathering=0):
    if base_style not in BASE_STYLES:raise ValueError('Unknown base style.')
    age=float(weathering)
    if not math.isfinite(age) or not 0<=age<=100:raise ValueError('Weathering must be 0–100.')
    return base_style,age

def geometry(letters,width,height,depth,base_style='strip'):
    options(base_style)
    base_depth=max(5.,depth+2.)
    if base_style=='none':
        return [],[([(x,y-1.2,z) for x,y,z in pts],n) for pts,n in letters],base_depth
    if base_style=='wall':
        height=max(y for pts,n in letters for x,y,z in pts)-1.2
        # The normal front of the game model faces negative Z.
        base=mesh.box((-width/2-1,0,depth/2+.05),(width/2+1,height+1.8,depth/2+1.25))
        base+=mesh.box((-width/2-1.25,0,-base_depth/2),(width/2+1.25,.4,base_depth/2))
    else:base=mesh.box((-width/2-1,0,-base_depth/2),(width/2+1,1.2,base_depth/2))
    return base,letters,base_depth

def write_geometry(path,base,letters):
    if (len(base)+len(letters))*3>=65536:raise ValueError('Model exceeds 65,535 vertices.')
    node=mesh.node('SloganBase',base,0,letters) if base else mesh.node('SloganBase',letters,1)
    mesh.write_model(path,[node])

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

def write_materials(folder,color,weathering):
    _,age=options(weathering=weathering)
    paint(color,age).save(folder/'red.dds')
    if age:paint('#b9b7ac',age,True).save(folder/'concrete.dds')
    mtl=(folder/'model.mtl').read_text()
    spec=.15-(age/100)*.12
    (folder/'model.mtl').write_text(mtl.replace('$SPECULARCOLOR 0.15 0.15 0.15 1',f'$SPECULARCOLOR {spec:.3f} {spec:.3f} {spec:.3f} 1'))
