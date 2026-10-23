"""python3 -m shortsfactory.render TIMELINE.json OUT.mp4 [--w 480 --h 854 --start 0 --end 3 --audio mix.wav]"""
import argparse
import os

from .engine import Renderer, load_timeline

ap = argparse.ArgumentParser()
ap.add_argument("timeline")
ap.add_argument("out")
ap.add_argument("--w", type=int, default=1080)
ap.add_argument("--h", type=int, default=1920)
ap.add_argument("--start", type=float, default=0.0)
ap.add_argument("--end", type=float, default=None)
ap.add_argument("--audio", default=None)
ap.add_argument("--publish", action="store_true", help="refuse reference-proxy assets")
a = ap.parse_args()
tl = load_timeline(a.timeline)
base = os.path.dirname(os.path.dirname(os.path.abspath(a.timeline)))
r = Renderer(tl, tl.get("base_dir") and os.path.join(base, tl["base_dir"]) or base, a.w, a.h)
r.allow_proxies = not a.publish
r.render(a.out, a.start, a.end, audio=a.audio)
print("wrote", a.out)
