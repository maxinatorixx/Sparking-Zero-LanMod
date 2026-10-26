"""Render our existing four-star vector motif into launcher icon formats.

Build-time Pillow only; no extracted game artwork and no runtime dependency.
"""
from pathlib import Path
import math


def build_icon(output=None):
    from PIL import Image, ImageDraw
    folder = Path(output) if output is not None else Path(__file__).resolve().parent / "assets"
    folder.mkdir(parents=True, exist_ok=True)
    scale = 512
    image = Image.new("RGBA", (scale, scale), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse((23, 25, 489, 491), fill="#6e3513")
    for radius in range(225, 0, -1):
        t = 1 - radius / 225
        color = (255, int(126 + 72 * t), int(18 + 41 * t), 255)
        draw.ellipse((256-radius, 252-radius, 256+radius, 252+radius), fill=color)
    draw.arc((35, 31, 477, 473), 196, 318, fill="#fff1a2", width=9)
    draw.ellipse((101, 78, 199, 120), fill="#ffe9a0")
    for x, y in ((199, 201), (313, 201), (199, 315), (313, 315)):
        points = []
        for i in range(10):
            angle = -math.pi / 2 + i * math.pi / 5
            radius = 44 if i % 2 == 0 else 19
            points.append((x + math.cos(angle) * radius, y + math.sin(angle) * radius))
        draw.polygon(points, fill="#bb3216")
    image.save(folder / "four-star.png")
    image.save(folder / "four-star.ico", sizes=[(n, n) for n in (16, 24, 32, 48, 64, 128, 256)])
    return folder


if __name__ == "__main__":
    print(build_icon())
