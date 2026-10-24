"""Photos / memes supplied by the user -> cut-outs or photo cards.

Sources in ../assets/photos_src/ (as uploaded), results in ../assets/png/photo_*.png
plus ../assets/manifest_photos.json. Cut-outs use rembg (isnet-general-use, model in
models/rembg/, GitHub release of danielgatis/rembg).

    python3 projects/elektroauto-sound/build/build_photos.py
"""
import json
import os

from PIL import Image, ImageFilter, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PROJ))
SRC = os.path.join(PROJ, "assets", "photos_src")
PNG = os.path.join(PROJ, "assets", "png")

MEME = "unknown (internet meme/photo supplied by the user) - clear rights before publishing"

# name -> (source file, crop box or None, "cutout" | "card", target long edge px, licence, note)
PHOTOS = {
    "geldmann": ("geldmann.png", None, "cutout", 1100, MEME, "Mann mit Geldstapeln"),
    "radio": ("baustellenradio.jpg", None, "cutout", 1000, MEME + " (product photo, Makita logo)", "Baustellenradio"),
    "tacho_no": ("tacho_no.jpg", (0, 48, 640, 492), "card", 1000, MEME, "Tacho 'NO!' ohne Bildunterschrift"),
    "oma_dj": ("oma_dj.jpg", (0, 0, 527, 696), "cutout", 1200, MEME, "Oma am DJ-Pult, ohne Wasserzeichen"),
    "oma_bust": ("oma_dj.jpg", (200, 0, 527, 440), "cutout", 900, MEME, "Oma, nur Oberkörper"),
    "schuhschnabel": ("schuhschnabel.jpg", None, "cutout", 1100, MEME, "Schuhschnabel"),
    "geige": ("geige.jpg", None, "cutout", 1000, MEME, "Mann mit Geige (Meme)"),
    "loewe": ("loewe.jpg", (0, 0, 413, 345), "cutout", 1000, MEME, "Löwe, Warzenschwein, Erdmännchen"),
    "oma_portrait": ("oma_portrait.png", (0, 0, 394, 255), "cutout", 900, MEME + " (Shutterstock preview)",
                     "Oma-Porträt, ohne Wasserzeichen-Leiste"),
    "roll_safe": ("roll_safe.jpg", None, "cutout", 1000, MEME, "Roll-Safe-Meme (Finger an der Schläfe)"),
    "geldmann2": ("geldmann2.jpg", (0, 255, 880, 1184), "cutout", 1100, MEME, "älterer Mann mit Dollarscheinen"),
    "vw": ("vw_id_polo.png", None, "alpha", 940, MEME + " (VW press/configurator image)", "VW ID. Polo, freigestellt geliefert"),
    "tars": ("tars.png", None, "white", 1100, MEME, "TARS (Interstellar) aus Lego"),
    "feiger_loewe": ("feiger_loewe.jpg", None, "cutout", 1100, MEME, "Feiger Löwe (Zauberer von Oz)"),
}


def upscale(im, long_edge):
    f = long_edge / max(im.size)
    if f > 1:
        im = im.resize((round(im.width * f), round(im.height * f)), Image.LANCZOS)
        im = im.filter(ImageFilter.UnsharpMask(radius=2, percent=60, threshold=2))
    return im


def cut_white(im, light=178):
    """cut-out for objects on a plain light background: light, unsaturated pixels are
    background; the largest dark component (holes filled) is the object."""
    import cv2
    import numpy as np
    a = cv2.GaussianBlur(np.asarray(im), (5, 5), 0).astype(np.int16)
    lum = a.mean(axis=2)
    sat = a.max(axis=2) - a.min(axis=2)
    fg = ((lum < light) | (sat > 25)).astype(np.uint8)
    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, np.ones((7, 7), np.uint8))
    n, lab, stats, _ = cv2.connectedComponentsWithStats(fg)
    keep = (lab == 1 + int(np.argmax(stats[1:, cv2.CC_STAT_AREA]))).astype(np.uint8) * 255
    # fill only small holes (specks inside the object), keep real gaps between the legs open
    holes = (keep == 0).astype(np.uint8)
    n, lab, stats, _ = cv2.connectedComponentsWithStats(holes, connectivity=4)
    filled = keep.copy()
    for i in range(1, n):
        x, y, w, h, area = stats[i]
        touches = x == 0 or y == 0 or x + w >= keep.shape[1] or y + h >= keep.shape[0]
        if not touches and area < 0.004 * keep.size:
            filled[lab == i] = 255
    alpha = cv2.GaussianBlur(filled, (3, 3), 0)
    out = im.convert("RGBA")
    out.putalpha(Image.fromarray(alpha))
    return out


def card(im, border=18):
    """photo card: white frame + soft shadow (like the reference's photo cards)."""
    framed = ImageOps.expand(im.convert("RGB"), border=border, fill="white").convert("RGBA")
    pad = 40
    out = Image.new("RGBA", (framed.width + 2 * pad, framed.height + 2 * pad), (0, 0, 0, 0))
    sh = Image.new("RGBA", framed.size, (0, 0, 0, 110))
    out.alpha_composite(sh, (pad + 10, pad + 14))
    out = out.filter(ImageFilter.GaussianBlur(12))
    out.alpha_composite(framed, (pad, pad))
    return out


def main():
    os.environ.setdefault("U2NET_HOME", os.path.join(ROOT, "models", "rembg"))
    from rembg import new_session, remove
    session = new_session("isnet-general-use")
    manifest = {}
    for name, (src, box, mode, edge, lic, note) in PHOTOS.items():
        im = Image.open(os.path.join(SRC, src))
        im = im.convert("RGBA" if mode == "alpha" else "RGB")
        if box:
            im = im.crop(box)
        if mode in ("cutout", "white", "alpha"):
            if mode == "cutout":
                cut = remove(im, session=session, post_process_mask=True)
            else:
                cut = cut_white(im) if mode == "white" else im
            bbox = cut.getchannel("A").point(lambda v: 255 if v > 16 else 0).getbbox()
            out = upscale(cut.crop(bbox), edge)
        else:
            out = card(upscale(im, edge))
        path = os.path.join(PNG, f"photo_{name}.png")
        out.save(path)
        manifest[f"photo_{name}"] = {"path": f"assets/png/photo_{name}.png", "design_scale": 1.0,
                                     "license": lic, "source": f"assets/photos_src/{src}", "note": note}
        print(name, out.size)
    # the car photo framed like the "ecar" emoji (1000x1000, car 940 wide, wheels on y=850),
    # so it drops into every position/scale used for the emoji car
    car = Image.open(os.path.join(PNG, "photo_vw.png"))
    car = car.resize((940, round(car.height * 940 / car.width)), Image.LANCZOS)
    frame = Image.new("RGBA", (1000, 1000), (0, 0, 0, 0))
    frame.alpha_composite(car, (30, 850 - car.height))
    frame.save(os.path.join(PNG, "photo_car.png"))
    manifest["photo_car"] = dict(manifest["photo_vw"], path="assets/png/photo_car.png",
                                 note="VW ID. Polo im Rahmen des ecar-Emojis")
    json.dump(manifest, open(os.path.join(PROJ, "assets", "manifest_photos.json"), "w"), indent=1,
              ensure_ascii=False)


if __name__ == "__main__":
    main()
