import ast,os,string,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from PIL import Image
from ui_i18n import LANGUAGES,catalogue,translate

class LocalizationTests(unittest.TestCase):
    def test_catalogue_coverage_and_placeholders(self):
        base=catalogue('English')
        self.assertEqual(len(LANGUAGES),18)
        for language in LANGUAGES:
            translated=catalogue(language)
            self.assertEqual(set(base),set(translated),language)
            fields=lambda text:{f for _,f,_,_ in string.Formatter().parse(text) if f}
            for key,value in translated.items():
                self.assertTrue(value.strip(),(language,key))
                self.assertEqual(fields(key),fields(value),(language,key))
        for filename in ('image_editor.py','image_layout.py','model_studio.py'):
            tree=ast.parse((Path(__file__).resolve().parents[1]/filename).read_text(encoding='utf8'))
            for node in ast.walk(tree):
                if isinstance(node,ast.Call) and isinstance(node.func,ast.Attribute) and node.func.attr=='tr' and len(node.args)>1 and isinstance(node.args[1],ast.Constant):
                    self.assertIn(node.args[1].value,base,filename)
                if isinstance(node,ast.Tuple):
                    values=[v.value for v in node.elts if isinstance(v,ast.Constant) and isinstance(v.value,str)]
                    for i in range(len(values)-1):
                        if any('\u4e00'<=c<='\u9fff' for c in values[i]) and not any('\u4e00'<=c<='\u9fff' for c in values[i+1]):
                            self.assertIn(values[i+1],base,filename)

    def test_language_switch_preserves_edits_and_reaches_studio(self):
        import tkinter as tk
        import model_studio
        from image_editor import open_editor
        root=tk.Tk();root.withdraw()
        with tempfile.TemporaryDirectory() as td,patch.dict(os.environ,{'SLOGAN_RECOVERY_DIR':td}):
            try:
                editor=open_editor(root,'English',td)
                editor.image=Image.new('RGB',(40,30),'white');editor.mask=Image.new('L',(40,30),255)
                editor.building_name.set('My building');editor.dirty=True
                editor=open_editor(root,'日本語',td)
                self.assertEqual(editor.language,'日本語');self.assertEqual(editor.building_name.get(),'My building')
                self.assertEqual(editor.mask.size,(40,30));self.assertTrue(editor.dirty)
                self.assertEqual(editor.tr('保存工程','Save project'),translate('日本語','Save project'))
                with patch.object(model_studio,'ModelStudio') as constructor:
                    editor.studio();self.assertEqual(constructor.call_args.args[1],'日本語')
                editor.destroy()
            finally:root.destroy()

if __name__=='__main__':unittest.main()
