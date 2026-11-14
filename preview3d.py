"""Small CPU 3D renderer. Uses export triangles, UVs and textures; no game engine."""
import math
import numpy as np
from PIL import Image,ImageDraw
from model_options import geometry,paint,iron_texture,stone_texture
import mesh

def scene(letters,width,height,depth,base_style='strip',color='#be0f0c',weathering=0,road_reference=False,base_size=None,base_color=None,supports=False):
    letter_count=len(letters)
    base,letters,_=geometry(letters,width,height,depth,base_style,base_size,supports)
    tris=base+letters
    points=np.array([t[0] for t in tris],float);normals=np.array([t[1] for t in tris],float)
    normals/=np.maximum(np.linalg.norm(normals,axis=1)[:,None],1e-9)
    tangent=np.tile([1.,0,0],(len(tris),1));tangent[np.abs(normals[:,0])>=.9]=[0,1.,0]
    tangent-=normals*np.sum(tangent*normals,axis=1)[:,None];tangent/=np.linalg.norm(tangent,axis=1)[:,None]
    binormal=np.cross(normals,tangent)
    uv=np.stack([np.einsum('ijk,ik->ij',points,tangent),np.einsum('ijk,ik->ij',points,binormal)],axis=-1)*.1
    materials=np.r_[np.zeros(len(base),int),np.ones(len(letters),int)]
    # View the exposed negative-Z face; keep source X order unchanged.
    points=points*np.array([1,1,-1]);normals=normals*np.array([1,1,-1])
    base_texture=paint(base_color or '#b9b7ac',weathering,True).convert('RGB') if weathering or base_color else Image.open(mesh.ASSETS/'concrete.dds').convert('RGB')
    if base_style=='stone':base_texture=stone_texture(weathering,base_color).convert('RGB')
    textures=[np.array(base_texture),np.array(paint(color,weathering).convert('RGB'))]
    if len(letters)>letter_count:
        materials[len(base)+letter_count:]=2
        textures.append(np.array(iron_texture(weathering).convert('RGB')))
    if road_reference:
        # Game paths/pathtypes.ini: road1lines WIDTH 7, TILESIZE 25.
        # Independent preview geometry; never passed to the building exporter.
        road_z=max(5.,float(points[:,:,2].max())+3)
        road=np.array([[[-12.5,0,road_z],[12.5,0,road_z],[12.5,0,road_z+7]],
                       [[-12.5,0,road_z],[12.5,0,road_z+7],[-12.5,0,road_z+7]]])
        road_uv=np.stack([(road[:,:,0]+12.5)/25,(road[:,:,2]-road_z)/7],axis=-1)
        texture=Image.new('RGB',(512,256),'#53565a');draw=ImageDraw.Draw(texture)
        draw.line((0,12,511,12),fill='#e1ddd2',width=3);draw.line((0,242,511,242),fill='#e1ddd2',width=3)
        for x in range(0,512,82):draw.rectangle((x,125,x+40,130),fill='#e1ddd2')
        points=np.concatenate([points,road]);normals=np.concatenate([normals,[[0,1,0],[0,1,0]]])
        uv=np.concatenate([uv,road_uv*.998]);materials=np.r_[materials,[len(textures)]*2];textures.append(np.array(texture))
    return points,normals,uv,materials,textures

def focus(data,base_style):
    # Rotate about the wall itself, excluding lettering, foot and reference road.
    if base_style in ('wall','stone'):
        wall=data[0][:12] if base_style=='wall' else data[0][data[3]==0]
        return (wall.min(axis=(0,1))+wall.max(axis=(0,1)))/2
    return None


def render(data,width=760,height=440,yaw=-18,pitch=15,zoom=1,quick=False,cancel=None,pivot=None):
    points,normals,uv,materials,textures=data
    a,b=math.radians(yaw),math.radians(pitch)
    ry=np.array([[math.cos(a),0,math.sin(a)],[0,1,0],[-math.sin(a),0,math.cos(a)]])
    rx=np.array([[1,0,0],[0,math.cos(b),-math.sin(b)],[0,math.sin(b),math.cos(b)]])
    rotation=rx@ry
    center=(points.min(axis=(0,1))+points.max(axis=(0,1)))/2 if pivot is None else np.asarray(pivot)
    pos=(points-center)@rotation.T
    radius=max(1,np.linalg.norm(points-center,axis=2).max())
    scale=min(width*.45,height*.43)/radius*zoom
    # Wide text should use available width instead of being height-limited by its radius.
    spans=pos.max(axis=(0,1))-pos.min(axis=(0,1))
    if pivot is not None:spans=2*np.max(np.abs(pos),axis=(0,1))
    scale=min((width-70)/max(spans[0],1),(height-70)/max(spans[1],1))*zoom
    screen=np.stack([pos[:,:,0]*scale+width/2,-pos[:,:,1]*scale+height/2,pos[:,:,2]],axis=-1)
    ns=normals@rotation.T;light=np.array([-.3,.6,.74]);light/=np.linalg.norm(light)
    shade=.52+.48*np.maximum(0,ns@light)
    bg=np.zeros((height,width,3),dtype=np.uint8);bg[:]=[236,241,248]
    if quick:
        im=Image.fromarray(bg);draw=ImageDraw.Draw(im);averages=[t.mean(axis=(0,1)) for t in textures]
        for i in np.argsort(pos[:,:,2].mean(axis=1)):
            if ns[i,2]<-1e-7:continue
            color=tuple(np.uint8(averages[materials[i]]*shade[i]))
            draw.polygon([tuple(x) for x in screen[i,:,:2]],fill=color)
        return im
    zbuffer=np.full((height,width),-np.inf)
    for i,tri in enumerate(screen):
        if i%64==0 and cancel is not None and cancel():return None
        if ns[i,2]<-1e-7:continue
        x0=max(0,int(np.floor(tri[:,0].min())));x1=min(width,int(np.ceil(tri[:,0].max()))+1)
        y0=max(0,int(np.floor(tri[:,1].min())));y1=min(height,int(np.ceil(tri[:,1].max()))+1)
        if x1<=x0 or y1<=y0:continue
        (ax,ay,az),(bx,by,bz),(cx,cy,cz)=tri
        den=(by-cy)*(ax-cx)+(cx-bx)*(ay-cy)
        if abs(den)<1e-10:continue
        yy,xx=np.mgrid[y0:y1,x0:x1];xx=xx+.5;yy=yy+.5
        w0=((by-cy)*(xx-cx)+(cx-bx)*(yy-cy))/den
        w1=((cy-ay)*(xx-cx)+(ax-cx)*(yy-cy))/den;w2=1-w0-w1
        z=w0*az+w1*bz+w2*cz;use=(w0>=-1e-6)&(w1>=-1e-6)&(w2>=-1e-6)&(z>zbuffer[y0:y1,x0:x1])
        if not use.any():continue
        weights=np.stack([w0[use],w1[use],w2[use]],axis=-1);texuv=weights@uv[i]
        texture=textures[materials[i]];ty,tx=texture.shape[:2]
        pixels=texture[(np.floor(texuv[:,1]*ty).astype(int)%ty),(np.floor(texuv[:,0]*tx).astype(int)%tx)]
        bg[y0:y1,x0:x1][use]=np.uint8(pixels*shade[i]);zbuffer[y0:y1,x0:x1][use]=z[use]
    return Image.fromarray(bg)
