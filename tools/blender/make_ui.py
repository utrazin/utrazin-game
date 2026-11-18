"""Ícones e formas do HUD (brancos com alfa; o HUD pinta com a cor que quiser)."""
import math, os, sys
from PIL import Image, ImageDraw, ImageFilter
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
S = 256

def canvas(): return Image.new("RGBA", (S * 4, S * 4), (255, 255, 255, 0))
def save(im, name):
    im = im.resize((S, S), Image.LANCZOS)
    im.save(os.path.join(OUT, f"T_UI_{name}.png"))

W = (255, 255, 255, 255)
# círculo (cantos arredondados de painéis e barras)
im = canvas(); d = ImageDraw.Draw(im); d.ellipse([0, 0, S * 4 - 1, S * 4 - 1], fill=W); save(im, "Circle")
# anel (mira de escopeta)
im = canvas(); d = ImageDraw.Draw(im); d.ellipse([40, 40, S * 4 - 41, S * 4 - 41], outline=W, width=70); save(im, "Ring")
# coração
im = canvas(); d = ImageDraw.Draw(im); k = S * 4
d.ellipse([0.08 * k, 0.12 * k, 0.54 * k, 0.58 * k], fill=W); d.ellipse([0.46 * k, 0.12 * k, 0.92 * k, 0.58 * k], fill=W)
d.polygon([(0.1 * k, 0.43 * k), (0.9 * k, 0.43 * k), (0.5 * k, 0.92 * k)], fill=W); save(im, "Heart")
# célula de energia (munição)
im = canvas(); d = ImageDraw.Draw(im)
d.rounded_rectangle([0.3 * k, 0.12 * k, 0.7 * k, 0.9 * k], radius=0.1 * k, fill=W)
d.rectangle([0.42 * k, 0.04 * k, 0.58 * k, 0.14 * k], fill=W)
d.rectangle([0.36 * k, 0.42 * k, 0.64 * k, 0.48 * k], fill=(255, 255, 255, 90)); save(im, "Cell")
# chama (nitro)
im = canvas(); d = ImageDraw.Draw(im)
d.ellipse([0.24 * k, 0.42 * k, 0.76 * k, 0.94 * k], fill=W)
d.polygon([(0.245 * k, 0.66 * k), (0.42 * k, 0.3 * k), (0.56 * k, 0.04 * k), (0.62 * k, 0.32 * k), (0.755 * k, 0.66 * k)], fill=W)
d.ellipse([0.38 * k, 0.6 * k, 0.62 * k, 0.88 * k], fill=(255, 255, 255, 110))
save(im, "Nitro")
# graveto
im = canvas(); d = ImageDraw.Draw(im)
d.line([(0.18 * k, 0.86 * k), (0.82 * k, 0.14 * k)], fill=W, width=int(0.09 * k))
d.line([(0.5 * k, 0.5 * k), (0.72 * k, 0.6 * k)], fill=W, width=int(0.05 * k))
d.line([(0.62 * k, 0.36 * k), (0.62 * k, 0.16 * k)], fill=W, width=int(0.045 * k))
for (x, y) in ((0.82, 0.14), (0.72, 0.6), (0.62, 0.16)):
    d.ellipse([(x - 0.06) * k, (y - 0.06) * k, (x + 0.06) * k, (y + 0.06) * k], fill=W)
save(im, "Stick")
# pistola
im = canvas(); d = ImageDraw.Draw(im)
d.rounded_rectangle([0.08 * k, 0.3 * k, 0.86 * k, 0.5 * k], radius=0.05 * k, fill=W)
d.rounded_rectangle([0.72 * k, 0.33 * k, 0.95 * k, 0.45 * k], radius=0.04 * k, fill=W)
d.polygon([(0.16 * k, 0.48 * k), (0.36 * k, 0.48 * k), (0.3 * k, 0.88 * k), (0.1 * k, 0.88 * k)], fill=W)
d.ellipse([0.42 * k, 0.24 * k, 0.6 * k, 0.4 * k], fill=W); save(im, "Pistol")
# escopeta
im = canvas(); d = ImageDraw.Draw(im)
d.rounded_rectangle([0.04 * k, 0.36 * k, 0.96 * k, 0.5 * k], radius=0.04 * k, fill=W)
d.rounded_rectangle([0.5 * k, 0.48 * k, 0.9 * k, 0.56 * k], radius=0.03 * k, fill=W)
d.polygon([(0.04 * k, 0.4 * k), (0.22 * k, 0.48 * k), (0.2 * k, 0.72 * k), (0.02 * k, 0.66 * k)], fill=W)
for x in (0.62, 0.72, 0.82):
    d.ellipse([(x - 0.035) * k, 0.26 * k, (x + 0.035) * k, 0.34 * k], fill=W)
save(im, "Shotgun")
# carro
im = canvas(); d = ImageDraw.Draw(im)
d.rounded_rectangle([0.06 * k, 0.42 * k, 0.94 * k, 0.68 * k], radius=0.07 * k, fill=W)
d.polygon([(0.26 * k, 0.43 * k), (0.36 * k, 0.24 * k), (0.66 * k, 0.24 * k), (0.78 * k, 0.43 * k)], fill=W)
for x in (0.26, 0.74):
    d.ellipse([(x - 0.11) * k, 0.58 * k, (x + 0.11) * k, 0.8 * k], fill=W)
save(im, "Car")
# fúria (raio)
im = canvas(); d = ImageDraw.Draw(im)
d.polygon([(0.58 * k, 0.04 * k), (0.2 * k, 0.56 * k), (0.46 * k, 0.56 * k), (0.38 * k, 0.96 * k), (0.8 * k, 0.4 * k), (0.54 * k, 0.4 * k)], fill=W)
save(im, "Fury")
# caveira (zumbi)
im = canvas(); d = ImageDraw.Draw(im)
d.ellipse([0.18 * k, 0.1 * k, 0.82 * k, 0.7 * k], fill=W); d.rectangle([0.32 * k, 0.6 * k, 0.68 * k, 0.86 * k], fill=W)
for x in (0.36, 0.64):
    d.ellipse([(x - 0.09) * k, 0.34 * k, (x + 0.09) * k, 0.52 * k], fill=(0, 0, 0, 0))
save(im, "Skull")
# gradiente vertical (brilho em barras)
g = Image.new("RGBA", (8, 256))
for y in range(256):
    a = int(255 * max(0, 1 - y / 128) ** 1.5 * 0.55)
    for x in range(8):
        g.putpixel((x, y), (255, 255, 255, a))
g.resize((64, 256)).save(os.path.join(OUT, "T_UI_Shine.png"))
# prévia
names = [f for f in sorted(os.listdir(OUT)) if f.endswith(".png")]
sheet = Image.new("RGBA", (len(names) * 140, 160), (40, 40, 60, 255))
for i, n in enumerate(names):
    t = Image.open(os.path.join(OUT, n)).resize((120, 120))
    sheet.alpha_composite(t, (i * 140 + 10, 10))
sheet.save(os.path.join(OUT, "_preview.png"))
print(names)
