"""Shared horizontal/multiline and upright vertical typography geometry."""
import math,unicodedata
from functools import lru_cache
from fontTools.ttLib import TTFont
from matplotlib.textpath import TextPath,TextToPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon
from shapely import affinity,unary_union

def normalize(text):
    text=unicodedata.normalize('NFC',text.replace('\r\n','\n').replace('\r','\n')).strip()
    if not text or len(text)>120 or len(text.split('\n'))>12 or any((ord(c)<32 and c!='\n') or (c.isspace() and c not in (' ','\n')) for c in text):
        raise ValueError('Text: 1–120 characters, up to 12 lines. Use Enter for a new line.')
    return text

@lru_cache(maxsize=24)
def layout(text,font,stroke=0,direction='horizontal',line_spacing=1.3):
    text=normalize(text);spacing=float(line_spacing);stroke=float(stroke)
    if direction not in ('horizontal','vertical') or not math.isfinite(spacing) or not .5<=spacing<=4 or not math.isfinite(stroke) or not 0<=stroke<=.3:raise ValueError('Line/column spacing: 0.5–4.0; extra weight: 0–0.3.')
    with TTFont(font,fontNumber=0) as ft:
        cmap=ft.getBestCmap() or {};missing=sorted(set(c for c in text if not c.isspace() and ord(c) not in cmap))
        if missing:raise ValueError('Font is missing: '+''.join(missing))
    prop=FontProperties(fname=font,size=10);metrics=TextToPath();glyphs={}
    for c in set(text)-{' ','\n'}:
        p=Polygon()
        for ring in TextPath((0,0),c,size=10,prop=prop).to_polygons():p=p.symmetric_difference(Polygon(ring))
        p=p.buffer(stroke,join_style='round',quad_segs=3)
        if p.is_empty:raise ValueError('Empty glyph: '+c)
        glyphs[c]=p
    ymax=max(p.bounds[3] for p in glyphs.values());ymin=min(p.bounds[1] for p in glyphs.values());unit=ymax-ymin
    cell=max(unit,max(p.bounds[2]-p.bounds[0] for p in glyphs.values()));parts=[]
    for col,line in enumerate(text.split('\n')):
        if direction=='horizontal':
            advance=metrics.get_text_width_height_descent(line,prop,False)[0]
            for i,c in enumerate(line):
                if c==' ':continue
                x=metrics.get_text_width_height_descent(line[:i],prop,False)[0]-advance/2
                parts.append(affinity.translate(glyphs[c],xoff=x,yoff=-col*unit*spacing))
        else:
            for row,c in enumerate(line):
                if c==' ':continue
                p=glyphs[c];x0,y0,x1,y1=p.bounds
                parts.append(affinity.translate(p,xoff=-col*cell*spacing-(x0+x1)/2,yoff=-row*unit*1.15-y1))
    shape=unary_union(parts)
    return shape,unit

def glyph_mesh(text,font,height=9,depth=1,stroke=0,direction='horizontal',line_spacing=1.3):
    from image_pipeline import extrude
    shape,unit=layout(text,font,stroke,direction,line_spacing)
    return extrude(shape,height*(shape.bounds[3]-shape.bounds[1])/unit,depth)
