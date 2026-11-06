"""Collage style toolkit: vintage maps, paper cutouts (stickers), labels,
halftone accents, torn paper and typewriter strips.

Everything here produces RGBA PNG assets that the timeline renderer animates.
Palette and fonts are shared so every topic looks like the same channel.
"""
import os

FONT_DIR = os.path.join(os.path.dirname(__file__), "..", "fonts")

PALETTE = {
    "black": (30, 30, 32),
    "orange": (232, 112, 58),
    "petrol": (79, 154, 166),
    "cream": (246, 240, 226),
    "paper": (236, 228, 208),
    "ink": (40, 36, 32),
    "sea": (124, 160, 146),
    "land": (216, 200, 160),
    "coast": (96, 80, 58),
}


def font(name):
    return os.path.join(FONT_DIR, {
        "label": "Anton-Regular.ttf",
        "typewriter": "SpecialElite-Regular.ttf",
        "serif": "OldStandard-Bold.ttf",
        "serif_italic": "OldStandard-Italic.ttf",
    }[name])
