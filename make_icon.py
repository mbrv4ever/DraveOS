# Maakt assets/icon.png + assets/icon.ico voor DraveOS.
# Eigen ontwerp: vier vensterruitjes (paars/goud) met in het midden een drakenoog.
# Copyright (C) 2026 Dravenlock (Roger & Claudio). GNU GPL v3.0. Pillow nodig.
import os
from PIL import Image, ImageDraw, ImageFilter
HIER = os.path.dirname(os.path.abspath(__file__))
N = 512
img = Image.new("RGBA", (N, N), (0, 0, 0, 0))
d = ImageDraw.Draw(img)
d.rounded_rectangle((16, 16, N - 16, N - 16), radius=100, fill=(22, 19, 31, 255), outline=(181, 156, 255, 255), width=12)
gl = Image.new("RGBA", (N, N), (0, 0, 0, 0))
ImageDraw.Draw(gl).ellipse((110, 110, 400, 400), fill=(127, 119, 221, 120))
img = Image.alpha_composite(img, gl.filter(ImageFilter.GaussianBlur(50)))
d = ImageDraw.Draw(img)
k = [(127, 119, 221, 255), (181, 156, 255, 255), (181, 156, 255, 255), (255, 200, 87, 255)]
pos = [(96, 96), (266, 96), (96, 266), (266, 266)]
for (x, y), c in zip(pos, k):
    d.rounded_rectangle((x, y, x + 150, y + 150), radius=26, fill=c)
# taakbalkje onder
d.rounded_rectangle((96, 436, 416, 456), radius=10, fill=(239, 234, 255, 255))
# drakenoog in het midden
d.ellipse((176, 196, 336, 316), fill=(22, 19, 31, 255))
d.ellipse((188, 206, 324, 306), fill=(255, 166, 40, 255))
d.ellipse((244, 206, 268, 306), fill=(22, 19, 31, 255))
d.ellipse((214, 220, 230, 236), fill=(255, 255, 255, 230))
os.makedirs(os.path.join(HIER, "assets"), exist_ok=True)
img.save(os.path.join(HIER, "assets", "icon.png"))
img.save(os.path.join(HIER, "assets", "icon.ico"), format="ICO",
         sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
print("icoon klaar")
