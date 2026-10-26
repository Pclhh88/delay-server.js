"""Vergrößerter Ausschnitt der Referenz mit feinem, beschriftetem Pixelraster (Vermessung).
python blender/measure_crop.py x0 y0 x1 y1 zoom step out.png"""
import sys, os
from PIL import Image, ImageDraw
x0, y0, x1, y1, z, step = map(int, sys.argv[1:7])
src = sys.argv[8] if len(sys.argv) > 8 else os.path.join(os.path.dirname(__file__), '..', 'reference', 'reference.png')
im = Image.open(src).convert('RGB').crop((x0, y0, x1, y1)).resize(((x1 - x0) * z, (y1 - y0) * z), Image.LANCZOS)
d = ImageDraw.Draw(im)
for x in range((x0 // step + 1) * step, x1, step):
    big = x % (step * 5) == 0
    d.line([((x - x0) * z, 0), ((x - x0) * z, im.height)], fill=(255, 0, 0) if big else (0, 160, 255), width=1)
    if big:
        d.text(((x - x0) * z + 2, 2), str(x), fill=(255, 255, 0))
for y in range((y0 // step + 1) * step, y1, step):
    big = y % (step * 5) == 0
    d.line([(0, (y - y0) * z), (im.width, (y - y0) * z)], fill=(255, 0, 0) if big else (0, 160, 255), width=1)
    if big:
        d.text((2, (y - y0) * z + 2), str(y), fill=(255, 255, 0))
im.save(sys.argv[7])
