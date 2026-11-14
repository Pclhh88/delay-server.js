import math, os, sys
import numpy as np, cv2
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, '/home/user/delay-server.js')
from shortsfactory.collage import graphics as g
from shortsfactory.collage.vmap import fractal_noise
A = '/home/user/delay-server.js/projects/amelia-earhart-long/build/assets/'
W, H = 1920, 1080
rng = np.random.default_rng(4)

def dark_collage(seed=0):
    r = np.random.default_rng(seed)
    base = Image.new('RGB', (W, H), (26, 26, 24))
    sheets = [Image.fromarray(g.newspaper(900, 1200, headline=h, date="1945", seed=s)).convert('L')
              for s, h in enumerate(["DAS ZIMMER\nIST WEG", "SCHATZ\nGESUCHT", "KÖNIGSBERG\nBRENNT"])]
    for i in range(80):
        sh = sheets[i % 3]
        w, h = int(r.uniform(150, 520)), int(r.uniform(120, 420))
        x0, y0 = int(r.uniform(0, sh.width - w)), int(r.uniform(0, sh.height - h))
        crop = np.asarray(sh.crop((x0, y0, x0 + w, y0 + h))).astype(np.float32)
        tone = r.uniform(0.07, 0.17)
        crop = cv2.GaussianBlur(crop, (0, 0), 0.8) * tone + r.uniform(8, 20)
        rgb = np.dstack([crop, crop * 0.98, crop * 0.93]).clip(0, 255).astype(np.uint8)
        m = (g.torn_mask(w, h, depth=6, seed=int(r.integers(1e6))) * 255).astype(np.uint8)
        piece = Image.fromarray(np.dstack([rgb, m]), 'RGBA').rotate(r.uniform(-25, 25), Image.BICUBIC, expand=True)
        base.paste(piece, (int(r.uniform(-150, W)), int(r.uniform(-150, H))), piece)
    a = np.asarray(base).astype(np.float32)
    a *= (1 + 0.15 * fractal_noise(H, W, seed)[..., None] - 0.07)
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert('RGBA')

def blob_mask(cx, cy, R, seed, sx=1.0, sy=1.0):
    r = np.random.default_rng(seed)
    th = np.linspace(0, 2 * np.pi, 400, endpoint=False)
    rad = R * (1 + sum(r.uniform(0.03, 0.09) * np.sin(k * th + r.uniform(0, 6.3)) for k in (2, 3, 4)))
    pts = np.stack([cx + rad * np.cos(th) * sx, cy + rad * np.sin(th) * sy], 1).astype(np.int32)
    m = np.zeros((H, W), np.uint8)
    cv2.fillPoly(m, [pts], 255, cv2.LINE_AA)
    return m

def paper_fill(color, seed):
    n = fractal_noise(H, W, seed + 9)
    c = np.array(color, np.float32)[None, None] * (0.86 + 0.24 * n[..., None])
    # creases
    cr = np.zeros((H, W), np.float32)
    r = np.random.default_rng(seed)
    for _ in range(14):
        p0 = r.uniform(0, [W, H]); p1 = p0 + r.uniform(-500, 500, 2)
        cv2.line(cr, tuple(p0.astype(int)), tuple(p1.astype(int)), 1.0, 2, cv2.LINE_AA)
    cr = cv2.GaussianBlur(cr, (0, 0), 1.2)
    c = c * (1 - 0.12 * cr[..., None])
    return c.clip(0, 255)

def put_shape(canvas, mask, fill):
    m = mask.astype(np.float32)[..., None] / 255
    sh = cv2.GaussianBlur(mask, (0, 0), 14).astype(np.float32)[..., None] / 255 * 0.5
    sh = np.roll(np.roll(sh, 10, 0), 6, 1)
    a = np.asarray(canvas.convert('RGB')).astype(np.float32)
    a = a * (1 - sh) 
    a = a * (1 - m) + fill * m
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)).convert('RGBA')

def sticker(canvas, name, cx, cy, width, rot=0):
    im = Image.open(A + name + '.png').convert('RGBA')
    im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    if rot: im = im.rotate(rot, Image.BICUBIC, expand=True)
    canvas.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def caption(canvas, text, cx, cy, size=78):
    f = ImageFont.truetype('/home/user/delay-server.js/shortsfactory/fonts/OldStandard-Bold.ttf', size)
    d = ImageDraw.Draw(canvas)
    d.text((cx, cy), text, font=f, fill=(255, 255, 255), anchor='mm', stroke_width=6, stroke_fill=(20, 20, 20))

# --- frame 1: orange blob + portrait popping out of the top
c1 = dark_collage(1)
m1 = blob_mask(1000, 600, 400, 3, 1.05, 1.0)
c1 = put_shape(c1, m1, paper_fill((214, 88, 40), 1))
sticker(c1, 'st_portrait', 1010, 560, 620, -3)
caption(c1, 'Wie verliert man ein ganzes Zimmer?', 960, 960)

# --- frame 2: circle filled with the vintage map, plane flies out of it
c2 = dark_collage(2)
yy, xx = np.mgrid[0:H, 0:W]
m2 = ((np.hypot(xx - 900, yy - 520) < 430) * 255).astype(np.uint8)
m2 = cv2.GaussianBlur(m2, (0, 0), 1)
mp = Image.open(A + 'map_pacific.png').convert('RGB')
crop = mp.crop((5600, 900, 5600 + 1500, 900 + 845)).resize((W, H), Image.LANCZOS)
fill = np.asarray(crop).astype(np.float32)
dots = g.halftone(np.full((H, W), 0.35, np.float32), cell=10, color=(0, 0, 0))[..., 3].astype(np.float32) / 255
fill = fill * (1 - 0.12 * dots[..., None])
c2 = put_shape(c2, m2, fill)
# white paper ring
ring = np.zeros((H, W), np.uint8); cv2.circle(ring, (900, 520), 430, 255, 10, cv2.LINE_AA)
a = np.asarray(c2).copy(); a[ring > 0, :3] = (240, 234, 220); c2 = Image.fromarray(a)
sticker(c2, 'st_electra', 1350, 760, 900, 12)
caption(c2, '1945: Königsberg', 900, 960)

out = Image.new('RGB', (W, H * 2 + 20), (255, 255, 255))
out.paste(c1.convert('RGB'), (0, 0)); out.paste(c2.convert('RGB'), (0, H + 20))
out.save('/home/user/delay-server.js/projects/bernsteinzimmer/output/stil_test.png')
print('ok')
