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


def work_area(window):
    """Work area in the same process coordinate space as Tk (taskbar excluded)."""
    import sys
    if sys.platform=='win32':
        try:
            import ctypes
            from ctypes import wintypes
            rect=wintypes.RECT()
            if ctypes.windll.user32.SystemParametersInfoW(48,0,ctypes.byref(rect),0):
                return rect.left,rect.top,rect.right,rect.bottom
        except (OSError,AttributeError):pass
    return 0,0,window.winfo_screenwidth(),window.winfo_screenheight()


def fit_window(window,width=1100,height=940):
    left,top,right,bottom=work_area(window)
    width=max(200,min(width,right-left-32));height=max(150,min(height,bottom-top-64))
    window.resizable(True,True)
    window.minsize(min(640,width),min(400,height))
    x=max(0,left+(right-left-width)//2);y=max(0,top+(bottom-top-height-32)//2)
    window.geometry(f'{width}x{height}+{x}+{y}')


class ScrollPage(ttk.Frame):
    """Scrollable window content; nested editors keep their own wheel controls."""
    def __init__(self,parent,min_width=900,min_height=0,padding=0):
        import tkinter as tk
        super().__init__(parent)
        self.min_width=min_width;self.min_height=min_height;self.pending=None
        self.canvas=tk.Canvas(self,highlightthickness=0,bg=BG)
        self.vertical=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.horizontal=ttk.Scrollbar(self,orient='horizontal',command=self.canvas.xview)
        self.canvas.configure(yscrollcommand=self.vertical.set,xscrollcommand=self.horizontal.set)
        self.canvas.grid(row=0,column=0,sticky='nsew');self.vertical.grid(row=0,column=1,sticky='ns');self.horizontal.grid(row=1,column=0,sticky='ew')
        self.rowconfigure(0,weight=1);self.columnconfigure(0,weight=1)
        self.content=ttk.Frame(self.canvas,padding=padding)
        self.item=self.canvas.create_window(0,0,anchor='nw',window=self.content)
        self.canvas.bind('<Configure>',self.schedule);self.content.bind('<Configure>',self.schedule)
        self.top=self.winfo_toplevel()
        self.wheel_binding=self.top.bind('<MouseWheel>',self.wheel,add='+')
        self.focus_binding=self.top.bind('<FocusIn>',self.reveal,add='+')
    def schedule(self,event=None):
        if self.pending is None:self.pending=self.after_idle(self.layout)
    def layout(self):
        self.pending=None
        width=max(self.min_width,self.content.winfo_reqwidth(),self.canvas.winfo_width())
        height=max(self.min_height,self.content.winfo_reqheight(),self.canvas.winfo_height())
        self.canvas.itemconfigure(self.item,width=width,height=height)
        self.canvas.configure(scrollregion=(0,0,width,height))
    def owns(self,widget):
        while widget is not None:
            if widget is self.content:return True
            widget=getattr(widget,'master',None)
        return False
    def wheel(self,event):
        widget=event.widget
        if widget is not self.canvas:
            if not self.owns(widget):return
            current=widget
            while current is not self.content:
                if current.winfo_class() in ('Canvas','Text','Listbox','TCombobox','TSpinbox','TScale'):return
                current=current.master
        direction=-1 if event.delta>0 else 1
        if event.state&1:self.canvas.xview_scroll(direction*3,'units')
        else:self.canvas.yview_scroll(direction*3,'units')
        return 'break'
    def reveal(self,event):
        widget=event.widget
        if not self.owns(widget) or widget.winfo_class() in ('Canvas','Frame','TFrame'):return
        self.update_idletasks()
        x=widget.winfo_rootx()-self.content.winfo_rootx();y=widget.winfo_rooty()-self.content.winfo_rooty()
        for position,size,extent,total,view,moveto in [
            (x,widget.winfo_width(),self.canvas.winfo_width(),self.content.winfo_width(),self.canvas.xview,self.canvas.xview_moveto),
            (y,widget.winfo_height(),self.canvas.winfo_height(),self.content.winfo_height(),self.canvas.yview,self.canvas.yview_moveto)]:
            start=view()[0]*total
            if position<start:moveto(max(0,position-8)/max(1,total))
            elif position+size>start+extent:moveto(max(0,position+size-extent+8)/max(1,total))
    def destroy(self):
        cancel_callbacks(self)
        try:
            self.top.unbind('<MouseWheel>',self.wheel_binding);self.top.unbind('<FocusIn>',self.focus_binding)
        except Exception:pass
        super().destroy()
