"""Setzt die gerenderten Frames zum fertigen Short zusammen: Hochskalieren auf 1080×1920,
Texte (League Spartan, weiß mit dunkler Kontur und Schatten), Rot-Flash, H.264-Video.

  python shorts/eiffel/compose.py [--src frames] [--out eiffel_short.mp4] [--preview]
"""
import argparse, glob, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import timeline as TL  # noqa: E402

FONT = os.path.join(HERE, '..', '..', '..', '..', 'shortsfactory', 'fonts', 'league-spartan-latin-800-normal.woff')
W, H = 1080, 1920
STYLE = {'cap': (74, 0.17), 'hook': (96, 0.15), 'big': (190, 0.16)}  # Schriftgröße, Zeilenmitte (Anteil von oben)
FLASH = (168, 40, 45)


def caption(t):
    for t0, t1, txt, st in TL.CAPTIONS:
        if t0 <= t < t1:
            return txt, st
    return None, None


def draw_text(img, txt, st, t):
    size, yc = STYLE[st]
    font = ImageFont.truetype(FONT, size)
    lines = txt.split('\n')
    lh = int(size * 1.08)
    y0 = int(H * yc) - lh * len(lines) // 2
    shadow = Image.new('L', (W, H), 0)
    sd = ImageDraw.Draw(shadow)
    layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    for i, ln in enumerate(lines):
        w = d.textlength(ln, font=font)
        x, y = (W - w) / 2, y0 + i * lh
        sd.text((x + 6, y + 8), ln, font=font, fill=150)
        d.text((x, y), ln, font=font, fill=(255, 255, 255, 255), stroke_width=max(3, size // 22),
               stroke_fill=(30, 26, 24, 255))
    shadow = shadow.filter(ImageFilter.GaussianBlur(8))
    img.paste((20, 15, 10), (0, 0), shadow)
    img.alpha_composite(layer) if img.mode == 'RGBA' else img.paste(layer, (0, 0), layer)


def flash_alpha(f):
    a = 0.0
    for ts in TL.RED_FLASH:
        k = f - int(ts * TL.FPS)
        if 0 <= k < 4:
            a = max(a, 0.82 * (k + 1) / 4)
        elif 4 <= k < 15:
            a = max(a, 0.82 * (1 - (k - 3) / 11))
    return a


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--src', default=os.path.join(HERE, 'frames'))
    ap.add_argument('--out', default=os.path.join(HERE, 'eiffel_short.mp4'))
    ap.add_argument('--tmp', default=os.path.join(HERE, 'composed'))
    a = ap.parse_args()
    os.makedirs(a.tmp, exist_ok=True)
    files = sorted(glob.glob(os.path.join(a.src, 'f*.png')))
    for p in files:
        f = int(os.path.basename(p)[1:5])
        t = f / TL.FPS
        img = Image.open(p).convert('RGB').resize((W, H), Image.LANCZOS)
        al = flash_alpha(f)
        if al > 0:
            img = Image.blend(img, Image.new('RGB', (W, H), FLASH), al)
        txt, st = caption(t)
        if txt:
            draw_text(img, txt, st, t)
        img.save(os.path.join(a.tmp, f'c{f:04d}.png'))
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(TL.FPS), '-start_number', '0', '-i',
                    os.path.join(a.tmp, 'c%04d.png'), '-vf', 'fps=30', '-c:v', 'libx264', '-pix_fmt', 'yuv420p',
                    '-crf', '18', '-movflags', '+faststart', a.out], check=True)
    print('Video:', a.out)


if __name__ == '__main__':
    main()
