"""Text rendering: word-by-word captions and free text layers."""
import glob
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

DEFAULT_CAPTION_STYLE = {
    "font": "league-spartan-700",
    "size": 50,             # design px (font size) for normal words
    "sizes": {"big": 72},   # named emphasis sizes
    "y": 960,               # vertical centre of the caption (design px)
    "fill": [255, 255, 255],
    "stroke": [25, 25, 25],
    "stroke_w": 2.5,
    "shadow": {"dx": 3, "dy": 4, "blur": 2.0, "color": [0, 0, 0], "alpha": 0.75},
    "uppercase": True,
}


class TextRenderer:
    def __init__(self, font_dir):
        self.font_dir = os.path.abspath(font_dir)
        self._fonts = {}
        self._cache = {}

    def font(self, name, px):
        key = (name, int(round(px)))
        if key not in self._fonts:
            cands = glob.glob(os.path.join(self.font_dir, f"{name}*")) + \
                glob.glob(os.path.join(self.font_dir, name.rsplit("-", 1)[0] + f"-latin-{name.rsplit('-', 1)[-1]}-normal.*"))
            if not cands:
                raise FileNotFoundError(f"font {name} in {self.font_dir}")
            self._fonts[key] = ImageFont.truetype(cands[0], key[1])
        return self._fonts[key]

    def render_word(self, text, style, size, k):
        """RGBA float premultiplied image of a styled word at output scale k,
        plus the anchor (centre) in pixels."""
        key = (text, size, k, id(style))
        if key in self._cache:
            return self._cache[key]
        px = size * k
        f = self.font(style["font"], px)
        sw = max(1, int(round(style.get("stroke_w", 0) * k)))
        sh = style.get("shadow") or {}
        pad = int(px * 0.6 + sw * 2 + 10 * k)
        bbox = f.getbbox(text, stroke_width=sw, anchor="ms")
        w = bbox[2] - bbox[0] + 2 * pad
        h = bbox[3] - bbox[1] + 2 * pad
        ox, oy = pad - bbox[0], pad - bbox[1]
        # vertical centring on cap height so all words sit on the same line
        cap = f.getbbox("H", anchor="ms")
        cy = oy + (cap[1] + cap[3]) / 2
        cx = ox + (bbox[0] + bbox[2]) / 2 - 0  # horizontal centre of ink
        layer = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if sh:
            shadow = Image.new("L", (w, h), 0)
            ImageDraw.Draw(shadow).text((ox + sh.get("dx", 0) * k, oy + sh.get("dy", 0) * k), text,
                                        font=f, fill=255, anchor="ms", stroke_width=sw, stroke_fill=255)
            if sh.get("blur", 0) > 0:
                shadow = shadow.filter(ImageFilter.GaussianBlur(sh["blur"] * k))
            col = tuple(sh.get("color", [0, 0, 0]))
            sl = Image.new("RGBA", (w, h), col + (0,))
            sl.putalpha(shadow.point(lambda v: int(v * sh.get("alpha", 0.7))))
            layer = Image.alpha_composite(layer, sl)
        d = ImageDraw.Draw(layer)
        d.text((ox, oy), text, font=f, fill=tuple(style.get("fill", [255, 255, 255])), anchor="ms",
               stroke_width=sw, stroke_fill=tuple(style.get("stroke", [0, 0, 0])))
        a = np.asarray(layer).astype(np.float32) / 255
        a[..., :3] *= a[..., 3:4]
        res = (a, (cx, cy))
        self._cache[key] = res
        return res

    def render_phrase(self, words, active, style, k):
        """One caption line (several words) as RGBA; the active word gets the
        highlight colour.  Cached per (phrase, active word)."""
        key = ("phrase", tuple(words), active, id(style), k)
        if key in self._cache:
            return self._cache[key]
        px = style["size"] * k
        f = self.font(style["font"], px)
        sw = max(1, int(round(style.get("stroke_w", 0) * k)))
        space = f.getlength(" ")
        widths = [f.getlength(wd) for wd in words]
        total = sum(widths) + space * (len(words) - 1)
        pad = int(px * 0.5 + sw * 2 + 8 * k)
        asc, desc = f.getmetrics()
        W, H = int(total + 2 * pad), int(asc + desc + 2 * pad)
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        box = style.get("box")
        if box:
            d0 = ImageDraw.Draw(layer)
            bp = box.get("pad", 14) * k
            d0.rounded_rectangle([pad - bp, pad - bp * 0.6, pad + total + bp, pad + asc + desc + bp * 0.6],
                                 radius=box.get("radius", 10) * k, fill=tuple(box["color"]) + (int(255 * box.get("alpha", 0.6)),))
        sh = style.get("shadow") or {}
        if sh:
            shadow = Image.new("L", (W, H), 0)
            ds = ImageDraw.Draw(shadow)
            x = pad
            for wd, wdt in zip(words, widths):
                ds.text((x + sh.get("dx", 0) * k, pad + sh.get("dy", 0) * k), wd, font=f, fill=255,
                        stroke_width=sw, stroke_fill=255)
                x += wdt + space
            shadow = shadow.filter(ImageFilter.GaussianBlur(sh.get("blur", 2) * k))
            sl = Image.new("RGBA", (W, H), tuple(sh.get("color", [0, 0, 0])) + (0,))
            sl.putalpha(shadow.point(lambda v: int(v * sh.get("alpha", 0.7))))
            layer = Image.alpha_composite(layer, sl)
        d = ImageDraw.Draw(layer)
        x = pad
        for i, (wd, wdt) in enumerate(zip(words, widths)):
            col = style.get("highlight", style["fill"]) if i == active else style["fill"]
            d.text((x, pad), wd, font=f, fill=tuple(col), stroke_width=sw, stroke_fill=tuple(style.get("stroke", [0, 0, 0])))
            x += wdt + space
        a = np.asarray(layer).astype(np.float32) / 255
        a[..., :3] *= a[..., 3:4]
        res = (a, (W / 2, H / 2))
        self._cache[key] = res
        return res

    def draw_caption(self, r, canvas, cap, t):
        style = dict(DEFAULT_CAPTION_STYLE)
        style.update(cap.get("style", {}))
        cap["style_resolved"] = style
        if style.get("mode") == "phrase":
            # cap["phrases"] = [{"start", "end", "words": [{"text","start","end"}]}]
            for ph in cap["phrases"]:
                if ph["start"] <= t < ph["end"]:
                    texts = [w["text"].upper() if style.get("uppercase") else w["text"] for w in ph["words"]]
                    active = max([i for i, w in enumerate(ph["words"]) if w["start"] <= t] or [-1])
                    img, (cx, cy) = self.render_phrase(texts, active, id_style(style), r.k)
                    x = style.get("x", r.DW / 2) * r.k
                    y = style["y"] * r.ky
                    M = np.array([[1, 0, x - cx], [0, 1, y - cy]], np.float64)
                    warped = cv2.warpAffine(img, M, (r.W, r.H), flags=cv2.INTER_LINEAR,
                                            borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
                    r._composite(canvas, warped, "normal", 1.0)
            return
        for w in cap["words"]:
            if w["start"] <= t < w["end"]:
                txt = w["text"].upper() if style.get("uppercase") else w["text"]
                size = style["sizes"].get(w.get("size"), style["size"]) if w.get("size") else style["size"]
                img, (cx, cy) = self.render_word(txt, id_style(style), size, r.k)
                x = w.get("x", r.DW / 2) * r.k
                y = w.get("y", style["y"]) * r.ky
                M = np.array([[1, 0, x - cx], [0, 1, y - cy]], np.float64)
                warped = cv2.warpAffine(img, M, (r.W, r.H), flags=cv2.INTER_LINEAR,
                                        borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
                r._composite(canvas, warped, "normal", w.get("opacity", 1.0))

    def draw_text_layer(self, r, layer, p, M):
        style = dict(DEFAULT_CAPTION_STYLE)
        style.update({"shadow": None, "stroke_w": 0})
        style.update(layer.get("style", {}))
        size = layer.get("size", 24)
        img, (cx, cy) = self.render_word(layer["text"], id_style(style), size, r.k)
        h, w = img.shape[:2]
        anc = layer.get("anchor")
        Mt = M @ r._local_matrix(layer, p)
        # img is already at output scale k: undo it so Mt (design->out) applies once
        S = np.array([[1 / r.k, 0, 0], [0, 1 / r.k, 0], [0, 0, 1]])
        ax, ay = (cx, cy) if anc is None else (anc[0] * w, anc[1] * h)
        T = np.array([[1, 0, -ax], [0, 1, -ay], [0, 0, 1]])
        full = Mt @ S @ T
        return cv2.warpAffine(img, full[:2], (r.W, r.H), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))


class _StyleKey(dict):
    """dict usable as a stable cache identity."""


_style_registry = {}


def id_style(style):
    key = repr(sorted((k, repr(v)) for k, v in style.items() if k != "style_resolved"))
    if key not in _style_registry:
        _style_registry[key] = _StyleKey(style)
    return _style_registry[key]
