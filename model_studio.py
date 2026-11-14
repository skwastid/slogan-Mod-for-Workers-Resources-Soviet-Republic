import ui_i18n
"""Shared model appearance, interactive 3D, export and local game installation."""
import tkinter as tk
from tkinter import ttk,colorchooser,filedialog,messagebox
from PIL import ImageTk
import threading,queue,math
import ui_theme,preview3d,game_install,model_options

class ModelStudio(tk.Toplevel):
    def __init__(self,parent,language,builder,exporter,height=9,depth=1,color='#be0f0c',title='',initial=None,on_change=None,on_save=None,building_name=''):
        super().__init__(parent);self.parent=parent;self.language=language;self.zh=language in ('简体中文','繁體中文','繁体中文')
        self.builder=builder;self.exporter=exporter;self.title(self.tr('3D 预览与外观','3D preview & appearance'))
        ui_theme.setup(self);self.transient(parent);self.grab_set();ui_theme.fit_window(self,1180,940)
        self.page_scroll=ui_theme.ScrollPage(self,min_width=940,min_height=780);self.page_scroll.pack(fill='both',expand=True)
        content=self.page_scroll.content
        self.height=tk.StringVar(value=str(height));self.depth=tk.StringVar(value=str(depth));self.color=tk.StringVar(value=color)
        self.age=tk.DoubleVar(value=0);self.style=tk.StringVar();self.game=tk.StringVar(value=game_install.detect_game())
        self.status=tk.StringVar();self.asset_label=title
        self.base_size={k:tk.StringVar(value=str((initial or {}).get('base_size',{}).get(k,0))) for k in ('length','depth','height','wall_height','wall_thickness','top_width','top_depth')}
        self.base_color=tk.StringVar(value=(initial or {}).get('base_color') or '')
        self.supports=tk.BooleanVar(value=(initial or {}).get('supports',False))
        self.content_revision=0;self.scene_cache=None
        self.road_reference=tk.BooleanVar(value=(initial or {}).get('road_reference',True))
        self.on_change=on_change;self.building_name=tk.StringVar(value=building_name)
        self.styles={self.tr('长条底座','Long plinth'):'strip',self.tr('无底座','No base'):'none',self.tr('标语墙','Slogan wall'):'wall',self.tr('门牌石','Stone sign'):'stone'};self.style.set(next(iter(self.styles)))
        self.yaw=-18.;self.pitch=15.;self.zoom=1.;self.dragging=False;self.drag_start=None
        initial=initial or {}
        for key in ('height','depth','color','age'):
            if key in initial:getattr(self,key).set(initial[key])
        self.style.set(next((k for k,v in self.styles.items() if v==initial.get('base_style')),self.style.get()))
        for key in ('yaw','pitch','zoom'):
            if key in initial:setattr(self,key,float(initial[key]))
        self.revision=0;self.requested=True;self.timer=None;self.busy=False;self.exporting=False;self.pending_export=None
        self.queue=queue.Queue();self.cache=None;self.latest_project=None;self.controls=[]
        ui_theme.heading(content,self.tr('预览、调整，然后导入游戏','Preview, refine, then install'),title.replace('\n',' / ')[:90] or self.tr('预览使用导出模型；游戏中的光照与阴影会有所不同。','Preview uses the export geometry; game lighting and shadows will differ.'))
        body=ttk.Frame(content,padding=12);body.pack(fill='both',expand=True)
        sidebar=ttk.Frame(body,width=300);sidebar.pack(side='right',fill='y');sidebar.pack_propagate(False)
        scroll=tk.Canvas(sidebar,highlightthickness=0,width=280,bg='#f4f6fa')
        scrollbar=ttk.Scrollbar(sidebar,orient='vertical',command=scroll.yview);scrollbar.pack(side='right',fill='y')
        scroll.pack(side='left',fill='both',expand=True);scroll.configure(yscrollcommand=scrollbar.set)
        side=ttk.Frame(scroll,padding=(12,0,8,0));side_window=scroll.create_window(0,0,anchor='nw',window=side)
        side.bind('<Configure>',lambda e:scroll.configure(scrollregion=scroll.bbox('all')))
        scroll.bind('<Configure>',lambda e:scroll.itemconfigure(side_window,width=e.width))
        self.sidebar=side;self.sidebar_scroll=scroll
        self.canvas=tk.Canvas(body,bg='#ecf1f8',highlightthickness=0);self.canvas.pack(side='left',fill='both',expand=True)
        self.canvas.bind('<ButtonPress-1>',self.down);self.canvas.bind('<B1-Motion>',self.drag);self.canvas.bind('<ButtonRelease-1>',self.up)
        self.canvas.bind('<MouseWheel>',self.wheel);self.canvas.bind('<Configure>',lambda e:self.request())
        ttk.Label(side,text=self.tr('建筑名称','Building name')).pack(anchor='w')
        name_entry=ttk.Entry(side,textvariable=self.building_name);name_entry.pack(fill='x');self.controls.append(name_entry)
        for label,var in [(self.tr('字高（米）','Letter height (m)'),self.height),(self.tr('厚度（米）','Depth (m)'),self.depth)]:
            ttk.Label(side,text=label,style='Section.TLabel').pack(anchor='w',pady=(8,3))
            e=ttk.Entry(side,textvariable=var);e.pack(fill='x');self.controls.append(e)
            if var is self.depth:self.depth_control=e
        ttk.Label(side,text=self.tr('底座样式','Base style'),style='Section.TLabel').pack(anchor='w',pady=(8,3))
        combo=ttk.Combobox(side,textvariable=self.style,values=list(self.styles),state='readonly');combo.pack(fill='x');self.controls.append(combo)
        support=ttk.Checkbutton(side,text=self.tr('','Iron back supports'),variable=self.supports);support.pack(anchor='w',pady=5);self.controls.append(support);self.support_control=support
        sizes=ttk.Frame(side);sizes.pack(fill='x',pady=(8,0))
        self.size_controls={};self.size_labels={}
        labels=['Base length (m)','Base depth (m)','Plinth height (m)','Wall height (m)','Wall thickness (m)','Top width (m)','Top thickness (m)']
        for i,(key,var) in enumerate(self.base_size.items()):
            cell=ttk.Frame(sizes);cell.grid(row=i//2,column=i%2,sticky='ew',padx=(0,5));sizes.columnconfigure(i%2,weight=1)
            caption=ttk.Label(cell,text=self.tr('',labels[i]),wraplength=115);caption.pack(anchor='w');self.size_labels[key]=caption
            entry=ttk.Entry(cell,textvariable=var,width=12);entry.pack(fill='x');self.controls.append(entry);self.size_controls[key]=entry
        ttk.Label(side,text=self.tr('','0 = automatic size'),style='Muted.TLabel').pack(anchor='w')
        base_colors=ui_theme.FlowBar(side);base_colors.pack(fill='x',pady=(6,0))
        for label,command in [('Base color',self.pick_base_color),('Default material',lambda:self.base_color.set(''))]:
            button=ttk.Button(base_colors,text=self.tr('',label),command=command);button.pack(side='left');self.controls.append(button)
        ttk.Label(side,textvariable=self.base_color,style='Muted.TLabel').pack(anchor='w')
        self.color_button=ttk.Button(side,text=self.tr('文字颜色','Letter color'),command=self.pick_color);self.color_button.pack(fill='x',pady=(8,3));self.controls.append(self.color_button)
        ttk.Label(side,textvariable=self.color,style='Muted.TLabel').pack(anchor='w')
        ttk.Label(side,text=self.tr('做旧程度','Weathering'),style='Section.TLabel').pack(anchor='w',pady=(8,3))
        age=ttk.Scale(side,from_=0,to=100,variable=self.age);age.pack(fill='x');self.controls.append(age)
        self.age_label=ttk.Label(side,text='0%');self.age_label.pack(anchor='w')
        ttk.Label(side,text=self.tr('0 全新 → 100 重度做旧\n褪色、锈蚀、脱漆；文字与底座同步。','0 new → 100 heavily aged\nFading, rust, chips; letters and base.'),wraplength=238,style='Muted.TLabel').pack(anchor='w',pady=5)
        location=ttk.Frame(content,padding=(12,0));location.pack(fill='x')
        ttk.Label(location,text=self.tr('游戏目录','Game folder')).pack(side='left')
        e=ttk.Entry(location,textvariable=self.game);e.pack(side='left',fill='x',expand=True,padx=6);self.controls.append(e)
        b=ttk.Button(location,text=self.tr('浏览','Browse'),command=self.browse);b.pack(side='right');self.controls.append(b)
        bar=ui_theme.FlowBar(content,padding=12);bar.pack(fill='x')
        ttk.Checkbutton(bar,text=self.tr('道路参照（7米）','Road reference (7 m)'),variable=self.road_reference,command=self.changed).pack(side='left')
        self.generate_button=ttk.Button(bar,text=self.tr('生成建筑','Generate building'),command=lambda:self.generate(False));self.generate_button.pack(side='left',padx=(0,6))
        self.install_button=ttk.Button(bar,text=self.tr('导入刚生成的建筑','Install last export'),command=self.install_last,state='disabled');self.install_button.pack(side='left')
        if on_save:ttk.Button(bar,text=self.tr('保存完整工程','Save full project'),command=on_save).pack(side='left',padx=6)
        ttk.Button(bar,text=self.tr('恢复视角','Reset view'),command=self.reset_view).pack(side='left',padx=4)
        self.both_button=ttk.Button(bar,text=self.tr('生成并导入游戏','Generate & install'),command=lambda:self.generate(True),style='Primary.TButton');self.both_button.pack(side='right')
        ttk.Label(content,textvariable=self.status,padding=(12,4),wraplength=1120).pack(fill='x')
        ttk.Label(content,text=self.tr('安装至本地 workshop_wip，不上传创意工坊、不覆盖已有建筑。导入后重启游戏。','Installs to local workshop_wip. No upload or overwrite. Restart the game after importing.'),style='Muted.TLabel',padding=(12,4)).pack(fill='x')
        for var in [self.height,self.depth,self.color,self.age,self.style,self.building_name,self.base_color,self.supports,*self.base_size.values()]:var.trace_add('write',self.changed)
        def scroll_settings(event):
            scroll.yview_scroll(-1 if event.delta>0 else 1,'units');return 'break'
        def bind_scroll(widget):
            widget.bind('<MouseWheel>',scroll_settings)
            for child in widget.winfo_children():bind_scroll(child)
        bind_scroll(side);scroll.bind('<MouseWheel>',scroll_settings)
        self.mode_controls()
        self.protocol('WM_DELETE_WINDOW',self.close);self.after(16,self.poll);self.after(150,self.request)
    def tr(self,zh,en):return ui_i18n.translate(self.language,en)
    def params(self):
        height=float(self.height.get());depth=float(self.depth.get());age=float(self.age.get())
        if not math.isfinite(height) or not 1<=height<=30 or not math.isfinite(depth) or not .1<=depth<=5:raise ValueError(self.tr('字高 1–30 米，厚度 0.1–5 米。','Height 1–30 m; depth 0.1–5 m.'))
        return height,depth,self.color.get(),self.styles[self.style.get()],age,model_options.base_options({k:v.get() for k,v in self.base_size.items()}),self.base_color.get() or None,self.supports.get()
    def mode_controls(self):
        style=self.styles[self.style.get()]
        for widget,enabled in [(self.support_control,style!='stone'),(self.depth_control,style!='stone'),(self.size_controls['wall_height'],style=='wall'),(self.size_controls['wall_thickness'],style=='wall'),(self.size_controls['top_width'],style=='stone'),(self.size_controls['top_depth'],style=='stone')]:
            widget.state(['!disabled'] if enabled else ['disabled'])
        self.size_labels['depth'].configure(text=self.tr('','Bottom thickness (m)' if style=='stone' else 'Base depth (m)'))
        self.size_labels['length'].configure(text=self.tr('','Bottom width (m)' if style=='stone' else 'Base length (m)'))
        self.size_labels['height'].configure(text=self.tr('','Stone height (m)' if style=='stone' else 'Plinth height (m)'))
    def changed(self,*args):
        self.mode_controls()
        self.content_revision+=1
        self.latest_project=None;self.install_button.state(['disabled']);self.age_label.configure(text=f'{self.age.get():.0f}%');self.request()
    def appearance(self):
        return dict(height=self.height.get(),depth=self.depth.get(),color=self.color.get(),age=self.age.get(),base_style=self.styles[self.style.get()],yaw=self.yaw,pitch=self.pitch,zoom=self.zoom,road_reference=self.road_reference.get(),base_size={k:v.get() for k,v in self.base_size.items()},base_color=self.base_color.get(),supports=self.supports.get())
    def request(self):
        if self.on_change and not self.dragging:self.on_change(self.appearance(),self.building_name.get())
        if not self.winfo_exists():return
        self.revision+=1;self.requested=True
        if self.dragging:
            if self.timer is None:self.timer=self.after(16,self.kick)
        else:
            if self.timer:self.after_cancel(self.timer)
            self.timer=self.after(170,self.kick)
    def kick(self):
        self.timer=None
        if self.busy or self.exporting:return
        if self.pending_export is not None:
            install=self.pending_export;self.pending_export=None;self.generate(install);return
        if not self.requested:return
        self.requested=False
        try:params=self.params()
        except Exception as e:self.status.set(str(e));return
        rev=self.revision;content_rev=self.content_revision;h,d,c,base,age,size,base_color,supports=params
        width=max(300,min(1000,self.canvas.winfo_width()));height=max(200,min(650,self.canvas.winfo_height()))
        yaw,pitch,zoom,quick=self.yaw,self.pitch,self.zoom,self.dragging
        road_reference=self.road_reference.get()
        cache=self.cache;scene_cache=self.scene_cache;self.busy=True
        scene_key=(h,d,c,base,age,tuple(size.items()),base_color,road_reference,supports)
        if cache is None or cache[0]!=(h,d):self.status.set(self.tr('正在构建预览模型……','Building preview geometry…'))
        def worker():
            try:
                letters,modelwidth=cache[1:] if cache and cache[0]==(h,d) else self.builder(h,d)
                data=scene_cache[1] if scene_cache and scene_cache[0]==scene_key else preview3d.scene(letters,modelwidth,h,d,base,c,age,road_reference,size,base_color,supports)
                im=preview3d.render(data,width,height,yaw,pitch,zoom,quick,cancel=lambda:self.revision!=rev,pivot=preview3d.focus(data,base))
                self.queue.put(('preview',True,(rev,content_rev,quick,((h,d),letters,modelwidth),(scene_key,data),im)))
            except Exception as e:self.queue.put(('preview',False,(rev,e)))
        threading.Thread(target=worker,daemon=True).start()
    def poll(self):
        if not self.winfo_exists():return
        try:
            while True:
                kind,ok,result=self.queue.get_nowait()
                if kind=='preview':
                    self.busy=False
                    if ok:
                        rev,content_rev,quick,self.cache,self.scene_cache,im=result
                        if im is not None and (rev==self.revision or (self.dragging and quick and content_rev==self.content_revision)):
                            self.canvas.delete('all');self.canvas.photo=ImageTk.PhotoImage(im)
                            self.canvas.create_image(self.canvas.winfo_width()/2,self.canvas.winfo_height()/2,image=self.canvas.photo)
                            self.status.set(self.tr('拖动旋转 · 滚轮缩放；松开后显示完整做旧贴图。','Drag to orbit · Wheel to zoom. Full aging textures return on release.'))
                    elif result[0]==self.revision:self.status.set(str(result[1]))
                    self.kick()
                else:
                    self.exporting=False;self.set_export_state(False)
                    if ok:
                        project,installed=result;self.latest_project=project;self.install_button.state(['disabled'] if installed else ['!disabled'])
                        self.status.set((self.tr('已导入：','Installed: ') if installed else self.tr('已生成：','Generated: '))+str(installed or project))
                    else:
                        error,project=result;self.latest_project=project
                        if project:self.install_button.state(['!disabled'])
                        self.status.set(self.tr('导出或导入失败：','Export / install failed: ')+str(error))
                        messagebox.showerror(self.tr('操作失败','Operation failed'),str(error)+(('\n'+str(project)) if project else ''),parent=self)
                    if self.requested:self.kick()
        except queue.Empty:pass
        self.after(16,self.poll)
    def set_export_state(self,disabled):
        for w in self.controls+[self.generate_button,self.both_button,self.install_button]:w.state(['disabled'] if disabled else ['!disabled'])
        if not self.latest_project:self.install_button.state(['disabled'])
        if not disabled:self.mode_controls()
    def generate(self,install=False):
        if self.exporting:return
        if self.busy:self.pending_export=install;self.status.set(self.tr('预览完成后开始生成……','Export will start when preview completes…'));return
        try:
            import export_helpers
            params=self.params();game=self.game.get();name=export_helpers.name(self.building_name.get())
            if install and not game_install.valid_game(game):raise ValueError(self.tr('请先选择包含 SOVIET64.exe 和 media_soviet 的游戏目录。','Select the game folder containing SOVIET64.exe and media_soviet.'))
        except Exception as e:self.status.set(str(e));return
        self.exporting=True;self.set_export_state(True);self.status.set(self.tr('正在生成并校验文件……','Generating and verifying files…'))
        def worker():
            project=None
            try:
                h,d,c,base,age,size,base_color,supports=params;project=self.exporter(h,d,c,base,age,name,size,base_color,supports)
                installed=game_install.install(project,game) if install else None
                self.queue.put(('export',True,(project,installed)))
            except Exception as e:self.queue.put(('export',False,(e,project)))
        threading.Thread(target=worker,daemon=True).start()
    def install_last(self):
        if self.exporting or not self.latest_project:return
        project=self.latest_project;game=self.game.get();self.exporting=True;self.set_export_state(True)
        def worker():
            try:self.queue.put(('export',True,(project,game_install.install(project,game))))
            except Exception as e:self.queue.put(('export',False,(e,project)))
        threading.Thread(target=worker,daemon=True).start()
    def pick_color(self):
        color=colorchooser.askcolor(self.color.get(),parent=self)[1]
        if color:self.color.set(color)
    def pick_base_color(self):
        color=colorchooser.askcolor(self.base_color.get() or '#b9b7ac',parent=self)[1]
        if color:self.base_color.set(color)
    def browse(self):
        folder=filedialog.askdirectory(parent=self,title=self.tr('选择 SovietRepublic 游戏目录','Select SovietRepublic game folder'))
        if folder:self.game.set(folder)
    def down(self,e):
        self.dragging=True;self.drag_start=(e.x,e.y,self.yaw,self.pitch);self.request()
    def drag(self,e):
        if self.drag_start:
            x,y,yaw,pitch=self.drag_start;self.yaw=yaw+(e.x-x)*.5;self.pitch=max(-80,min(80,pitch+(e.y-y)*.5));self.request()
    def up(self,e):self.dragging=False;self.drag_start=None;self.request()
    def wheel(self,e):self.zoom=max(.4,min(3,self.zoom*(1.12 if e.delta>0 else 1/1.12)));self.request()
    def reset_view(self):self.yaw=-18.;self.pitch=15.;self.zoom=1.;self.request()
    def destroy(self):
        ui_theme.cancel_callbacks(self);super().destroy()
    def close(self):
        if self.exporting:self.status.set(self.tr('正在写入文件，请等待完成。','Wait until file writing is complete.'));return
        if self.timer:self.after_cancel(self.timer)
        self.destroy()
