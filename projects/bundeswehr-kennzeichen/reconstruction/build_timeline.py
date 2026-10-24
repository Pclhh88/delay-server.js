"""Assemble the reconstruction timeline (timeline.json) from measurements.

All numbers that come from the reference are measured (see measurements.json
and ../analysis/*.json); the code here only converts them into layers and
keyframes.  Times are seconds (frame / 30).  Positions are design units
(1080x1920 canvas); reference pixels (480x854) are multiplied by D = 2.25.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PROJ))
sys.path.insert(0, ROOT)

FPS = 30
D = 2.25            # design units per reference pixel
ARROW_L = 443.0     # measured arrow length (design units)


def F(n):
    """frame number -> seconds"""
    return round(n / FPS, 5)


def load(name):
    with open(os.path.join(HERE, name)) as f:
        return json.load(f)


MEAS = load("measurements.json")
CAPTIONS = json.load(open(os.path.join(PROJ, "analysis", "captions.json"), encoding="utf-8"))
STYLE = json.load(open(os.path.join(PROJ, "analysis", "style_measurements.json"), encoding="utf-8"))


# ------------------------------------------------------------------ helpers
def cam_keys(M, origin, Fm, frames, extra=None):
    """Keys for a mosaic layer (anchor 0,0, asset design_scale = D/Fm).

    reference px of mosaic pixel m in frame n:  s_n*(m/Fm + o) + t_n
    """
    keys = []
    for n in frames:
        m = M[str(n)]
        s = math.hypot(m[0][0], m[1][0])
        rot = math.degrees(math.atan2(m[1][0], m[0][0]))
        # position of the mosaic origin (m=0)
        x = m[0][0] * origin[0] + m[0][1] * origin[1] + m[0][2]
        y = m[1][0] * origin[0] + m[1][1] * origin[1] + m[1][2]
        keys.append({"t": F(n), "x": round(x * D, 2), "y": round(y * D, 2),
                     "scale": round(s, 5), "rot": round(rot, 3)})
    if extra:
        keys += extra
    keys.sort(key=lambda k: k["t"])
    return keys


def arrow_keys(points, length=ARROW_L):
    """points: [(frame, tip_x_ref, tip_y_ref, angle_deg[, opacity])]"""
    keys = []
    for p in points:
        k = {"t": F(p[0]), "x": round(p[1] * D, 2), "y": round(p[2] * D, 2), "rot": round(p[3], 2)}
        if len(p) > 4:
            k["opacity"] = p[4]
        keys.append(k)
    return keys


def along(tip, ang, dist):
    """point `dist` reference px behind `tip` along the arrow axis."""
    a = math.radians(ang)
    return tip[0] - math.cos(a) * dist, tip[1] - math.sin(a) * dist


def credit(text, start, end, keys=None):
    """Vertical source credit at the right edge (reads top -> bottom)."""
    return {"id": f"credit_{start}", "type": "text", "text": text, "start": start, "end": end,
            "size": STYLE["credit"]["size"], "style": {"font": STYLE["credit"]["font"],
                                                       "fill": STYLE["credit"]["fill"]},
            "keys": keys or [{"t": start, "x": STYLE["credit"]["x"], "y": STYLE["credit"]["y_center"],
                              "rot": 90, "opacity": STYLE["credit"]["opacity"]}]}


def label(text, start, end, appear_frame=None, appear=None, exit=None):
    """Source marker like [Q1] top-left; slides in from the top.
    appear/exit = (first_frame, last_frame, distance_ref_px) for measured slides."""
    st = STYLE["label"]
    x, y = st["x"], st["y"]
    keys = [{"t": start, "x": x, "y": y, "opacity": st["opacity"]}]
    if appear_frame is not None:
        a = F(appear_frame)
        keys = [{"t": a, "x": x, "y": y - st["slide"], "opacity": st["opacity"]},
                {"t": a + st["slide_dur"], "x": x, "y": y, "opacity": st["opacity"], "ease": "out3"}]
    if appear is not None:
        keys = [{"t": F(appear[0]), "x": x, "y": y - appear[2] * D, "opacity": st["opacity"]},
                {"t": F(appear[1]), "x": x, "y": y, "opacity": st["opacity"], "ease": "out"}]
    if exit is not None:
        keys += [{"t": F(exit[0]), "x": x, "y": y},
                 {"t": F(exit[1]), "x": x, "y": y - exit[2] * D, "ease": "in"}]
    return {"id": f"label_{text}_{start}", "type": "text", "text": text, "start": start, "end": end,
            "size": st["size"], "style": {"font": st["font"], "fill": st["fill"]},
            "keys": keys}


# ------------------------------------------------------------------ scenes
def scene_q1():
    """0.00-2.83  Hook: Bundeswehr-Kennzeichen reflektieren nicht."""
    q = MEAS["q1"]
    frames = [0, 2, 3, 4, 5, 42, 43, 44, 45, 69, 70, 71, 72, 82, 83]
    jeep_keys = cam_keys(q["M"], q["origin"], q["F"], frames)
    # frame 84: the jeep has left the frame to the right (whip)
    last = dict(jeep_keys[-1])
    last.update({"t": F(84), "x": last["x"] + 900 * D})
    jeep_keys.append(last)

    A = MEAS["arrows_raw"]
    t45 = A["45"]
    t72 = A["72"]
    a1 = [
        (43, *along(t45[:2], t45[2], 2 * 217), t45[2]),
        (44, *along(t45[:2], t45[2], 217), t45[2] + 8),
        (45, t45[0], t45[1], t45[2]),
        (69, t45[0], t45[1], t45[2]),
        (70, *A["70"][:3]),
        (71, *A["71"][:3]),
        (72, t72[0], t72[1], t72[2]),
        (82, t72[0], t72[1], t72[2]),
        (83, *A["83"][:3]),
        (84, *A["84"][:3]),
    ]
    layers = [
        {"id": "q1_backdrop", "type": "image", "asset": "q1_backdrop", "anchor": [0, 0],
         "keys": [{"t": 0, "x": 0, "y": 0}]},
        {"id": "q1_jeep", "type": "image", "asset": "q1_jeep_photo", "anchor": [0, 0],
         "keys": jeep_keys},
        {"id": "q1_arrow", "type": "arrow", "start": F(43), "keys": arrow_keys(a1),
         "shape": {"length": ARROW_L}},
        credit("QUELLE: WIKI COMMONS: DARKONE - CC2.5", 0, F(84)),
        label("[Q1]", F(5), F(84), appear_frame=5),
    ]
    return {"id": "s01_hook_q1", "type": "group", "start": 0, "end": F(85),
            "children": layers}


def track_keys(track, frames=None, design=True, extra=None, scale_mul=1.0):
    """Keys from a sprite track (centre/scale/rot per frame)."""
    keys = []
    for n, v in sorted(track.items(), key=lambda kv: int(kv[0])):
        n = int(n)
        if frames is not None and n not in frames:
            continue
        keys.append({"t": F(n), "x": round(v["cx"] * D, 2), "y": round(v["cy"] * D, 2),
                     "scale": round(v["scale"] * scale_mul, 4), "rot": round(v.get("rot", 0.0), 2)})
    if extra:
        keys += extra
    keys.sort(key=lambda k: k["t"])
    return dedupe(keys)


def dedupe(keys):
    """Drop keys that lie on the straight line between their neighbours."""
    if len(keys) < 3:
        return keys
    out = [keys[0]]
    for i in range(1, len(keys) - 1):
        a, b, c = out[-1], keys[i], keys[i + 1]
        same = True
        for k in b:
            if k in ("t", "ease") or k not in a or k not in c:
                continue
            span = c["t"] - a["t"]
            if span <= 0:
                continue
            p = (b["t"] - a["t"]) / span
            if isinstance(b[k], (int, float)) and abs(a[k] + (c[k] - a[k]) * p - b[k]) > 1e-3 * max(1, abs(b[k])):
                same = False
        if not same or b.get("ease"):
            out.append(b)
    out.append(keys[-1])
    return out


def M_keys(track, frames, origin, Fm):
    """Camera keys for a mosaic asset from similarity matrices {frame: {"M": ..}}."""
    M = {str(n): track[str(n)]["M"] for n in frames if track.get(str(n))}
    return cam_keys(M, origin, Fm, [int(n) for n in M])


def k(n, **kw):
    d = {"t": F(n)}
    d.update(kw)
    return d


def logo_placeholder(start, end):
    """Neutral 2x2 tile logo in place of the broadcaster logo (pops in at 93,
    'morphs' at 120 like the original)."""
    tile = 34 * D
    gap = 4 * D
    cx, cy = 240 * D, 150 * D
    tiles = []
    for i, (dx, dy) in enumerate([(-1, -1), (1, -1), (-1, 1), (1, 1)]):
        x = cx + dx * (tile + gap) / 2 - tile / 2
        y = cy + dy * (tile + gap) / 2 - tile / 2
        tiles.append({"type": "solid", "rect": [x, y, tile, tile], "color": [255, 255, 255]})
    return {"id": "brand_logo_placeholder", "type": "group", "start": start, "end": end,
            "pivot": [cx, cy],
            "keys": [k(92, sx=1.0, sy=0.0), k(93, sx=0.9, sy=0.08), k(96, sx=1.05, sy=0.6),
                     k(99, sx=1.0, sy=1.12, ease="out"), k(102, sx=1.0, sy=1.0, ease="out"),
                     k(119, scale=1.0), k(121, scale=0.85, rot=-8), k(124, scale=1.08, rot=4),
                     k(127, scale=1.0, rot=0, ease="out")],
            "children": tiles,
            "_note": "Original: Senderlogo mit Buchstaben-Morph. Bewusst nicht nachgebaut (Markenrecht)."}


def scene_s3():
    """2.83-6.20  'Waere ja auch dumm, wenn du das ganze Fahrzeug in John-Cena-
    Lackierung anmalst' - grey jeep pops in, Bob Ross paints it camo."""
    jt = MEAS["s3_jeep_grey_track"]
    pop = {n: v for n, v in jt.items() if 98 <= int(n) <= 103}
    grey_keys = track_keys(pop, extra=[k(97, x=233.5 * D, y=433.5 * D, scale=0.0)])
    bt = MEAS["s3_bob_track"]
    bob = {n: v for n, v in bt.items() if 131 <= int(n) <= 184}
    bob_keys = track_keys(bob, extra=[k(130, x=-52 * D, y=307 * D, scale=1.0, rot=0.0),
                                      k(185, x=-40 * D, y=860 * D, scale=1.0, rot=0.0)])
    jeep_xy = {"x": 233.5 * D, "y": 433.5 * D}
    return {"id": "s03_paint", "type": "group", "start": F(85), "end": F(186), "children": [
        {"id": "jeep_grey", "type": "image", "asset": "s3_jeep_grey", "start": F(97), "keys": grey_keys},
        {"id": "jeep_painted", "type": "image", "asset": "s3_jeep_painted", "start": F(126), "end": F(184),
         "reveal_map": "s3_paint_reveal_map", "reveal_soft": 0.08,
         "keys": [k(126, reveal=0.0, **jeep_xy), k(171, reveal=1.0, **jeep_xy)]},
        {"id": "jeep_camo", "type": "image", "asset": "s3_jeep_camo", "start": F(184), "keys": [k(184, **jeep_xy)]},
        {"id": "bob_ross", "type": "image", "asset": "s3_bob", "start": F(130), "end": F(186), "keys": bob_keys},
        credit("QUELLE: WIKI COMMONS: DARKONE - CC2.5 (BEARBEITET)", F(98), F(168)),
        credit("QUELLE: WIKI COMMONS: DARKONE - CC2.5", F(168), F(186)),
    ]}


def world_camera_keys():
    bt = MEAS["bush_track"]
    frames = [193, 213, 214, 215, 216, 282, 283, 284, 285, 316]
    keys = []
    for n in frames:
        m = bt[str(n)]["M"]
        s_ = math.hypot(m[0][0], m[1][0])
        # group transform: x/y = image of the world origin (pivot 0,0)
        keys.append(k(n, x=round(m[0][2] * D, 2), y=round(m[1][2] * D, 2), scale=round(s_, 5)))
    return keys


def scene_world():
    """6.17-10.57  bush / Minecraft figure / torch / flash (world = frame 205)."""
    w = MEAS["world"]
    origin = w["origin"]
    jc = w["jeep_center"]
    bush_keys = [k(185, x=(origin[0] + 434.2) * D, y=origin[1] * D),
                 k(193, x=origin[0] * D, y=origin[1] * D)]
    jeep_keys = [k(185, x=233.5 * D, y=433.5 * D), k(193, x=jc[0] * D, y=jc[1] * D)]
    tint = MEAS["jeep_tint"]
    G = MEAS["bush_green"][::-1]
    tint_keys = []
    for n in [188, 189, 190, 191, 192, 193, 194, 195, 199, 215, 216]:
        tint_keys.append(k(n, tint=[G[0], G[1], G[2], tint[str(n)]]))
    jeep_keys = merge_keys(jeep_keys, tint_keys)
    bt = MEAS["bush_track"]
    M216 = bt["216"]["M"]
    s216 = math.hypot(M216[0][0], M216[1][0])

    def from216(p):
        return ((p[0] - M216[0][2]) / s216, (p[1] - M216[1][2]) / s216)

    o216 = from216((0.0, 0.0))
    pi = from216(MEAS["pillager_idle_ref"]["center_216"])
    pt = from216(MEAS["pillager_torch_ref"]["center_216"])
    gl = (MEAS["world_ground_line_216"] - M216[1][2]) / s216
    sky = MEAS["world_sky_bgr"][::-1]
    ground = MEAS["world_ground_bgr"][::-1]
    lc = STYLE.get("torch", {})
    world = {"id": "world", "type": "group", "pivot": [0, 0], "start": F(185), "end": F(317),
             "keys": world_camera_keys(), "children": [
                 {"id": "sky", "type": "solid", "start": F(214), "rect": [-3000, -3000, 6000, 6000], "color": sky},
                 {"id": "bush_back", "type": "image", "asset": "bush_back", "anchor": [0, 0], "keys": bush_keys},
                 {"id": "ground", "type": "solid", "start": F(214), "rect": [-3000, gl * D, 6000, 3000],
                  "color": ground},
                 {"id": "jeep_in_bush", "type": "image", "asset": "s3_jeep_camo", "keys": jeep_keys},
                 {"id": "bush_front", "type": "image", "asset": "bush_front", "anchor": [0, 0], "keys": bush_keys},
                 {"id": "pillager_idle", "type": "image", "asset": "pillager_idle", "start": F(214), "end": F(237),
                  "keys": [k(214, x=pi[0] * D, y=pi[1] * D, scale=round(1 / s216, 5))]},
                 {"id": "pillager_torch", "type": "image", "asset": "pillager_torch", "start": F(237),
                  "keys": [k(237, x=pt[0] * D, y=pt[1] * D, scale=round(1 / s216, 5))]},
                 # measured light map (frame-216 pixels) placed back into the world
                 {"id": "torch_light", "type": "image", "asset": "torch_light_216", "start": F(237),
                  "blend": "screen", "anchor": [0, 0],
                  "keys": [k(237, x=round(o216[0] * D, 2), y=round(o216[1] * D, 2), scale=round(1 / s216, 5),
                             opacity=0.0),
                           k(239, opacity=1.0)]},
             ]}
    glint = {"id": "plate_glint", "type": "glow", "start": F(312), "end": F(319), "softness": 0.35,
             "keys": [k(312, x=226 * D, y=520 * D, radius=18 * D, sx=3.0, sy=0.35),
                      k(313, radius=39 * D, sx=2.5, sy=0.4),
                      k(314, radius=28 * D, sx=1.0, sy=1.0),
                      k(315, radius=47 * D),
                      k(316, radius=114 * D),
                      k(317, radius=300 * D),
                      k(318, radius=900 * D)]}
    white = {"id": "whiteout", "type": "solid", "start": F(317), "end": F(355), "color": [255, 255, 255],
             "keys": [k(317, opacity=0.92), k(318, opacity=1.0)]}
    cat = {"id": "blinded_cat", "type": "image", "asset": "blinded_cat", "anchor": [0, 0], "start": F(319),
           "end": F(355), "keys": [k(319, x=0, y=0, opacity=0.0), k(320, opacity=0.03), k(354, opacity=1.0)]}
    return [world,
            credit("QUELLE: WIKI COMMONS: DARKONE - CC2.5", F(186), F(355)),
            label("[Q2]", F(192), F(317), appear_frame=192),
            glint, white, cat]


def merge_keys(a, b):
    by_t = {}
    for key in a + b:
        by_t.setdefault(key["t"], {}).update(key)
    return [by_t[t] for t in sorted(by_t)]


FLASH1 = [(445, 0.0), (446, .25), (447, .45), (448, .62), (449, .76), (450, .82), (451, .82), (452, .77),
          (453, .72), (454, .66), (455, .62), (456, .47), (457, .31), (458, .22), (459, .14), (460, .06),
          (461, 0.0)]
FLASH2 = [(581, 0.0), (582, .135), (583, .30), (584, .47), (585, .67), (586, .82), (587, .82), (588, .80),
          (589, .69), (590, .64), (591, .55), (592, .48), (593, .42), (594, .33), (595, .28), (596, .21),
          (597, .13), (598, .09), (599, .09)]


def red_flash(points, idn):
    return {"id": idn, "type": "solid", "color": STYLE["red_flash"]["color"], "start": F(points[0][0]),
            "end": F(points[-1][0] + 1), "keys": [k(n, opacity=a) for n, a in points]}


def scene_plates():
    """11.83-20.00  plates: Y, map, X (NATO), TUEV."""
    py = MEAS["plate_y"]
    ty = MEAS["plate_y_track"]
    frames_y = [n for n in list(range(355, 446)) + list(range(456, 506)) if ty.get(str(n))]
    y_keys = M_keys(ty, frames_y, py["origin"], py["F"])
    # hold the close-up through the red flash (tracking is blind there): 445 -> 455
    hold = dict([kk for kk in y_keys if kk["t"] == F(445)][0])
    hold["t"] = F(455)
    y_keys = sorted(y_keys + [hold], key=lambda kk: kk["t"])
    # push out to the left (measured -195 px/frame)
    last = dict(y_keys[-1])
    for n, dx in ((506, -195), (507, -390), (508, -585)):
        kk = dict(last)
        kk.update({"t": F(n), "x": last["x"] + dx * D})
        y_keys.append(kk)
    # during the red flash (446-455) the camera holds (s = 1)
    pxp = MEAS["plate_x_push"]
    x_keys = [k(506, x=770 * D, y=130 * D), k(507, x=530 * D, y=130 * D), k(508, x=410 * D, y=130 * D),
              k(542, x=410 * D, y=130 * D), k(543, x=628 * D, y=130 * D), k(544, x=846 * D, y=130 * D)]
    pt = MEAS["plate_tuev"]
    tt = MEAS["plate_tuev_track"]
    tp = MEAS["plate_tuev_push"]
    t_keys = [k(543, x=tp["543"]["cx"] * D, y=tp["543"]["cy"] * D, scale=tp["543"]["scale"]),
              k(544, x=tp["544"]["cx"] * D, y=tp["544"]["cy"] * D, scale=tp["544"]["scale"]),
              k(545, x=tp["545"]["cx"] * D, y=tp["545"]["cy"] * D, scale=tp["545"]["scale"])]
    # zoom 549-552 from the similarity track, expressed as sprite-centre keys
    from PIL import Image
    w, h = Image.open(os.path.join(PROJ, "assets", "proxies", "plate_tuev.png")).size
    for n in (549, 550, 551, 552, 599):
        m = tt[str(n)]["M"]
        cxr = pt["origin"][0] + w / 2 / pt["F"]
        cyr = pt["origin"][1] + h / 2 / pt["F"]
        x = m[0][0] * cxr + m[0][1] * cyr + m[0][2]
        y = m[1][0] * cxr + m[1][1] * cyr + m[1][2]
        t_keys.append(k(n, x=round(x * D, 2), y=round(y * D, 2), scale=round(math.hypot(m[0][0], m[1][0]), 4)))
    dbw = MEAS["drake_bw_track"]
    rest_bw = dbw["430"]
    bw_keys = [k(408, x=rest_bw["cx"] * D, y=990 * D, scale=1.0), k(409, x=rest_bw["cx"] * D, y=819 * D),
               k(410, x=rest_bw["cx"] * D, y=rest_bw["cy"] * D), k(455, x=rest_bw["cx"] * D, y=rest_bw["cy"] * D),
               k(456, y=818 * D), k(457, y=1000 * D)]
    dn = MEAS["drake_nato_track"]
    rn = dn["530"]
    nato_keys = [k(522, x=249 * D, y=815 * D, scale=0.59), k(523, x=rn["cx"] * D, y=rn["cy"] * D, scale=1.0),
                 k(542, x=rn["cx"] * D, y=rn["cy"] * D, scale=1.0), k(543, y=802 * D), k(544, y=1100 * D)]
    gm = MEAS["germany_map_track"]
    r1 = gm["470"]
    r2 = gm["490"]
    # vertical offsets measured from the flag bands (black top / red top), ref px
    map_keys = [k(465, x=r1["cx"] * D, y=(r1["cy"] + 417) * D, scale=r1["scale"]),
                k(466, y=(r1["cy"] + 210) * D), k(467, y=r1["cy"] * D),
                k(476, x=r1["cx"] * D, y=r1["cy"] * D, scale=r1["scale"])]
    for n in (477, 478):
        v = gm[str(n)]
        map_keys.append(k(n, x=v["cx"] * D, y=v["cy"] * D, scale=v["scale"]))
    map_keys += [k(479, x=r2["cx"] * D, y=r2["cy"] * D, scale=1.0), k(499, x=r2["cx"] * D, y=r2["cy"] * D),
                 k(500, y=(r2["cy"] + 247) * D), k(501, y=(r2["cy"] + 491) * D)]
    A = MEAS["arrows_raw"]
    a2 = (187.0, 358.0, -53.0)
    a3 = (163.0, 318.0, -52.0)
    arrow2 = [(371, *along(a2[:2], a2[2], 234), a2[2]), (372, *along(a2[:2], a2[2], 117), a2[2]),
              (373, *a2), (399, *a2), (400, *along(a2[:2], a2[2], 117), a2[2]),
              (401, *along(a2[:2], a2[2], 234), a2[2])]
    return [
        {"id": "plate_y", "type": "image", "asset": "plate_y", "anchor": [0, 0], "start": F(355), "end": F(509),
         "keys": y_keys},
        {"id": "arrow_y", "type": "arrow", "start": F(371), "end": F(401), "keys": arrow_keys(arrow2)},
        {"id": "drake_bw", "type": "image", "asset": "drake_bw", "start": F(408), "end": F(458), "keys": bw_keys},
        {"id": "germany_map", "type": "image", "asset": "germany_map", "start": F(465), "end": F(502),
         "keys": map_keys},
        {"id": "plate_x", "type": "image", "asset": "plate_x", "start": F(506), "end": F(545), "keys": x_keys},
        {"id": "drake_nato", "type": "image", "asset": "drake_nato", "start": F(522), "end": F(545),
         "keys": nato_keys},
        {"id": "plate_tuev", "type": "image", "asset": "plate_tuev", "start": F(543), "end": F(600), "keys": t_keys},
        {"id": "arrow_tuev", "type": "arrow", "start": F(552), "end": F(601),
         "keys": arrow_keys([(552, *a3), (599, *a3), (600, *along(a3[:2], a3[2], 234), a3[2])])},
        red_flash(FLASH1, "red_flash_keine"),
        red_flash(FLASH2, "red_flash_nicht_sehen"),
        credit("QUELLE: WIKI COMMONS: THORSTENS - CC3", F(355), F(407)),
        credit("QUELLE: WIKI COMMONS: THORSTENS - CC3, BUNDESWEHR - GEMEINFREI", F(407), F(458)),
        credit("QUELLE: WIKI COMMONS: THORSTENS - CC3", F(458), F(521)),
        credit("QUELLE: WIKI COMMONS: THORSTENS - CC3, SANGJINHWA - GEMEINFREI", F(521), F(544)),
        credit("QUELLE: WIKI COMMONS: THORSTENS - CC3", F(544), F(602)),
        label("[Q3]", F(355), F(506), appear_frame=355),
        label("[Q4]", F(506), F(551), appear_frame=506),
        label("[Q5]", F(551), F(643), appear_frame=551),
    ]


AUDIO = [
    # narration: separated voice stem of the reference (proxy, see manifest)
    {"id": "voice", "src": "audio/voice_reference_proxy.flac", "start": 0.0, "gain_db": 0.0,
     "license": "reference_proxy"},
    {"id": "sfx_impact", "src": "@sfx/impact_low", "start": 2.35, "gain_db": -4.0},
    {"id": "sfx_swoosh_scene", "src": "@sfx/swoosh", "start": 2.80, "gain_db": -14.0},
    {"id": "sfx_pop_jeep", "src": "@sfx/pop", "start": 3.29, "gain_db": -11.0},
    {"id": "sfx_bob_magic", "src": "@sfx/magic_glide", "start": 4.30, "gain_db": -16.0},
    {"id": "sfx_flash", "src": "@sfx/camera_flash", "start": 10.80, "gain_db": -5.0},
    {"id": "sfx_tinnitus", "src": "@sfx/tinnitus", "start": 11.07, "gain_db": -15.0},
    {"id": "sfx_buzzer_1", "src": "@sfx/buzzer", "start": 14.87, "gain_db": -12.0},
    {"id": "sfx_whoosh_x", "src": "@sfx/swoosh", "start": 16.90, "gain_db": -9.0},
    {"id": "sfx_whoosh_y", "src": "@sfx/swoosh_down", "start": 18.15, "gain_db": -9.0},
    {"id": "sfx_buzzer_2", "src": "@sfx/buzzer", "start": 19.42, "gain_db": -12.0},
]


def wipe_in(frame_start, frame_end, from_x_ref):
    """New gradient scene pushes in from the left with a white leading edge."""
    return {"id": f"wipe_{frame_start}", "type": "group", "start": F(frame_start), "end": F(frame_end),
            "keys": [{"t": F(frame_start), "x": 540 + from_x_ref * D},
                     {"t": F(frame_end), "x": 540}],
            "isolate": True, "clip": [0, 0, 1080, 1920],
            "children": [
                {"type": "stripes_bg", **STYLE["stripes_bg"]},
                {"type": "solid", "rect": [1080 - 5 * D, 0, 5 * D, 1920], "color": [255, 255, 255]},
            ]}


def build():
    import timeline_part2 as P2
    import timeline_part3 as P3
    words = P3.fix_part2_words(P2.fix_part1_words(CAPTIONS["words"]) + P2.caption_words2()) + P3.caption_words3()
    cap_style = dict(STYLE["caption"])
    cap_style["sizes"] = dict(cap_style["sizes"], huge=128)
    tl = {
        "meta": {"title": "Bundeswehr-Kennzeichen (Rekonstruktion)", "fps": FPS, "width": 1080,
                 "height": 1920, "duration": 50.5, "reference": "references/Bundeswehr-Kennzeichen.mp4"},
        "assets": json.load(open(os.path.join(PROJ, "assets", "manifest.json"), encoding="utf-8")),
        "layers": [
            {"id": "bg_stripes", "type": "stripes_bg", **STYLE["stripes_bg"]},
            scene_q1(),
            wipe_in(84, 85, -458),
            scene_s3(),
            *scene_world(),
            logo_placeholder(F(92), F(193)),
            *scene_plates(),
            *P2.layers_part2(),
            *P3.layers_part3(),
        ],
        "captions": {"style": cap_style, "words": words},
        "audio": AUDIO + P2.AUDIO2 + P3.AUDIO3,
    }
    out = os.path.join(PROJ, "reconstruction", "timeline.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(tl, f, indent=1, ensure_ascii=False)
    print("wrote", out)


if __name__ == "__main__":
    build()
