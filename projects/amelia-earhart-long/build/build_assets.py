"""Builds the image assets of the long Amelia Earhart video (16:9).

Re-uses the Short's asset builder (map, island tiles, stickers, quote strips)
and adds the long version's stickers and labels.

    python3 projects/amelia-earhart-long/build/build_assets.py
"""
import json
import os
import sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
PROJ = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PROJ))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "projects", "amelia-earhart", "build"))

from shortsfactory.collage import graphics as g  # noqa: E402
from shortsfactory.collage.sticker import sticker_file  # noqa: E402
import build_assets as AB  # noqa: E402  (the Short's builder)

OUT = os.path.join(HERE, "assets")
CUT = os.path.join(PROJ, "assets", "cutouts")

STICKERS = {
    "young": "C1_earhart_jung.png", "vega": "C2_vega.png", "lindbergh": "C3_lindbergh.png",
    "noonan": "C4_noonan.png", "electra2": "C5_luke_field.png", "norwich": "C6_norwich_city.png",
    "gallagher": "C7_gallagher.png", "floatplane": "C8_wasserflugzeug.png", "photo2017": "C9_foto_2017.png",
    "potatoes": "D1_kartoffelsack.png", "book": "D2_buch.png", "morse": "D3_morsetaste.png",
    "auv": "D4_tauchroboter.png", "rock": "D5_felsen.png", "crab": "D6_kokoskrabbe.png",
    "listener": "D7_radiohoererin.png", "caliper": "D8_messschieber.png", "jar": "D9_cremedose.png",
    "alu": "D10_aluminium.png", "logs": "D11_baumstaemme.png", "travelbook": "D12_reisebuch.png",
    "tv": "D13_fernseher.png", "house": "D14_haus.png", "court": "D15_gerichtsakte.png",
}

PLACES = {
    "atchison": (-95.12, 39.56), "los_angeles": (-118.24, 34.05),
    "trepassey": (-53.36, 46.74), "burry_port": (-4.25, 51.68),
    "harbour_grace": (-53.22, 47.70), "culmore": (-7.29, 55.04),
}

LABELS = [
    ("lbl_date", "2. Juli 1937", "black", 110), ("lbl_stille", "Stille.", "petrol", 150),
    ("lbl_kein_flugzeug", "Kein Flugzeug", "black", 100), ("lbl_kein_wrack", "Kein Wrack", "orange", 100),
    ("lbl_keine_leiche", "Keine Leiche", "petrol", 100), ("lbl_okt2026", "Oktober 2026", "orange", 120),
    ("lbl_satellit", "Satellitenbild", "petrol", 90), ("lbl_theorie", "Welche Theorie stimmt?", "black", 100),
    ("lbl_kap", "Kapitel 1", "black", 70), ("lbl_kap_title", "Wer war Amelia Earhart?", "orange", 110),
    ("lbl_1897", "1897", "black", 150), ("lbl_kansas", "Kansas", "petrol", 100),
    ("lbl_1920", "1920", "black", 150), ("lbl_10min", "10 Minuten", "orange", 100),
    ("lbl_la", "Los Angeles", "petrol", 95), ("lbl_jobbt", "Jobben · Sparen", "black", 90),
    ("lbl_gebraucht", "Gebraucht gekauft", "orange", 90), ("lbl_1928", "1928", "black", 150),
    ("lbl_passagierin", "Nur Passagierin", "orange", 110), ("lbl_1932", "1932", "black", 150),
    ("lbl_allein", "Allein über den Atlantik", "petrol", 95), ("lbl_nr2", "Nr. 2 nach Lindbergh", "black", 90),
    ("lbl_weltstar", "Weltstar", "orange", 150), ("lbl_mode", "Mode", "petrol", 110),
    ("lbl_chancen", "Gleiche Chancen", "black", 110), ("lbl_rekord", "Ein letzter Rekord", "orange", 120),
]


def main():
    AB.OUT = OUT                       # build the Short's assets into this project
    AB.main()
    meta = json.load(open(os.path.join(OUT, "meta.json")))
    for i, (name, src) in enumerate(STICKERS.items()):
        meta[f"st_{name}"] = sticker_file(os.path.join(CUT, src), os.path.join(OUT, f"st_{name}.png"), seed=100 + i)
        print("sticker", name)

    def save(name, arr, **extra):
        Image.fromarray(arr, "RGBA").save(os.path.join(OUT, name + ".png"))
        meta[name] = dict(w=arr.shape[1], h=arr.shape[0], **extra)

    for i, (n, t, c, s) in enumerate(LABELS):
        save(n, g.label(t, c, s, seed=200 + i))
    save("newspaper_1928", g.newspaper(headline="GIRL FLIER\nCROSSES OCEAN", date="JUNE 1928", seed=8))
    save("page", g.page_overlay(1920, 1080, seed=3))
    proj = meta["map_pacific"]["proj"]
    meta["places"] = {k: [(lon - proj["lon_min"]) * proj["ppd"], (proj["lat_max"] - lat) * proj["ppd"]]
                      for k, (lon, lat) in PLACES.items()}
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
    print("done ->", OUT)


if __name__ == "__main__":
    main()
