"""Vintage map renderer (Natural Earth land polygons, equirectangular).

The window may span more than 360° of longitude (land is drawn at -360/0/+360
offsets), so routes around the world stay continuous.

    m = VintageMap(lon_min=90, lon_max=300, lat_max=60, lat_min=-50, ppd=24)
    img = m.render(labels=[...])      # RGBA uint8
    x, y = m.xy(lon, lat)             # map pixel of a coordinate
"""
import json
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import PALETTE, font

DATA = os.path.join(os.path.dirname(__file__), "data", "ne_50m_land.geojson")


def _noise(h, w, scale, seed):
    rng = np.random.default_rng(seed)
    sh, sw = max(2, h // scale + 2), max(2, w // scale + 2)
    n = rng.random((sh, sw)).astype(np.float32)
    return cv2.resize(n, (w, h), interpolation=cv2.INTER_CUBIC)


def fractal_noise(h, w, seed=0, octaves=(400, 120, 30, 6), weights=(0.45, 0.3, 0.17, 0.08)):
    out = np.zeros((h, w), np.float32)
    for i, (s, wt) in enumerate(zip(octaves, weights)):
        out += wt * _noise(h, w, s, seed + i)
    return out


class VintageMap:
    def __init__(self, lon_min, lon_max, lat_max, lat_min, ppd=20):
        self.lon_min, self.lon_max = lon_min, lon_max
        self.lat_max, self.lat_min = lat_max, lat_min
        self.ppd = ppd
        self.W = int(round((lon_max - lon_min) * ppd))
        self.H = int(round((lat_max - lat_min) * ppd))

    def params(self):
        return dict(lon_min=self.lon_min, lon_max=self.lon_max, lat_max=self.lat_max,
                    lat_min=self.lat_min, ppd=self.ppd, w=self.W, h=self.H)

    def unwrap(self, lon):
        while lon < self.lon_min:
            lon += 360
        while lon > self.lon_max:
            lon -= 360
        return lon

    def xy(self, lon, lat, unwrap=True):
        if unwrap:
            lon = self.unwrap(lon)
        return ((lon - self.lon_min) * self.ppd, (self.lat_max - lat) * self.ppd)

    def route_xy(self, pts):
        """Continuous route: longitudes unwrapped so consecutive points never jump >180°."""
        out, prev = [], None
        for lon, lat in pts:
            if prev is None:
                lon = self.unwrap(lon)
            else:
                while lon - prev > 180:
                    lon -= 360
                while lon - prev < -180:
                    lon += 360
            prev = lon
            out.append(self.xy(lon, lat, unwrap=False))
        return out

    def land_mask(self, ss=2):
        gj = json.load(open(DATA, encoding="utf-8"))
        mask = np.zeros((self.H * ss, self.W * ss), np.uint8)
        polys = []
        for f in gj["features"]:
            g = f["geometry"]
            parts = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            for poly in parts:
                for ring_i, ring in enumerate(poly):
                    polys.append((ring_i, np.array(ring, np.float64)))
        for off in (-360, 0, 360):
            for ring_i, ring in polys:
                lon = ring[:, 0] + off
                if lon.max() < self.lon_min - 1 or lon.min() > self.lon_max + 1:
                    continue
                x = (lon - self.lon_min) * self.ppd * ss
                y = (self.lat_max - ring[:, 1]) * self.ppd * ss
                pts = np.round(np.c_[x, y] * 4).astype(np.int32)
                cv2.fillPoly(mask, [pts], 0 if ring_i else 255, lineType=cv2.LINE_AA, shift=2)
        return cv2.resize(mask, (self.W, self.H), interpolation=cv2.INTER_AREA).astype(np.float32) / 255

    def render(self, labels=(), seed=3, grid=15, folds=(3, 2), water_lines=True):
        H, W = self.H, self.W
        land = self.land_mask()
        sea = np.array(PALETTE["sea"], np.float32) / 255
        lnd = np.array(PALETTE["land"], np.float32) / 255
        coast = np.array(PALETTE["coast"], np.float32) / 255
        n = fractal_noise(H, W, seed)
        img = sea[None, None] * (0.86 + 0.28 * n[..., None])
        # land: paler towards the interior, warm blotches
        dist_in = cv2.distanceTransform((land > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
        inner = np.clip(dist_in / (3.0 * self.ppd), 0, 1)[..., None]
        land_col = lnd[None, None] * (0.9 + 0.2 * n[..., None]) * (0.94 + 0.08 * inner)
        img = img * (1 - land[..., None]) + land_col * land[..., None]
        # water lining (offshore ripple lines, classic engraved maps)
        if water_lines:
            dist_out = cv2.distanceTransform((land < 0.5).astype(np.uint8), cv2.DIST_L2, 5)
            for k, d in enumerate((0.25, 0.55, 0.95)):
                dd = d * self.ppd
                line = np.clip(1 - np.abs(dist_out - dd) / max(1.0, self.ppd * 0.035), 0, 1)
                img -= (line * (0.10 - 0.025 * k))[..., None] * 0.9
        # coastline ink
        edge = cv2.morphologyEx((land * 255).astype(np.uint8), cv2.MORPH_GRADIENT, np.ones((3, 3), np.uint8))
        edge = cv2.GaussianBlur(edge.astype(np.float32) / 255, (0, 0), max(0.6, self.ppd / 30))
        edge = np.clip(edge * 1.6, 0, 1)[..., None]
        img = img * (1 - edge * 0.8) + coast[None, None] * edge * 0.8
        img = np.clip(img, 0, 1)
        pil = Image.fromarray((img * 255).astype(np.uint8), "RGB").convert("RGBA")
        ov = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        lw = max(1, int(self.ppd / 14))
        gcol = (60, 80, 70, 70)
        lon0 = math.ceil(self.lon_min / grid) * grid
        for lon in range(int(lon0), int(self.lon_max) + 1, grid):
            x = (lon - self.lon_min) * self.ppd
            d.line([(x, 0), (x, H)], fill=gcol, width=lw)
        lat0 = math.floor(self.lat_max / grid) * grid
        for lat in range(int(lat0), int(self.lat_min) - 1, -grid):
            y = (self.lat_max - lat) * self.ppd
            if lat == 0:
                for x0 in range(0, W, int(self.ppd)):
                    d.line([(x0, y), (x0 + self.ppd * 0.6, y)], fill=(70, 60, 45, 140), width=lw + 1)
            else:
                d.line([(0, y), (W, y)], fill=gcol, width=lw)
        for lab in labels:
            self._label(d, lab)
        pil = Image.alpha_composite(pil, ov)
        img = np.asarray(pil.convert("RGB")).astype(np.float32) / 255
        # folds / creases
        fx, fy = folds
        for i in range(1, fx):
            x = int(W * i / fx)
            band = np.exp(-((np.arange(W) - x) / (self.ppd * 0.5)) ** 2)
            img *= (1 - 0.07 * band)[None, :, None]
            img[:, x:x + max(1, lw)] = np.minimum(1, img[:, x:x + max(1, lw)] * 1.12)
        for i in range(1, fy):
            y = int(H * i / fy)
            band = np.exp(-((np.arange(H) - y) / (self.ppd * 0.5)) ** 2)
            img *= (1 - 0.07 * band)[:, None, None]
            img[y:y + max(1, lw)] = np.minimum(1, img[y:y + max(1, lw)] * 1.12)
        # aged paper: stains + grain + slight yellowing
        stains = fractal_noise(H, W, seed + 10, octaves=(700, 200, 50), weights=(0.6, 0.3, 0.1))
        img *= (0.9 + 0.12 * stains)[..., None]
        img = img * np.array([1.0, 0.985, 0.94], np.float32)
        grain = np.random.default_rng(seed).normal(0, 0.025, (H, W)).astype(np.float32)
        img += grain[..., None]
        img = np.clip(img, 0, 1)
        out = np.dstack([(img * 255).astype(np.uint8), np.full((H, W), 255, np.uint8)])
        return out

    def _label(self, d, lab):
        """lab: {"text", "lon", "lat", "size" (deg), "style": serif|serif_italic, "spacing", "color"}"""
        px = int(lab.get("size", 2.0) * self.ppd)
        f = ImageFont.truetype(font(lab.get("style", "serif_italic")), px)
        txt = lab["text"]
        sp = lab.get("spacing", 0.25) * px
        x, y = self.xy(lab["lon"], lab["lat"])
        widths = [f.getlength(c) for c in txt]
        total = sum(widths) + sp * (len(txt) - 1)
        cx = x - total / 2
        col = tuple(lab.get("color", (70, 58, 42))) + (lab.get("alpha", 190),)
        for c, w in zip(txt, widths):
            d.text((cx, y), c, font=f, fill=col, anchor="lm")
            cx += w + sp
