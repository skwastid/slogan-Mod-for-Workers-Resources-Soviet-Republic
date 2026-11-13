import ui_i18n
"""Experimental image editing window, independent of font generation."""
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
from PIL import Image, ImageTk, ImageDraw
import threading, queue
import image_pipeline as pipeline
import ui_theme, project_store, copy

class ImageEditor(tk.Toplevel):
    def __init__(self,parent,language,output):
        super().__init__(parent)
        self.language=language;self.zh=language in ('简体中文','繁體中文','繁体中文')
        self.title(self.tr('图片标语 · 实验功能','Image slogans · Experimental'))
        ui_theme.setup(self)
        self.geometry('1280x940');self.minsize(1180,880)
        self.layout_state=None;self.working_layout=None;self.layout_window=None;self.appearance={};self.original_image=None;self.restoring=False
        self.building_name=tk.StringVar()
        self.image=None;self.mask=None;self.history=[];self.future=[];self.points=[]
        self.dirty=False;self.busy=False;self.zoom=1.;self.last=None;self.active=False
        self.jobs=queue.Queue();self.controls=[]
        self.mode=tk.StringVar(value='paint');self.brush=tk.IntVar(value=12)
        self.threshold=tk.IntVar(value=145);self.minimum=tk.IntVar(value=12)
        self.dark=tk.BooleanVar(value=True);self.adaptive=tk.BooleanVar(value=False)
        self.by_color=tk.BooleanVar(value=False);self.sample_color=tk.StringVar(value='#be0f0c');self.tolerance=tk.IntVar(value=65);self.pointer=None
        self.overlay=tk.BooleanVar(value=False);self.smooth=tk.DoubleVar(value=.8)
        self.height=tk.StringVar(value='9');self.depth=tk.StringVar(value='1')
        self.color=tk.StringVar(value='#be0f0c');self.output=tk.StringVar(value=output)
        self.status=tk.StringVar(value=self.tr('导入图片或打开修补工程。','Import an image or open an editing project.'))
        ui_theme.heading(self,self.tr('图片标语工作台','Image slogan studio'),self.tr('01 导入图片    /    02 裁剪与校正    /    03 提取与修补    /    04 排列与生成','01 Import    /    02 Crop & rectify    /    03 Extract & repair    /    04 Arrange & generate'))
        bar=ui_theme.FlowBar(self,padding=8);bar.pack(fill='x')
        for zh,en,fn in [('导入图片','Import image',self.open_image),('打开工程','Open project',self.open_project),('保存工程','Save project',self.save_project),('恢复上次','Recover',self.recover_project),('撤销','Undo',self.undo),('重做','Redo',self.redo)]:
            self.button(bar,self.tr(zh,en),fn).pack(side='left',padx=3)
        self.button(bar,'−',lambda:self.set_zoom(self.zoom/1.25)).pack(side='right')
        self.button(bar,'+',lambda:self.set_zoom(self.zoom*1.25)).pack(side='right')
        self.button(bar,self.tr('适应窗口','Fit'),self.fit).pack(side='right')
        settings=ui_theme.FlowBar(self,padding=(8,0));settings.pack(fill='x')
        ttk.Checkbutton(settings,text=self.tr('黑字（取消为白字）','Dark letters (off: light)'),variable=self.dark).pack(side='left')
        ttk.Checkbutton(settings,text=self.tr('局部对比','Local contrast'),variable=self.adaptive).pack(side='left')
        for label,var,lo,hi in [(self.tr('阈值','Threshold'),self.threshold,1,254),(self.tr('去杂点/像素','Noise area/px'),self.minimum,0,500)]:
            ttk.Label(settings,text=label).pack(side='left',padx=(8,2))
            ttk.Spinbox(settings,from_=lo,to=hi,textvariable=var,width=5).pack(side='left')
        self.button(settings,self.tr('自动提取 / 重置','Extract / reset'),self.extract).pack(side='left',padx=8)
        self.button(settings,self.tr('裁剪后提取','Crop then extract'),self.crop_extract).pack(side='left',padx=4)
        self.button(settings,self.tr('拆字与重排','Cut / arrange'),self.layout).pack(side='left',padx=8)
        colorbar=ui_theme.FlowBar(self,padding=(8,2));colorbar.pack(fill='x')
        ttk.Checkbutton(colorbar,text=self.tr('按颜色提取','Extract by color'),variable=self.by_color).pack(side='left')
        self.button(colorbar,self.tr('吸管：点选原图颜色','Eyedropper: pick source color'),self.pick_source_color).pack(side='left',padx=5)
        self.swatch=tk.Label(colorbar,textvariable=self.sample_color,bg=self.sample_color.get(),fg='white',width=10);self.swatch.pack(side='left',padx=5)
        ttk.Label(colorbar,text=self.tr('颜色容差','Color tolerance')).pack(side='left')
        ttk.Spinbox(colorbar,from_=1,to=255,textvariable=self.tolerance,width=5).pack(side='left',padx=4)
        ttk.Label(colorbar,text=self.tr('选色后点击自动提取；容差越大，包含的相近颜色越多。','Pick a color, then Extract. Higher tolerance includes more shades.'),style='Muted.TLabel').pack(side='left',padx=6)
        tools=ui_theme.FlowBar(self,padding=8);tools.pack(fill='x')
        for mode,zh,en in [('paint','填补','Paint'),('erase','擦除','Erase'),('fill','填充区域','Fill region'),('remove','删除区域','Erase region'),('crop','裁剪','Crop'),('perspective','四点校正','4-point rectify')]:
            ttk.Radiobutton(tools,text=self.tr(zh,en),variable=self.mode,value=mode,command=self.change_mode).pack(side='left',padx=3)
        ttk.Label(tools,text=self.tr('笔刷','Brush')).pack(side='left')
        ttk.Spinbox(tools,from_=1,to=150,textvariable=self.brush,width=4).pack(side='left')
        ttk.Checkbutton(tools,text=self.tr('叠加原图','Overlay'),variable=self.overlay,command=self.render).pack(side='left',padx=6)
        ttk.Label(self,text=self.tr('左：原图（裁剪拖框；校正依次点左上、右上、右下、左下）   右：修补；滚轮缩放，右键拖动平移。','Left: source (drag to crop; rectify TL → TR → BR → BL). Right: edit. Wheel: zoom; right drag: pan.'),wraplength=1120).pack(fill='x',padx=12)
        panes=ttk.Panedwindow(self,orient='horizontal');panes.pack(fill='both',expand=True,padx=8,pady=6)
        self.canvases=[]
        for title in [self.tr('原图','Source'),self.tr('提取 / 修补结果','Extracted / repaired mask')]:
            frame=ttk.LabelFrame(panes,text=title);panes.add(frame,weight=1)
            canvas=tk.Canvas(frame,bg='#e8edf4',highlightthickness=0)
            sx=ttk.Scrollbar(frame,orient='horizontal',command=canvas.xview);sy=ttk.Scrollbar(frame,orient='vertical',command=canvas.yview)
            canvas.configure(xscrollcommand=sx.set,yscrollcommand=sy.set)
            canvas.grid(row=0,column=0,sticky='nsew');sy.grid(row=0,column=1,sticky='ns');sx.grid(row=1,column=0,sticky='ew')
            frame.rowconfigure(0,weight=1);frame.columnconfigure(0,weight=1)
            canvas.bind('<MouseWheel>',lambda e:self.set_zoom(self.zoom*(1.2 if e.delta>0 else 1/1.2)))
            canvas.bind('<ButtonPress-3>',lambda e,c=canvas:c.scan_mark(e.x,e.y))
            canvas.bind('<B3-Motion>',lambda e,c=canvas:c.scan_dragto(e.x,e.y,gain=1))
            self.canvases.append(canvas)
        self.canvases[0].bind('<ButtonPress-1>',self.source_down)
        self.canvases[0].bind('<B1-Motion>',self.source_drag)
        self.canvases[0].bind('<ButtonRelease-1>',self.source_up)
        self.canvases[1].bind('<ButtonPress-1>',self.down)
        self.canvases[1].bind('<B1-Motion>',self.drag)
        self.canvases[1].bind('<ButtonRelease-1>',self.up)
        self.canvases[1].bind('<Motion>',self.brush_cursor)
        self.canvases[1].bind('<Leave>',self.hide_brush)
        self.brush.trace_add('write',lambda *a:self.draw_brush())
        bottom=ui_theme.FlowBar(self,padding=8);bottom.pack(fill='x')
        for label,var in [(self.tr('字高 m','Height m'),self.height),(self.tr('厚度 m','Depth m'),self.depth),(self.tr('平滑 px','Smooth px'),self.smooth)]:
            ttk.Label(bottom,text=label).pack(side='left');ttk.Entry(bottom,textvariable=var,width=6).pack(side='left',padx=3)
        self.button(bottom,self.tr('颜色','Colour'),self.pick_color).pack(side='left',padx=4)
        ttk.Label(bottom,textvariable=self.color).pack(side='left')
        self.button(bottom,self.tr('检查复杂度','Check complexity'),self.check).pack(side='left',padx=4)
        self.button(bottom,self.tr('3D / 外观 / 导入','3D / appearance / install'),self.studio).pack(side='right',padx=5)
        self.button(bottom,self.tr('快速生成','Quick export'),self.generate).pack(side='right')
        namebar=ui_theme.FlowBar(self,padding=(8,4));namebar.pack(fill='x')
        ttk.Label(namebar,text=self.tr('建筑名称','Building name')).pack(side='left')
        ttk.Entry(namebar,textvariable=self.building_name).pack(side='left',fill='x',expand=True,padx=6)
        location=ttk.Frame(self,padding=(8,0));location.pack(fill='x')
        ttk.Label(location,text=self.tr('输出目录','Output')).pack(side='left')
        ttk.Entry(location,textvariable=self.output).pack(side='left',fill='x',expand=True)
        self.button(location,self.tr('浏览','Browse'),self.pick_output).pack(side='right')
        ttk.Label(self,textvariable=self.status,wraplength=1120,padding=8).pack(fill='x')
        self.bind('<Control-z>',lambda e:self.undo());self.bind('<Control-y>',lambda e:self.redo())
        self.protocol('WM_DELETE_WINDOW',self.close)
        self.recovery=project_store.Recovery(self,'image',self.project_state)
        for key in self.setting_keys():getattr(self,key).trace_add('write',self.changed_project)
        self.after(150,self.render)
        self.after(250,self.offer_recovery)

    def offer_recovery(self):
        if self.image is None and project_store.recovery_path('image').exists():
            if messagebox.askyesno(self.tr('恢复工程','Recover project'),self.tr('恢复上次自动保存的图片工程？','Restore the last autosaved image project?'),parent=self):self.recover_project()

    def tr(self,zh,en): return ui_i18n.translate(self.language,en)
    def button(self,parent,label,fn):
        b=ttk.Button(parent,text=label,command=fn,style='Primary.TButton' if fn.__name__ in ('generate','crop_extract','studio') else 'TButton');self.controls.append(b);return b
    def error(self,e): messagebox.showerror(self.tr('操作失败','Operation failed'),ui_i18n.error(self.language,e),parent=self)
    def discard(self):
        return not self.dirty or messagebox.askyesno(self.tr('未保存的修补','Unsaved edits'),self.tr('继续会丢失未保存的修补。继续吗？','Continue and discard unsaved edits?'),parent=self)
    def setting_keys(self):return ['threshold','minimum','dark','adaptive','smooth','height','depth','color','by_color','sample_color','tolerance','output','building_name','brush','overlay']
    def project_state(self):
        if self.image is None:return None
        working=self.layout_window.export_state() if self.layout_window is not None and self.layout_window.winfo_exists() else self.working_layout
        return dict(kind='image',image=self.image.copy(),mask=self.mask.copy(),original_image=self.original_image,settings={k:getattr(self,k).get() for k in self.setting_keys()},layout=copy.deepcopy(self.layout_state),working_layout=copy.deepcopy(working),appearance=self.appearance.copy(),zoom=self.zoom)
    def changed_project(self,*args):
        if not self.restoring and hasattr(self,'recovery'):
            self.dirty=True;self.recovery.schedule()
    def restore_state(self,state):
        if state.get('kind')!='image':raise ValueError('Open font projects in the main window.')
        if state['image'].size!=state['mask'].size:raise ValueError('Image and mask sizes differ.')
        self.restoring=True
        try:
            self.image=state['image'].copy();self.mask=state['mask'].copy();self.original_image=state.get('original_image',self.image).copy() if state.get('original_image',self.image) is not None else self.image.copy()
            self.layout_state=copy.deepcopy(state.get('layout'));self.working_layout=copy.deepcopy(state.get('working_layout'));self.appearance=state.get('appearance',{}).copy()
            for key in self.setting_keys():
                if key in state.get('settings',{}):getattr(self,key).set(state['settings'][key])
            self.points=[];self.swatch.configure(bg=self.sample_color.get());self.zoom=float(state.get('zoom',1));self.render()
        finally:self.restoring=False
    def remember(self):
        self.history.append(self.project_state());self.history=self.history[-15:];self.future.clear()
        self.layout_state=None;self.working_layout=None;self.changed_project()
    def undo(self):
        if self.busy or not self.history:return
        self.future.append(self.project_state());self.restore_state(self.history.pop());self.changed_project()
    def redo(self):
        if self.busy or not self.future:return
        self.history.append(self.project_state());self.restore_state(self.future.pop());self.changed_project()
    def open_image(self):
        if self.busy or not self.discard():return
        path=filedialog.askopenfilename(parent=self,filetypes=[(self.tr('图片','Images'),'*.png *.jpg *.jpeg *.bmp *.tif *.tiff *.webp')])
        if not path:return
        try:
            im=pipeline.load_image(path)
            self.layout_state=None;self.working_layout=None;self.original_image=im.copy()
            self.image=im;self.mask=Image.new('L',im.size,0);self.history=[];self.future=[];self.dirty=False;self.points=[]
            self.fit();self.status.set(self.tr('点击“裁剪后提取”，在左侧框住标语即可。图片最大处理尺寸为 1600×1000。','Click Crop then extract and select the slogan on the left. Processing size is limited to 1600×1000.'))
        except Exception as e:self.error(e)
    def open_project(self):
        if self.busy or not self.discard():return
        path=filedialog.askopenfilename(parent=self,filetypes=[(self.tr('标语工程','Slogan project'),'*.sloganproj')])
        if not path:return
        try:
            self.restore_state(project_store.load(path));self.history=[];self.future=[];self.dirty=False
            self.status.set(self.tr('已打开工程。','Project opened.'))
        except Exception as e:self.error(e)
    def recover_project(self):
        if self.busy or not self.discard():return
        try:self.restore_state(project_store.recover('image'));self.history=[];self.future=[];self.dirty=True;self.status.set(self.tr('已恢复，包括未应用的字块排列。','Recovered, including unapplied layout edits.'))
        except Exception as e:self.error(e)
    def save_project(self):
        if self.image is None or self.busy:return
        parent=self.grab_current() or self
        path=filedialog.asksaveasfilename(parent=parent,defaultextension='.sloganproj',filetypes=[(self.tr('标语工程','Slogan project'),'*.sloganproj')])
        if not path:return
        try:project_store.save(path,self.project_state());self.dirty=False;self.status.set(path)
        except Exception as e:self.error(e)
    def update_appearance(self,state,name):
        self.appearance=state;self.building_name.set(name);self.height.set(state['height']);self.depth.set(state['depth']);self.color.set(state['color']);self.changed_project()
    def job(self,fn,done):
        if self.busy:return
        self.busy=True
        for b in self.controls:b.state(['disabled'])
        self.status.set(self.tr('处理中……','Processing…'))
        def worker():
            try:self.jobs.put((True,fn()))
            except Exception as e:self.jobs.put((False,e))
        def poll():
            try:ok,result=self.jobs.get_nowait()
            except queue.Empty:self.after(80,poll);return
            self.busy=False
            for b in self.controls:b.state(['!disabled'])
            if ok:done(result)
            else:self.status.set(str(result));self.error(result)
        threading.Thread(target=worker,daemon=True).start();self.after(80,poll)
    def extract(self):
        if self.image is None or self.busy:return
        if self.dirty and not messagebox.askyesno(self.tr('重新提取','Re-extract'),self.tr('重新提取会替换当前修补结果（可撤销）。继续吗？','Replace the current mask? You can undo this operation.'),parent=self):return
        try:operation=self.extraction_job(self.image.copy())
        except Exception as e:self.error(e);return
        def done(mask):
            self.remember();self.mask=mask;self.render();self.status.set(self.tr('已提取。红色区域会生成实体；可在右侧擦除或填补。','Extracted. Coloured pixels become solid geometry. Repair on the right.'))
        self.job(operation,done)
    def crop_extract(self):
        if self.busy or self.image is None:return
        self.mode.set('crop_extract');self.change_mode()
        self.status.set(self.tr('请在左侧原图拖框圈住标语；松开后自动裁剪并提取。可撤销恢复完整原图。','Drag around the slogan on the left. Release to crop and extract. Undo restores the full image.'))
    def change_mode(self):
        self.points=[];self.last=None;self.canvases[0].configure(cursor='crosshair' if self.mode.get()=='eyedropper' else '');self.render()
    def coords(self,canvas,event):
        return (int(canvas.canvasx(event.x)/self.zoom),int(canvas.canvasy(event.y)/self.zoom))
    def bounded(self,p):return self.image is not None and 0<=p[0]<self.image.width and 0<=p[1]<self.image.height
    def source_down(self,event):
        if self.busy or self.image is None:return
        p=self.coords(self.canvases[0],event)
        if not self.bounded(p):return
        if self.mode.get()=='eyedropper':
            rgb=self.image.getpixel(p);self.sample_color.set('#%02x%02x%02x'%rgb);self.swatch.configure(bg=self.sample_color.get());self.by_color.set(True)
            self.mode.set('paint');self.canvases[0].configure(cursor='')
            self.status.set(self.tr('颜色已选取。调整容差后点击“自动提取”。','Color picked. Adjust tolerance and click Extract.'));return
        if self.mode.get() in ('crop','crop_extract'):self.last=p
        elif self.mode.get()=='perspective':
            self.points.append(p);self.render()
            if len(self.points)==4:
                try:
                    im=pipeline.rectify(self.image,self.points)
                    self.remember();self.image=im;self.mask=Image.new('L',im.size,0);self.points=[];self.fit()
                    self.status.set(self.tr('校正完成，请重新提取。','Rectified. Extract the lettering again.'))
                except Exception as e:self.points=[];self.error(e);self.render()
    def source_drag(self,event):
        if self.last is None or self.mode.get() not in ('crop','crop_extract'):return
        c=self.canvases[0];c.delete('selection');x,y=self.coords(c,event)
        c.create_rectangle(self.last[0]*self.zoom,self.last[1]*self.zoom,x*self.zoom,y*self.zoom,outline='cyan',width=2,tags='selection')
    def source_up(self,event):
        if self.busy or self.last is None or self.mode.get() not in ('crop','crop_extract'):return
        p=self.coords(self.canvases[0],event);a=self.last;self.last=None
        bounds=(max(0,min(a[0],p[0])),max(0,min(a[1],p[1])),min(self.image.width,max(a[0],p[0])),min(self.image.height,max(a[1],p[1])))
        if bounds[2]-bounds[0]<2 or bounds[3]-bounds[1]<2:return
        if self.mode.get()=='crop_extract':
            cropped=self.image.crop(bounds)
            try:operation=self.extraction_job(cropped)
            except Exception as e:self.error(e);return
            def done(mask):
                self.remember();self.image=cropped;self.mask=mask;self.mode.set('paint');self.points=[];self.fit()
                self.status.set(self.tr('已裁剪并提取。右侧可擦除或填补；阈值不合适可调整后重新提取。撤销可恢复整张图片。','Cropped and extracted. Repair on the right, or adjust threshold and extract again. Undo restores the full image.'))
            self.job(operation,done)
        else:
            self.remember();self.image=self.image.crop(bounds);self.mask=self.mask.crop(bounds);self.fit()
    def down(self,event):
        self.pointer=(event.x,event.y)
        if self.busy or self.mask is None:return
        p=self.coords(self.canvases[1],event)
        if not self.bounded(p) or self.mode.get() not in ['paint','erase','fill','remove']:return
        self.remember();self.active=True;self.last=p
        if self.mode.get() in ['fill','remove']:
            ImageDraw.floodfill(self.mask,p,255 if self.mode.get()=='fill' else 0,thresh=0)
            self.active=False;self.last=None;self.render()
        else:self.stroke(p,p)
    def stroke(self,a,b):
        try:size=max(1,min(150,self.brush.get()))
        except tk.TclError:return
        draw=ImageDraw.Draw(self.mask);v=255 if self.mode.get()=='paint' else 0
        draw.line([a,b],fill=v,width=size);r=size/2
        draw.ellipse((b[0]-r,b[1]-r,b[0]+r,b[1]+r),fill=v);self.render()
    def drag(self,event):
        self.pointer=(event.x,event.y)
        if self.busy or not self.active:return
        p=self.coords(self.canvases[1],event)
        self.stroke(self.last,p);self.last=p
    def up(self,event):self.active=False;self.last=None
    def fit(self):
        if self.image is None:return
        self.update_idletasks()
        self.zoom=min(max(100,c.winfo_width())/self.image.width for c in self.canvases)
        self.zoom=min(self.zoom,min(max(100,c.winfo_height())/self.image.height for c in self.canvases))
        self.zoom=max(.1,min(4,self.zoom));self.render()
        for c in self.canvases:c.xview_moveto(0);c.yview_moveto(0)
    def set_zoom(self,value):self.zoom=max(.1,min(6,value));self.render()
    def render(self):
        if self.image is None:
            for c in self.canvases:
                c.delete('all');c.create_text(max(150,c.winfo_width()/2),max(100,c.winfo_height()/2),text=self.tr('导入一张图片，开始制作标语','Import an image to start'),fill='#64748b',font=('Microsoft YaHei UI',12))
            return
        result=Image.new('RGB',self.image.size,'#eee9dd')
        if self.overlay.get():result=Image.blend(result,self.image,.6)
        try:result.paste(self.color.get(),(0,0),self.mask)
        except ValueError:result.paste('#be0f0c',(0,0),self.mask)
        size=(max(1,int(self.image.width*self.zoom)),max(1,int(self.image.height*self.zoom)))
        for c,im in zip(self.canvases,[self.image,result]):
            c.delete('all');c.photo=ImageTk.PhotoImage(im.resize(size,Image.Resampling.NEAREST if self.zoom>1 else Image.Resampling.BILINEAR))
            c.create_image(0,0,image=c.photo,anchor='nw');c.configure(scrollregion=(0,0,*size))
        for i,(x,y) in enumerate(self.points):
            self.canvases[0].create_oval(x*self.zoom-4,y*self.zoom-4,x*self.zoom+4,y*self.zoom+4,fill='cyan')
            self.canvases[0].create_text(x*self.zoom+10,y*self.zoom,text=str(i+1),fill='cyan')
        self.draw_brush()
        if not self.restoring:self.recovery.schedule()
    def layout(self):
        if self.busy or self.mask is None:return
        from image_layout import LayoutEditor
        if self.layout_window is not None and self.layout_window.winfo_exists():self.layout_window.lift();return
        self.layout_window=LayoutEditor(self)
    def extraction_job(self,image):
        minimum=self.minimum.get()
        if self.by_color.get():
            color=self.sample_color.get();tolerance=self.tolerance.get()
            return lambda:pipeline.extract_color(image,color,tolerance,minimum)
        dark=self.dark.get();threshold=self.threshold.get();adaptive=self.adaptive.get()
        return lambda:pipeline.extract(image,dark,threshold,minimum,adaptive)
    def pick_source_color(self):
        if self.image is None or self.busy:return
        self.mode.set('eyedropper');self.change_mode()
        self.status.set(self.tr('请点击左侧文字内部的颜色，尽量避开边缘与阴影。','Click inside a letter in the source, away from edges and shadows.'))
    def brush_cursor(self,event):
        self.pointer=(event.x,event.y);self.draw_brush()
    def hide_brush(self,event=None):
        self.pointer=None;self.canvases[1].delete('brush-cursor')
    def draw_brush(self):
        c=self.canvases[1];c.delete('brush-cursor')
        if self.pointer is None or self.mask is None or self.mode.get() not in ('paint','erase'):return
        try:r=max(1,min(150,self.brush.get()))*self.zoom/2
        except tk.TclError:return
        x,y=self.pointer;x=c.canvasx(x);y=c.canvasy(y)
        c.create_oval(x-r,y-r,x+r,y+r,outline='white',width=3,tags='brush-cursor')
        c.create_oval(x-r,y-r,x+r,y+r,outline='#2563eb' if self.mode.get()=='paint' else '#c43535',width=1,tags='brush-cursor')
    def studio(self):
        if self.mask is None or self.busy:return
        try:
            mask=self.mask.copy();smooth=float(self.smooth.get());height=float(self.height.get());depth=float(self.depth.get());color=self.color.get();output=self.output.get()
            if mask.getbbox() is None:raise ValueError(self.tr('请先提取或绘制文字。','Extract or paint lettering first.'))
        except Exception as e:self.error(e);return
        from model_studio import ModelStudio
        cached={}
        def builder(h,d):
            if 'shape' not in cached:cached['shape']=pipeline.polygons(mask,smooth)
            return pipeline.extrude(cached['shape'],h,d)
        def exporter(h,d,c,base,age,name):return pipeline.generate_image(mask,output,h,d,c,smooth,base,age,name)
        ModelStudio(self,self.language,builder,exporter,height,depth,color,self.tr('图片标语 · 当前修补结果','Image slogan · current repaired mask'),initial=dict(self.appearance,height=height,depth=depth,color=color),on_change=self.update_appearance,on_save=self.save_project,building_name=self.building_name.get())
    def pick_color(self):
        c=colorchooser.askcolor(self.color.get(),parent=self)[1]
        if c:self.color.set(c);self.render()
    def pick_output(self):
        p=filedialog.askdirectory(parent=self)
        if p:self.output.set(p)
    def check(self):
        if self.mask is None:return
        try:mask=self.mask.copy();smooth=self.smooth.get()
        except Exception as e:self.error(e);return
        self.job(lambda:pipeline.complexity(mask,smooth),lambda r:self.status.set(self.tr('顶点 {vertices}/65535；独立块 {components}；字内空洞 {holes}。','Vertices {vertices}/65535; components {components}; holes {holes}.').format(**r)))
    def generate(self):
        if self.mask is None:return
        try:args=(self.mask.copy(),self.output.get(),float(self.height.get()),float(self.depth.get()),self.color.get(),self.smooth.get(),self.appearance.get('base_style','strip'),self.appearance.get('age',0),self.building_name.get())
        except Exception as e:self.error(e);return
        def done(path):
            self.status.set(str(path));messagebox.showinfo(self.tr('生成完成','Generated'),str(path)+'\n\n'+self.tr('将数字文件夹复制到 media_soviet/workshop_wip。分离笔画可能悬空。','Copy the numeric folder to media_soviet/workshop_wip. Disconnected strokes may float.'),parent=self)
        self.job(lambda:pipeline.generate_image(*args),done)
    def destroy(self):
        if hasattr(self,'recovery'):self.recovery.stop(flush=True)
        ui_theme.cancel_callbacks(self);super().destroy()
    def close(self):
        if not self.busy and self.discard():self.destroy()

def open_editor(parent,language,output):
    existing=getattr(parent,'image_editor',None)
    if existing is not None and existing.winfo_exists():
        if existing.language==language:existing.lift();return existing
        if existing.busy:
            existing.after(150,lambda:open_editor(parent,language,output));return existing
        state=existing.project_state();history=existing.history;future=existing.future;dirty=existing.dirty
        existing.destroy()
        parent.image_editor=ImageEditor(parent,language,output)
        if state is not None:parent.image_editor.restore_state(state)
        parent.image_editor.history=history;parent.image_editor.future=future;parent.image_editor.dirty=dirty
        return parent.image_editor
    parent.image_editor=ImageEditor(parent,language,output)
    return parent.image_editor
