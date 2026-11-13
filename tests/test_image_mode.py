import sys, tempfile, unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PIL import Image, ImageDraw
import image_pipeline as p

class ImageModeTests(unittest.TestCase):
    def sample(self):
        im=Image.new('RGB',(160,100),'white');d=ImageDraw.Draw(im)
        d.rectangle((20,15,100,85),fill='black');d.rectangle((40,35,80,65),fill='white')
        d.point((145,5),fill='black')
        return im
    def test_extract_holes_and_noise(self):
        mask=p.extract(self.sample(),minimum=3)
        self.assertEqual(mask.getpixel((145,5)),0)
        self.assertEqual(mask.getpixel((50,50)),0)
        self.assertEqual(mask.getpixel((25,25)),255)
        stats=p.complexity(mask)
        self.assertEqual(stats['holes'],1);self.assertEqual(stats['components'],1)
    def test_project_roundtrip(self):
        im=self.sample();mask=p.extract(im)
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'test.sloganproj';p.save_project(path,im,mask,{'height':'9'})
            actual,edited,settings=p.load_project(path)
            self.assertEqual(im.tobytes(),actual.tobytes());self.assertEqual(mask.tobytes(),edited.tobytes())
            self.assertEqual(settings['height'],'9')
    def test_rectification_and_bad_corners(self):
        im=self.sample();fixed=p.rectify(im,[(0,0),(160,0),(160,100),(0,100)])
        self.assertEqual(im.tobytes(),fixed.tobytes())
        with self.assertRaises(ValueError):p.rectify(im,[(0,0),(160,100),(160,0),(0,100)])
    def test_export_and_empty_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            dest=p.generate_image(p.extract(self.sample()),tmp)
            self.assertTrue((dest/'slogan/model.nmf').is_file())
            self.assertIn('$OBJECT_BUILDING slogan',(dest/'workshopconfig.ini').read_text())
            with self.assertRaises(ValueError):p.generate_image(Image.new('L',(10,10)),tmp)
    def test_editor_paint_undo_redo_crop(self):
        import tkinter as tk
        from types import SimpleNamespace
        from image_editor import ImageEditor
        root=tk.Tk();root.withdraw()
        try:
            ui=ImageEditor(root,'简体中文',tempfile.gettempdir());ui.update()
            ui.image=self.sample();ui.mask=p.extract(ui.image);ui.zoom=1;ui.render()
            original=ui.mask.tobytes()
            ui.mode.set('erase');ui.down(SimpleNamespace(x=25,y=25));ui.up(None)
            changed=ui.mask.tobytes();self.assertNotEqual(original,changed)
            ui.undo();self.assertEqual(original,ui.mask.tobytes())
            ui.redo();self.assertEqual(changed,ui.mask.tobytes())
            ui.mode.set('crop');ui.source_down(SimpleNamespace(x=10,y=10));ui.source_up(SimpleNamespace(x=120,y=90))
            self.assertEqual(ui.image.size,(110,80));ui.undo();self.assertEqual(ui.image.size,(160,100))
            ui.destroy()
        finally:root.destroy()

    def test_crop_extract_atomic_undo(self):
        import tkinter as tk, time
        from types import SimpleNamespace
        from image_editor import ImageEditor
        root=tk.Tk();root.withdraw()
        try:
            ui=ImageEditor(root,'简体中文',tempfile.gettempdir());ui.update()
            ui.image=self.sample();ui.mask=Image.new('L',ui.image.size);ui.zoom=1;ui.render()
            before=ui.image.tobytes();ui.crop_extract()
            ui.source_down(SimpleNamespace(x=10,y=10));ui.source_up(SimpleNamespace(x=120,y=90))
            deadline=time.monotonic()+5
            while ui.busy and time.monotonic()<deadline:root.update();time.sleep(.01)
            self.assertFalse(ui.busy);self.assertEqual(ui.image.size,(110,80))
            self.assertIsNotNone(ui.mask.getbbox());self.assertEqual(len(ui.history),1)
            ui.undo();self.assertEqual(ui.image.tobytes(),before);self.assertIsNone(ui.mask.getbbox())
            ui.destroy()
        finally:root.destroy()

if __name__=='__main__':unittest.main()
