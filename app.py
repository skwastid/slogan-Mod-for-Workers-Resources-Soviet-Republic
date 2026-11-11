import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from pathlib import Path
from matplotlib import font_manager
from generator import generate
from i18n import STRINGS, PREVIEW_LABELS
from PIL import ImageTk
from preview import render
import sys, threading, queue

if '--self-test' in sys.argv:
    testout=Path(sys.argv[sys.argv.index('--self-test')+1])
    testfont=font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans'))
    target=generate('hello',testfont,testout,stroke=.11)
    (testout/'success.txt').write_text(str(target),encoding='utf8')
    sys.exit(0)

root=tk.Tk();root.title('3D Slogan Generator');root.geometry('980x880');root.minsize(920,840)
style=ttk.Style();style.configure('TButton',padding=7);style.configure('TLabel',padding=3)
fonts={};fontchoice=tk.StringVar();text=tk.StringVar(value='为人民服务')
height=tk.StringVar(value='9');thickness=tk.StringVar(value='1');stroke=tk.StringVar(value='0.11');color=tk.StringVar(value='#be0f0c')
output=tk.StringVar(value=str(Path.home()/'Documents'/'SloganBuildings'));status=tk.StringVar();results=queue.Queue();busy=False
preview_traces=[];preview_job=None
page=None;current='简体中文';labels=[]

def clear():
    global page,preview_job
    if preview_job is not None:
        root.after_cancel(preview_job);preview_job=None
    for var,handle in preview_traces:var.trace_remove('write',handle)
    preview_traces.clear()
    if page is not None: page.destroy()
    page=ttk.Frame(root,padding=24);page.pack(fill='both',expand=True)

def languages():
    if busy:return
    clear();root.title('3D Slogan Generator — Language / 语言')
    ttk.Label(page,text='选择语言 / Choose your language',font=('Segoe UI',21)).pack(pady=(16,8))
    ttk.Label(page,text='3D Slogan Generator · v0.3').pack(pady=(0,24))
    grid=ttk.Frame(page);grid.pack(fill='both',expand=True)
    for c in range(3):grid.columnconfigure(c,weight=1)
    for i,name in enumerate(STRINGS):
        ttk.Button(grid,text=name,command=lambda n=name:form(n)).grid(row=i//3,column=i%3,sticky='nsew',padx=8,pady=8)
    for r in range(6):grid.rowconfigure(r,weight=1)

def loadfonts():
    if fonts:return
    for path in sorted(font_manager.findSystemFonts()):
        try:fonts[font_manager.FontProperties(fname=path).get_name()+' — '+Path(path).name]=path
        except Exception:pass
    if fonts:fontchoice.set(next((n for n in fonts if 'simhei' in n.lower()),next(iter(fonts))))

def form(language):
    global current,labels
    current=language;t=STRINGS[language];clear();loadfonts();root.title(t[0]);labels=[]
    page.columnconfigure(1,weight=1)
    ttk.Label(page,text=t[0],font=('Segoe UI',19)).grid(row=0,column=0,columnspan=3,sticky='w',pady=(0,16))
    def label(row,index):
        w=ttk.Label(page,text=t[index]);w.grid(row=row,column=0,sticky='w',padx=(0,10),pady=7);labels.append(w)
    def entry(row,index,var):
        label(row,index);ttk.Entry(page,textvariable=var).grid(row=row,column=1,sticky='ew',pady=7)
    entry(1,1,text);label(2,2)
    combo=ttk.Combobox(page,textvariable=fontchoice,values=sorted(fonts),state='readonly');combo.grid(row=2,column=1,sticky='ew',pady=7)
    def fontfile():
        f=filedialog.askopenfilename(title=t[3],filetypes=[('TTF / OTF / TTC','*.ttf *.otf *.ttc')])
        if f:fonts[f]=f;combo['values']=sorted(fonts);fontchoice.set(f)
    ttk.Button(page,text=t[3],command=fontfile).grid(row=2,column=2,padx=8)
    entry(3,4,height);entry(4,5,thickness);entry(5,6,stroke);entry(6,7,color)
    def pickcolor():
        c=colorchooser.askcolor(color.get(),title=t[8])[1]
        if c:color.set(c)
    ttk.Button(page,text=t[8],command=pickcolor).grid(row=6,column=2,padx=8)
    entry(7,9,output)
    def pickdir():
        d=filedialog.askdirectory(title=t[9])
        if d:output.set(d)
    ttk.Button(page,text=t[10],command=pickdir).grid(row=7,column=2,padx=8)
    ttk.Label(page,text=t[18],wraplength=880).grid(row=8,column=0,columnspan=3,sticky='w',pady=12)
    ttk.Label(page,text=PREVIEW_LABELS[language]).grid(row=9,column=0,columnspan=3,sticky='w')
    canvas=tk.Canvas(page,height=180,bg='#f2f0e9',highlightthickness=1,highlightbackground='#d2cfc5')
    canvas.grid(row=10,column=0,columnspan=3,sticky='ew',pady=(4,10))
    def paint():
        global preview_job
        preview_job=None
        if not canvas.winfo_exists():return
        canvas.delete('all');w=max(400,canvas.winfo_width())
        try:
            im=render(text.get(),fonts[fontchoice.get()],float(stroke.get().replace(',','.')),color.get(),w,180)
            canvas.photo=ImageTk.PhotoImage(im);canvas.create_image(w/2,90,image=canvas.photo)
        except Exception as e:
            canvas.photo=None;canvas.create_text(w/2,90,text=t[16]+'\n'+str(e),width=w-32,fill='#9a342e')
    def schedule(*args):
        global preview_job
        if preview_job is not None:root.after_cancel(preview_job)
        preview_job=root.after(200,paint)
    for var in (text,fontchoice,stroke,color):preview_traces.append((var,var.trace_add('write',schedule)))
    canvas.bind('<Configure>',schedule);schedule()
    button=ttk.Button(page,text=t[11]);button.grid(row=11,column=1,pady=12,sticky='ew')
    back=ttk.Button(page,text=t[12],command=languages);back.grid(row=11,column=0,pady=12,sticky='w')
    status.set('');ttk.Label(page,textvariable=status,wraplength=880).grid(row=12,column=0,columnspan=3,sticky='w',pady=10)
    def finish():
        global busy
        try:ok,value=results.get_nowait()
        except queue.Empty:root.after(100,finish);return
        busy=False;button.state(['!disabled']);back.state(['!disabled'])
        if ok:
            status.set(t[14]+' — '+str(value));messagebox.showinfo(t[14],str(value)+'\n\n'+t[17])
        else:
            status.set(t[15]);messagebox.showerror(t[15],t[16]+'\n\n'+str(value))
    def run():
        global busy
        if busy:return
        try:args=(text.get(),fonts[fontchoice.get()],output.get(),float(height.get().replace(',','.')),float(thickness.get().replace(',','.')),float(stroke.get().replace(',','.')),color.get())
        except Exception as e:messagebox.showerror(t[15],t[16]+'\n'+str(e));return
        busy=True;button.state(['disabled']);back.state(['disabled']);status.set(t[13])
        def worker():
            try:results.put((True,generate(*args)))
            except Exception as e:results.put((False,e))
        threading.Thread(target=worker,daemon=True).start();root.after(100,finish)
    button.configure(command=run)

languages()
if '--ui-test' in sys.argv:
    import json
    root.withdraw();checks=[]
    for lang in STRINGS:
        form(lang);root.update_idletasks();checks.append({'language':lang,'fields':len(labels),'fonts':len(fonts)})
    languages();root.update_idletasks()
    Path(sys.argv[sys.argv.index('--ui-test')+1]).write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8')
    root.destroy()
else:root.mainloop()
