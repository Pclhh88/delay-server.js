"""Reusable choreography helpers for collage timelines (keyframes, word times,
fly-to camera over a map, audio cues).  Used by projects/*/build/build_timeline.py.
"""
import json
import math

from shortsfactory.render.keyframes import ease as _ease

JIT = {"pos": 1.6, "rot": 0.25, "fps": 12}


class Show:
    def __init__(self, meta_path, words_path, sfx_dir="audio/sfx_prepared"):
        self.META = json.load(open(meta_path))
        self.WORDS = json.load(open(words_path, encoding="utf-8"))
        self.layers, self.audio, self.map_children = [], [], []
        self.sfx_dir = sfx_dir
        self.quiet = {"paper_slide": -9.0}

    # ------------------------------------------------------------ words / audio
    def w(self, text, after=0.0, which="start"):
        for x in self.WORDS:
            if x["start"] >= after - 1e-6 and x["text"].strip("„“\".,:;?!").lower().startswith(text.lower()):
                return x[which]
        raise KeyError(text)

    def rec(self, name, t, gain=-8.0, trim=None, fade=None, peak=0.0):
        a = {"src": f"{self.sfx_dir}/{name}.wav", "start": round(t - peak, 3),
             "gain_db": gain + self.quiet.get(name, 0.0)}
        if trim:
            a["trim"] = trim
        if fade:
            a["fade_out"] = fade
        self.audio.append(a)

    def scale_for(self, asset, width):
        return width / self.META[asset]["w"]

    # ------------------------------------------------------------ layers
    def image(self, id_, asset, start, end, keys, anchor=None, jitter=True, **extra):
        L = {"id": id_, "type": "image", "asset": asset, "start": round(start, 3), "end": round(end, 3),
             "anchor": anchor or self.META[asset].get("anchor", [0.5, 0.5]), "keys": fix_keys(keys)}
        if jitter:
            L["jitter"] = JIT
        L.update(extra)
        self.layers.append(L)
        return L

    def sticker(self, id_, asset, t_in, t_out, x, y, width, rot=0.0, exit=(0, 2300), how="pop",
                sound="paper_drop", gain=-6.0, frm=None, dur_out=0.3):
        """Common case: appear at t_in (pop or slide from `frm`), hold, leave at t_out."""
        s = self.scale_for(asset, width)
        if how == "pop":
            k = pop_in(t_in, x, y, s, rot)
        else:
            fx, fy = frm
            k = slide_in(t_in, fx, fy, x, y, s, rot + 8, rot)
        k += [{"t": t_out, "x": x, "y": y}, exit_to(t_out, exit[0], exit[1], dur_out)]
        self.image(id_, asset, t_in, t_out + dur_out + 0.05, k)
        if sound:
            self.rec(sound, t_in + 0.1, gain, peak=0.42 if sound == "paper_slide" else 0.0)

    def flash(self, id_, t, color=(168, 40, 45), peak=0.45):
        self.layers.append({"id": id_, "type": "solid", "start": t - 0.02, "end": t + 0.6, "color": list(color),
                            "keys": [{"t": t - 0.02, "opacity": 0.0}, {"t": t + 0.1, "opacity": peak},
                                     {"t": t + 0.55, "opacity": 0.0}]})

    def captions(self, hide=(), big=()):
        caps = []
        for i, x in enumerate(self.WORDS):
            if any(a <= x["start"] < b for a, b in hide):
                continue
            nxt = self.WORDS[i + 1]["start"] if i + 1 < len(self.WORDS) else x["end"] + 0.3
            txt = x["text"].replace("„", "").replace("“", "").replace('"', "")
            c = {"text": txt, "start": x["start"], "end": round(min(nxt, x["end"] + 0.25), 3)}
            if txt.lower().strip(".,:;?!") in big:
                c["size"] = "big"
            caps.append(c)
        return {"style": {"font": "league-spartan-800", "size": 66, "sizes": {"big": 92}, "y": 1450,
                          "stroke_w": 3.0}, "words": caps}


def pop_in(t, x, y, s, rot=0.0, dur=0.28, from_scale=0.15):
    return [
        {"t": t, "x": x, "y": y, "scale": s * from_scale, "rot": rot - 6, "opacity": 0.0},
        {"t": t + 0.04, "opacity": 1.0},
        {"t": t + dur * 0.55, "scale": s * 1.08, "rot": rot + 1.5, "ease": "out"},
        {"t": t + dur, "scale": s, "rot": rot, "ease": "inout"},
    ]


def slide_in(t, x0, y0, x, y, s, rot0, rot, dur=0.35):
    return [{"t": t, "x": x0, "y": y0, "scale": s, "rot": rot0, "opacity": 1.0},
            {"t": t + dur, "x": x, "y": y, "rot": rot, "ease": "out3"}]


def exit_to(t, x, y, dur=0.3, rot=None, scale=None):
    k = {"t": t + dur, "x": x, "y": y, "ease": "in"}
    if rot is not None:
        k["rot"] = rot
    if scale is not None:
        k["scale"] = scale
    return k


def fix_keys(keys):
    last, out = {}, []
    for k in sorted(keys, key=lambda k: k["t"]):
        k = dict(k)
        for p, v in list(k.items()):
            if v is None:
                if p in last:
                    k[p] = last[p]
                else:
                    del k[p]
        for p, v in k.items():
            if p not in ("t", "ease"):
                last[p] = v
        out.append(k)
    return out


def fly_camera(cam, end, fps=30):
    """cam: [(t, focus_x, focus_y, zoom, ease)] in map px -> (scale keys, pan keys).
    Zoom interpolates geometrically, pan weighted by 1/zoom (smooth 'fly-to')."""
    def at(t):
        if t <= cam[0][0]:
            return cam[0][1:4]
        for a, b in zip(cam, cam[1:]):
            if a[0] <= t <= b[0]:
                e = _ease(b[4] or "linear", (t - a[0]) / max(1e-6, b[0] - a[0]))
                s0, s1 = a[3], b[3]
                s_ = math.exp(math.log(s0) + (math.log(s1) - math.log(s0)) * e)
                wgt = e if abs(s1 - s0) < 1e-9 else (1 / s0 - 1 / s_) / (1 / s0 - 1 / s1)
                return a[1] + (b[1] - a[1]) * wgt, a[2] + (b[2] - a[2]) * wgt, s_
        return cam[-1][1:4]
    sk, pk = [], []
    for n in range(int(end * fps) + 2):
        t = n / fps
        x, y, s_ = at(t)
        sk.append({"t": round(t, 4), "scale": s_})
        pk.append({"t": round(t, 4), "x": 540 - x, "y": 960 - y})
    return sk, pk


def path_keys(pts, t0, t1, n=30, rot_smooth=0.3):
    """Keys that move an object along a polyline (inout), heading follows the path."""
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]
    tot = sum(seg)

    def pt(f):
        d = f * tot
        for (a, b), sl in zip(zip(pts, pts[1:]), seg):
            if d <= sl:
                u = d / sl if sl else 0
                return a[0] + (b[0] - a[0]) * u, a[1] + (b[1] - a[1]) * u, math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
            d -= sl
        a, b = pts[-2], pts[-1]
        return b[0], b[1], math.degrees(math.atan2(b[1] - a[1], b[0] - a[0]))
    keys, prog, prev = [], [], None
    for k in range(n + 1):
        f = k / n
        ff = f * f * (3 - 2 * f)
        x, y, a = pt(ff)
        t = round(t0 + (t1 - t0) * f, 3)
        keys.append({"t": t, "x": x, "y": y})
        prog.append({"t": t, "progress": ff})
    return keys, prog
