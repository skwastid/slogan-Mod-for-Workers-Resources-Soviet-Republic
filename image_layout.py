import ui_i18n
"""Cut repaired silhouettes into movable, scalable, rotatable pieces."""
import copy
import math
import tkinter as tk
from tkinter import ttk, messagebox
from PIL import Image, ImageTk, ImageChops, ImageDraw
import ui_theme


def transformed(piece):
    scale=float(piece['scale']);angle=float(piece['angle'])
    if not math.isfinite(scale) or not .1<=scale<=5 or not math.isfinite(angle):
        raise ValueError('Scale: 0.1–5; rotation must be finite.')
    im=piece['mask']
    size=(max(1,round(im.width*scale)),max(1,round(im.height*scale)))
    return im.resize(size,Image.Resampling.NEAREST).rotate(angle,resample=Image.Resampling.NEAREST,expand=True)


def compose(base,pieces):
    items=[(base,0,0)]+[(transformed(p),round(p['x']),round(p['y'])) for p in pieces]
    bounds=[]
    for im,x,y in items:
        box=im.getbbox()
        if box:bounds.append((x+box[0],y+box[1],x+box[2],y+box[3]))
    if not bounds:raise ValueError('No lettering remains.')
    left=min(b[0] for b in bounds);top=min(b[1] for b in bounds)
    right=max(b[2] for b in bounds);bottom=max(b[3] for b in bounds)
    if right-left>1600 or bottom-top>1000:raise ValueError('Layout exceeds 1600 × 1000 pixels. Reduce scale or spacing.')
    result=Image.new('L',(right-left,bottom-top))
    for im,x,y in items:
        layer=Image.new('L',result.size);layer.paste(im,(x-left,y-top))
        result=ImageChops.lighter(result,layer)
    return result


def align_pieces(pieces,selected,operation):
    indices=sorted(selected)
    if len(indices)<2:return
    axis='x' if operation in ('left','right','center_x','distribute_x') else 'y'
    sizes={i:(transformed(pieces[i]).width if axis=='x' else transformed(pieces[i]).height) for i in indices}
    start=min(pieces[i][axis] for i in indices);end=max(pieces[i][axis]+sizes[i] for i in indices)
    if operation.startswith('distribute'):
        indices.sort(key=lambda i:pieces[i][axis]);gap=(end-start-sum(sizes.values()))/(len(indices)-1);cursor=start
        for i in indices:pieces[i][axis]=cursor;cursor+=sizes[i]+gap
    else:
        for i in indices:
            pieces[i][axis]=start if operation in ('left','top') else end-sizes[i] if operation in ('right','bottom') else (start+end-sizes[i])/2


class LayoutEditor(tk.Toplevel):
    """Source selection above, live arrangement below. Source pixels stay immutable."""
    def __init__(self,parent):
        super().__init__(parent);self.parent=parent;self.tr=parent.tr;ui_theme.setup(self)
        self.title(self.tr('拆字与实时排列','Select letters · Live layout'))
        ui_theme.fit_window(self,1180,940)
        self.page_scroll=ui_theme.ScrollPage(self,min_width=1060,min_height=800);self.page_scroll.pack(fill='both',expand=True)
        content=self.page_scroll.content
        self.original=parent.mask.copy();self.base=self.original.copy()
        self.pieces=[];self.history=[];self.future=[];self.selected=None;self.selection=set()
        self.pending=Image.new('L',self.base.size);self.points=[];self.start=None;self.gesture=None
        self.mode=tk.StringVar(value='rect');self.keep=tk.BooleanVar(value=True)
        saved=getattr(parent,'working_layout',None) or getattr(parent,'layout_state',None)
        if saved:
            self.original=saved['original'].copy();self.base=saved['base'].copy();self.pieces=copy.deepcopy(saved['pieces']);self.keep.set(saved.get('keep',True));self.pending=Image.new('L',self.base.size)
        self.scale=tk.StringVar(value='100');self.angle=tk.StringVar(value='0')
        self.note=tk.StringVar(value=self.tr('先在上方选字，再点“加入排列”；下方直接拖动字块。','Select above, then Add to layout. Drag pieces directly below.'))
        self.syncing=False;self.live_job=None;self.group_job=None;self.grouping=False
        self.views={};self.photos={};self.bounds={};self.handles={}
        bar=ui_theme.FlowBar(content,padding=8);bar.pack(fill='x')
        for mode,zh,en in [('rect','矩形框选','Rectangle'),('polygon','连续点选','Polygon')]:
            ttk.Radiobutton(bar,text=self.tr(zh,en),variable=self.mode,value=mode,command=self.clear_selection).pack(side='left',padx=3)
        for zh,en,fn in [('完成点选','Close polygon',self.finish_polygon),('清除选区','Clear selection',self.clear_selection),('加入排列 ↓','Add to layout ↓',self.cut),('撤销','Undo',self.undo),('重做','Redo',self.redo)]:
            ttk.Button(bar,text=self.tr(zh,en),command=fn,style='Primary.TButton' if fn==self.cut else 'TButton').pack(side='left',padx=3)
        self.panes=ttk.Panedwindow(content,orient='vertical');self.panes.pack(fill='both',expand=True,padx=8)
        source=ttk.LabelFrame(self.panes,text=self.tr('① 选字：拖框或连续点轮廓，双击完成。蓝色是待拆笔画，灰色是已拆部分。','① Select: drag rectangle or click polygon vertices; double-click to finish. Blue = selection, grey = extracted.'))
        self.panes.add(source,weight=1)
        self.source=tk.Canvas(source,bg='#eee9dd',highlightthickness=0);self.source.pack(fill='both',expand=True)
        lower=ttk.LabelFrame(self.panes,text=self.tr('② 实时排列：拖动字块；右下角方块缩放，上方圆点旋转。','② Live layout: drag to move; bottom-right square scales; top circle rotates.'))
        self.panes.add(lower,weight=2)
        side=ttk.Frame(lower,padding=8);side.pack(side='right',fill='y')
        self.list=tk.Listbox(side,width=19,height=7,exportselection=False,selectmode='extended');self.list.pack(fill='both',expand=True)
        self.list.bind('<<ListboxSelect>>',self.select_list)
        for title,var,lo,hi in [(self.tr('比例 %（实时）','Scale % (live)'),self.scale,10,500),(self.tr('旋转 °（实时）','Rotation ° (live)'),self.angle,-180,180)]:
            ttk.Label(side,text=title).pack(anchor='w',pady=(6,0))
            entry=ttk.Entry(side,textvariable=var,width=15);entry.pack(fill='x')
            slider=ttk.Scale(side,from_=lo,to=hi,command=lambda v,var=var:var.set(f'{float(v):.1f}'))
            slider.pack(fill='x');var.trace_add('write',self.schedule_live)
            if var is self.scale:self.scale_slider=slider
            else:self.angle_slider=slider
        ttk.Button(side,text=self.tr('恢复原尺寸 / 角度','Reset size / angle'),command=self.reset_transform).pack(fill='x',pady=5)
        ttk.Button(side,text=self.tr('放回上方原图','Return to source'),command=self.return_piece).pack(fill='x')
        self.canvas=tk.Canvas(lower,bg='#faf8f2',highlightthickness=0);self.canvas.pack(fill='both',expand=True)
        foot=ui_theme.FlowBar(content,padding=8);foot.pack(fill='x')
        ttk.Button(foot,text=self.tr('排成一行 / 底部对齐','One row / align bottoms'),command=self.arrange).pack(side='left')
        ttk.Button(foot,text=self.tr('保存工程','Save project'),command=parent.save_project).pack(side='left',padx=4)
        ttk.Button(foot,text=self.tr('适应窗口','Fit views'),command=self.fit).pack(side='left',padx=6)
        ttk.Checkbutton(foot,text=self.tr('保留未拆部分','Keep uncut pixels'),variable=self.keep,command=self.render_layout).pack(side='left')
        ttk.Button(foot,text=self.tr('应用到修补图','Apply to mask'),command=self.apply,style='Primary.TButton').pack(side='right')
        operations=ui_theme.FlowBar(content,padding=(8,2));operations.pack(fill='x')
        self.operations={self.tr('左对齐','Align left'):'left',self.tr('右对齐','Align right'):'right',self.tr('顶部对齐','Align top'):'top',self.tr('底部对齐','Align bottom'):'bottom',self.tr('水平居中','Center horizontally'):'center_x',self.tr('垂直居中','Center vertically'):'center_y',self.tr('水平等间距','Equal horizontal gaps'):'distribute_x',self.tr('垂直等间距','Equal vertical gaps'):'distribute_y'}
        self.operation=tk.StringVar(value=next(iter(self.operations)))
        ttk.Combobox(operations,textvariable=self.operation,values=list(self.operations),state='readonly',width=25).pack(side='left')
        ttk.Button(operations,text=self.tr('应用到选中字块','Apply to selected'),command=self.align_selected).pack(side='left',padx=5)
        ttk.Button(operations,text=self.tr('全选字块','Select all'),command=self.select_all).pack(side='left')
        ttk.Label(content,textvariable=self.note,padding=(10,2),wraplength=1150).pack(fill='x')
        ttk.Label(content,text=self.tr('Ctrl 点选多选 · 空白处拖框多选 · 拖动选中组；工程保留独立字块。再次用笔刷修补会合并字块，可撤销。','Ctrl-click / drag an empty area to multi-select. Drag selected pieces together. Projects preserve layers; painting merges them (undo available).'),padding=(10,2),wraplength=1120).pack(fill='x')
        for c in [self.source,self.canvas]:
            self.views[c]=[1.,20.,30.]
            c.bind('<MouseWheel>',lambda e,c=c:self.wheel(c,e))
            c.bind('<ButtonPress-3>',lambda e,c=c:self.pan_start(c,e))
            c.bind('<B3-Motion>',lambda e,c=c:self.pan(c,e))
        self.source.bind('<ButtonPress-1>',self.source_down);self.source.bind('<B1-Motion>',self.source_drag);self.source.bind('<ButtonRelease-1>',self.source_up)
        self.source.bind('<Double-Button-1>',lambda e:self.finish_polygon())
        self.canvas.bind('<ButtonPress-1>',self.down);self.canvas.bind('<B1-Motion>',self.drag);self.canvas.bind('<ButtonRelease-1>',self.up)
        self.bind('<Control-z>',lambda e:self.undo());self.bind('<Control-y>',lambda e:self.redo())
        self.protocol('WM_DELETE_WINDOW',self.close);self.transient(parent);self.grab_set()
        self.bind('<Map>',lambda e:self.after(100,self.fit) if e.widget is self else None)

    def snapshot(self):return (self.base.copy(),copy.deepcopy(self.pieces))
    def remember(self):
        self.history.append(self.snapshot());self.history=self.history[-20:];self.future.clear()
    def cancel_live(self):
        for job in [self.live_job,self.group_job]:
            if job:self.after_cancel(job)
        self.live_job=self.group_job=None;self.grouping=False
    def undo(self):
        self.cancel_live()
        if self.history:
            self.future.append(self.snapshot());self.base,self.pieces=self.history.pop();self.selected=None;self.selection=set();self.clear_selection();self.render()
    def redo(self):
        self.cancel_live()
        if self.future:
            self.history.append(self.snapshot());self.base,self.pieces=self.future.pop();self.selected=None;self.selection=set();self.clear_selection();self.render()
    def point(self,c,e):
        z,ox,oy=self.views[c];return ((e.x-ox)/z,(e.y-oy)/z)
    def screen(self,c,x,y):
        z,ox,oy=self.views[c];return (x*z+ox,y*z+oy)
    def draw_mask(self,c,mask,x,y,color):
        z,ox,oy=self.views[c]
        rgba=Image.new('RGBA',mask.size,color);rgba.putalpha(mask)
        photo=ImageTk.PhotoImage(rgba.resize((max(1,round(mask.width*z)),max(1,round(mask.height*z))),Image.Resampling.NEAREST))
        self.photos[c].append(photo);c.create_image(x*z+ox,y*z+oy,image=photo,anchor='nw')
    def clear_selection(self):
        self.pending=Image.new('L',self.base.size);self.points=[];self.start=None;self.render_source()
    def selection_mask(self,points):
        area=Image.new('L',self.base.size);ImageDraw.Draw(area).polygon(points,fill=255)
        return ImageChops.darker(area,self.base)
    def source_down(self,e):
        p=self.point(self.source,e)
        if self.mode.get()=='rect':self.start=p;self.points=[];self.pending=Image.new('L',self.base.size)
        else:
            if not self.points or math.dist(p,self.points[-1])>1:self.points.append(p)
            if len(self.points)>=3:self.pending=self.selection_mask(self.points)
            self.render_source()
    def source_drag(self,e):
        if self.mode.get()!='rect' or self.start is None:return
        x,y=self.point(self.source,e);a,b=self.start
        self.points=[(a,b),(x,b),(x,y),(a,y)];self.pending=self.selection_mask(self.points);self.render_source()
    def source_up(self,e):
        if self.mode.get()=='rect' and self.start is not None:self.source_drag(e);self.start=None
    def finish_polygon(self):
        if len(self.points)>=3:
            self.pending=self.selection_mask(self.points);self.note.set(self.tr('蓝色笔画已选中，点“加入排列”。','Blue strokes selected. Click Add to layout.'));self.render_source()
    def cut(self):
        box=self.pending.getbbox()
        if not box:self.note.set(self.tr('选区内没有未拆出的笔画。','No remaining strokes in the selection.'));return
        self.flush_live();self.remember();full=self.pending.copy()
        self.base=ImageChops.subtract(self.base,full)
        self.pieces.append(dict(mask=full.crop(box),source=full,x=box[0],y=box[1],scale=1.,angle=0.))
        self.select(len(self.pieces)-1);self.clear_selection();self.render()
        self.note.set(self.tr('字块已加入下方，可直接拖动；继续在上方选下一个字。','Piece added below. Drag it freely, or select the next letter above.'))
    def render_source(self):
        c=self.source;c.delete('all');self.photos[c]=[]
        self.draw_mask(c,self.original,0,0,'#ccc7bb');self.draw_mask(c,self.base,0,0,'#5b5650')
        if self.selected is not None and self.selected<len(self.pieces):self.draw_mask(c,self.pieces[self.selected]['source'],0,0,'#279cae')
        self.draw_mask(c,self.pending,0,0,'#1682eb')
        if len(self.points)>1:
            coords=[v for p in self.points for v in self.screen(c,*p)]
            c.create_line(*coords,fill='#1682eb',width=2)
            if len(self.points)>=3:c.create_line(*self.screen(c,*self.points[-1]),*self.screen(c,*self.points[0]),fill='#1682eb',dash=(4,3))
        for p in self.points:
            x,y=self.screen(c,*p);c.create_oval(x-3,y-3,x+3,y+3,fill='#1682eb',outline='white')
    def render_layout(self):
        c=self.canvas;c.delete('all');self.photos[c]=[];self.bounds={};self.handles={}
        if self.keep.get():self.draw_mask(c,self.base,0,0,'#877b72')
        for i,p in enumerate(self.pieces):
            im=transformed(p);self.draw_mask(c,im,p['x'],p['y'],'#be0f0c')
            a,b=self.screen(c,p['x'],p['y']);r,d=self.screen(c,p['x']+im.width,p['y']+im.height)
            self.bounds[i]=(a,b,r,d)
            if i in self.selection:
                c.create_rectangle(a,b,r,d,outline='#1682eb',width=2)
                c.create_text(a,b-9,text=self.tr('字块 ','Piece ')+str(i+1),fill='#1261a8',anchor='sw')
                c.create_rectangle(r-5,d-5,r+5,d+5,fill='white',outline='#1682eb',width=2)
                cx=(a+r)/2;c.create_line(cx,b,cx,b-25,fill='#1682eb')
                c.create_oval(cx-5,b-30,cx+5,b-20,fill='white',outline='#1682eb',width=2)
                if i==self.selected:self.handles={'scale':(r,d),'rotate':(cx,b-25)}
        self.list.delete(0,'end')
        for i in range(len(self.pieces)):self.list.insert('end',self.tr('字块 ','Piece ')+str(i+1))
        for i in self.selection:self.list.selection_set(i)
        if hasattr(self.parent,'recovery'):self.parent.recovery.schedule()
    def render(self):self.render_source();self.render_layout()
    def select(self,i):
        self.cancel_live();self.selected=i;self.selection={i} if i is not None else set();self.sync_fields()
    def sync_fields(self):
        if self.selected is None:return
        self.syncing=True;p=self.pieces[self.selected]
        self.scale_slider.set(p['scale']*100);self.angle_slider.set(p['angle'])
        self.scale.set(f"{p['scale']*100:.1f}");self.angle.set(f"{p['angle']:.1f}");self.syncing=False
    def select_list(self,event=None):
        chosen=self.list.curselection()
        if set(chosen)!=self.selection:
            self.flush_live();self.selection=set(chosen);self.selected=chosen[-1] if chosen else None;self.sync_fields();self.render()
    def schedule_live(self,*args):
        if self.syncing or self.selected is None:return
        if self.live_job:self.after_cancel(self.live_job)
        self.live_job=self.after(40,self.update_piece)
    def flush_live(self):
        if self.live_job:self.after_cancel(self.live_job);self.live_job=None;self.update_piece()
        self.cancel_live()
    def end_group(self):self.grouping=False;self.group_job=None
    def update_piece(self):
        self.live_job=None
        if self.selected is None:return
        try:
            scale=float(self.scale.get())/100;angle=float(self.angle.get())
            if not math.isfinite(angle) or not -180<=angle<=180 or not .1<=scale<=5:raise ValueError()
        except (ValueError,tk.TclError):
            self.note.set(self.tr('比例范围 10–500%，角度范围 −180–180°。','Scale: 10–500%; angle: −180–180°.'));return
        p=self.pieces[self.selected]
        if scale==p['scale'] and angle==p['angle']:return
        if not self.grouping:self.remember();self.grouping=True
        old=transformed(p);cx=p['x']+old.width/2;cy=p['y']+old.height/2
        p['scale']=scale;p['angle']=angle;new=transformed(p);p['x']=cx-new.width/2;p['y']=cy-new.height/2
        if self.group_job:self.after_cancel(self.group_job)
        self.group_job=self.after(650,self.end_group);self.render_layout()
    def reset_transform(self):self.scale.set('100');self.angle.set('0')
    def down(self,e):
        self.flush_live();point=self.point(self.canvas,e)
        if self.selected is not None:
            for kind,(x,y) in self.handles.items():
                if math.hypot(e.x-x,e.y-y)<=10:
                    self.remember();p=self.pieces[self.selected];im=transformed(p);cx=p['x']+im.width/2;cy=p['y']+im.height/2
                    self.gesture=(kind,point,copy.copy(p),(cx,cy));return
        chosen=None
        for i in reversed(range(len(self.pieces))):
            p=self.pieces[i];im=transformed(p);x=round(point[0]-p['x']);y=round(point[1]-p['y'])
            if 0<=x<im.width and 0<=y<im.height and im.getpixel((x,y)):
                chosen=i;break
        additive=bool(getattr(e,'state',0)&4)
        if chosen is not None:
            if additive:
                if chosen in self.selection:self.selection.remove(chosen)
                else:self.selection.add(chosen)
            elif chosen not in self.selection:self.selection={chosen}
            self.selected=chosen if chosen in self.selection else next(iter(self.selection),None)
            self.sync_fields();self.remember()
            self.gesture=('move_group',point,{i:(self.pieces[i]['x'],self.pieces[i]['y']) for i in self.selection},None)
        else:
            if not additive:self.selection=set();self.selected=None
            self.gesture=('marquee',point,set(self.selection),None)
        self.render()
    def drag(self,e):
        if not self.gesture:return
        kind,start,old,center=self.gesture;x,y=self.point(self.canvas,e)
        if kind=='marquee':
            a,b=min(start[0],x),min(start[1],y);r,d=max(start[0],x),max(start[1],y)
            self.selection=set(old)
            for i,p in enumerate(self.pieces):
                im=transformed(p)
                if p['x']<r and p['x']+im.width>a and p['y']<d and p['y']+im.height>b:self.selection.add(i)
            self.selected=next(iter(self.selection),None);self.render_layout()
            self.canvas.create_rectangle(*self.screen(self.canvas,a,b),*self.screen(self.canvas,r,d),outline='#1682eb',dash=(4,3));return
        if kind=='move_group':
            for i,(px,py) in old.items():self.pieces[i]['x']=px+x-start[0];self.pieces[i]['y']=py+y-start[1]
        elif self.selected is not None:
            p=self.pieces[self.selected];cx,cy=center
            if kind=='scale':p['scale']=max(.1,min(5,old['scale']*math.hypot(x-cx,y-cy)/max(1,math.hypot(start[0]-cx,start[1]-cy))))
            else:p['angle']=(old['angle']-math.degrees(math.atan2(y-cy,x-cx)-math.atan2(start[1]-cy,start[0]-cx))+180)%360-180
            im=transformed(p);p['x']=cx-im.width/2;p['y']=cy-im.height/2;self.sync_fields()
        self.render_layout()
    def up(self,e):self.gesture=None;self.sync_fields();self.render_layout()
    def select_all(self):
        self.selection=set(range(len(self.pieces)));self.selected=next(iter(self.selection),None);self.sync_fields();self.render()
    def align_selected(self):
        if len(self.selection)<2:self.note.set(self.tr('请先选中至少两个字块。','Select at least two pieces.'));return
        self.flush_live();self.remember();align_pieces(self.pieces,self.selection,self.operations[self.operation.get()]);self.render_layout()
    def export_state(self):
        return dict(original=self.original.copy(),base=self.base.copy(),pieces=copy.deepcopy(self.pieces),keep=self.keep.get())
    def return_piece(self):
        if self.selected is None:return
        self.flush_live();self.remember()
        for i in sorted(self.selection or {self.selected},reverse=True):
            p=self.pieces.pop(i);self.base=ImageChops.lighter(self.base,p['source'])
        self.selected=None;self.selection=set();self.render()
    def arrange(self):
        if not self.pieces:return
        self.flush_live();self.remember();images=[transformed(p) for p in self.pieces];baseline=max(im.height for im in images);x=0
        for p,im in zip(self.pieces,images):p['x']=x;p['y']=baseline-im.height;x+=im.width+12
        self.fit_layout();self.render_layout()
    def fit_canvas(self,c,box):
        x,y,r,b=box;w=max(200,c.winfo_width());h=max(100,c.winfo_height())
        z=max(.1,min(4,(w-70)/max(1,r-x),(h-70)/max(1,b-y)))
        self.views[c]=[z,(w-(r-x)*z)/2-x*z,(h-(b-y)*z)/2-y*z]
    def fit_layout(self):
        boxes=[]
        if self.keep.get() and self.base.getbbox():boxes.append(self.base.getbbox())
        for p in self.pieces:
            im=transformed(p);boxes.append((p['x'],p['y'],p['x']+im.width,p['y']+im.height))
        if not boxes:boxes=[(0,0,*self.base.size)]
        self.fit_canvas(self.canvas,(min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)))
    def fit(self):
        self.update_idletasks();self.fit_canvas(self.source,(0,0,*self.base.size));self.fit_layout();self.render()
    def wheel(self,c,e):
        x,y=self.point(c,e);z,ox,oy=self.views[c];z=max(.1,min(8,z*(1.2 if e.delta>0 else 1/1.2)))
        self.views[c]=[z,e.x-x*z,e.y-y*z];self.render()
    def pan_start(self,c,e):self.pan_state=(c,e.x,e.y,list(self.views[c]))
    def pan(self,c,e):
        _,x,y,(z,ox,oy)=self.pan_state;self.views[c]=[z,ox+e.x-x,oy+e.y-y];self.render()
    def apply(self):
        self.flush_live()
        try:mask=compose(self.base if self.keep.get() else Image.new('L',self.base.size),self.pieces)
        except Exception as e:messagebox.showerror(self.tr('无法应用','Cannot apply'),ui_i18n.error(self.parent.language,e),parent=self);return
        self.parent.remember();self.parent.mask=mask
        source=Image.new('RGB',mask.size,'#eee9dd');source.paste('#333333',(0,0),mask)
        self.parent.image=source;self.parent.layout_state=self.export_state();self.parent.working_layout=None;self.parent.points=[];self.parent.fit();self.destroy()
    def destroy(self):
        self.cancel_live();self.parent.layout_window=None;ui_theme.cancel_callbacks(self);super().destroy()
    def close(self):
        if not self.history or messagebox.askyesno(self.tr('放弃重排？','Discard layout?'),self.tr('关闭并放弃未应用的重排？','Close and discard unapplied layout edits?'),parent=self):
            self.parent.working_layout=None;self.destroy()
            if hasattr(self.parent,'recovery'):self.parent.recovery.schedule()
