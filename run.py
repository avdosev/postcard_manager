import os

from PIL import Image, ImageDraw, ImageFont
from utils import deep_merge, read_json
from aspectfit import to_aspect, parse_aspect

CARD_WIDTH = 146+2
CARD_HEIGHT = 105+2

def draw_text(draw, text, position, font_name=None, font_size=None, fill=(0, 0, 0, 255)):
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


def images_to_pdf(images, output_pdf_path):
    """
    Конвертирует два изображения в PDF с размером страниц 104x146 мм
    
    Args:
        image1_path: путь к первому изображению
        image2_path: путь к второму изображению  
        output_pdf_path: путь для сохранения PDF файла
    """
    
    # Размеры страницы в мм
    page_width_mm = CARD_WIDTH+2
    page_height_mm = CARD_HEIGHT+2
    
    # Конвертируем мм в пиксели (300 DPI для высокого качества печати)
    dpi = 600
    image_width_px = int(CARD_WIDTH * dpi / 25.4)
    image_height_px = int(CARD_HEIGHT * dpi / 25.4)
    page_width_px = int(page_width_mm * dpi / 25.4)
    page_height_px = int(page_height_mm * dpi / 25.4)
    
    print(f"Размер страницы в пикселях: {page_width_px}x{page_height_px}")
    
    # Список для хранения обработанных изображений
    images_for_pdf = []
    
    # Обрабатываем каждое изображение
    for i, img_info in enumerate(images, 1):
        img_path = img_info['path']
        if not os.path.exists(img_path):
            raise FileNotFoundError(f"Изображение не найдено: {img_path}")
            
        # Открываем изображение
        img = Image.open(img_path)
        print(f"Изображение {i}: {img.size}, режим: {img.mode}")
        
        # Конвертируем в RGB если необходимо (для PDF)
        if img.mode != 'RGB':
            img = img.convert('RGB')

        if 'rotate' in img_info:
            rotate_angle = img_info.get('rotate', 0)
            img = img.rotate(rotate_angle, expand=True)
        
        if img_info['adoptation'] == 'fit':
            # Изменяем размер изображения под страницу, сохраняя пропорции
            img_resized = resize_image_to_fit(img, image_width_px, image_height_px)
        else:
            img_resized = resize_image_to_exact(img, image_width_px, image_height_px, gravity=img_info["gravity"])
            print("Ресайзнутое изображение:", img_resized.size)
        # Создаем белую страницу нужного размера
        page = Image.new('RGB', (page_width_px, page_height_px), 'white')
        
        # Центрируем изображение на странице
        x_offset = (page_width_px - img_resized.width) // 2
        y_offset = (page_height_px - img_resized.height) // 2
        page.paste(img_resized, (x_offset, y_offset))
        
        images_for_pdf.append(page)
    
    # Сохраняем в PDF
    images_for_pdf[0].save(
        output_pdf_path,
        save_all=True,
        append_images=images_for_pdf[1:],
        resolution=dpi,
        format='PDF'
    )
    
    print(f"PDF успешно создан: {output_pdf_path}")

def resize_image_to_fit(img, target_width, target_height):
    """
    Изменяет размер изображения, сохраняя пропорции и вписывая в заданные размеры
    """
    # Вычисляем коэффициенты масштабирования
    scale_w = target_width / img.width
    scale_h = target_height / img.height
    
    # Выбираем меньший коэффициент, чтобы изображение поместилось целиком
    scale = min(scale_w, scale_h)
    
    # Новые размеры
    new_width = int(img.width * scale)
    new_height = int(img.height * scale)
    
    # Изменяем размер с высоким качеством
    # Для фотографий используем LANCZOS, для черно-белой графики - NEAREST или LANCZOS
    return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

# Альтернативная функция для точного соответствия размеру (с обрезкой)
def resize_image_to_exact(img, target_width, target_height, gravity):
    """
    Изменяет размер изображения точно под заданные размеры (может обрезать края)
    """
    img = to_aspect(img, aspect=parse_aspect(f"{target_width}:{target_height}"), crop_gravity=gravity)
    print("Обрезанное изображение:", img.size)
    return img.resize((target_width, target_height), Image.Resampling.LANCZOS)
    # return img

# Пример использования
def process_card(config_name):
    config = read_json(config_name)

    if "parent" in config:
        parent_config = read_json(config["parent"])
        config = deep_merge(parent_config, config)


    background_path = config['layout']['path']

    # Open image
    img = Image.open(background_path).convert("RGBA")
    W, H = img.size

    draw = ImageDraw.Draw(img)

    draw_text(
        draw,
        text=config['username_info']['content'],
        position=config['username_info']["position"],
        font_name=config['username_info']['font'],
        font_size=45,
    )

    draw_text(
        draw,
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

    # Укажите пути к вашим изображениям
    photo_path = config['image']['path']
    layout_path = out_path
    output_path = config['output_pdf']
    
    try:
        images_to_pdf(
            [
                {
                    'path': photo_path,
                    'adoptation': 'aspect_fit',
                    "gravity": config['image'].get("gravity", "center"),
                    "rotate": config['image'].get('rotate', 0)
                },
                {
                    'path': layout_path,
                    'adoptation': 'fit',
                    "rotate": config['layout'].get('rotate', 0)
                },
            ], 
            output_path,
        )
    except Exception as e:
        print(f"Ошибка: {e}")


if "__main__" == __name__:
    for i in range(4):
        id = i+1
        process_card(f'cards/{id}.json')