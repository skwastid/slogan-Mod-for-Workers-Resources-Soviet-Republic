"""Shared game-safe names and rendered model thumbnails."""
import unicodedata

def name(value):
    value=str(value).strip()
    if len(value)>80 or any(c in '"\\' or unicodedata.category(c).startswith('C') for c in value):
        raise ValueError('Building name: up to 80 characters; no quotes, backslashes or control characters.')
    return value

def thumbnail(root,letters,width,height,depth,base,color,age,base_size=None,base_color=None,supports=False):
    import preview3d
    from PIL import Image
    data=preview3d.scene(letters,width,height,depth,base,color,age,base_size=base_size,base_color=base_color,supports=supports)
    picture=preview3d.render(data,512,512,pivot=preview3d.focus(data,base))
    picture.save(root/'previewimage.png')
    picture.resize((256,256),Image.Resampling.LANCZOS).save(root/'slogan'/'imagegui.png')
