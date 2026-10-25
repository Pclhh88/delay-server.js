"""Nebeneinander-Vergleich von Standbildern mit Beschriftung.

    python3 -m cityshorts.compare_stills OUT.png bild1.png "Titel 1" bild2.png "Titel 2" [...]
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

FONT = os.path.join(os.path.dirname(__file__), "..", "shortsfactory", "fonts", "league-spartan-latin-700-normal.woff")


def compare(out, items, height=1200, pad=24, label_h=70):
    ims = []
    for path, title in items:
        im = Image.open(path).convert("RGB")
        im = im.resize((int(im.width * height / im.height), height), Image.LANCZOS)
        ims.append((im, title))
    W = sum(im.width for im, _ in ims) + pad * (len(ims) + 1)
    sheet = Image.new("RGB", (W, height + label_h + 2 * pad), (245, 241, 234))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.truetype(FONT, 40)
    x = pad
    for im, title in ims:
        d.text((x + im.width / 2, pad + label_h / 2), title, font=font, fill=(40, 36, 30), anchor="mm")
        sheet.paste(im, (x, pad + label_h))
        x += im.width + pad
    sheet.save(out)
    return out


if __name__ == "__main__":
    a = sys.argv[2:]
    compare(sys.argv[1], list(zip(a[0::2], a[1::2])))
