from pathlib import Path
import sys,struct,math,shutil,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont
from matplotlib.textpath import TextPath, TextToPath
from matplotlib.font_manager import FontProperties
from shapely.geometry import Polygon
from shapely import constrained_delaunay_triangles

ASSETS=Path(__file__).resolve().parent/'assets'
template=(ASSETS/'template.nmf').read_bytes()
pack=lambda fmt,*v:struct.pack('<'+fmt,*v)
name=lambda s:s.encode('ascii').ljust(64,b'\0')

def node(label,tris,material,extra=None):
    base_count=len(tris)*3
    if extra:tris=tris+extra
    vertices=[];normals=[];tangents=[];binormals=[];uv=[];planes=[];bounds=[]
    for pts,normal in tris:
        pts=np.array(pts,float);normal=np.array(normal,float);normal/=np.linalg.norm(normal)
        if np.dot(np.cross(pts[1]-pts[0],pts[2]-pts[0]),normal)<0:pts=pts[[0,2,1]]
        tangent=np.array([1.,0,0]) if abs(normal[0])<.9 else np.array([0.,1,0])
        tangent-=normal*np.dot(tangent,normal);tangent/=np.linalg.norm(tangent)
        binormal=np.cross(normal,tangent)
        vertices.extend(pts);normals.extend([normal]*3);tangents.extend([tangent]*3);binormals.extend([binormal]*3)
        uv.extend([(float(np.dot(p,tangent))*.1,float(np.dot(p,binormal))*.1) for p in pts])
        planes.extend([*normal,-float(np.dot(normal,pts[0]))])
        bounds.extend([*pts.min(axis=0),*pts.max(axis=0)])
    nv=len(vertices);assert 0<nv<65536
    arrays=lambda a:np.array(a,dtype='<f4').tobytes()
    subsets=pack('2I2H',0,base_count,material,0)
    if extra:subsets+=pack('2I2H',base_count,nv-base_count,1,0)
    data=pack(f'{nv}H',*range(nv))+b''.join(arrays(a) for a in (vertices,normals,tangents,binormals,uv,planes,bounds))+subsets
    lod=pack('7I',28+len(data)+8,nv,nv,2 if extra else 1,0,262458,0)+data
    v=np.array(vertices); bb=pack('6f',*v.min(axis=0),*v.max(axis=0))
    head=bytearray(template[84:84+232]);head[8:72]=name(label);head[204:228]=bb
    struct.pack_into('<I',head,4,len(head)+len(lod)+4)
    return bytes(head)+lod

def box(lo,hi):
    x,y,z=lo;X,Y,Z=hi;tris=[]
    for q,n in [([(x,y,z),(X,y,z),(X,Y,z),(x,Y,z)],(0,0,-1)), ([(x,y,Z),(X,y,Z),(X,Y,Z),(x,Y,Z)],(0,0,1)), ([(x,y,z),(x,y,Z),(x,Y,Z),(x,Y,z)],(-1,0,0)), ([(X,y,z),(X,y,Z),(X,Y,Z),(X,Y,z)],(1,0,0)), ([(x,y,z),(X,y,z),(X,y,Z),(x,y,Z)],(0,-1,0)), ([(x,Y,z),(X,Y,z),(X,Y,Z),(x,Y,Z)],(0,1,0))]:
        tris.extend([(q[:3],n),([q[0],q[2],q[3]],n)])
    return tris

def write_model(path,nodes):
    body=b''.join(nodes);header=b'B3DMH\x0010'+pack('3I',2,len(nodes),20+128+len(body))+name('concrete')+name('red')
    path.write_bytes(header+body)

def glyph_nodes(text,height=9.0,stroke=.11,font_path='',thickness=1.0):
    font=FontProperties(fname=font_path,size=10);polys=[];positions=[];metrics=TextToPath()
    for index,ch in enumerate(text):
        if ch.isspace(): continue
        positions.append(metrics.get_text_width_height_descent(text[:index],font,False)[0] if index else 0)
        rings=TextPath((0,0),ch,size=10,prop=font).to_polygons()
        shape=Polygon()
        for ring in rings:shape=shape.symmetric_difference(Polygon(ring))
        shape=shape.buffer(stroke,join_style='round',quad_segs=3)
        polys.append(shape)
    miny=min(p.bounds[1] for p in polys);maxy=max(p.bounds[3] for p in polys);s=height/(maxy-miny)
    total=metrics.get_text_width_height_descent(text,font,False)[0]*s;nodes=[]
    for k,shape in enumerate(polys):
        cx=0;offset=positions[k]*s-total/2
        convert=lambda p,z:((p[0]-cx)*s+offset,(p[1]-miny)*s+1.2,z*thickness)
        tris=[]
        parts=list(shape.geoms) if hasattr(shape,'geoms') else [shape]
        for part in parts:
            selected=list(constrained_delaunay_triangles(part).geoms)
            assert abs(sum(t.area for t in selected)-part.area)<1e-5
            for t in selected:
                xy=list(t.exterior.coords)[:3]
                tris.extend([([convert(p,.5) for p in xy],(0,0,1)),([convert(p,-.5) for p in xy],(0,0,-1))])
            for ring in [part.exterior,*part.interiors]:
                coords=list(ring.coords)
                for a,b in zip(coords,coords[1:]):
                    # Probe which side lies outside the solid; robust for holes.
                    dx,dy=b[0]-a[0],b[1]-a[1];length=math.hypot(dx,dy)
                    if length<1e-7:continue
                    from shapely.geometry import Point
                    n=np.array([dy,-dx])/length
                    mid=(np.array(a)+np.array(b))/2
                    if part.contains(Point(mid+n*.0001)):n=-n
                    q=[convert(a,-.5),convert(b,-.5),convert(b,.5),convert(a,.5)]
                    nn=(n[0],n[1],0)
                    tris.extend([(q[:3],nn),([q[0],q[2],q[3]],nn)])
        nodes.extend([([(-p[0],p[1],p[2]) for p in pts],(-n[0],n[1],n[2])) for pts,n in tris])
    return nodes,total
