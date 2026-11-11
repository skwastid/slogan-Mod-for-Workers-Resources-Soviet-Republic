"""Flat preview using the same font outlines and stroke buffer as the mesh."""
from functools import lru_cache
import math, re, unicodedata
from fontTools.ttLib import TTFont
from matplotlib.textpath import TextPath, TextToPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon
from PIL import Image, ImageDraw

@lru_cache(maxsize=32)
def coverage(font):
    with TTFont(font,fontNumber=0) as f:return frozenset((f.getBestCmap() or {}).keys())

@lru_cache(maxsize=16)
def outlines(text,font,stroke):
    prop=FontProperties(fname=font,size=10);metrics=TextToPath();shapes=[]
    for i,ch in enumerate(text):
        if ch==' ':continue
        shape=Polygon()
        for ring in TextPath((0,0),ch,size=10,prop=prop).to_polygons():shape=shape.symmetric_difference(Polygon(ring))
        shape=shape.buffer(stroke,join_style='round',quad_segs=3)
        if shape.is_empty:raise ValueError('FONT: '+ch)
        x=metrics.get_text_width_height_descent(text[:i],prop,False)[0] if i else 0
        shapes.append((shape,x))
    return shapes

def render(text,font,stroke,color,width=880,height=180):
    text=unicodedata.normalize('NFC',text.strip())
    if not text or len(text)>40 or any((c.isspace() and c!=' ') or ord(c)<32 for c in text):raise ValueError('TEXT: 1–40')
    if not math.isfinite(stroke) or not 0<=stroke<=.3:raise ValueError('RANGE: 0–0.3')
    if not re.fullmatch(r'#[0-9a-fA-F]{6}',color):raise ValueError('COLOR: #RRGGBB')
    missing=sorted(set(c for c in text if ord(c) not in coverage(font)))
    if missing:raise ValueError('FONT: '+''.join(missing))
    shapes=outlines(text,font,stroke)
    x0=min(p.bounds[0]+x for p,x in shapes);x1=max(p.bounds[2]+x for p,x in shapes)
    y0=min(p.bounds[1] for p,x in shapes);y1=max(p.bounds[3] for p,x in shapes)
    scale=min((width-40)/max(.01,x1-x0),(height-36)/max(.01,y1-y0));aa=2
    im=Image.new('RGB',(width*aa,height*aa),'#f2f0e9')
    dx=(width-(x1-x0)*scale)/2;dy=(height-(y1-y0)*scale)/2
    mask=Image.new('L',im.size,0);draw=ImageDraw.Draw(mask)
    for shape,x in shapes:
        for poly in (list(shape.geoms) if hasattr(shape,'geoms') else [shape]):
            def points(ring):return [((dx+(px+x-x0)*scale)*aa,(height-dy-(py-y0)*scale)*aa) for px,py in ring.coords]
            draw.polygon(points(poly.exterior),fill=255)
            for ring in poly.interiors:draw.polygon(points(ring),fill=0)
    im.paste(color,(0,0,im.width,im.height),mask)
    return im.resize((width,height),Image.Resampling.LANCZOS)
