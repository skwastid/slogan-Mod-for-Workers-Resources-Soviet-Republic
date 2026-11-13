import unittest
from types import SimpleNamespace
from PIL import Image, ImageDraw
from image_layout import compose, transformed, LayoutEditor

class LayoutTests(unittest.TestCase):
    def test_composition_preserves_overlap_and_negative_positions(self):
        a=Image.new('L',(12,20));ImageDraw.Draw(a).rectangle((1,1,10,18),fill=255)
        ImageDraw.Draw(a).rectangle((4,5,7,12),fill=0)
        p=dict(mask=a,x=-30,y=-15,scale=2.,angle=90.)
        im=transformed(p);result=compose(Image.new('L',(20,20)),[p])
        self.assertEqual(result.tobytes(),im.crop(im.getbbox()).tobytes())
        self.assertIn(0,result.getdata());self.assertIn(255,result.getdata())
        with self.assertRaises(ValueError):compose(Image.new('L',(10,10)),[dict(p,x=0),dict(p,x=2000)])

    def test_cut_transform_apply_and_parent_undo(self):
        import tkinter as tk
        from image_editor import ImageEditor
        root=tk.Tk();root.withdraw()
        try:
            parent=ImageEditor(root,'简体中文','');parent.image=Image.new('RGB',(100,60),'white')
            parent.mask=Image.new('L',(100,60));d=ImageDraw.Draw(parent.mask)
            d.rectangle((10,10,25,40),fill=255);d.rectangle((50,10,70,40),fill=255)
            original=parent.mask.tobytes();ui=LayoutEditor(parent);ui.update()
            def ev(canvas,x,y):
                a,b=ui.screen(canvas,x,y);return SimpleNamespace(x=a,y=b)
            ui.source_down(ev(ui.source,5,5));ui.source_up(ev(ui.source,30,45))
            self.assertEqual(ui.pending.getbbox(),(10,10,26,41));self.assertEqual(len(ui.pieces),0)
            ui.cut();self.assertEqual(len(ui.pieces),1);self.assertEqual(ui.base.getpixel((50,20)),255)
            self.assertEqual(compose(ui.base,ui.pieces).tobytes(),parent.mask.crop(parent.mask.getbbox()).tobytes())
            ui.scale.set('150');ui.angle.set('20');ui.flush_live();self.assertEqual(ui.pieces[0]['scale'],1.5)
            ui.undo();self.assertEqual(ui.pieces[0]['scale'],1.)
            ui.redo();self.assertEqual(ui.pieces[0]['scale'],1.5)
            ui.select(0);ui.return_piece();self.assertEqual(ui.base.tobytes(),original)
            ui.undo();ui.mode.set('polygon')
            for x,y in [(45,5),(75,5),(75,45),(45,45)]:ui.source_down(ev(ui.source,x,y))
            ui.finish_polygon();ui.cut();self.assertEqual(len(ui.pieces),2);self.assertIsNone(ui.base.getbbox())
            ui.select(1);ui.render();p=ui.pieces[1];x,y=p['x'],p['y']
            ui.down(ev(ui.canvas,x+5,y+5));ui.drag(ev(ui.canvas,x+25,y+15));ui.up(None)
            self.assertAlmostEqual(ui.pieces[1]['x'],x+20);self.assertAlmostEqual(ui.pieces[1]['y'],y+10)
            ui.apply();parent.undo();self.assertEqual(parent.mask.tobytes(),original)
            parent.destroy()
        finally:root.destroy()
