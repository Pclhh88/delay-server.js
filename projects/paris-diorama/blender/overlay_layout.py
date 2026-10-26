"""Projiziert Grundrisse/Höhen aus layout.py als Drahtgitter auf die Referenz.
Schneller Abgleich ohne Rendern:  python blender/overlay_layout.py out.png"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PIL import Image, ImageDraw
import layout as LY

im = Image.open(os.path.join(os.path.dirname(__file__), '..', 'reference', 'reference.png')).convert('RGB')
d = ImageDraw.Draw(im)
cols = [(255, 0, 0), (0, 160, 255), (0, 200, 0), (255, 0, 255), (255, 140, 0), (0, 0, 0), (120, 0, 200)]
for i, b in enumerate(LY.BUILDINGS):
    fp = b['footprint']
    zt = LY.BLOCK_Z + b.get('ground_h', 1.5) + b.get('floors', 5) * b.get('floor_h', 1.25)
    roof = b.get('roof', 'mansard')
    ztop = zt + (b.get('roof_h', 1.8) + 0.13 if roof.startswith('mansard') else (1.1 if roof == 'attic' else 0.2))
    c = cols[i % len(cols)]
    for z, w in ((LY.BLOCK_Z, 3), (zt, 3), (ztop, 1)):
        pts = [tuple(LY.world2img((x, y, z))) for x, y in fp]
        d.line(pts + [pts[0]], fill=c, width=w)
    for x, y in fp:
        d.line([tuple(LY.world2img((x, y, LY.BLOCK_Z))), tuple(LY.world2img((x, y, zt)))], fill=c, width=2)
    u, v = LY.world2img((sum(p[0] for p in fp) / len(fp), sum(p[1] for p in fp) / len(fp), ztop))
    d.text((u, v), b['name'], fill=c)
tx, ty, tz = LY.TOWER['location']
d.line([tuple(LY.world2img((tx, ty, tz))), tuple(LY.world2img((tx, ty, tz + 331 * LY.TOWER['scale'])))], fill=(0, 0, 0), width=3)
for (sx, sy), k, s in LY.TREES_IMG:
    d.ellipse([sx - 8, sy - 8, sx + 8, sy + 8], outline=(0, 120, 0), width=3)
im.resize((1024, 1024)).save(sys.argv[1])
