"""Vergleich Gebäude F: Vorlage-Ausschnitt | Render, plus Silhouette des Modells über der Vorlage.
python blender/compare_landmark.py  -> renders/compare_landmark_{side,outline}.png (lokal, nicht im Git)"""
import os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

P = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
x0, y0, S = 1210, 605, 660
ref = Image.open(os.path.join(P, 'reference', 'reference.png')).convert('RGB').crop((x0, y0, x0 + S, y0 + S))
ren = Image.open(os.path.join(P, 'renders', 'landmark_closeup.png')).convert('RGB')
W = ren.width
ref = ref.resize((W, W), Image.LANCZOS)
mask = np.array(Image.open(os.path.join(P, 'renders', 'landmark_mask.png')).convert('RGBA').resize((W, W)))[..., 3] > 128
edge = np.zeros_like(mask)
edge[:-1] |= mask[:-1] != mask[1:]
edge[:, :-1] |= mask[:, :-1] != mask[:, 1:]
edge = np.array(Image.fromarray(edge.astype(np.uint8) * 255).filter(ImageFilter.MaxFilter(5))) > 0
ov = np.array(ref).copy()
ov[edge] = (255, 30, 30)
Image.fromarray(ov).save(os.path.join(P, 'renders', 'compare_landmark_outline.png'))
side = Image.new('RGB', (2 * W, W + 40), (255, 255, 255))
side.paste(ref, (0, 40)); side.paste(ren, (W, 40))
d = ImageDraw.Draw(side)
d.text((12, 12), 'Referenz (Ausschnitt)', fill=(0, 0, 0))
d.text((W + 12, 12), 'Blender-Modell, gleiche Kamera', fill=(0, 0, 0))
side.save(os.path.join(P, 'renders', 'compare_landmark_side.png'))
print('ok')
