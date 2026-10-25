"""Filmischer Look in der Nachbearbeitung (für Standbilder und Videoframes):
warme Tönung, sanftes Bloom/Glow, leichte Vignette, angehobene Schwärzen."""
import numpy as np
from PIL import Image, ImageFilter


def grade(img, warmth=0.035, bloom=0.14, vignette=0.18, lift=0.025):
    x = np.asarray(img.convert("RGB"), np.float32) / 255.0
    x *= np.array([1 + warmth, 1.0, 1 - 1.6 * warmth], np.float32)
    if bloom:
        hi = np.clip((x - 0.6) / 0.4, 0, 1) * x
        r = max(2, int(min(img.size) * 0.02))
        hb = np.asarray(Image.fromarray((hi * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(r)), np.float32) / 255
        x = 1 - (1 - x) * (1 - hb * bloom * 2)
    if vignette:
        h, w = x.shape[:2]
        yy, xx = np.mgrid[0:h, 0:w]
        d = ((xx - w / 2) / (w / 2)) ** 2 + ((yy - h / 2) / (h / 2)) ** 2
        x *= (1 - vignette * np.clip(d - 0.3, 0, 1.5) / 1.5)[..., None]
    x = lift + x * (1 - lift)
    return Image.fromarray((np.clip(x, 0, 1) * 255 + 0.5).astype(np.uint8))
