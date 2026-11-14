"""Installed-font names and Chinese coverage, without copying font files."""
from functools import lru_cache
from pathlib import Path
from fontTools.ttLib import TTFont

@lru_cache(maxsize=2048)
def describe(path):
    with TTFont(path,fontNumber=0,lazy=True) as font:
        names=font['name'].names
        def pick(ids,chinese):
            candidates=[]
            for item in names:
                if item.nameID not in ids:continue
                is_zh=item.platformID==3 and (item.langID&0x3ff)==4
                if is_zh!=chinese:continue
                try:value=item.toUnicode().strip()
                except Exception:continue
                if value:candidates.append((ids.index(item.nameID),0 if item.langID==0x804 else 1,value))
            return min(candidates)[2] if candidates else ''
        en=pick([4,1],False) or Path(path).stem
        zh=pick([4,1],True)
        cmap=font.getBestCmap() or {}
        chinese=all(ord(c) in cmap for c in '中文')
        aliases=' '.join(dict.fromkeys(item.toUnicode() for item in names if item.nameID in (1,4,6,16) and item.isUnicode()))
        return dict(en=en,zh=zh,chinese=chinese,aliases=aliases)

def label(path):
    info=describe(path)
    title=info['zh'] or info['en']
    if info['zh'] and info['zh']!=info['en']:title+=' / '+info['en']
    return title+' — '+Path(path).name

def matches(path,query='',chinese_only=False):
    info=describe(path)
    return (not chinese_only or info['chinese']) and query.casefold() in (info['aliases']+' '+Path(path).name).casefold()
