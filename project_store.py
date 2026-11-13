"""Versioned, atomic full projects and per-session recovery, without embedding fonts."""
from pathlib import Path
import io,json,zipfile,os,tempfile,time
from PIL import Image

MAX_PROJECT_BYTES=160_000_000

def save(path,state):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True);images={}
    def encode(value):
        if isinstance(value,Image.Image):
            key=f'images/{len(images)}.png';images[key]=value;return {'__image__':key}
        if isinstance(value,dict):return {str(k):encode(v) for k,v in value.items()}
        if isinstance(value,(list,tuple)):return [encode(v) for v in value]
        if isinstance(value,Path):return str(value)
        return value
    document={'format':'slogan-full-project','version':1,'state':encode(state)}
    fd,tmp=tempfile.mkstemp(prefix=path.name+'.',suffix='.tmp',dir=path.parent);os.close(fd)
    try:
        with zipfile.ZipFile(tmp,'w',zipfile.ZIP_DEFLATED) as z:
            z.writestr('project.json',json.dumps(document,ensure_ascii=False,allow_nan=False))
            for key,im in images.items():
                data=io.BytesIO();im.save(data,format='PNG');z.writestr(key,data.getvalue())
        if Path(tmp).stat().st_size>MAX_PROJECT_BYTES:raise ValueError('Project is too large.')
        os.replace(tmp,path)
    finally:
        if Path(tmp).exists():Path(tmp).unlink()

def load(path):
    with zipfile.ZipFile(path) as z:
        if sum(n.file_size for n in z.infolist())>MAX_PROJECT_BYTES:raise ValueError('Project is too large.')
        if 'project.json' not in z.namelist():raise ValueError('Only the current 1.0 full project format is supported.')
        doc=json.loads(z.read('project.json'))
        if doc.get('format')!='slogan-full-project' or doc.get('version')!=1:raise ValueError('Unsupported project version.')
        cache={}
        def decode(value):
            if isinstance(value,dict) and set(value)=={'__image__'}:
                name=value['__image__']
                if name not in cache:
                    if not isinstance(name,str) or not name.startswith('images/'):raise ValueError('Invalid image reference.')
                    im=Image.open(io.BytesIO(z.read(name)))
                    if im.width>1600 or im.height>1000:raise ValueError('Image dimensions exceed project limits.')
                    im.load();cache[name]=im.convert('RGB' if im.mode in ('RGB','RGBA') else 'L')
                return cache[name].copy()
            if isinstance(value,dict):return {k:decode(v) for k,v in value.items()}
            if isinstance(value,list):return [decode(v) for v in value]
            return value
        state=decode(doc['state'])
        if state.get('kind') not in ('font','image'):raise ValueError('Unknown project type.')
        return state

def recovery_path(kind):
    root=Path(os.environ.get('SLOGAN_RECOVERY_DIR',str(Path(os.environ.get('LOCALAPPDATA',Path.home()))/'YourOwnBigSlogan'/'Recovery')))
    return root/(kind+'.sloganproj')

class Recovery:
    def __init__(self,owner,kind,getter):
        self.owner=owner;self.kind=kind;self.getter=getter;self.timer=None;self.error=None;self.written=None
    def schedule(self):
        if self.timer:self.owner.after_cancel(self.timer)
        self.timer=self.owner.after(1000,self.flush)
    def flush(self):
        self.timer=None
        try:
            state=self.getter()
            if state is None:return
            path=recovery_path(self.kind)
            # Keep a valid previous checkpoint if the latest file later becomes damaged.
            if path.exists():
                try:
                    load(path);previous=path.with_suffix('.previous.sloganproj')
                    previous.write_bytes(path.read_bytes())
                except Exception:pass
            save(path,state);self.error=None;self.written=time.time()
        except Exception as e:self.error=str(e)
    def stop(self,flush=False):
        if self.timer:self.owner.after_cancel(self.timer);self.timer=None
        if flush:self.flush()

def recover(kind):
    path=recovery_path(kind)
    try:return load(path)
    except Exception:
        previous=path.with_suffix('.previous.sloganproj')
        if previous.exists():return load(previous)
        raise
