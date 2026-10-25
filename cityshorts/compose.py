"""Endschnitt: Blender-Frames + animierte Untertitel + Titel -> MP4 (FFmpeg).

Untertitel: 1-3 Wörter pro Einblendung, Pop-Animation, aktives Wort gelb,
Betonungswörter (city.json -> beat.emphasis) größer.
"""
import glob
import math
import os
import subprocess

from PIL import Image, ImageDraw, ImageFont

FONT = os.path.join(os.path.dirname(__file__), "..", "shortsfactory", "fonts", "league-spartan-latin-800-normal.woff")
W, H = 1080, 1920
YELLOW = (255, 214, 0)


def chunk_words(words, max_words=3, max_chars=16):
    groups, cur = [], []
    for w in words:
        cur.append(w)
        txt = " ".join(x["text"] for x in cur)
        if len(cur) >= max_words or len(txt) >= max_chars or w["text"][-1] in ".,:?!":
            groups.append(cur)
            cur = []
    if cur:
        groups.append(cur)
    return groups


def _key(word):
    return word.lower().strip(".,:;?!\"'")


def back_out(u, s=2.2):
    u = max(0.0, min(1.0, u)) - 1
    return u * u * ((s + 1) * u + s) + 1


class Captions:
    def __init__(self, plan, y=1280):
        self.y = y
        self.groups = []
        for b in plan["beats"]:
            emph = {_key(e) for e in b.get("emphasis", [])}
            gs = chunk_words(b["words"])
            for i, g in enumerate(gs):
                end = gs[i + 1][0]["start"] if i + 1 < len(gs) else g[-1]["end"] + 0.25
                self.groups.append({"start": g[0]["start"], "end": end, "words": g, "emph": emph})
        self.fonts = {}
        self.title = plan.get("title")

    def font(self, px):
        if px not in self.fonts:
            self.fonts[px] = ImageFont.truetype(FONT, px)
        return self.fonts[px]

    def draw(self, img, t):
        d = ImageDraw.Draw(img)
        if self.title and t < self.title["end"]:
            self._title(img, d, t)
        g = next((g for g in self.groups if g["start"] <= t < g["end"]), None)
        if not g:
            return img
        k = back_out((t - g["start"]) / 0.14)
        items = []
        for w in g["words"]:
            big = _key(w["text"]) in g["emph"]
            px = int((96 if big else 78) * (0.6 + 0.4 * k))
            items.append((w["text"].upper(), self.font(px), big))
        space = 22
        widths = [d.textlength(s, font=f) for s, f, _ in items]
        total = sum(widths) + space * (len(items) - 1)
        lines = [items]
        if total > W - 120:  # zu breit -> zwei Zeilen
            lines = [items[:len(items) // 2 or 1], items[len(items) // 2 or 1:]]
        y = self.y - (len(lines) - 1) * 50
        for line in lines:
            ws = [d.textlength(s, font=f) for s, f, _ in line]
            x = (W - (sum(ws) + space * (len(line) - 1))) / 2
            for (s, f, big), wdt in zip(line, ws):
                col = YELLOW if big else (255, 255, 255)
                # Schatten + Kontur für Lesbarkeit auf hellem Hintergrund
                d.text((x + 4, y + 6), s, font=f, fill=(0, 0, 0), anchor="lm", stroke_width=9, stroke_fill=(0, 0, 0))
                d.text((x, y), s, font=f, fill=col, anchor="lm", stroke_width=8, stroke_fill=(20, 20, 20))
                x += wdt + space
            y += 100
        return img

    def _title(self, img, d, t):
        ti = self.title
        u_in = back_out((t - ti.get("start", 0.2)) / 0.35)
        u_out = min(1.0, max(0.0, (ti["end"] - t) / 0.3))
        a = u_in * u_out
        if a <= 0:
            return
        f = self.font(int(150 * (0.7 + 0.3 * a)))
        f2 = self.font(int(54 * (0.7 + 0.3 * a)))
        y = 300 - (1 - a) * 80
        d.text((W / 2 + 5, y + 7), ti["text"], font=f, fill=(0, 0, 0), anchor="mm", stroke_width=12, stroke_fill=(0, 0, 0))
        d.text((W / 2, y), ti["text"], font=f, fill=YELLOW, anchor="mm", stroke_width=11, stroke_fill=(20, 20, 20))
        if ti.get("sub"):
            d.text((W / 2, y + 110), ti["sub"], font=f2, fill=(255, 255, 255), anchor="mm", stroke_width=6,
                   stroke_fill=(20, 20, 20))


def compose(plan, frames_dir, audio, out_mp4, fps=None):
    fps = fps or plan["fps"]
    frames = sorted(glob.glob(os.path.join(frames_dir, "*.png")))
    if not frames:
        raise SystemExit("keine Frames in " + frames_dir)
    step = 1
    if len(frames) > 1:
        step = int(os.path.basename(frames[1])[:5]) - int(os.path.basename(frames[0])[:5])
    caps = Captions(plan)
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(fps / step), "-i", "-", "-i", audio, "-map", "0:v", "-map", "1:a",
           "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", "-r", str(fps),
           "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", out_mp4]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for path in frames:
        f = int(os.path.basename(path)[:5])
        img = Image.open(path).convert("RGB")
        if img.size != (W, H):
            img = img.resize((W, H), Image.LANCZOS)
        caps.draw(img, f / fps)
        p.stdin.write(img.tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise SystemExit("ffmpeg fehlgeschlagen")
    return out_mp4
