
#!/usr/bin/env python3
import argparse
from pathlib import Path
from PIL import Image
import numpy as np

def process_image(input_path: str, output_path: str, move_size=4):
    img = Image.open(input_path)
    arr = np.array(img)

    # Ожидаем 2D (L) или 3D (RGB/RGBA)
    if arr.ndim == 2:
        h, w = arr.shape
        channels = None
    elif arr.ndim == 3:
        h, w, channels = arr.shape
    else:
        raise ValueError("Неподдерживаемый формат изображения.")

    if w < 5:
        raise ValueError("Ширина изображения должна быть ≥ 5 пикселей.")

    # 1) Обрезаем справа 4 пикселя
    cropped = arr[:, :w-move_size] if channels is None else arr[:, :w-move_size, :]

    # 2) Дублируем левый столбец и добавляем 4 пикселя слева
    if channels is None:
        left_col = cropped[:, :1]
    else:
        left_col = cropped[:, :1, :]

    pad_left = np.repeat(left_col, move_size, axis=1)
    out_arr = np.concatenate([pad_left, cropped], axis=1)

    # Приводим обратно к изображению
    out_img = Image.fromarray(out_arr)
    # Если исходное было палитровым (P), мы уже потеряли палитру; сохраняем как PNG.
    save_kwargs = {}
    if img.mode == "P":
        save_kwargs["format"] = "PNG"

    out_img.save(output_path, **save_kwargs)


def main():
    parser = argparse.ArgumentParser(description="Обрезать справа на 4px и продублировать слева 4px (edge).")
    parser.add_argument("input", help="Входной файл изображения")
    parser.add_argument("output", help="Выходной файл")
    args = parser.parse_args()

    process_image(args.input, args.output, 12)


if __name__ == "__main__":
    main()
