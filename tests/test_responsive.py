import unittest
from unittest.mock import patch
import tkinter as tk
from tkinter import ttk
import ui_theme

class ResponsiveTests(unittest.TestCase):
    def test_small_work_area_and_scroll_access(self):
        root=tk.Tk()
        try:
            with patch.object(ui_theme,'work_area',return_value=(0,0,1024,728)):
                ui_theme.fit_window(root)
            root.update()
            self.assertLessEqual(root.winfo_height()+root.winfo_y(),728)
            root.geometry('800x480');root.update()
            self.assertEqual(root.winfo_height(),480)
            page=ui_theme.ScrollPage(root,min_width=1000,min_height=1000);page.pack(fill='both',expand=True)
            footer=ttk.Button(page.content,text='Generate & install');footer.pack(side='bottom')
            root.update();page.reveal(type('Event',(),{'widget':footer})());root.update()
            self.assertLessEqual(footer.winfo_rooty()+footer.winfo_height(),page.canvas.winfo_rooty()+page.canvas.winfo_height()+2)
            self.assertGreater(page.canvas.yview()[0],0)
            page.canvas.xview_moveto(1);self.assertGreater(page.canvas.xview()[0],0)
            # Editor canvases keep wheel events, instead of also scrolling the page.
            canvas=tk.Canvas(page.content)
            before=page.canvas.yview()
            page.wheel(type('Event',(),{'widget':canvas,'delta':120,'state':0})())
            self.assertEqual(before,page.canvas.yview())
        finally:root.destroy()
