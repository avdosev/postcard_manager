from PIL import Image, ImageDraw, ImageFont
import textwrap, os
from utils import deep_merge, read_json

global_config = read_json('cards/global.json')
concrete_config = read_json('cards/1.json')

config = deep_merge(global_config, concrete_config)

background_path = config['layout']

# Open image
img = Image.open(background_path).convert("RGBA")
W, H = img.size

draw = ImageDraw.Draw(img)

def draw_text(text, position, font_name=None, font_size=None, fill=(0, 0, 0, 255)):
    # position: (x, y) или (x, y, w, h) — лишнее игнорим
    if not isinstance(position, (list, tuple)) or len(position) < 2:
        raise TypeError("position должен быть (x, y) или (x, y, w, h)")
    x, y = position[0], position[1]

    # шрифт: либо truetype, либо дефолт
    if font_name is None or not os.path.exists(font_name):
        print(f"{font_name}: not found, path not exist")
        font = ImageFont.load_default()
    else:
        if font_size is None:
            font_size = int(W * 0.06)  # хочешь — переопредели
        font = ImageFont.truetype(font_name, font_size)

    draw.text((x, y), text, font=font, fill=fill)
    return {"pos": (x, y), "font_size": getattr(font, "size", None)}


draw_text(
    text=config['username_info']['content'],
    position=config['username_info']["position"],
    font_name=config['username_info']['font'],
    font_size=45,
)

draw_text(
    text=config['cardname_info']['content'],
    position=config['cardname_info']["position"],
    font_name=config['cardname_info']['font'],
    font_size=60,
)

# сохраняем итог в файл
out_path = "tmp/card.png"
os.makedirs(os.path.dirname(out_path), exist_ok=True)
img.save(out_path)

print("saved tmp image:", out_path)
