
#!/usr/bin/env python3
"""
aspectfit.py — обрезка и/или расширение изображения до заданного соотношения сторон.

Заводской режим: сохраняем одну из сторон (width|height), вторую подгоняем под целевое
соотношение. Если новая вторая сторона меньше исходной — обрезаем. Больше — добавляем поля.

Примеры:
  # Сохраняем высоту, делаем 16:9. Если ширины много — обрежет; если мало — добавит поля.
  python aspectfit.py in.jpg out.jpg --aspect 16:9 --keep height --pad-color 0,0,0

  # Сохраняем ширину, 1:1, обрезка сверху/снизу смещена к верху, паддинг снизу.
  python aspectfit.py in.jpg out.jpg --aspect 1:1 --keep width --crop-gravity top --pad-gravity bottom

  # Пакетно для папки:
  python aspectfit.py input_dir output_dir --aspect 4:5 --keep height --recursive
"""
import argparse
import os
from typing import Tuple, Literal
from PIL import Image, ImageOps

Gravity = Literal['center','top','bottom','left','right']

def parse_aspect(s: str) -> float:
    if ':' in s:
        a, b = s.split(':', 1)
        return float(a) / float(b)
    return float(s)

def _parse_color(s: str) -> Tuple[int,int,int,int]:
    parts = [int(x) for x in s.split(',')]
    if len(parts) == 3:
        parts.append(255)
    if len(parts) != 4:
        raise ValueError("--pad-color ожидает R,G,B[,A]")
    return tuple(parts)  # type: ignore

def _apply_exif_orientation(img: Image.Image) -> Image.Image:
    try:
        return ImageOps.exif_transpose(img)
    except Exception:
        return img

def _crop_with_gravity(img: Image.Image, box_w: int, box_h: int, gravity: Gravity) -> Image.Image:
    W, H = img.size
    left = (W - box_w) // 2
    top  = (H - box_h) // 2
    if gravity == 'left':
        left = 0
    if gravity == 'right':
        left = W - box_w
    if gravity == 'top':
        top = 0
    if gravity == 'bottom':
        top = H - box_h
    left = max(0, min(left, W - box_w))
    top  = max(0, min(top,  H - box_h))
    return img.crop((left, top, left + box_w, top + box_h))

def _pad_with_gravity(img: Image.Image, box_w: int, box_h: int, gravity: Gravity, color: Tuple[int,int,int,int]) -> Image.Image:
    W, H = img.size
    canvas = Image.new('RGBA', (box_w, box_h), color)
    x = (box_w - W) // 2
    y = (box_h - H) // 2
    if gravity == 'left':
        x = 0
    if gravity == 'right':
        x = box_w - W
    if gravity == 'top':
        y = 0
    if gravity == 'bottom':
        y = box_h - H
    canvas.paste(img, (x, y))
    return canvas

def to_aspect(
    img: Image.Image,
    aspect: float,
    keep: Literal['width','height'] = 'height',
    crop_gravity: Gravity = 'center',
    pad_gravity: Gravity = 'center',
    pad_color: Tuple[int,int,int,int] = (0,0,0,0),
    prefer_integer: bool = True
) -> Image.Image:
    """
    Доводит изображение до aspect, сохраняя одну сторону (keep).
    Обрезает или добавляет поля по второй стороне в зависимости от нехватки/избытка.
    Возвращает изображение в RGBA.
    """
    img = _apply_exif_orientation(img).convert('RGBA')
    W, H = img.size
    if keep == 'height':
        target_h = H
        target_w = aspect * target_h
    else:
        target_w = W
        target_h = (1.0 / aspect) * target_w
    if prefer_integer:
        target_w = int(round(target_w))
        target_h = int(round(target_h))
    # Решаем: обрезка или поля
    if target_w <= W and target_h <= H:
        # Обе стороны влезают: просто crop до коробки
        return _crop_with_gravity(img, int(target_w), int(target_h), crop_gravity)
    elif target_w > W and target_h <= H:
        # Не хватает ширины: обрежем по высоте до target_h, а ширину дополним полями
        cropped = _crop_with_gravity(img, W, int(target_h), crop_gravity)
        return _pad_with_gravity(cropped, int(target_w), int(target_h), pad_gravity, pad_color)
    elif target_w <= W and target_h > H:
        # Не хватает высоты: обрежем по ширине до target_w, а высоту дополним
        cropped = _crop_with_gravity(img, int(target_w), H, crop_gravity)
        return _pad_with_gravity(cropped, int(target_w), int(target_h), pad_gravity, pad_color)
    else:
        # Обе стороны не хватает: паддинг по двум сторонам
        return _pad_with_gravity(img, int(target_w), int(target_h), pad_gravity, pad_color)

def process_one(
    inp_path: str,
    out_path: str,
    aspect: float,
    keep: str = 'height',
    crop_gravity: str = 'center',
    pad_gravity: str = 'center',
    pad_color=(0,0,0,0),
    quality: int = 95
) -> None:
    with Image.open(inp_path) as im:
        out = to_aspect(im, aspect, keep=keep, crop_gravity=crop_gravity, pad_gravity=pad_gravity, pad_color=pad_color)
        # Сохраняем с сохранением профиля, где возможно
        ext = os.path.splitext(out_path.lower())[1]
        if ext in ['.jpg', '.jpeg']:
            out = out.convert('RGB')
            out.save(out_path, quality=quality, subsampling=0, icc_profile=im.info.get('icc_profile'))
        elif ext == '.png':
            out.save(out_path, compress_level=6)
        else:
            out.save(out_path)

def _iter_files(root: str, recursive: bool):
    if os.path.isfile(root):
        yield root
        return
    for dirpath, _, filenames in os.walk(root):
        for f in filenames:
            p = os.path.join(dirpath, f)
            yield p
        if not recursive:
            break

def main():
    ap = argparse.ArgumentParser(description='Обрезать/расширить изображение до заданного соотношения сторон.')
    ap.add_argument('input', help='файл или папка с файлами')
    ap.add_argument('output', help='файл или папка для результата')
    ap.add_argument('--aspect', required=True, help='например 16:9, 4:5, 1.777')
    ap.add_argument('--keep', choices=['width','height'], default='height', help='какую сторону сохранить неизменной')
    ap.add_argument('--crop-gravity', choices=['center','top','bottom','left','right'], default='center', help='куда смещать обрезку')
    ap.add_argument('--pad-gravity', choices=['center','top','bottom','left','right'], default='center', help='куда прижимать картинку при добавлении полей')
    ap.add_argument('--pad-color', default='0,0,0,0', help='RGBA как R,G,B[,A]. По умолчанию прозрачный.')
    ap.add_argument('--quality', type=int, default=95, help='JPEG качество')
    ap.add_argument('--recursive', action='store_true', help='рекурсивно обрабатывать папки')
    args = ap.parse_args()

    aspect = parse_aspect(args.aspect)
    pad_color = _parse_color(args.pad_color)

    input_is_file = os.path.isfile(args.input)
    output_is_file = os.path.splitext(args.output)[1] != '' or input_is_file

    if input_is_file and not output_is_file:
        raise SystemExit('Когда вход — файл, выход тоже должен быть файлом.')

    if not input_is_file and output_is_file:
        raise SystemExit('Когда вход — папка, выход тоже должен быть папкой.')

    if not os.path.exists(args.output):
        if input_is_file:
            os.makedirs(os.path.dirname(args.output) or '.', exist_ok=True)
        else:
            os.makedirs(args.output, exist_ok=True)

    if input_is_file:
        process_one(args.input, args.output, aspect, keep=args.keep, crop_gravity=args.crop_gravity, pad_gravity=args.pad_gravity, pad_color=pad_color, quality=args.quality)
    else:
        for inp in _iter_files(args.input, args.recursive):
            try:
                rel = os.path.relpath(inp, args.input)
            except ValueError:
                rel = os.path.basename(inp)
            name, _ = os.path.splitext(rel)
            out_path = os.path.join(args.output, f"{name}.jpg")
            try:
                process_one(inp, out_path, aspect, keep=args.keep, crop_gravity=args.crop_gravity, pad_gravity=args.pad_gravity, pad_color=pad_color, quality=args.quality)
                print(f"OK: {inp} -> {out_path}")
            except Exception as e:
                print(f"FAIL: {inp} ({e})")

if __name__ == '__main__':
    main()
