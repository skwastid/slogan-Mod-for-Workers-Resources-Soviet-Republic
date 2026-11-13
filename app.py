import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from pathlib import Path
from matplotlib import font_manager
from generator import generate
from i18n import STRINGS, PREVIEW_LABELS, DEFAULT_TEXT
from PIL import ImageTk
from preview import render
import sys, threading, queue
import ui_theme, project_store, ui_i18n

if '--localization-self-test' in sys.argv:
    import json,tempfile,os,string
    from PIL import Image
    from image_editor import ImageEditor
    from image_layout import LayoutEditor
    from model_studio import ModelStudio
    target=Path(sys.argv[sys.argv.index('--localization-self-test')+1]);target.parent.mkdir(parents=True,exist_ok=True)
    checks=[];window=tk.Tk();window.withdraw()
    with tempfile.TemporaryDirectory() as td:
        os.environ['SLOGAN_RECOVERY_DIR']=td
        for language in ui_i18n.LANGUAGES:
            cat=ui_i18n.catalogue(language)
            assert set(cat)==set(ui_i18n.catalogue('English'))
            for key,value in cat.items():
                fields=lambda text:{f for _,f,_,_ in string.Formatter().parse(text) if f}
                assert fields(key)==fields(value)
            editor=ImageEditor(window,language,td);editor.image=Image.new('RGB',(40,30),'white');editor.mask=Image.new('L',(40,30),255)
            assert editor.title()==ui_i18n.translate(language,'Image slogans · Experimental')
            layout=LayoutEditor(editor)
            assert layout.title()==ui_i18n.translate(language,'Select letters · Live layout')
            layout.destroy()
            studio=ModelStudio(editor,language,lambda h,d:([],1),lambda *a:None)
            assert studio.title()==ui_i18n.translate(language,'3D preview & appearance')
            studio.destroy();editor.destroy()
            checks.append(dict(language=language,messages=len(cat),windows=3))
    window.destroy();target.write_text(json.dumps(checks,ensure_ascii=False,indent=2),encoding='utf8');sys.exit(0)

if '--studio-self-test' in sys.argv:
    import time,json,tempfile
    import mesh,preview3d,game_install
    from model_studio import ModelStudio
    target=Path(sys.argv[sys.argv.index('--studio-self-test')+1]);target.mkdir(parents=True,exist_ok=True)
    testfont=font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans'))
    letters,width=mesh.glyph_nodes('Test',9,0,testfont,.8)
    preview3d.render(preview3d.scene(letters,width,9,.8,'wall','#be0f0c',75),700,420).save(target/'preview3d.png')
    project=generate('Test',testfont,target,base_style='none',weathering=75)
    with tempfile.TemporaryDirectory() as td:
        game=Path(td);(game/'SOVIET64.exe').touch();(game/'media_soviet').mkdir()
        installed=game_install.install(project,game)
        assert (installed/'slogan/model.nmf').read_bytes()==(project/'slogan/model.nmf').read_bytes()
    window=tk.Tk();window.withdraw()
    studio=ModelStudio(window,'English',lambda h,d:mesh.glyph_nodes('Test',h,0,testfont,d),lambda *a:None)
    until=time.monotonic()+20
    while time.monotonic()<until:
        window.update();time.sleep(.02)
        if getattr(studio.canvas,'photo',None) is not None and not studio.busy:break
    assert getattr(studio.canvas,'photo',None) is not None
    studio.close();window.destroy()
    (target/'studio-success.txt').write_text(str(project),encoding='utf8')
    sys.exit(0)

if '--image-self-test' in sys.argv:
    import image_pipeline
    from PIL import Image, ImageDraw
    target=Path(sys.argv[sys.argv.index('--image-self-test')+1]);target.mkdir(parents=True,exist_ok=True)
    source=Image.new('RGB',(160,100),'white');draw=ImageDraw.Draw(source)
    draw.rectangle((20,10,140,90),fill='black');draw.rectangle((50,30,110,70),fill='white')
    mask=image_pipeline.extract(source)
    assert image_pipeline.complexity(mask)['holes']==1
    image_pipeline.save_project(target/'test.sloganproj',source,mask,{})
    assert image_pipeline.load_project(target/'test.sloganproj')[1].tobytes()==mask.tobytes()
    generated=image_pipeline.generate_image(mask,target)
    from image_editor import ImageEditor
    window=tk.Tk();window.withdraw();editor=ImageEditor(window,'简体中文',str(target))
    editor.image=source;editor.mask=mask;editor.update();editor.fit();editor.update();editor.destroy();window.destroy()
    (target/'image-success.txt').write_text(str(generated),encoding='utf8')
    sys.exit(0)

if '--self-test' in sys.argv:
    testout=Path(sys.argv[sys.argv.index('--self-test')+1])
    testfont=font_manager.findfont(font_manager.FontProperties(family='DejaVu Sans'))
    target=generate('hello',testfont,testout,stroke=.11)
    (testout/'success.txt').write_text(str(target),encoding='utf8')
    sys.exit(0)

root=tk.Tk();root.title('3D Slogan Generator');root.geometry('1100x940');root.minsize(1020,900)
style=ui_theme.setup(root)
fonts={};fontchoice=tk.StringVar();text=tk.StringVar(value=DEFAULT_TEXT['简体中文'])
height=tk.StringVar(value='9');thickness=tk.StringVar(value='1');stroke=tk.StringVar(value='0.11');color=tk.StringVar(value='#be0f0c')
output=tk.StringVar(value=str(Path.home()/'Documents'/'SloganBuildings'));status=tk.StringVar();results=queue.Queue();busy=False
preview_traces=[];preview_job=None
page=None;current='简体中文';labels=[]
building_name=tk.StringVar();direction=tk.StringVar(value='horizontal');line_spacing=tk.StringVar(value='1.3')
appearance={};loading=False;recovery_ready=False;recovery_offered=False

def tr(en):return ui_i18n.translate(current,en)

def project_state():
    return dict(kind='font',language=current,settings={k:v.get() for k,v in dict(text=text,height=height,thickness=thickness,stroke=stroke,color=color,output=output,building_name=building_name,direction=direction,line_spacing=line_spacing).items()},font=fonts.get(fontchoice.get(),''),appearance=appearance.copy())

recovery=project_store.Recovery(root,'font',project_state)
def changed_project(*args):
    if not loading and recovery_ready:recovery.schedule()
for variable in (text,fontchoice,height,thickness,stroke,color,output,building_name,direction,line_spacing):variable.trace_add('write',changed_project)

def save_project():
    path=filedialog.asksaveasfilename(parent=root.grab_current() or root,defaultextension='.sloganproj',filetypes=[(tr('Slogan project'),'*.sloganproj')])
    if path:
        try:project_store.save(path,project_state());status.set(path)
        except Exception as e:messagebox.showerror(tr('Project'),ui_i18n.error(current,e),parent=root)

def restore_project(state):
    global appearance,loading
    if state['kind']=='image':
        from image_editor import open_editor
        editor=open_editor(root,current,output.get());editor.restore_state(state);return
    loading=True
    try:
        form(state.get('language',current) if state.get('language',current) in STRINGS else current)
        for key,var in dict(text=text,height=height,thickness=thickness,stroke=stroke,color=color,output=output,building_name=building_name,direction=direction,line_spacing=line_spacing).items():
            if key in state.get('settings',{}):var.set(state['settings'][key])
        font=state.get('font','');fonts[font]=font;fontchoice.set(font)
        appearance=state.get('appearance',{}).copy()
        if not Path(font).is_file():messagebox.showwarning(tr('Font'),tr('Select an installed font. The saved font is unavailable.'),parent=root)
    finally:loading=False

def open_project():
    path=filedialog.askopenfilename(parent=root,filetypes=[(tr('Slogan project'),'*.sloganproj')])
    if path:
        try:restore_project(project_store.load(path));status.set(path)
        except Exception as e:messagebox.showerror(tr('Project'),ui_i18n.error(current,e),parent=root)

def recover_project():
    try:restore_project(project_store.recover('font'));status.set(tr('Recovered, including unapplied layout edits.'))
    except Exception as e:messagebox.showerror(tr('Recovery'),ui_i18n.error(current,e),parent=root)

def update_appearance(state,name):
    global appearance
    appearance=state;building_name.set(name);height.set(state['height']);thickness.set(state['depth']);color.set(state['color']);changed_project()


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
    ttk.Label(page,text='YOUR OWN BIG SLOGAN',style='Brand.TLabel').pack(pady=(4,8))
    ttk.Label(page,text='选择语言 / Choose your language',style='Title.TLabel').pack(pady=(0,8))
    ttk.Label(page,text='3D Slogan Generator · v1.0',style='Muted.TLabel').pack(pady=(0,18))
    grid=ttk.Frame(page);grid.pack(fill='both',expand=True)
    for c in range(3):grid.columnconfigure(c,weight=1)
    for i,name in enumerate(STRINGS):
        ttk.Button(grid,text=name,style='Language.TButton',command=lambda n=name:form(n)).grid(row=i//3,column=i%3,sticky='nsew',padx=8,pady=8)
    for r in range(6):grid.rowconfigure(r,weight=1)

def loadfonts():
    if fonts:return
    for path in sorted(font_manager.findSystemFonts()):
        try:fonts[font_manager.FontProperties(fname=path).get_name()+' — '+Path(path).name]=path
        except Exception:pass
    if fonts:fontchoice.set(next((n for n in fonts if 'simhei' in n.lower()),next(iter(fonts))))

def form(language):
    global current,labels,recovery_offered,recovery_ready
    if text.get()==DEFAULT_TEXT[current]:text.set(DEFAULT_TEXT[language])
    current=language;t=STRINGS[language];clear();loadfonts();root.title(t[0]);labels=[]
    page.columnconfigure(1,weight=1)
    ttk.Label(page,text=t[0],style='Title.TLabel').grid(row=0,column=0,columnspan=2,sticky='w',pady=(0,8))
    def image_mode():
        if busy:return
        from image_editor import open_editor
        open_editor(root,current,output.get())
    ttk.Button(page,text=tr('Image mode (experimental)'),command=image_mode).grid(row=0,column=2,sticky='e')
    def label(row,index):
        w=ttk.Label(page,text=t[index]);w.grid(row=row,column=0,sticky='w',padx=(0,10),pady=7);labels.append(w)
    def entry(row,index,var):
        label(row,index);ttk.Entry(page,textvariable=var).grid(row=row,column=1,sticky='ew',pady=7)
    toolbar=ttk.Frame(page);toolbar.grid(row=1,column=0,columnspan=3,sticky='ew',pady=4)
    zh=language in ('简体中文','繁體中文','繁体中文')
    for title,fn in [(tr('Open project'),open_project),(tr('Save project'),save_project),(tr('Recover'),recover_project)]:ttk.Button(toolbar,text=title,command=fn).pack(side='left',padx=3)
    ttk.Label(toolbar,text=tr('Building name')).pack(side='left',padx=(12,4))
    ttk.Entry(toolbar,textvariable=building_name).pack(side='left',fill='x',expand=True)
    label(2,1)
    editor=tk.Text(page,height=3,wrap='none',font=('Microsoft YaHei UI',12),undo=True)
    editor.grid(row=2,column=1,columnspan=2,sticky='ew',pady=4);editor.insert('1.0',text.get())
    def text_changed(event=None):
        if editor.edit_modified():
            value=editor.get('1.0','end-1c')
            if value!=text.get():text.set(value)
            editor.edit_modified(False)
    def sync_text(*args):
        if editor.get('1.0','end-1c')!=text.get():editor.delete('1.0','end');editor.insert('1.0',text.get());editor.edit_modified(False)
    editor.bind('<<Modified>>',text_changed);preview_traces.append((text,text.trace_add('write',sync_text)))
    label(3,2)
    combo=ttk.Combobox(page,textvariable=fontchoice,values=sorted(fonts),state='readonly');combo.grid(row=3,column=1,sticky='ew',pady=4)
    def fontfile():
        f=filedialog.askopenfilename(title=t[3],filetypes=[('TTF / OTF / TTC','*.ttf *.otf *.ttc')])
        if f:fonts[f]=f;combo['values']=sorted(fonts);fontchoice.set(f)
    ttk.Button(page,text=t[3],command=fontfile).grid(row=3,column=2,padx=8)
    params=ui_theme.FlowBar(page);params.grid(row=4,column=0,columnspan=3,sticky='ew',pady=8)
    for caption,var in [(t[4],height),(t[5],thickness),(t[6],stroke)]:
        ttk.Label(params,text=caption).pack(side='left',padx=(0,6));ttk.Entry(params,textvariable=var,width=8).pack(side='left',padx=(0,16))
    layoutbar=ui_theme.FlowBar(page);layoutbar.grid(row=5,column=0,columnspan=3,sticky='ew',pady=6)
    ttk.Radiobutton(layoutbar,text=tr('Horizontal'),variable=direction,value='horizontal').pack(side='left')
    ttk.Radiobutton(layoutbar,text=tr('Vertical'),variable=direction,value='vertical').pack(side='left',padx=12)
    ttk.Label(layoutbar,text=tr('Line / column spacing (0.5–4)')).pack(side='left')
    ttk.Entry(layoutbar,textvariable=line_spacing,width=7).pack(side='left',padx=6)
    entry(6,7,color)
    def pickcolor():
        c=colorchooser.askcolor(color.get(),title=t[8])[1]
        if c:color.set(c)
    ttk.Button(page,text=t[8],command=pickcolor).grid(row=6,column=2,padx=8)
    entry(7,9,output)
    def pickdir():
        d=filedialog.askdirectory(title=t[9])
        if d:output.set(d)
    ttk.Button(page,text=t[10],command=pickdir).grid(row=7,column=2,padx=8)
    ttk.Label(page,text=tr('Enter: new line / column. Up to 120 characters, 12 lines. Height is per line.'),wraplength=980,style='Muted.TLabel').grid(row=8,column=0,columnspan=3,sticky='w',pady=12)
    ttk.Label(page,text=PREVIEW_LABELS[language],style='Section.TLabel').grid(row=9,column=0,columnspan=3,sticky='w')
    canvas=tk.Canvas(page,height=180,bg='#f2f0e9',highlightthickness=1,highlightbackground='#d2cfc5')
    canvas.grid(row=10,column=0,columnspan=3,sticky='ew',pady=(4,10))
    def paint():
        global preview_job
        preview_job=None
        if not canvas.winfo_exists():return
        canvas.delete('all');w=max(400,canvas.winfo_width())
        try:
            im=render(text.get(),fonts[fontchoice.get()],float(stroke.get().replace(',','.')),color.get(),w,180,direction.get(),float(line_spacing.get()))
            canvas.photo=ImageTk.PhotoImage(im);canvas.create_image(w/2,90,image=canvas.photo)
        except Exception as e:
            canvas.photo=None;canvas.create_text(w/2,90,text=t[16]+'\n'+str(e),width=w-32,fill='#9a342e')
    def schedule(*args):
        global preview_job
        if preview_job is not None:root.after_cancel(preview_job)
        preview_job=root.after(200,paint)
    for var in (text,fontchoice,stroke,color,direction,line_spacing):preview_traces.append((var,var.trace_add('write',schedule)))
    canvas.bind('<Configure>',schedule);schedule()
    def studio():
        if busy:return
        from model_studio import ModelStudio
        import typography
        try:
            words=text.get();font=fonts[fontchoice.get()];weight=float(stroke.get().replace(',','.'));h=float(height.get().replace(',','.'));d=float(thickness.get().replace(',','.'));c=color.get();out=output.get()
            mode=direction.get();spacing=float(line_spacing.get());render(words,font,weight,c,200,80,mode,spacing)
        except Exception as e:messagebox.showerror(t[15],str(e));return
        def builder(h,d):return typography.glyph_mesh(words,font,h,d,weight,mode,spacing)
        def exporter(h,d,c,base,age,name):return generate(words,font,out,h,d,weight,c,base,age,name,mode,spacing)
        ModelStudio(root,current,builder,exporter,h,d,c,words,initial=dict(appearance,height=h,depth=d,color=c),on_change=update_appearance,on_save=save_project,building_name=building_name.get())
    ttk.Button(page,text=tr('3D / appearance / install'),command=studio,style='Primary.TButton').grid(row=11,column=2,padx=8,pady=12)
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
        try:args=(text.get(),fonts[fontchoice.get()],output.get(),float(height.get().replace(',','.')),float(thickness.get().replace(',','.')),float(stroke.get().replace(',','.')),color.get(),appearance.get('base_style','strip'),appearance.get('age',0),building_name.get(),direction.get(),float(line_spacing.get()))
        except Exception as e:messagebox.showerror(t[15],t[16]+'\n'+str(e));return
        busy=True;button.state(['disabled']);back.state(['disabled']);status.set(t[13])
        def worker():
            try:results.put((True,generate(*args)))
            except Exception as e:results.put((False,e))
        threading.Thread(target=worker,daemon=True).start();root.after(100,finish)
    button.configure(command=run)
    if not recovery_offered:
        recovery_offered=True
        if '--ui-test' not in sys.argv and project_store.recovery_path('font').exists():
            if messagebox.askyesno(tr('Recover project'),tr('Restore the last autosaved project?'),parent=root):recover_project()
        recovery_ready=True

def close_app():
    recovery.stop(flush=recovery_ready);root.destroy()
root.protocol('WM_DELETE_WINDOW',close_app)
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
