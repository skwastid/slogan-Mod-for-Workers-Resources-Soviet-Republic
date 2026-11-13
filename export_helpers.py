"""Shared game-safe names and rendered model thumbnails."""
import unicodedata

def name(value):
    value=str(value).strip()
    if len(value)>80 or any(c in '"\\' or unicodedata.category(c).startswith('C') for c in value):
        raise ValueError('Building name: up to 80 characters; no quotes, backslashes or control characters.')
    return value

def thumbnail(root,letters,width,height,depth,base,color,age):
    import preview3d
    from PIL import Image
    picture=preview3d.render(preview3d.scene(letters,width,height,depth,base,color,age),512,512)
    picture.save(root/'previewimage.png')
    picture.resize((256,256),Image.Resampling.LANCZOS).save(root/'slogan'/'imagegui.png')
