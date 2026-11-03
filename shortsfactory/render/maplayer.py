"""Karten-Ebene ("type": "map") – Stil-Profil map_doc (Referenz 3).

Eine Karten-Ebene zeigt eine große Weltkarte (Meter, z. B. UTM) durch eine Kamera:

  keys: cx, cy   Weltpunkt in der Bildmitte (Meter)
        mpp      Meter pro Design-Pixel (Zoom; kleiner = näher)
        rot      Drehung der Karte auf dem Bildschirm (Grad, gegen den Uhrzeigersinn)
        tilt     3D-Neigung (Grad; 0 = senkrecht von oben, oben liegt dann weiter weg)
        ox, oy   Bildmitte in Design-Pixeln (Standard 540/960)

Die Ebene hat "items", die der Reihe nach gezeichnet werden; jedes Item hat eigene keys:

  raster   Rasterbild mit Geotransform (Satellit, Papier). keys: opacity, value, sat,
           out_value/out_sat (außerhalb der Maske), tint [r,g,b,amt] (innerhalb der Maske),
           dissolve (0..1, Tinten-Übergang mit Rauschkante)
  lines    viele Linien (Straßenraster). keys: opacity, reveal (0..1 entlang reveal_dir)
  path     eine Linie, die sich zeichnet (Neon). keys: opacity, progress, start
  polygon  Fläche (Insel). keys: opacity, fill_opacity, edge_opacity
  sprite   Bild an einem Weltpunkt (Figur, Zelt). keys: opacity, scale, dx, dy, rot
  label    Text an einem Weltpunkt, auf der Karte liegend oder aufrecht. keys wie sprite

Alle Breiten/Größen in Design-Pixeln (1080x1920), außer *_m (Meter auf der Karte).
"""
import json
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .keyframes import props_at

DESIGN_W, DESIGN_H = 1080, 1920


# --------------------------------------------------------------------------- data
class MapData:
    """Lädt Raster (JSON mit Geotransform) und Vektoren eines Kartenprojekts (mit Cache)."""

    def __init__(self, base_dir, spec):
        self.base = base_dir
        self.spec = spec
        self.rasters = {}
        self.masks = {}
        self.vectors = None
        self._lines = {}

    def raster(self, name):
        if name not in self.rasters:
            meta = json.load(open(os.path.join(self.base, self.spec["rasters"][name])))
            img = cv2.imread(os.path.join(self.base, meta["path"]), cv2.IMREAD_COLOR)
            a, b, c, d, e, f = meta["transform"]
            A = np.array([[a, b, c], [d, e, f], [0, 0, 1]], np.float64)
            levels = [img]
            while min(levels[-1].shape[:2]) > 256:
                levels.append(cv2.pyrDown(levels[-1]))
            self.rasters[name] = (levels, A, abs(a))
        return self.rasters[name]

    def mask(self, name):
        if name not in self.masks:
            m = cv2.imread(os.path.join(self.base, self.spec["masks"][name]), cv2.IMREAD_GRAYSCALE)
            levels = [m]
            while min(levels[-1].shape[:2]) > 256:
                levels.append(cv2.pyrDown(levels[-1]))
            self.masks[name] = levels
        return self.masks[name]

    def vec(self, name):
        if self.vectors is None:
            self.vectors = json.load(open(os.path.join(self.base, self.spec["vectors"])))
        return self.vectors[name]

    def lines(self, name):
        """Liste von Linien -> (alle Punkte Nx2, Startindizes, Mittelpunkte)."""
        if name not in self._lines:
            ls = self.vec(name)
            if ls and isinstance(ls[0][0], (int, float)):
                ls = [ls]
            arrs = [np.asarray(l, np.float64) for l in ls]
            pts = np.vstack(arrs)
            idx = np.cumsum([0] + [len(a) for a in arrs])
            mids = np.array([a.mean(0) for a in arrs])
            self._lines[name] = (pts, idx, mids)
        return self._lines[name]


# --------------------------------------------------------------------------- camera
def camera_matrix(p, k, ky):
    """3x3-Homographie Welt (Meter) -> Ausgabe-Pixel."""
    cx, cy, mpp = p["cx"], p["cy"], p["mpp"]
    rot = math.radians(p.get("rot", 0.0) or 0.0)
    tilt = math.radians(p.get("tilt", 0.0) or 0.0)
    f = p.get("focal", 1400.0)
    flat = np.array([[1 / mpp, 0, -cx / mpp], [0, -1 / mpp, cy / mpp], [0, 0, 1]])
    c, s = math.cos(rot), math.sin(rot)
    R = np.array([[c, s, 0], [-s, c, 0], [0, 0, 1]])  # gegen den Uhrzeigersinn auf dem Schirm
    T = np.array([[f, 0, 0], [0, f * math.cos(tilt), 0], [0, -math.sin(tilt), f]])
    sx, sy = p.get("ox", DESIGN_W / 2), p.get("oy", DESIGN_H / 2)
    S = np.array([[k, 0, k * sx], [0, ky, ky * sy], [0, 0, 1]])
    return S @ T @ R @ flat


def project(H, pts):
    pts = np.asarray(pts, np.float64)
    q = pts @ H[:, :2].T + H[:, 2]
    w = q[:, 2:3]
    w = np.where(np.abs(w) < 1e-9, 1e-9, w)
    return q[:, :2] / w, q[:, 2]


def local_scale(H, pt):
    """Ausgabe-Pixel pro Meter an einem Weltpunkt."""
    a, _ = project(H, [pt, [pt[0] + 1, pt[1]], [pt[0], pt[1] + 1]])
    return 0.5 * (np.hypot(*(a[1] - a[0])) + np.hypot(*(a[2] - a[0])))


# --------------------------------------------------------------------------- helpers
def _ink_noise(h, w, seed=3):
    rng = np.random.default_rng(seed)
    n = np.zeros((h, w), np.float32)
    for s, wt in ((6, 0.35), (24, 0.4), (96, 0.25)):
        sm = rng.random((h // s + 2, w // s + 2)).astype(np.float32)
        n += wt * cv2.resize(sm, (w, h), interpolation=cv2.INTER_CUBIC)
    return n


def _blur_glow(mask, sigma):
    """Weicher Glow aus einer Maske; Unschärfe auf verkleinertem Bild (schnell)."""
    if sigma <= 0.5:
        return mask
    f = max(1, int(sigma / 3))
    small = cv2.resize(mask, (mask.shape[1] // f, mask.shape[0] // f), interpolation=cv2.INTER_AREA)
    small = cv2.GaussianBlur(small, (0, 0), sigma / f)
    return cv2.resize(small, (mask.shape[1], mask.shape[0]), interpolation=cv2.INTER_LINEAR)


def _add_color(canvas, alpha, color, mode="over"):
    col = np.asarray(color[:3], np.float32) / 255.0
    a = alpha[..., None]
    if mode == "add":
        canvas += col * a
    elif mode == "screen":
        canvas[:] = 1 - (1 - canvas) * (1 - col * a)
    else:
        canvas *= (1 - a)
        canvas += col * a


class TextCache:
    def __init__(self, font_dir):
        self.font_dir = font_dir
        self.cache = {}

    def font(self, name, px):
        import glob
        c = glob.glob(os.path.join(self.font_dir, name + "*"))
        if not c:
            raise FileNotFoundError(name)
        return ImageFont.truetype(c[0], int(px))

    def render(self, text, font, px, color=(255, 255, 255), shadow=None, stroke=0, stroke_color=(0, 0, 0),
               glow=None, tracking=0):
        """RGBA uint8-Bild des Texts (Anker = Mitte). shadow=[dx,dy,blur,alpha] in px."""
        key = (text, font, int(px), tuple(color), json.dumps(shadow), stroke, tuple(stroke_color), json.dumps(glow))
        if key in self.cache:
            return self.cache[key]
        f = self.font(font, px)
        bb = f.getbbox(text, stroke_width=stroke)
        pad = int(px * 0.6) + (int(glow[1]) * 3 if glow else 0)
        w, h = bb[2] - bb[0] + 2 * pad, bb[3] - bb[1] + 2 * pad
        ox, oy = pad - bb[0], pad - bb[1]
        base = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        if glow:  # [r,g,b,blur,alpha] farbige weiche Hülle (z. B. rote Box hinter "Broadway")
            g = Image.new("L", (w, h), 0)
            ImageDraw.Draw(g).text((ox, oy), text, font=f, fill=255, stroke_width=int(px * 0.35))
            g = g.filter(ImageFilter.GaussianBlur(glow[3]))
            col = Image.new("RGBA", (w, h), tuple(glow[:3]) + (0,))
            col.putalpha(g.point(lambda v: int(min(255, v * glow[4] * 1.6))))
            base = Image.alpha_composite(base, col)
        if shadow:
            s = Image.new("L", (w, h), 0)
            ImageDraw.Draw(s).text((ox + shadow[0], oy + shadow[1]), text, font=f, fill=255, stroke_width=stroke)
            s = s.filter(ImageFilter.GaussianBlur(shadow[2]))
            sh = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            sh.putalpha(s.point(lambda v: int(v * shadow[3])))
            base = Image.alpha_composite(base, sh)
        d = ImageDraw.Draw(base)
        d.text((ox, oy), text, font=f, fill=tuple(color) + (255,), stroke_width=stroke,
               stroke_fill=tuple(stroke_color) + (255,))
        arr = np.asarray(base)
        self.cache[key] = arr
        return arr


# --------------------------------------------------------------------------- renderer
class MapRenderer:
    def __init__(self, renderer):
        self.r = renderer
        self.data = {}
        self.text = TextCache(os.path.join(os.path.dirname(__file__), "..", "fonts"))
        self._noise = None

    def mapdata(self, name):
        if name not in self.data:
            self.data[name] = MapData(self.r.base, self.r.tl["maps"][name])
        return self.data[name]

    def render(self, layer, p, t):
        r = self.r
        W, H_ = r.W, r.H
        md = self.mapdata(layer["map"])
        self.mapdata_cur = md
        H = camera_matrix(p, r.k, r.ky)
        canvas = np.zeros((H_, W, 3), np.float32)
        alpha = np.zeros((H_, W), np.float32)
        for it in layer.get("items", []):
            if t < it.get("start", -1e9) or t >= it.get("end", 1e9):
                continue
            ip = props_at(it.get("keys", []), t, it.get("props"))
            if ip.get("opacity", 1.0) <= 0.002:
                continue
            fn = getattr(self, "_" + it["kind"])
            fn(canvas, alpha, md, H, it, ip, p)
        return canvas, alpha

    # ---------------------------------------------------------------- raster
    def _raster(self, canvas, alpha, md, H, it, ip, cam):
        r = self.r
        levels, A, res = md.raster(it["src"])
        scale = res / cam["mpp"] * r.k  # Ausgabe-px pro Raster-px (Bildmitte)
        lvl = 0
        while scale < 0.5 and lvl + 1 < len(levels):
            scale *= 2
            lvl += 1
        f = 2 ** lvl
        Hr = H @ A @ np.diag([f, f, 1.0])
        img = levels[lvl]
        flags = cv2.INTER_LINEAR if scale < 1.6 else cv2.INTER_CUBIC
        ext = it.get("extend", False)  # Rand fortsetzen (z. B. Horizont bei starker Neigung)
        warped = cv2.warpPerspective(img, Hr, (r.W, r.H), flags=flags,
                                     borderMode=cv2.BORDER_REFLECT if ext else cv2.BORDER_CONSTANT,
                                     borderValue=(0, 0, 0)).astype(np.float32)[..., ::-1] / 255.0
        if ext:
            cov = np.ones((r.H, r.W), np.float32)
        else:
            cov = cv2.warpPerspective(self._feather(it["src"], lvl, img.shape[:2], it.get("edge_feather", 0.0)), Hr,
                                      (r.W, r.H), flags=cv2.INTER_LINEAR).astype(np.float32) / 255.0
        m = None
        if it.get("mask"):
            ml = md.mask(it["mask"])
            mm = ml[min(lvl, len(ml) - 1)]
            mf = img.shape[1] / mm.shape[1]
            m = cv2.warpPerspective(mm, Hr @ np.diag([mf, mf, 1.0]), (r.W, r.H),
                                    flags=cv2.INTER_LINEAR).astype(np.float32) / 255.0
            if it.get("mask_feather"):
                m = cv2.GaussianBlur(m, (0, 0), it["mask_feather"] * r.k)
        sat, val = ip.get("sat", 1.0), ip.get("value", 1.0)
        osat, oval = ip.get("out_sat", sat), ip.get("out_value", val)
        if m is not None and (osat != sat or oval != val):
            gray = warped @ np.array([0.299, 0.587, 0.114], np.float32)
            mi = m[..., None]
            s_ = sat * mi + osat * (1 - mi)
            v_ = val * mi + oval * (1 - mi)
            warped = (gray[..., None] + (warped - gray[..., None]) * s_) * v_
        else:
            if sat != 1.0:
                gray = warped @ np.array([0.299, 0.587, 0.114], np.float32)
                warped = gray[..., None] + (warped - gray[..., None]) * sat
            if val != 1.0:
                warped *= val
        tint = ip.get("tint")
        if tint and tint[3] > 0:
            col = np.asarray(tint[:3], np.float32) / 255.0
            amt = tint[3] * (m[..., None] if m is not None else 1.0)
            mode = it.get("tint_mode", "mix")
            if mode == "multiply":
                warped = warped * (1 - amt) + warped * col * amt * 1.6
            else:
                warped = warped * (1 - amt) + col * amt
        a = cov * ip.get("opacity", 1.0)
        dis = ip.get("dissolve")
        if dis is not None:
            a *= self._dissolve_mask(dis, it)
        _add = a[..., None]
        canvas *= (1 - _add)
        canvas += np.clip(warped, 0, 1) * _add
        np.maximum(alpha, a, out=alpha)

    def _feather(self, src, lvl, shape, frac):
        """Deckungsmaske eines Rasters mit weich auslaufendem Rand (frac = Anteil der kürzeren Seite)."""
        key = (src, lvl, frac)
        if not hasattr(self, "_fcache"):
            self._fcache = {}
        if key not in self._fcache:
            m = np.full(shape, 255, np.uint8)
            if frac > 0:
                b = max(2, int(min(shape) * frac))
                m = np.zeros(shape, np.uint8)
                m[b:-b, b:-b] = 255
                m = cv2.GaussianBlur(m, (0, 0), b / 2.5)
            self._fcache[key] = m
        return self._fcache[key]

    def _dissolve_mask(self, d, it):
        """Tinten-Übergang: sichtbar, wo (Radialabstand + Rauschen) < d."""
        r = self.r
        if d >= 1.0:
            return 1.0
        if d <= 0.0:
            return 0.0
        if self._noise is None or self._noise.shape != (r.H, r.W):
            self._noise = _ink_noise(r.H, r.W)
        c = it.get("dissolve_center", [540, 1100])
        yy, xx = np.mgrid[0:r.H, 0:r.W].astype(np.float32)
        dist = np.hypot(xx - c[0] * r.k, yy - c[1] * r.ky) / (np.hypot(r.W, r.H))
        field = dist * 0.8 + self._noise * 0.45
        soft = 0.04
        return np.clip((d * 1.3 - field) / soft, 0, 1)

    # ---------------------------------------------------------------- lines
    def _geom(self, md, it):
        """Geometrie eines Items: it["points"] (inline, eine Linie oder Liste) oder Vektor it["src"]."""
        if "points" in it:
            if "_geom" not in it:
                ls = it["points"]
                if ls and isinstance(ls[0][0], (int, float)):
                    ls = [ls]
                arrs = [np.asarray(l, np.float64) for l in ls]
                it["_geom"] = (np.vstack(arrs), np.cumsum([0] + [len(a) for a in arrs]),
                               np.array([a.mean(0) for a in arrs]))
            return it["_geom"]
        return md.lines(it["src"])

    def _lines(self, canvas, alpha, md, H, it, ip, cam):
        r = self.r
        pts, idx, mids = self._geom(md, it)
        q, w = project(H, pts)
        keep = np.ones(len(idx) - 1, bool)
        rev = ip.get("reveal")
        if rev is not None and rev < 1.0:
            d = np.asarray(it.get("reveal_dir", [0, 1]), np.float64)
            d /= np.linalg.norm(d)
            s = mids @ d
            lo, hi = it.get("reveal_range") or (s.min(), s.max())
            keep &= (s - lo) / (hi - lo + 1e-9) <= rev
        polys = [q[idx[i]:idx[i + 1]].astype(np.int32) for i in np.nonzero(keep)[0]
                 if (w[idx[i]:idx[i + 1]] > 0).all()]
        if not polys:
            return
        zoom = (it.get("ref_mpp", cam["mpp"]) / cam["mpp"]) ** it.get("width_zoom", 0.0)
        width = it.get("width", 1.5) * r.k * zoom
        m = np.zeros((r.H, r.W), np.uint8)
        # Linienbreite < 1 px -> als 1 px mit reduzierter Deckkraft
        th = max(1, int(round(width)))
        cv2.polylines(m, polys, False, 255, th, cv2.LINE_AA)
        mask = m.astype(np.float32) / 255.0 * min(1.0, width / th if width < 1 else 1.0)
        op = ip.get("opacity", 1.0)
        if it.get("glow"):
            g = it["glow"]
            gm = _blur_glow(mask, g.get("width", 6) * r.k) * g.get("strength", 1.0)
            _add_color(canvas, np.clip(gm * op, 0, 1), g["color"], g.get("mode", "screen"))
        _add_color(canvas, mask * op * it.get("alpha", 1.0), it.get("color", [255, 255, 255]))

    # ---------------------------------------------------------------- path
    def _path(self, canvas, alpha, md, H, it, ip, cam):
        r = self.r
        pts, idx, _ = self._geom(md, it)
        P = pts[idx[0]:idx[1]]
        seg = np.hypot(*np.diff(P, axis=0).T)
        s = np.concatenate([[0], np.cumsum(seg)])
        L = s[-1]
        a0, a1 = ip.get("start", 0.0), ip.get("progress", 1.0)
        if it.get("reverse"):
            a0, a1 = 1 - a1, 1 - a0
        if a1 <= a0:
            return
        ss = np.linspace(a0 * L, a1 * L, max(2, int((a1 - a0) * len(P) * 1.5)))
        sub = np.stack([np.interp(ss, s, P[:, 0]), np.interp(ss, s, P[:, 1])], 1)
        q, w = project(H, sub)
        q = q[w > 0]
        if len(q) < 2:
            return
        pl = [np.round(q * 4).astype(np.int32)]  # Subpixel (shift=2)
        op = ip.get("opacity", 1.0)
        zoom = (it.get("ref_mpp", cam["mpp"]) / cam["mpp"]) ** it.get("width_zoom", 0.0)

        def stroke(width):
            m = np.zeros((r.H, r.W), np.uint8)
            th = max(1, int(round(width * r.k * zoom)))
            if it.get("dash"):
                dl, gl = it["dash"]
                # gestrichelt: Bogenlänge in Ausgabe-px
                d = np.concatenate([[0], np.cumsum(np.hypot(*np.diff(q, axis=0).T))])
                per = (dl + gl) * r.k * zoom
                on = (d % per) < dl * r.k * zoom
                for i in range(len(q) - 1):
                    if on[i]:
                        cv2.line(m, tuple(np.round(q[i] * 4).astype(int)), tuple(np.round(q[i + 1] * 4).astype(int)),
                                 255, th, cv2.LINE_AA, shift=2)
            else:
                cv2.polylines(m, pl, False, 255, th, cv2.LINE_AA, shift=2)
            return m.astype(np.float32) / 255.0

        for g in it.get("glows", []):  # [{"width":.., "blur":.., "color":.., "strength":..}]
            gm = _blur_glow(stroke(g["width"]), g.get("blur", 0) * r.k) * g.get("strength", 1.0)
            _add_color(canvas, np.clip(gm * op, 0, 1), g["color"], g.get("mode", "over"))
        cw = ip.get("core_width", it.get("core_width", 0))
        if cw > 0:
            _add_color(canvas, stroke(cw) * op, it.get("core_color", [255, 255, 255]))

    # ---------------------------------------------------------------- polygon
    def _polygon(self, canvas, alpha, md, H, it, ip, cam):
        r = self.r
        pts, idx, _ = self._geom(md, it)
        q, w = project(H, pts[idx[0]:idx[1]])
        if (w <= 0).any():
            return
        pl = [np.round(q * 4).astype(np.int32)]
        op = ip.get("opacity", 1.0)
        m = np.zeros((r.H, r.W), np.uint8)
        cv2.fillPoly(m, pl, 255, cv2.LINE_AA, shift=2)
        fill = m.astype(np.float32) / 255.0
        if it.get("feather"):
            fill = cv2.GaussianBlur(fill, (0, 0), it["feather"] * r.k)
        if it.get("fill"):
            fo = ip.get("fill_opacity", 1.0) * op
            mode = it.get("fill_mode", "over")
            if mode == "lighten":  # Fläche aufhellen (wie die gelbliche Insel im Hook)
                col = np.asarray(it["fill"][:3], np.float32) / 255.0
                a = (fill * fo)[..., None]
                canvas[:] = canvas * (1 - a) + (1 - (1 - canvas) * (1 - col)) * a
            elif mode == "multiply":
                col = np.asarray(it["fill"][:3], np.float32) / 255.0
                a = (fill * fo)[..., None]
                canvas[:] = canvas * (1 - a) + canvas * col * a
            else:
                _add_color(canvas, fill * fo, it["fill"])
        if it.get("edge_width"):
            em = np.zeros((r.H, r.W), np.uint8)
            cv2.polylines(em, pl, True, 255, max(1, int(round(it["edge_width"] * r.k))), cv2.LINE_AA, shift=2)
            e = em.astype(np.float32) / 255.0
            eo = ip.get("edge_opacity", 1.0) * op
            if it.get("edge_glow"):
                g = it["edge_glow"]
                gm = _blur_glow(e, g.get("blur", 8) * r.k) * g.get("strength", 1.0)
                _add_color(canvas, np.clip(gm * eo, 0, 1), g["color"], g.get("mode", "screen"))
            _add_color(canvas, e * eo, it.get("edge_color", [255, 255, 255]))

    # ---------------------------------------------------------------- ink
    def _ink(self, canvas, alpha, md, H, it, ip, cam):
        """Tintenfleck-Übergang: deckende Farbe, die sich mit Rauschkante ausbreitet (keys: grow 0..1, opacity)."""
        m = self._dissolve_mask(ip.get("grow", 0.0), it)
        if np.isscalar(m) and m == 0:
            return
        a = (m * ip.get("opacity", 1.0))
        if not np.isscalar(a):
            a = cv2.GaussianBlur(a.astype(np.float32), (0, 0), 6 * self.r.k)
        _add_color(canvas, a if not np.isscalar(a) else np.full(canvas.shape[:2], a, np.float32), it.get("color", [0, 0, 0]))

    # ---------------------------------------------------------------- sprite / label
    def _place(self, canvas, img_rgba, H, it, ip, cam, px_per_unit):
        """Setzt ein RGBA-Bild (uint8) an den Weltpunkt it['at'].
        on_map=True: liegt auf der Karte (dreht/neigt mit), Größe in Metern;
        sonst aufrecht, Größe in Design-px (skaliert optional mit dem Zoom)."""
        r = self.r
        if it.get("on_path"):
            pts, idx, _ = self.mapdata_cur.lines(it["on_path"]) if isinstance(it["on_path"], str) else (None, None, None)
            P = pts[idx[0]:idx[1]]
            seg = np.hypot(*np.diff(P, axis=0).T)
            sd = np.concatenate([[0], np.cumsum(seg)])
            u = ip.get("pos", 0.0) * sd[-1]
            at = np.array([np.interp(u, sd, P[:, 0]), np.interp(u, sd, P[:, 1])])
        elif it.get("at") == "camera":
            at = None
        else:
            at = np.asarray(ip.get("at") or it["at"], np.float64)
        sc = ip.get("scale", 1.0)
        op = ip.get("opacity", 1.0)
        h, w = img_rgba.shape[:2]
        anc = it.get("anchor", [0.5, 0.5])
        rgba = img_rgba.astype(np.float32) / 255.0
        rgba[..., :3] *= rgba[..., 3:4]
        if it.get("on_map"):
            # Bild-px -> Welt: Drehung (Grad, gegen Uhrzeigersinn) um den Anker, px_per_unit = Bild-px pro Meter
            ang = math.radians(it.get("angle", 0.0) + ip.get("rot", 0.0))
            c, s = math.cos(ang), math.sin(ang)
            u = 1.0 / px_per_unit * sc
            M = np.array([[c * u, s * u, 0], [s * u, -c * u, 0], [0, 0, 1]])  # Bild-y nach unten -> Welt-y nach oben
            M = np.array([[1, 0, at[0]], [0, 1, at[1]], [0, 0, 1]]) @ M @ \
                np.array([[1, 0, -anc[0] * w], [0, 1, -anc[1] * h], [0, 0, 1]])
            Hs = H @ M
        else:
            if at is None:  # an die Bildmitte geheftet (Bildschirm-Grafik)
                x, y = cam.get("ox", DESIGN_W / 2) * r.k, cam.get("oy", DESIGN_H / 2) * r.ky
            else:
                q, wv = project(H, [at])
                if wv[0] <= 0:
                    return
                x, y = q[0]
            x += ip.get("dx", it.get("dx", 0.0)) * r.k
            y += ip.get("dy", it.get("dy", 0.0)) * r.ky
            zoom = (it.get("ref_mpp", cam["mpp"]) / cam["mpp"]) ** it.get("size_zoom", 0.0)
            u = px_per_unit * sc * zoom * r.k
            ang = math.radians(ip.get("rot", 0.0))
            c, s = math.cos(ang), math.sin(ang)
            Hs = np.array([[c * u, s * u, x], [-s * u, c * u, y], [0, 0, 1]]) @ \
                np.array([[1, 0, -anc[0] * w], [0, 1, -anc[1] * h], [0, 0, 1]])
        # Mip für starke Verkleinerung
        eff = math.sqrt(abs(np.linalg.det(Hs[:2, :2]))) if not it.get("on_map") else local_scale(H, at) / px_per_unit * sc
        src = rgba
        f = 1
        while eff * f < 0.5 and min(src.shape[:2]) > 8:
            src = cv2.pyrDown(src)
            f *= 2
        Hs = Hs @ np.diag([f, f, 1.0])
        warped = cv2.warpPerspective(src, Hs, (r.W, r.H), flags=cv2.INTER_LINEAR,
                                     borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))
        a = warped[..., 3:4] * op
        canvas *= (1 - a)
        canvas += warped[..., :3] * op

    def _sprite(self, canvas, alpha, md, H, it, ip, cam):
        a = self.r.asset(it["asset"])
        img = a.levels[0]
        rgba = np.clip(img.copy(), 0, 1)
        un = rgba.copy()
        un[..., :3] = np.where(un[..., 3:4] > 1e-4, un[..., :3] / np.maximum(un[..., 3:4], 1e-4), 0)
        u8 = (un * 255).astype(np.uint8)
        if it.get("on_map"):
            ppu = u8.shape[1] / it["size_m"]  # Bild-px pro Meter
        else:
            ppu = it.get("size", u8.shape[1]) / u8.shape[1]  # Design-px pro Bild-px
        self._place(canvas, u8, H, it, ip, cam, ppu)

    def _label(self, canvas, alpha, md, H, it, ip, cam):
        px = it.get("render_px", 160)
        img = self.text.render(it["text"], it.get("font", "roboto-latin-700-normal"), px,
                               tuple(it.get("color", [255, 255, 255])), it.get("shadow"),
                               it.get("stroke", 0), tuple(it.get("stroke_color", [0, 0, 0])), it.get("glow"))
        # PIL liefert RGBA (nicht vormultipliziert, RGB-Reihenfolge) -> passt zu _place
        cap = px * 0.7  # grobe Versalhöhe in Bild-px
        if it.get("on_map"):
            ppu = cap / it["height_m"]
        else:
            ppu = it.get("size", 40) / cap
        self._place(canvas, img, H, it, ip, cam, ppu)
