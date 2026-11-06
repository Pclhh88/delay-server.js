"""Stickman rig: a character drawn from vector parts and posed by numbers.

Local units: origin = ground point between the feet, y points down, the
character is ~1000 units tall (cap top at y = -1000).  Proportions and colours
come from a character spec (JSON, see projects/*/characters/*.json); the pose
is a flat dict of numbers/strings so it can be keyframed by the timeline.

Pose keys (all optional):
  expression   neutral | surprised | happy | angry | sad | nervous | grim | shocked | sly
  mouth_open   0..1   (talking; combined with the expression's mouth)
  blink        0..1   (1 = eyes shut)
  look         -1..1  (eyes + face features shift sideways, 3/4 look)
  head_rot     degrees, head tilt around the neck
  lean         degrees, whole upper body tilt around the hips
  bob          units, vertical body offset (breathing / walking)
  arm_l, arm_r       shoulder angle, degrees: 0 = hanging, + = away from body
  elbow_l, elbow_r   elbow bend, degrees, + = forearm bends further outward/up
  hand_l, hand_r     [x, y] IK target in local units (overrides the angles)
  handshape_l/_r     open | point | fist
  leg_l, leg_r       hip angle, degrees, + = toward `facing`
  knee_l, knee_r     knee bend, degrees (>= 0)
  facing       -1 | 0 | 1  (toes direction; 0 = front)
  thought      0..1   (thought bubble with gears, pop scale)
"""
import math

import skia

# ---------------------------------------------------------------- defaults
DEFAULT_SPEC = {
    "outline": [20, 16, 14], "outline_w": 8.0,
    "skin": [250, 238, 222], "cap": [150, 117, 90], "cap_shade": [128, 98, 74],
    "mustache": [137, 104, 78], "jacket": [149, 115, 89], "jacket_shade": [128, 97, 74],
    "shirt": [234, 213, 190], "shorts": [74, 71, 70], "boots": [125, 94, 73],
    "legs": [20, 16, 14], "mouth": [96, 38, 38], "tongue": [232, 120, 120],
    "head_r": 140.0, "head_y": -805.0,
    "neck_top": -640.0, "shoulder_y": -625.0, "shoulder_x": 92.0,
    "body_top_w": 96.0, "body_bot_w": 112.0, "hem_y": -345.0,
    "shorts_top": -390.0, "shorts_bot": -298.0, "shorts_w": 100.0,
    "hip_x": 52.0, "hip_y": -300.0, "thigh": 90.0, "shin": 85.0,
    "boot_h": 135.0, "boot_w": 92.0,
    "upper_arm": 145.0, "forearm": 140.0, "sleeve_w": 62.0, "hand_r": 37.0,
    "headwear": "flatcap", "buttons": 4,
}


def _c(rgb, a=255):
    return skia.Color(int(rgb[0]), int(rgb[1]), int(rgb[2]), a)


class Pen:
    def __init__(self, spec):
        self.s = spec
        self.ol = spec["outline_w"]

    def fill(self, rgb):
        return skia.Paint(AntiAlias=True, Color=_c(rgb), Style=skia.Paint.kFill_Style)

    def stroke(self, rgb=None, w=None, cap=skia.Paint.kRound_Cap):
        return skia.Paint(AntiAlias=True, Color=_c(rgb or self.s["outline"]),
                          Style=skia.Paint.kStroke_Style, StrokeWidth=w or self.ol,
                          StrokeCap=cap, StrokeJoin=skia.Paint.kRound_Join)

    def shape(self, cv, path, rgb, ow=None):
        cv.drawPath(path, self.fill(rgb))
        cv.drawPath(path, self.stroke(w=ow))

    def capsule(self, cv, pts, width, rgb):
        """Outlined thick polyline (sleeves)."""
        p = skia.Path()
        p.moveTo(*pts[0])
        for q in pts[1:]:
            p.lineTo(*q)
        cv.drawPath(p, self.stroke(w=width + 2 * self.ol))
        cv.drawPath(p, self.stroke(rgb, w=width))


def _dir(angle_deg, side):
    """Unit vector: angle 0 = straight down, + = away from the body on `side` (-1 left, +1 right)."""
    a = math.radians(angle_deg)
    return (side * math.sin(a), math.cos(a))


def _ik(sx, sy, tx, ty, a, b, side):
    dx, dy = tx - sx, ty - sy
    d = max(abs(a - b) + 1e-3, min(a + b - 1e-3, math.hypot(dx, dy)))
    base = math.atan2(dy, dx)
    cos_a = (a * a + d * d - b * b) / (2 * a * d)
    ang = math.acos(max(-1, min(1, cos_a)))
    # elbow bends outward (away from the body centre)
    c1 = base + ang
    c2 = base - ang
    e1 = (sx + a * math.cos(c1), sy + a * math.sin(c1))
    e2 = (sx + a * math.cos(c2), sy + a * math.sin(c2))
    ex, ey = e1 if (e1[1] - e2[1]) + 0.3 * (e1[0] - e2[0]) * side > 0 else e2
    ux, uy = tx - ex, ty - ey
    n = math.hypot(ux, uy) or 1
    return (ex, ey), (ex + ux / n * b, ey + uy / n * b)


class Stickman:
    def __init__(self, spec=None):
        s = dict(DEFAULT_SPEC)
        s.update(spec or {})
        self.s = s
        self.pen = Pen(s)

    # ------------------------------------------------------------ public
    def draw(self, cv, pose):
        s, P = self.s, pose
        cv.save()
        legs = self._leg_points(P)
        # lift so the lowest foot stands on the ground
        low = max(legs[0][2][1], legs[1][2][1]) + s["boot_h"] * 0.72
        cv.translate(0, -low)
        bob = P.get("bob", 0.0)
        for side, (hip, knee, ankle) in zip((-1, 1), legs):
            self._leg(cv, hip, knee, ankle, side, P)
        cv.save()
        cv.translate(0, bob)
        cv.rotate(P.get("lean", 0.0), 0, s["hip_y"])
        arms = {side: self._arm_points(P, side) for side in (-1, 1)}
        # arms that reach across the body are drawn on top of it
        front = {side: P.get("arm_behind_" + ("l" if side < 0 else "r")) is None for side in (-1, 1)}
        for side in (-1, 1):
            if not front[side]:
                self._arm(cv, arms[side], side, P)
        self._shorts(cv)
        self._torso(cv)
        self._head(cv, P)
        for side in (-1, 1):
            if front[side]:
                self._arm(cv, arms[side], side, P)
        if P.get("thought", 0) > 0.01:
            self._thought(cv, P)
        cv.restore()
        cv.restore()

    # ------------------------------------------------------------ legs
    def _leg_points(self, P):
        s = self.s
        out = []
        facing = P.get("facing", 0)
        f = facing if facing else 1
        for side, k in ((-1, "l"), (1, "r")):
            hip = (side * s["hip_x"] * (0.45 if facing else 1.0), s["hip_y"])
            a = math.radians(P.get("leg_" + k, 0.0))
            kb = math.radians(P.get("knee_" + k, 0.0))
            knee = (hip[0] + f * math.sin(a) * s["thigh"], hip[1] + math.cos(a) * s["thigh"])
            a2 = a - kb
            ankle = (knee[0] + f * math.sin(a2) * s["shin"], knee[1] + math.cos(a2) * s["shin"])
            out.append((hip, knee, ankle))
        return out

    def _leg(self, cv, hip, knee, ankle, side, P):
        s, pen = self.s, self.pen
        p = skia.Path()
        p.moveTo(*hip)
        p.lineTo(*knee)
        p.lineTo(*ankle)
        cv.drawPath(p, pen.stroke(s["legs"], w=18))
        # boot: shaft + sole, toe points outward (front) or to `facing`
        facing = P.get("facing", 0)
        toe = facing if facing else side
        w, h = s["boot_w"], s["boot_h"]
        x0, y1 = ankle[0], ankle[1] + h * 0.72
        b = skia.Path()
        sh = w * 0.36
        b.moveTo(x0 - sh, ankle[1] - h * 0.28)
        b.lineTo(x0 + sh, ankle[1] - h * 0.28)
        b.lineTo(x0 + sh + toe * 0.0, y1 - h * 0.25)
        if toe > 0:
            b.cubicTo(x0 + sh + w * 0.45, y1 - h * 0.28, x0 + sh + w * 0.55, y1 - h * 0.05, x0 + sh + w * 0.45, y1)
            b.lineTo(x0 - sh - w * 0.08, y1)
        else:
            b.lineTo(x0 + sh + w * 0.08, y1)
            b.lineTo(x0 - sh - w * 0.45, y1)
            b.cubicTo(x0 - sh - w * 0.55, y1 - h * 0.05, x0 - sh - w * 0.45, y1 - h * 0.28, x0 - sh, y1 - h * 0.25)
        b.close()
        pen.shape(cv, b, s["boots"])
        cv.drawLine(x0 - sh - w * 0.1 * (toe < 0) * 4, y1 - 14, x0 + sh + w * 0.1 * (toe > 0) * 4, y1 - 14,
                    pen.stroke(w=5))

    # ------------------------------------------------------------ body
    def _shorts(self, cv):
        s, pen = self.s, self.pen
        w, t, bt = s["shorts_w"], s["shorts_top"], s["shorts_bot"]
        p = skia.Path()
        p.moveTo(-w * 0.95, t)
        p.lineTo(w * 0.95, t)
        p.cubicTo(w * 1.05, t + 40, w * 1.0, bt, w * 0.6, bt)
        p.quadTo(w * 0.15, bt + 6, 0, bt - 22)
        p.quadTo(-w * 0.15, bt + 6, -w * 0.6, bt)
        p.cubicTo(-w * 1.0, bt, -w * 1.05, t + 40, -w * 0.95, t)
        p.close()
        pen.shape(cv, p, s["shorts"])

    def _torso(self, cv):
        s, pen = self.s, self.pen
        tw, bw, ty, hy = s["body_top_w"], s["body_bot_w"], s["shoulder_y"] - 18, s["hem_y"]
        # shirt + belt (visible between the open jacket)
        shirt = skia.Path()
        shirt.addRect(skia.Rect.MakeLTRB(-tw * 0.45, ty + 10, tw * 0.45, hy - 4))
        cv.drawPath(shirt, pen.fill(s["shirt"]))
        cv.drawPath(shirt, pen.stroke(w=5))
        belt = skia.Rect.MakeLTRB(-bw * 0.55, hy - 52, bw * 0.55, hy - 28)
        cv.drawRect(belt, pen.fill(s["jacket_shade"]))
        cv.drawRect(belt, pen.stroke(w=5))
        for i in range(s.get("buttons", 4)):
            y = ty + 70 + i * (hy - ty - 140) / max(1, s.get("buttons", 4) - 1)
            cv.drawCircle(0, y, 5.5, pen.fill(s["outline"]))
        # V collar
        col = skia.Path()
        col.moveTo(-tw * 0.4, ty + 8)
        col.lineTo(0, ty + 52)
        col.lineTo(tw * 0.4, ty + 8)
        cv.drawPath(col, pen.stroke(w=6))
        # jacket halves
        for side in (-1, 1):
            j = skia.Path()
            j.moveTo(side * tw * 0.42, ty + 2)
            j.quadTo(side * tw * 1.0, ty - 6, side * tw * 1.08, ty + 40)
            j.lineTo(side * bw * 1.08, hy - 10)
            j.quadTo(side * bw * 1.05, hy + 4, side * bw * 0.9, hy + 4)
            j.lineTo(side * tw * 0.38, hy + 4)
            j.lineTo(side * tw * 0.36, ty + 110)
            j.close()
            pen.shape(cv, j, s["jacket"])
            # lapel
            lp = skia.Path()
            lp.moveTo(side * tw * 0.42, ty + 4)
            lp.lineTo(side * tw * 0.6, ty + 95)
            lp.lineTo(side * tw * 0.37, ty + 140)
            cv.drawPath(lp, pen.stroke(w=5))
        # neck
        for side in (-1, 1):
            cv.drawLine(side * 11, s["neck_top"] + 10, side * 11, ty + 10, pen.stroke(w=7))

    def _arm_points(self, P, side):
        s = self.s
        k = "l" if side < 0 else "r"
        sh = (side * s["shoulder_x"], s["shoulder_y"])
        tgt = P.get("hand_" + k)
        if tgt is not None:
            el, wr = _ik(sh[0], sh[1], tgt[0], tgt[1], s["upper_arm"], s["forearm"], side)
            return sh, el, wr
        a = P.get("arm_" + k, 8.0)
        e = P.get("elbow_" + k, 4.0)
        d1 = _dir(a, side)
        el = (sh[0] + d1[0] * s["upper_arm"], sh[1] + d1[1] * s["upper_arm"])
        d2 = _dir(a + e, side)
        wr = (el[0] + d2[0] * s["forearm"], el[1] + d2[1] * s["forearm"])
        return sh, el, wr

    def _arm(self, cv, pts, side, P):
        s, pen = self.s, self.pen
        sh, el, wr = pts
        # sleeve stops a bit before the wrist
        ux, uy = wr[0] - el[0], wr[1] - el[1]
        n = math.hypot(ux, uy) or 1
        cuff = (wr[0] - ux / n * s["hand_r"] * 0.55, wr[1] - uy / n * s["hand_r"] * 0.55)
        pen.capsule(cv, [sh, el, cuff], s["sleeve_w"], s["jacket"])
        k = "l" if side < 0 else "r"
        hs = P.get("handshape_" + k, "open")
        hr = s["hand_r"]
        if hs == "point":
            fx, fy = wr[0] + ux / n * hr * 1.9, wr[1] + uy / n * hr * 1.9
            pen.capsule(cv, [wr, (fx, fy)], hr * 0.55, s["skin"])
        r = hr * (0.85 if hs == "fist" else 1.0)
        cv.drawCircle(wr[0], wr[1], r, pen.fill(s["skin"]))
        cv.drawCircle(wr[0], wr[1], r, pen.stroke())
        if hs == "point":
            p = skia.Path()
            p.moveTo(wr[0] - uy / n * r * 0.2, wr[1] + ux / n * r * 0.2)
            p.lineTo(wr[0] + ux / n * r * 0.5, wr[1] + uy / n * r * 0.5)
            cv.drawPath(p, pen.stroke(w=5))

    # ------------------------------------------------------------ head
    def _head(self, cv, P):
        s, pen = self.s, self.pen
        r = s["head_r"]
        cv.save()
        cv.rotate(P.get("head_rot", 0.0), 0, s["neck_top"])
        cv.translate(0, s["head_y"])
        cv.drawCircle(0, 0, r, pen.fill(s["skin"]))
        cv.drawCircle(0, 0, r, pen.stroke())
        self._face(cv, P, r)
        if s.get("headwear") == "flatcap":
            self._flatcap(cv, r, P.get("look", 0.0))
        cv.restore()

    def _flatcap(self, cv, r, look):
        s, pen = self.s, self.pen
        lx = look * r * 0.18
        yl, yr = -r * 0.36, -r * 0.6          # brim edge, tilted like on the sheet
        dome = skia.Path()
        dome.moveTo(-r * 1.04 + lx * 0.3, yl)
        dome.cubicTo(-r * 1.3 + lx, -r * 1.45, r * 1.0 + lx, -r * 1.6, r * 1.04 + lx * 0.3, yr)
        dome.quadTo(lx * 0.4, -r * 0.62, -r * 1.04 + lx * 0.3, yl)
        dome.close()
        pen.shape(cv, dome, s["cap"])
        brim = skia.Path()
        brim.moveTo(-r * 1.06 + lx * 0.3, yl)
        brim.quadTo(lx * 0.4, -r * 0.66, r * 1.06 + lx * 0.3, yr)
        brim.quadTo(r * 1.1 + lx * 0.3, yr + r * 0.12, r * 0.95 + lx * 0.3, yr + r * 0.14)
        brim.quadTo(lx * 0.4, -r * 0.48, -r * 0.95 + lx * 0.3, yl + r * 0.12)
        brim.quadTo(-r * 1.12 + lx * 0.3, yl + r * 0.1, -r * 1.06 + lx * 0.3, yl)
        brim.close()
        pen.shape(cv, brim, s["cap_shade"])
        seam = skia.Path()
        seam.moveTo(-r * 0.8 + lx, -r * 0.72)
        seam.quadTo(-r * 0.2 + lx, -r * 1.22, r * 0.6 + lx, -r * 1.12)
        cv.drawPath(seam, pen.stroke(w=5))

    def _face(self, cv, P, r):
        s, pen = self.s, self.pen
        ex = P.get("expression", "neutral")
        lx = P.get("look", 0.0) * r * 0.35
        blink = P.get("blink", 0.0)
        mo = P.get("mouth_open", 0.0)
        ink = pen.fill(s["outline"])
        eye_y, eye_dx, er = -r * 0.1, r * 0.32, r * 0.075
        # brows
        brow = {"angry": 22, "grim": 14, "sad": -20, "nervous": -16, "surprised": 0,
                "shocked": 0, "sly": 8}.get(ex)
        if brow is not None:
            lift = r * (0.2 if ex in ("surprised", "shocked") else 0.0)
            for side in (-1, 1):
                cx = lx + side * eye_dx
                a = -math.radians(brow) * side
                L = r * 0.17
                y0 = eye_y - r * 0.2 - lift
                cv.drawLine(cx - L * math.cos(a), y0 - L * math.sin(a),
                            cx + L * math.cos(a), y0 + L * math.sin(a), pen.stroke(w=9))
        # eyes
        for side in (-1, 1):
            cx = lx + side * eye_dx
            if ex == "happy":
                p = skia.Path()
                p.moveTo(cx - er * 1.6, eye_y + er * 0.6)
                p.quadTo(cx, eye_y - er * 2.0, cx + er * 1.6, eye_y + er * 0.6)
                cv.drawPath(p, pen.stroke(w=7))
            elif ex == "sad" or blink > 0.85:
                p = skia.Path()
                p.moveTo(cx - er * 1.5, eye_y)
                p.quadTo(cx, eye_y + er * (1.4 if ex == "sad" else 0.5), cx + er * 1.5, eye_y)
                cv.drawPath(p, pen.stroke(w=6))
            elif ex == "shocked":
                cv.drawCircle(cx, eye_y, er * 2.3, pen.fill([255, 255, 255]))
                cv.drawCircle(cx, eye_y, er * 2.3, pen.stroke(w=6))
                cv.drawCircle(cx, eye_y, er * 0.8, ink)
            else:
                k = 1.3 if ex == "surprised" else 1.0
                ry = er * k * max(0.12, 1 - blink)
                cv.drawOval(skia.Rect.MakeLTRB(cx - er * k, eye_y - ry, cx + er * k, eye_y + ry), ink)
        if ex == "nervous":
            d = skia.Path()
            x0, y0 = lx - r * 0.72, -r * 0.05
            d.moveTo(x0, y0 - 28)
            d.cubicTo(x0 + 18, y0, x0 + 16, y0 + 22, x0, y0 + 22)
            d.cubicTo(x0 - 16, y0 + 22, x0 - 18, y0, x0, y0 - 28)
            pen.shape(cv, d, [150, 205, 235], ow=5)
        if ex == "shocked":
            for a in (-60, -35, -10):
                rad = math.radians(a)
                cv.drawLine(r * 1.15 * math.cos(rad), r * 1.15 * math.sin(rad) - r * 0.3,
                            r * 1.38 * math.cos(rad), r * 1.38 * math.sin(rad) - r * 0.3, pen.stroke(w=6))
        # mouth (under the mustache)
        my = r * 0.42
        shape = {"happy": "smile", "surprised": "o", "shocked": "o", "angry": "shout",
                 "sad": "frown", "grim": "frown"}.get(ex, "flat")
        if mo > 0.05 and shape in ("flat", "frown", "smile", "o"):
            shape = "talk" if shape != "o" else "o"
        if shape == "smile":
            m = skia.Path()
            m.moveTo(lx - r * 0.3, my - 4)
            m.quadTo(lx, my + r * 0.55, lx + r * 0.3, my - 4)
            m.close()
            pen.shape(cv, m, s["mouth"], ow=6)
            cv.drawOval(skia.Rect.MakeXYWH(lx - r * 0.13, my + r * 0.12, r * 0.26, r * 0.13), pen.fill(s["tongue"]))
        elif shape in ("talk", "shout"):
            h = r * (0.1 + 0.28 * (mo if shape == "talk" else max(0.5, mo)))
            w = r * (0.2 if shape == "talk" else 0.26)
            rect = skia.Rect.MakeLTRB(lx - w, my - 4, lx + w, my - 4 + h + 10)
            cv.drawOval(rect, pen.fill(s["mouth"]))
            cv.drawOval(rect, pen.stroke(w=6))
            if h > r * 0.18:
                cv.drawOval(skia.Rect.MakeXYWH(lx - w * 0.5, my + h * 0.55, w, h * 0.45), pen.fill(s["tongue"]))
        elif shape == "o":
            k = 0.07 + 0.06 * mo
            cv.drawCircle(lx, my + r * 0.08, r * k, pen.fill(s["mouth"]))
            cv.drawCircle(lx, my + r * 0.08, r * k, pen.stroke(w=6))
        elif shape == "frown":
            m = skia.Path()
            m.moveTo(lx - r * 0.14, my + r * 0.12)
            m.quadTo(lx, my, lx + r * 0.14, my + r * 0.12)
            cv.drawPath(m, pen.stroke(w=6))
        self._mustache(cv, lx, r, ex)

    def _mustache(self, cv, lx, r, ex):
        s, pen = self.s, self.pen
        y = r * 0.18
        droop = {"angry": 0.08, "sad": 0.12, "happy": -0.08}.get(ex, 0.0) * r
        p = skia.Path()
        p.moveTo(lx, y - r * 0.08)
        for side in (1, -1):
            if side == -1:
                p.moveTo(lx, y - r * 0.08)
            p.cubicTo(lx + side * r * 0.2, y - r * 0.2, lx + side * r * 0.45, y - r * 0.12,
                      lx + side * r * 0.5, y + r * 0.12 + droop)
            p.cubicTo(lx + side * r * 0.52, y + r * 0.24 + droop, lx + side * r * 0.4, y + r * 0.26 + droop,
                      lx + side * r * 0.36, y + r * 0.16 + droop)
            p.cubicTo(lx + side * r * 0.25, y + r * 0.1, lx + side * r * 0.1, y + r * 0.14, lx, y + r * 0.08)
            p.close()
        pen.shape(cv, p, s["mustache"], ow=6)

    # ------------------------------------------------------------ extras
    def _thought(self, cv, P):
        s, pen = self.s, self.pen
        k = P["thought"]
        cx, cy = s["head_r"] * 0.9, s["head_y"] - s["head_r"] * 1.55
        cv.save()
        cv.translate(cx, cy)
        cv.scale(k, k)
        bub = skia.Path()
        for dx, dy, rr in ((-60, 10, 55), (0, -25, 70), (65, 5, 58), (20, 45, 55), (-35, 45, 45)):
            bub.addCircle(dx, dy, rr)
        bub.setFillType(skia.PathFillType.kWinding)
        cv.drawPath(bub, pen.stroke(w=pen.ol * 2))
        cv.drawPath(bub, pen.fill([255, 255, 255]))
        for x, y, rr in ((-95, 110, 16), (-120, 150, 10)):
            cv.drawCircle(x, y, rr, pen.fill([255, 255, 255]))
            cv.drawCircle(x, y, rr, pen.stroke(w=6))
        rot = P.get("t", 0.0) * 120
        for gx, gy, gr, d in ((-25, 5, 34, 1), (40, 25, 26, -1)):
            self._gear(cv, gx, gy, gr, rot * d)
        cv.restore()

    def _gear(self, cv, x, y, r, rot):
        pen = self.pen
        g = skia.Path()
        n = 8
        for i in range(n * 2):
            a0 = math.radians(rot + i * 180 / n)
            rr = r if i % 2 == 0 else r * 0.72
            for da in (-0.5, 0.5):
                a = a0 + math.radians(da * 180 / n * 0.9)
                px, py = x + rr * math.cos(a), y + rr * math.sin(a)
                if i == 0 and da < 0:
                    g.moveTo(px, py)
                else:
                    g.lineTo(px, py)
        g.close()
        g.addCircle(x, y, r * 0.3, skia.PathDirection.kCCW)
        g.setFillType(skia.PathFillType.kEvenOdd)
        cv.drawPath(g, pen.fill(self.s["outline"]))
