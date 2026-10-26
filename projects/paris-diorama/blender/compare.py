"""Vergleich Render <-> Referenz: Nebeneinander, 50%-Überblendung und Kanten-Overlay."""
import sys
from PIL import Image, ImageChops, ImageFilter, ImageOps

ref = Image.open(sys.argv[1]).convert('RGB')
ren = Image.open(sys.argv[2]).convert('RGB').resize(ref.size, Image.LANCZOS)
out = sys.argv[3]
W, H = ref.size
side = Image.new('RGB', (W * 2, H))
side.paste(ref, (0, 0)); side.paste(ren, (W, 0))
side.resize((W, H // 2)).save(out.replace('.png', '_side.png'))
Image.blend(ref, ren, 0.5).resize((W // 2, H // 2)).save(out.replace('.png', '_blend.png'))
# Kanten der Referenz rot über dem Render
e = ImageOps.autocontrast(ref.convert('L').filter(ImageFilter.FIND_EDGES)).point(lambda v: 255 if v > 60 else 0)
ov = ren.copy(); red = Image.new('RGB', ref.size, (255, 0, 0)); ov.paste(red, (0, 0), e)
ov.resize((W // 2, H // 2)).save(out.replace('.png', '_edges.png'))
