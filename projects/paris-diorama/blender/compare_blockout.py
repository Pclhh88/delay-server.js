"""Blockout-Abgleich: Umrisse der Blockout-Objekte (aus dem ID-Render) über der Vorlage.
python blender/compare_blockout.py [tag]   -> renders/compare_<tag>_{side,outline,blend}.png"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
tag = sys.argv[1] if len(sys.argv) > 1 else 'blockout'
ref = Image.open(os.path.join(P, 'reference', 'reference.png')).convert('RGB')
ren = Image.open(os.path.join(P, 'renders', f'{tag}.png')).convert('RGB').resize(ref.size, Image.LANCZOS)
idimg = Image.open(os.path.join(P, 'renders', f'{tag}_id.png')).convert('RGBA').resize(ref.size, Image.NEAREST)
ida = np.array(idimg).astype(int)
# Etiketten: Farben grob quantisieren, Hintergrund = transparent; Ausreißer per Modusfilter entfernen
q = (ida[..., 0] // 43) * 36 + (ida[..., 1] // 43) * 6 + (ida[..., 2] // 43) + 1
q[ida[..., 3] < 128] = 0
lab = np.array(Image.fromarray(q.astype(np.uint8)).filter(ImageFilter.ModeFilter(7))).astype(int)
edge = np.zeros(lab.shape, bool)
edge[:-1] |= lab[:-1] != lab[1:]
edge[:, :-1] |= lab[:, :-1] != lab[:, 1:]
edge = np.array(Image.fromarray(edge.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(3))) > 0
pal = {}
for l in np.unique(lab):
    m = lab == l
    pal[l] = ida[..., :3][m].mean(0) if l else np.array([255, 0, 0])
lc = np.zeros(ida.shape[:2] + (3,))
for l, c in pal.items():
    lc[lab == l] = c * 0.8
out = np.array(ref).copy()
out[edge] = lc[edge]
o = Image.fromarray(out.astype(np.uint8))
o.save(os.path.join(P, 'renders', f'compare_{tag}_outline.png'))
side = Image.new('RGB', (ref.width * 2, ref.height))
side.paste(ref, (0, 0)); side.paste(ren, (ref.width, 0))
side.resize((ref.width, ref.height // 2)).save(os.path.join(P, 'renders', f'compare_{tag}_side.png'))
Image.blend(ref, ren, 0.5).save(os.path.join(P, 'renders', f'compare_{tag}_blend.png'))
print('ok')
