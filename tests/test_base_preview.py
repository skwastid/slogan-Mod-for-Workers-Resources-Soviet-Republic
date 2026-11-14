import json,time,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import numpy as np
from PIL import Image,ImageDraw
import model_options,preview3d,image_pipeline,project_store

class BasePreviewTests(unittest.TestCase):
    def sample(self):
        mask=Image.new('L',(80,60));ImageDraw.Draw(mask).rectangle((10,10,70,50),fill=255)
        return mask
    def test_custom_geometry_color_and_export(self):
        letters,width=image_pipeline.extrude(image_pipeline.polygons(self.sample()),9,1)
        size=dict(length=24,depth=8,height=2,wall_height=12,wall_thickness=0,top_width=0,top_depth=0)
        base,shifted,depth=model_options.geometry(letters,width,9,1,'strip',size)
        pts=np.array([p for tri,n in base for p in tri])
        np.testing.assert_allclose(np.ptp(pts,axis=0),[24,2,8])
        self.assertAlmostEqual(min(y for tri,n in shifted for x,y,z in tri),2)
        wall,_,_=model_options.geometry(letters,width,9,1,'wall',size)
        self.assertAlmostEqual(max(y for tri,n in wall for x,y,z in tri),14)
        with tempfile.TemporaryDirectory() as td:
            for age in (0,70):
                dest=image_pipeline.generate_image(self.sample(),td,base_size=size,base_color='#123456',weathering=age)
                meta=json.loads((dest/'generation.json').read_text())
                self.assertEqual(meta['base_size'],size);self.assertEqual(meta['base_color'],'#123456')
                data=preview3d.scene(letters,width,9,1,weathering=age,base_size=size,base_color='#123456')
                np.testing.assert_array_equal(np.array(Image.open(dest/'slogan/concrete.dds').convert('RGB')),data[4][0])
            state=dict(kind='font',appearance=dict(base_size=size,base_color='#123456'))
            path=Path(td)/'full.sloganproj';project_store.save(path,state)
            self.assertEqual(project_store.load(path),state)
        for invalid in (-1,.01,float('nan'),501):
            with self.assertRaises(ValueError):model_options.base_options({'length':invalid})
        self.assertIsNone(preview3d.render(data,cancel=lambda:True))
    def test_optional_regular_supports(self):
        mask=self.sample();ImageDraw.Draw(mask).rectangle((30,1,35,5),fill=255)
        letters,width=image_pipeline.extrude(image_pipeline.polygons(mask,0),9,1)
        _,plain,_=model_options.geometry(letters,width,9,1,'none')
        _,supported,_=model_options.geometry(letters,width,9,1,'none',supports=True)
        self.assertEqual(supported[:len(plain)],plain)
        self.assertGreater(len(supported),len(plain))
        added=supported[len(plain):]
        self.assertEqual(min(y for tri,n in added for x,y,z in tri),0)
        self.assertGreater(max(y for tri,n in added for x,y,z in tri),8)
        self.assertGreaterEqual(min(z for tri,n in added for x,y,z in tri),.2)
        from generator import generate
        with tempfile.TemporaryDirectory() as td:
            dest=generate('Test',r'C:\Windows\Fonts\arial.ttf',td,base_size={'height':2},base_color='#123456',supports=True)
            self.assertTrue(json.loads((dest/'generation.json').read_text())['supports'])
            self.assertEqual(Image.open(dest/'slogan/concrete.dds').getpixel((0,0))[:3],(18,52,86))

    def test_regular_frame_columns_braces_and_foundation(self):
        letters,width=image_pipeline.extrude(image_pipeline.polygons(self.sample()),9,1)
        base,supported,depth=model_options.geometry(letters,width,9,1,supports=True)
        frames=supported[len(letters):]
        count=(len(frames)-36)//48
        self.assertGreaterEqual(count,2)
        centers=[];tops=[]
        for i in range(count):
            post=np.array([tri for tri,n in frames[i*48:i*48+12]])
            centers.append((post[:,:,0].min()+post[:,:,0].max())/2);tops.append(post[:,:,1].max())
            brace=frames[i*48+12:i*48+24]
            self.assertTrue(any(abs(n[1])>.1 and abs(n[2])>.1 for tri,n in brace))
        np.testing.assert_allclose(np.diff(centers),np.diff(centers)[0])
        np.testing.assert_allclose(tops,tops[0])
        self.assertLessEqual(max(z for tri,n in frames for x,y,z in tri),depth/2)

    def test_iron_material_export_and_rust(self):
        import struct
        mask=self.sample();letters,width=image_pipeline.extrude(image_pipeline.polygons(mask),9,1)
        with tempfile.TemporaryDirectory() as td:
            for enabled in (False,True):
                dest=image_pipeline.generate_image(mask,td,supports=enabled,weathering=80)
                model=(dest/'slogan/model.nmf').read_bytes()
                materials,nodes,size=struct.unpack_from('<3I',model,8)
                self.assertEqual(size,len(model));self.assertEqual(materials,3 if enabled else 2)
                self.assertEqual(nodes,2 if enabled else 1)
                self.assertEqual((dest/'slogan/iron.dds').exists(),enabled)
                if enabled:
                    self.assertIn(b'iron',model[20:212]);self.assertIn(b'SloganSupports',model)
                    self.assertIn('$SUBMATERIAL iron',(dest/'slogan/model.mtl').read_text())
                    scene=preview3d.scene(letters,width,9,1,supports=True,weathering=80)
                    np.testing.assert_array_equal(scene[4][2],np.array(Image.open(dest/'slogan/iron.dds').convert('RGB')))
                    self.assertTrue(np.any(scene[3]==2))
        previous=-1
        for age in (0,25,50,75,100):
            pixels=np.array(model_options.iron_texture(age))[:,:,:3].astype(float)
            rust=np.mean(pixels[:,:,0]>pixels[:,:,2])
            self.assertGreaterEqual(rust,previous);previous=rust
        self.assertGreater(previous,.75)

    def test_wall_thickness_and_wall_center(self):
        letters,width=image_pipeline.extrude(image_pipeline.polygons(self.sample()),9,1)
        for thickness in (.2,1.2,4):
            size={'wall_thickness':thickness,'height':2,'wall_height':12}
            base,shifted,_=model_options.geometry(letters,width,9,1,'wall',size)
            wall=np.array([tri for tri,n in base[:12]])
            bounds_min=wall.min(axis=(0,1));bounds_max=wall.max(axis=(0,1))
            self.assertAlmostEqual(bounds_max[2]-bounds_min[2],thickness)
            self.assertAlmostEqual((bounds_min[2]+bounds_max[2])/2,0)
            self.assertGreater(bounds_min[2],max(z for tri,n in shifted for x,y,z in tri))
            for road in (False,True):
                scene=preview3d.scene(letters,width,9,1,'wall',base_size=size,road_reference=road)
                np.testing.assert_allclose(preview3d.focus(scene,'wall'),[0,8,0],atol=1e-8)

    def test_stone_sign_flat_surface_and_export(self):
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        mask=self.sample();letters,width=image_pipeline.extrude(image_pipeline.polygons(mask),9,1)
        size={'length':20,'depth':2,'height':4}
        base,flat,depth=model_options.geometry(letters,width,9,1,'stone',size,True)
        self.assertTrue(all(n==(0,0,-1) for tri,n in flat))
        self.assertTrue(all(z==-1 for tri,n in flat for x,y,z in tri))
        points=np.array([tri for tri,n in base]);np.testing.assert_allclose(np.ptp(points.reshape(-1,3),axis=0),[20,4,2])
        ink=unary_union([Polygon([(x,y) for x,y,z in tri]) for tri,n in flat])
        face=unary_union([Polygon([(x,y) for x,y,z in tri]) for tri,n in base if n==(0,0,-1)])
        self.assertLess(ink.intersection(face).area,1e-8)
        self.assertAlmostEqual(ink.union(face).area,76)
        with tempfile.TemporaryDirectory() as td:
            dest=image_pipeline.generate_image(mask,td,base_style='stone',base_size=size,supports=True)
            self.assertFalse((dest/'slogan/iron.dds').exists())
            self.assertFalse(json.loads((dest/'generation.json').read_text())['supports'])
            scene=preview3d.scene(letters,width,9,1,'stone',base_size=size)
            np.testing.assert_array_equal(scene[4][0],np.array(Image.open(dest/'slogan/concrete.dds').convert('RGB')))

    def test_stone_top_and_bottom_width(self):
        from shapely.geometry import Polygon
        from shapely.ops import unary_union
        letters,width=image_pipeline.extrude(image_pipeline.polygons(self.sample()),9,1)
        for bottom,top in [(20,12),(20,20),(12,20),(20,.1)]:
            base,flat,_=model_options.geometry(letters,width,9,1,'stone',{'length':bottom,'top_width':top,'height':4})
            points=np.array([p for tri,n in base for p in tri])
            self.assertAlmostEqual(np.ptp(points[points[:,1]==0,0]),bottom)
            self.assertAlmostEqual(np.ptp(points[points[:,1]==4,0]),top)
            face=unary_union([Polygon([(x,y) for x,y,z in tri]) for tri,n in base+flat if n==(0,0,-1)])
            self.assertAlmostEqual(face.area,(bottom+top)*2)
            self.assertTrue(all(z==-1 for tri,n in flat for x,y,z in tri))

    def test_stone_top_thickness_and_flush_letters(self):
        letters,width=image_pipeline.extrude(image_pipeline.polygons(self.sample()),9,1)
        for bottom,top in [(3,1),(2,2),(1,3)]:
            base,flat,_=model_options.geometry(letters,width,9,1,'stone',{'length':20,'top_width':18,'depth':bottom,'top_depth':top,'height':4})
            points=np.array([p for tri,n in base for p in tri])
            self.assertAlmostEqual(np.ptp(points[points[:,1]==0,2]),bottom)
            self.assertAlmostEqual(np.ptp(points[points[:,1]==4,2]),top)
            slope=(bottom-top)/8
            for tri,n in flat:
                for x,y,z in tri:self.assertAlmostEqual(z,-bottom/2+slope*y)
                np.testing.assert_allclose(n,np.array([0,slope,-1])/np.linalg.norm([0,slope,-1]))
            for tri,n in base:
                self.assertAlmostEqual(np.dot(np.array(tri[1])-tri[0],n),0,places=7)
                self.assertAlmostEqual(np.dot(np.array(tri[2])-tri[0],n),0,places=7)

    def test_continuous_drag_displays_frames_and_reuses_scene(self):
        import tkinter as tk
        from model_studio import ModelStudio
        root=tk.Tk();root.withdraw();shape=image_pipeline.polygons(self.sample())
        try:
            studio=ModelStudio(root,'English',lambda h,d:image_pipeline.extrude(shape,h,d),lambda *args:None)
            deadline=time.monotonic()+5
            while time.monotonic()<deadline:
                root.update();time.sleep(.01)
                if getattr(studio.canvas,'photo',None) is not None and not studio.busy:break
            self.assertIsNotNone(studio.scene_cache)
            with patch.object(preview3d,'scene',wraps=preview3d.scene) as build,patch.object(studio.canvas,'create_image',wraps=studio.canvas.create_image) as frames:
                studio.down(SimpleNamespace(x=0,y=0))
                for i in range(60):
                    studio.drag(SimpleNamespace(x=i*2,y=i//2));root.update();time.sleep(.015)
                self.assertGreater(frames.call_count,4,'Continuous motion must display frames before release')
                self.assertEqual(build.call_count,0,'Camera motion must not rebuild textures')
                studio.up(None)
            studio.close()
        finally:root.destroy()
