import copy,json,tempfile,unittest,zipfile,os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from PIL import Image,ImageDraw
from matplotlib import font_manager
import project_store,typography,preview3d,model_options
from image_layout import align_pieces,LayoutEditor,transformed
from generator import generate

class FullProjectTests(unittest.TestCase):
    def test_full_roundtrip_and_recovery_fallback(self):
        mask=Image.new('L',(90,50));ImageDraw.Draw(mask).rectangle((10,10,30,40),fill=255)
        state=dict(kind='image',image=mask.convert('RGB'),mask=mask,settings={'building_name':'测试'},layout={'pieces':[dict(mask=mask,x=-10,y=4,scale=1.4,angle=32)]},appearance={'age':72,'base_style':'wall','yaw':21})
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'SLOGAN_RECOVERY_DIR':td}):
            path=Path(td)/'roundtrip.sloganproj';project_store.save(path,state);loaded=project_store.load(path)
            self.assertEqual(loaded['layout']['pieces'][0]['mask'].tobytes(),mask.tobytes())
            self.assertEqual(loaded['appearance'],state['appearance']);self.assertEqual(loaded['settings'],state['settings'])
            autosave=project_store.Recovery(None,'image',lambda:state);autosave.flush();state['settings']['building_name']='Changed';autosave.flush()
            self.assertIsNone(autosave.error);self.assertEqual(project_store.recover('image')['settings']['building_name'],'Changed')
            project_store.recovery_path('image').write_bytes(b'broken')
            self.assertEqual(project_store.recover('image')['settings']['building_name'],'测试')
            with zipfile.ZipFile(Path(td)/'old.sloganproj','w') as z:z.writestr('settings.json','{}')
            with self.assertRaises((KeyError,ValueError)):project_store.load(Path(td)/'old.sloganproj')

    def test_alignment_and_equal_gaps_keep_other_pieces(self):
        pieces=[dict(mask=Image.new('L',(w,20),255),x=x,y=y,scale=1.,angle=0.) for w,x,y in [(10,3,4),(20,30,12),(30,90,-5),(10,150,8)]]
        untouched=copy.deepcopy(pieces[3]);align_pieces(pieces,{0,1,2},'bottom')
        self.assertEqual([p['y']+20 for p in pieces[:3]],[32,32,32])
        align_pieces(pieces,{0,1,2},'distribute_x')
        self.assertEqual(pieces[1]['x']-pieces[0]['x']-10,pieces[2]['x']-pieces[1]['x']-20)
        self.assertEqual(pieces[3]['x'],untouched['x']);self.assertEqual(pieces[3]['y'],untouched['y'])

    def test_ui_layers_reopen_group_move_and_unapplied_save(self):
        import tkinter as tk
        from image_editor import ImageEditor
        root=tk.Tk();root.withdraw()
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'SLOGAN_RECOVERY_DIR':td}):
            try:
                editor=ImageEditor(root,'English',td);editor.image=Image.new('RGB',(120,70),'white');editor.mask=Image.new('L',(120,70))
                draw=ImageDraw.Draw(editor.mask);draw.rectangle((10,10,29,39),fill=255);draw.rectangle((60,15,79,44),fill=255)
                editor.layout();ui=editor.layout_window;ui.update()
                for box in [(5,5,35,45),(55,10,85,50)]:
                    ui.pending=ui.selection_mask([(box[0],box[1]),(box[2],box[1]),(box[2],box[3]),(box[0],box[3])]);ui.cut()
                ui.select_all();ui.render();before=[(p['x'],p['y']) for p in ui.pieces]
                def ev(x,y):
                    a,b=ui.screen(ui.canvas,x,y);return SimpleNamespace(x=a,y=b,state=0)
                ui.down(ev(15,20));ui.drag(ev(35,27));ui.up(None)
                for p,(x,y) in zip(ui.pieces,before):self.assertAlmostEqual(p['x'],x+20);self.assertAlmostEqual(p['y'],y+7)
                path=Path(td)/'unapplied.sloganproj';project_store.save(path,editor.project_state())
                state=project_store.load(path);self.assertEqual(len(state['working_layout']['pieces']),2)
                ui.apply();self.assertEqual(len(editor.layout_state['pieces']),2)
                path=Path(td)/'applied.sloganproj';project_store.save(path,editor.project_state());editor.restore_state(project_store.load(path));editor.layout()
                ui=editor.layout_window;self.assertEqual(len(ui.pieces),2);ui.select(0);ui.scale.set('175');ui.flush_live();self.assertEqual(ui.pieces[0]['scale'],1.75)
                ui.destroy();editor.destroy()
            finally:root.destroy()

    def test_multiline_vertical_and_rendered_named_export(self):
        font=font_manager.findfont('DejaVu Sans')
        one,u=typography.layout('Test',font)
        two,u=typography.layout('Test\nTest',font,line_spacing=1.3)
        wide,u=typography.layout('Test\nTest',font,line_spacing=2.)
        vertical,u=typography.layout('Test',font,direction='vertical')
        self.assertGreater(two.bounds[3]-two.bounds[1],one.bounds[3]-one.bounds[1])
        self.assertGreater(wide.bounds[3]-wide.bounds[1],two.bounds[3]-two.bounds[1])
        self.assertGreater(vertical.bounds[3]-vertical.bounds[1],vertical.bounds[2]-vertical.bounds[0])
        letters,width=typography.glyph_mesh('Test\nTest',font)
        base,_,_=model_options.geometry(letters,width,9,1,'wall')
        self.assertGreater(max(y for pts,n in base for x,y,z in pts),max(y for pts,n in letters for x,y,z in pts))
        with tempfile.TemporaryDirectory() as td:
            folder=generate('Test\nTest',font,td,building_name='测试建筑',base_style='none',weathering=55)
            self.assertIn('$NAME_STR "测试建筑"',(folder/'slogan/building.ini').read_text(encoding='utf8'))
            expected=preview3d.render(preview3d.scene(letters,width,9,1,'none','#be0f0c',55),512,512)
            self.assertEqual(Image.open(folder/'previewimage.png').tobytes(),expected.tobytes())
            self.assertEqual(json.loads((folder/'generation.json').read_text(encoding='utf8'))['direction'],'horizontal')
            with self.assertRaises(ValueError):generate('Test',font,td,building_name='bad"name')

if __name__=='__main__':unittest.main()
