from PIL import Image, ImageDraw, ImageFont
import textwrap, os
from utils import deep_merge, read_json

global_config = read_json('cards/global.json')
concrete_config = read_json('cards/1.json')

config = deep_merge(global_config, concrete_config)


# Paths
input_path = "/mnt/data/d920fda4-e308-47a3-a24c-3e27e73b46f8.png"
output_path = "/mnt/data/translated_image.png"

# Open image
img = Image.open(input_path).convert("RGBA")
W, H = img.size

# Text to place (user-provided Russian translation)
text = "Я не могу дождаться, когда общество рухнет, чтобы МОЯ идеология восстала из пепла!"

# Choose font (DejaVu should be available). Fallback to default if not.
font_name = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
if not os.path.exists(font_name):
    # try another common path
    font_name = "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"
if not os.path.exists(font_name):
    font = ImageFont.load_default()
else:
    # Start with a large font and decrease until text fits
    font_size = int(W * 0.06)  # heuristic starting size
    font = ImageFont.truetype(font_name, font_size)

draw = ImageDraw.Draw(img)

# Determine bubble area roughly (centered). We'll place text centered in the main bubble.
# Use a max width as a proportion of image width
max_text_width = int(W * 0.7)

# Wrap text into multiple lines to fit the max width, adjusting font size if needed
def wrap_text_for_font(text, font, max_width):
    lines = []
    words = text.split()
    current = ""
    for word in words:
        test = current + (" " if current else "") + word
        w, _ = draw.textsize(test, font=font)
        if w <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines

# Adjust font size down until wrapped text fits reasonably in bubble height
while True:
    lines = wrap_text_for_font(text, font, max_text_width)
    # compute height
    line_height = font.getsize("A")[1] + 6
    text_height = line_height * len(lines)
    if text_height <= H * 0.45 or (hasattr(font, "path") and font.size <= 12):
        break
    # decrease font
    if isinstance(font, ImageFont.FreeTypeFont):
        font = ImageFont.truetype(font_name, font.size - 2)
    else:
        break

# Render text onto a transparent layer so we can composite without altering kittens
txt_layer = Image.new("RGBA", img.size, (255,255,255,0))
txt_draw = ImageDraw.Draw(txt_layer)

# Calculate starting position (centered)
total_text_height = (font.getsize("A")[1] + 6) * len(lines)
y_start = int(H*0.38 - total_text_height/2)  # tweak to better center inside bubble
x_center = W // 2

# Draw a white rounded rectangle slightly larger than the text to cover the original English text
# Calculate text width
text_width = max([txt_draw.textsize(line, font=font)[0] for line in lines])
pad_x = 20
pad_y = 12
rect_w = text_width + pad_x*2
rect_h = total_text_height + pad_y*2
rect_x0 = x_center - rect_w//2
rect_y0 = y_start - pad_y
rect_x1 = rect_x0 + rect_w
rect_y1 = rect_y0 + rect_h

# Draw white rectangle with slight transparency to match bubble (bubble is white so fully opaque)
txt_draw.rectangle([rect_x0, rect_y0, rect_x1, rect_y1], fill=(255,255,255,255))

# Draw text lines centered
y = y_start
for line in lines:
    w, h = txt_draw.textsize(line, font=font)
    x = x_center - w//2
    txt_draw.text((x, y), line, font=font, fill=(0,0,0,255))
    y += font.getsize("A")[1] + 6

# Composite the text layer onto the image
result = Image.alpha_composite(img, txt_layer).convert("RGB")
result.save(output_path, quality=95)

# Provide output info
output_path, os.path.exists(output_path), result.size

