import sys,tempfile,unittest,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image,ImageDraw
import numpy as np
import image_pipeline as pipeline
import model_options,preview3d,game_install,mesh

class StudioTests(unittest.TestCase):
    def ring(self):
        im=Image.new('L',(60,60));d=ImageDraw.Draw(im);d.rectangle((5,5,55,55),fill=255);d.rectangle((20,20,40,40),fill=0);return im
    def test_color_extraction_and_project_settings(self):
        im=Image.new('RGB',(60,30),'#e8e4de');d=ImageDraw.Draw(im);d.rectangle((5,5,20,25),fill='#174bb5');d.rectangle((30,5,45,25),fill='#be0f0c')
        mask=pipeline.extract_color(im,'#174bb5',45,2)
        self.assertEqual(mask.getpixel((10,10)),255);self.assertEqual(mask.getpixel((35,10)),0)
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'p.sloganproj';pipeline.save_project(path,im,mask,{'version':1,'by_color':True,'sample_color':'#174bb5'})
            self.assertTrue(pipeline.load_project(path)[2]['by_color'])
        with self.assertRaises(ValueError):pipeline.extract_color(im,'blue',50)
    def test_base_geometry_and_materials(self):
        letters,width=pipeline.extrude(pipeline.polygons(self.ring()),9,1)
        b,l,_=model_options.geometry(letters,width,9,1,'none');self.assertFalse(b)
        self.assertAlmostEqual(min(p[1] for pts,n in l for p in pts),0)
        b,l,_=model_options.geometry(letters,width,9,1,'wall');self.assertEqual(len(b),24)
        self.assertEqual(model_options.paint('#be0f0c',80).tobytes(),model_options.paint('#be0f0c',80).tobytes())
        self.assertNotEqual(model_options.paint('#be0f0c',0).tobytes(),model_options.paint('#be0f0c',80).tobytes())
    def test_render_hole_and_style_difference(self):
        letters,width=pipeline.extrude(pipeline.polygons(self.ring()),9,1)
        plain=preview3d.scene(letters,width,9,1,'none','#be0f0c',0)
        im=preview3d.render(plain,300,240,0,0)
        self.assertEqual(im.getpixel((150,120)),(236,241,248))
        aged=preview3d.render(preview3d.scene(letters,width,9,1,'wall','#be0f0c',85),300,240,0,0)
        self.assertNotEqual(im.tobytes(),aged.tobytes())
        self.assertNotEqual(aged.getpixel((150,120)),(236,241,248))
    def test_export_install_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            td=Path(td);game=td/'game';game.mkdir();(game/'SOVIET64.exe').touch();(game/'media_soviet').mkdir()
            for style in model_options.BASE_STYLES:
                dest=pipeline.generate_image(self.ring(),td/'out',base_style=style,weathering=80)
                meta=json.loads((dest/'generation.json').read_text());self.assertEqual(meta['base_style'],style)
                installed=game_install.install(dest,game);self.assertEqual((dest/'slogan/model.nmf').read_bytes(),(installed/'slogan/model.nmf').read_bytes())
                with self.assertRaises(FileExistsError):game_install.install(dest,game)
            with self.assertRaises(ValueError):game_install.install(dest,td/'wrong')
    def test_eyedropper_brush_and_studio(self):
        import tkinter as tk
        from types import SimpleNamespace
        from image_editor import ImageEditor
        from model_studio import ModelStudio
        root=tk.Tk();root.withdraw()
        try:
            ui=ImageEditor(root,'简体中文','');ui.update();ui.image=Image.new('RGB',(60,60),'#174bb5');ui.mask=self.ring();ui.zoom=2;ui.render()
            ui.pick_source_color();ui.source_down(SimpleNamespace(x=20,y=20));self.assertTrue(ui.by_color.get());self.assertEqual(ui.sample_color.get(),'#174bb5')
            ui.brush_cursor(SimpleNamespace(x=20,y=20));self.assertEqual(len(ui.canvases[1].find_withtag('brush-cursor')),2)
            ui.hide_brush();self.assertFalse(ui.canvases[1].find_withtag('brush-cursor'))
            shape=pipeline.polygons(self.ring())
            studio=ModelStudio(ui,'简体中文',lambda h,d:pipeline.extrude(shape,h,d),lambda *a:None)
            deadline=time.monotonic()+12
            while time.monotonic()<deadline:
                root.update();time.sleep(.02)
                if getattr(studio.canvas,'photo',None) is not None and not studio.busy:break
            self.assertIsNotNone(getattr(studio.canvas,'photo',None))
            studio.close();ui.destroy()
        finally:root.destroy()
