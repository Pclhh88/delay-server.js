"""Timeline renderer.

Renders a timeline JSON (see docs/TIMELINE_SCHEMA.md) into an MP4.
All coordinates in the timeline are *design units* on a 1080x1920 canvas;
the output resolution is free (e.g. 480x854 for comparison against the
reference, 1080x1920 for publishing).

Compositing is done in float32, premultiplied alpha, with OpenCV warps.
"""
import json
import math
import os
import subprocess
import sys

import cv2
import numpy as np

from .keyframes import props_at
from . import shapes
from .text import TextRenderer

DESIGN_W, DESIGN_H = 1080, 1920


def _mat(a, b, c, d, e, f):
    return np.array([[a, b, c], [d, e, f], [0, 0, 1]], np.float64)


def translate(x, y):
    return _mat(1, 0, x, 0, 1, y)


def scale(sx, sy):
    return _mat(sx, 0, 0, 0, sy, 0)


def rotate(deg):
    r = math.radians(deg)
    c, s = math.cos(r), math.sin(r)
    return _mat(c, -s, 0, s, c, 0)


class Asset:
    """An RGBA image with a mip pyramid, premultiplied float32."""

    def __init__(self, path, design_scale=1.0):
        im = cv2.imread(path, cv2.IMREAD_UNCHANGED)
        if im is None:
            raise FileNotFoundError(path)
        if im.ndim == 2:
            im = cv2.cvtColor(im, cv2.COLOR_GRAY2BGRA)
        if im.shape[2] == 3:
            im = cv2.cvtColor(im, cv2.COLOR_BGR2BGRA)
        im = cv2.cvtColor(im, cv2.COLOR_BGRA2RGBA).astype(np.float32) / 255.0
        im[..., :3] *= im[..., 3:4]
        self.levels = [im]
        while min(self.levels[-1].shape[:2]) > 64:
            self.levels.append(cv2.pyrDown(self.levels[-1]))
        self.h, self.w = im.shape[:2]
        self.design_scale = design_scale

    def level_for(self, eff_scale):
        lvl = 0
        while eff_scale < 0.5 and lvl + 1 < len(self.levels):
            eff_scale *= 2
            lvl += 1
        return lvl


class Renderer:
    def __init__(self, timeline, base_dir, out_w=1080, out_h=1920):
        self.tl = timeline
        self.base = base_dir
        self.W, self.H = out_w, out_h
        self.k = out_w / DESIGN_W
        self.ky = out_h / DESIGN_H
        self.fps = timeline["meta"].get("fps", 30)
        self.assets = {}
        manifest = timeline.get("assets", {})
        self.manifest = manifest
        self.text = TextRenderer(os.path.join(os.path.dirname(__file__), "..", "fonts"))
        self.allow_proxies = True

    # ------------------------------------------------------------ assets
    def asset(self, aid, frame=None):
        """Image asset; for sequence assets (spec "frames": N, path with {i})
        `frame` selects the image (cached individually)."""
        if frame is not None:
            spec = self.manifest[aid]
            frame = int(min(max(frame, 0), spec["frames"] - 1))
            key = f"{aid}#{frame}"
            if key not in self.assets:
                if spec.get("license") == "reference_proxy" and not self.allow_proxies:
                    raise RuntimeError(f"asset {aid} is a reference proxy without publishing rights")
                path = os.path.join(self.base, spec["path"].format(i=frame))
                self.assets[key] = Asset(path, spec.get("design_scale", 1.0))
            return self.assets[key]
        if aid not in self.assets:
            spec = self.manifest[aid]
            if spec.get("license") == "reference_proxy" and not self.allow_proxies:
                raise RuntimeError(
                    f"asset {aid} is a reference proxy without publishing rights")
            path = os.path.join(self.base, spec["path"])
            self.assets[aid] = Asset(path, spec.get("design_scale", 1.0))
        return self.assets[aid]

    # ------------------------------------------------------------ compositing
    def _composite(self, canvas, rgba, blend="normal", opacity=1.0):
        if opacity <= 0:
            return
        if opacity < 1:
            rgba = rgba * opacity
        a = rgba[..., 3:4]
        rgb = rgba[..., :3]
        if blend == "normal":
            canvas *= (1 - a)
            canvas += rgb
        elif blend == "add":
            canvas += rgb
        elif blend == "screen":
            canvas[:] = 1 - (1 - canvas) * (1 - rgb)
        elif blend == "multiply":
            # rgb premultiplied: result = c*(1-a) + c*rgb
            canvas[:] = canvas * (1 - a) + canvas * rgb
        else:
            raise ValueError(blend)

    def _warp(self, img, M):
        """Warp RGBA image with 3x3 matrix M (src px -> output px)."""
        return cv2.warpAffine(img, M[:2], (self.W, self.H), flags=cv2.INTER_LINEAR,
                              borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0, 0))

    def _design_to_out(self):
        return scale(self.k, self.ky)

    # ------------------------------------------------------------ layers
    def _local_matrix(self, layer, p):
        """Matrix that maps the layer's local design space into its parent's."""
        x = p.get("x")
        y = p.get("y")
        if x is None:
            x = layer.get("pivot", [DESIGN_W / 2, DESIGN_H / 2])[0]
        if y is None:
            y = layer.get("pivot", [DESIGN_W / 2, DESIGN_H / 2])[1]
        s = p.get("scale", 1.0)
        return translate(x, y) @ rotate(p.get("rot", 0.0)) @ scale(s * p.get("sx", 1.0), s * p.get("sy", 1.0))

    def render_layer(self, canvas, layer, t, parent_M, parent_op):
        if t < layer.get("start", -1e9) or t >= layer.get("end", 1e9):
            return
        p = props_at(layer.get("keys", []), t, layer.get("props"))
        op = parent_op * p.get("opacity", 1.0)
        if op <= 0.001:
            return
        typ = layer["type"]
        blend = layer.get("blend", "normal")
        if typ == "group":
            pivot = layer.get("pivot", [DESIGN_W / 2, DESIGN_H / 2])
            M = parent_M @ self._local_matrix(layer, p) @ translate(-pivot[0], -pivot[1])
            if layer.get("isolate"):
                buf = np.zeros(canvas.shape[:2] + (4,), np.float32)
                self._render_children_rgba(buf, layer["children"], t, M)
                if layer.get("clip"):
                    x, y, w, h = layer["clip"]
                    Mo = self._design_to_out() @ M
                    rect = shapes._apply(Mo, [[x, y], [x + w, y], [x + w, y + h], [x, y + h]])
                    mask = shapes._fill_poly(self, rect, [255, 255, 255, 1.0])[..., 3:4]
                    buf *= mask
                self._composite(canvas, buf, blend, op)
            else:
                for ch in layer["children"]:
                    self.render_layer(canvas, ch, t, M, op)
            return
        if typ in ("image", "sequence"):
            if typ == "sequence":
                fps = layer.get("fps", self.fps)
                a = self.asset(layer["asset"], (t - layer.get("start", 0.0)) * fps + 1e-3)
            else:
                a = self.asset(layer["asset"])
            anc = layer.get("anchor", [0.5, 0.5])
            ds = a.design_scale
            Mlocal = self._local_matrix(layer, p) @ scale(ds, ds) @ translate(-anc[0] * a.w, -anc[1] * a.h)
            M = self._design_to_out() @ parent_M @ Mlocal
            eff = math.sqrt(abs(np.linalg.det(M[:2, :2])))
            lvl = a.level_for(eff)
            img = a.levels[lvl]
            f = 2 ** lvl
            M = M @ scale(f, f)
            warped = self._warp(img, M)
            if layer.get("reveal_map"):
                # per-pixel reveal: map value v (0..1) becomes visible once the
                # keyed "reveal" value passes it (brush / paint-on effect)
                rm = self.asset(layer["reveal_map"])
                rl = min(lvl, len(rm.levels) - 1)
                rf = 2 ** rl
                sx, sy = a.w / rm.w, a.h / rm.h
                Mm = self._design_to_out() @ parent_M @ Mlocal @ scale(sx * rf, sy * rf)
                mv = self._warp(rm.levels[rl], Mm)[..., 0:1]
                rev = p.get("reveal", 0.0)
                soft = layer.get("reveal_soft", 0.06)
                warped *= np.clip((rev - mv) / soft + 0.5, 0, 1)
            tint = p.get("tint")
            if tint:
                r, g, b, amt = tint
                col = np.array([r, g, b], np.float32) / 255.0
                warped[..., :3] = warped[..., :3] * (1 - amt) + col * warped[..., 3:4] * amt
            self._composite(canvas, warped, blend, op)
            return
        if typ == "grade":
            if canvas.shape[2] == 3:
                sat = p.get("saturation", 1.0)
                val = p.get("value", 1.0)
                if sat != 1.0:
                    gray = canvas @ np.array([0.299, 0.587, 0.114], np.float32)
                    canvas[:] = gray[..., None] + (canvas - gray[..., None]) * sat
                if val != 1.0:
                    canvas *= val
            return
        # procedural layers draw in output space given full matrix
        M = self._design_to_out() @ parent_M
        rgba = shapes.draw(typ, layer, p, t, M, self)
        if rgba is not None:
            self._composite(canvas, rgba, blend, op)

    def _render_children_rgba(self, buf, children, t, M):
        """Render children into an RGBA buffer (premultiplied "over" on all
        four channels), so a whole group can be faded or blended as one."""
        saved = self._composite

        def comp(canvas, rgba, blend="normal", opacity=1.0):
            if opacity < 1:
                rgba = rgba * opacity
            a = rgba[..., 3:4]
            if blend == "add":
                canvas[..., :3] += rgba[..., :3]
                canvas[..., 3:4] = np.maximum(canvas[..., 3:4], a)
            else:
                canvas *= (1 - a)
                canvas += rgba
        self._composite = comp
        try:
            for ch in children:
                self.render_layer(buf, ch, t, M, 1.0)
        finally:
            self._composite = saved

    # ------------------------------------------------------------ frame
    def render_frame(self, t):
        canvas = np.zeros((self.H, self.W, 3), np.float32)
        I = np.eye(3)
        for layer in self.tl.get("layers", []):
            if not layer.get("above_captions"):
                self.render_layer(canvas, layer, t, I, 1.0)
        cap = self.tl.get("captions")
        if cap:
            self.text.draw_caption(self, canvas, cap, t)
        for layer in self.tl.get("layers", []):
            if layer.get("above_captions"):
                self.render_layer(canvas, layer, t, I, 1.0)
        return np.clip(canvas, 0, 1)

    def render(self, out_path, start=0.0, end=None, audio=None, crf=18, progress=True):
        end = end if end is not None else self.tl["meta"]["duration"]
        n0 = int(round(start * self.fps))
        n1 = int(round(end * self.fps))
        tmp = out_path + ".video.mp4"
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24",
               "-s", f"{self.W}x{self.H}", "-r", str(self.fps), "-i", "-",
               "-c:v", "libx264", "-preset", "medium", "-crf", str(crf),
               "-pix_fmt", "yuv420p", tmp]
        proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for n in range(n0, n1):
            # tiny offset: timeline times are rounded frame times (n/30), the frame
            # must land on/after its own key, never just before it
            t = n / self.fps + 1e-4
            fr = self.render_frame(t)
            proc.stdin.write((fr * 255 + 0.5).astype(np.uint8).tobytes())
            if progress and (n - n0) % 30 == 0:
                print(f"  frame {n}/{n1}", file=sys.stderr)
        proc.stdin.close()
        proc.wait()
        if audio:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", tmp, "-i", audio,
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest",
                            out_path], check=True)
            os.remove(tmp)
        else:
            os.replace(tmp, out_path)
        return out_path


def load_timeline(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)
