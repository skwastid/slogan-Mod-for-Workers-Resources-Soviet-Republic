"""Shared native Tk styling; no external theme dependencies."""
from tkinter import ttk

BG='#f3f5f9'
INK='#18283c'
MUTED='#64748b'
ACCENT='#2563eb'

def setup(window):
    style=ttk.Style(window)
    if style.theme_use()!='clam':style.theme_use('clam')
    window.configure(background=BG)
    from tkinter import font as tkfont
    tkfont.nametofont('TkDefaultFont',root=window).configure(family='Microsoft YaHei UI',size=10)
    window.option_add('*Listbox.font',('Microsoft YaHei UI',10))
    window.option_add('*Listbox.background','#ffffff')
    window.option_add('*Listbox.foreground',INK)
    window.option_add('*Listbox.selectBackground','#dbeafe')
    window.option_add('*Listbox.selectForeground','#173b72')
    style.configure('.',font=('Microsoft YaHei UI',10),background=BG,foreground=INK)
    style.configure('TFrame',background=BG)
    style.configure('TLabel',padding=2)
    style.configure('Title.TLabel',font=('Microsoft YaHei UI',22,'bold'),foreground=INK)
    style.configure('Section.TLabel',font=('Microsoft YaHei UI',11,'bold'),foreground=INK)
    style.configure('Muted.TLabel',foreground=MUTED)
    style.configure('Brand.TLabel',font=('Segoe UI',10,'bold'),foreground=ACCENT)
    style.configure('TButton',padding=(12,8),background='#ffffff',bordercolor='#d6dfeb',lightcolor='#ffffff',darkcolor='#ffffff',relief='flat',focuscolor='#93b4ee')
    style.map('TButton',background=[('disabled','#e9edf3'),('pressed','#dbeafe'),('active','#edf3ff')],foreground=[('disabled','#94a3b8')],bordercolor=[('focus','#2563eb')])
    style.configure('Primary.TButton',background=ACCENT,foreground='white',bordercolor=ACCENT,font=('Microsoft YaHei UI',10,'bold'))
    style.map('Primary.TButton',background=[('disabled','#a8bde7'),('pressed','#1e40af'),('active','#1d4ed8')],foreground=[('disabled','#f1f5f9'),('!disabled','white')])
    style.configure('Language.TButton',font=('Microsoft YaHei UI',12),padding=(18,12))
    style.configure('TEntry',fieldbackground='white',padding=7,bordercolor='#d6dfeb',lightcolor='#d6dfeb',darkcolor='#d6dfeb')
    style.map('TEntry',bordercolor=[('focus',ACCENT)])
    style.configure('TCombobox',fieldbackground='white',padding=6,bordercolor='#d6dfeb',arrowsize=15)
    style.map('TCombobox',fieldbackground=[('readonly','white')],foreground=[('readonly',INK)],selectbackground=[('readonly','#dbeafe')],selectforeground=[('readonly',INK)])
    style.configure('TSpinbox',fieldbackground='white',padding=4,bordercolor='#d6dfeb')
    style.configure('TLabelframe',background=BG,bordercolor='#d6dfeb',relief='solid',borderwidth=1)
    style.configure('TLabelframe.Label',font=('Microsoft YaHei UI',10,'bold'),foreground='#334155',padding=(8,5))
    style.configure('TCheckbutton',padding=(3,5));style.configure('TRadiobutton',padding=(3,5))
    style.map('TCheckbutton',background=[('active',BG)]);style.map('TRadiobutton',background=[('active',BG)])
    style.configure('Horizontal.TScale',background=BG,troughcolor='#dce5f2')
    return style

def heading(parent,title,subtitle=None):
    frame=ttk.Frame(parent,padding=(16,10,16,8));frame.pack(fill='x')
    ttk.Label(frame,text=title,style='Section.TLabel').pack(anchor='w')
    if subtitle:ttk.Label(frame,text=subtitle,style='Muted.TLabel',wraplength=1000).pack(anchor='w',pady=(3,0))
    return frame


class FlowBar(ttk.Frame):
    """Wrap translated toolbar controls instead of clipping long labels."""
    def __init__(self,parent,**kwargs):
        super().__init__(parent,**kwargs)
        self.pending=None;self.last_width=None
        self.bind('<Configure>',self.schedule)
        self.after_idle(self.reflow)
    def schedule(self,event=None):
        if self.pending is None:self.pending=self.after_idle(self.reflow)
    def reflow(self):
        self.pending=None
        if not self.winfo_exists():return
        available=max(200,self.winfo_width()-20)
        x=y=0;rowheight=0
        for child in self.winfo_children():
            if child.winfo_manager()=='pack':child.pack_forget()
            w=min(available,child.winfo_reqwidth());h=child.winfo_reqheight()
            if x and x+w>available:x=0;y+=rowheight+4;rowheight=0
            child.place(x=x,y=y,width=w,height=h)
            x+=w+6;rowheight=max(rowheight,h)
        height=y+rowheight+8
        if self.winfo_reqheight()!=height:self.configure(height=height)
    def destroy(self):
        cancel_callbacks(self);super().destroy()


def cancel_callbacks(window):
    """Cancel only callbacks registered by this widget before it is destroyed."""
    commands=set(window._tclCommands or [])
    for token in window.tk.call('after','info'):
        try:
            script=window.tk.call('after','info',token)[0]
            if str(script).split()[0] in commands:window.after_cancel(token)
        except Exception:pass
