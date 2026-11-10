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

# optional user images; until they exist a generated stand-in is used
OPTIONAL = {
    "sonar": "E1_sonarbild.png",
    "news1928": "N1_zeitung_1928.png", "news1932": "N2_zeitung_1932.png",
    "news1937": "N3_zeitung_1937.png", "news2024": "N4_zeitung_2024.png",
    "satplane": "E3_satellitenbild.png",
}
NEWS_FALLBACK = {
    "news1928": ("ERSTE FRAU\nÜBER DEN ATLANTIK", "JUNI 1928"), "news1932": ("ALLEIN ÜBER\nDEN OZEAN!", "MAI 1932"),
    "news1937": ("AMELIA EARHART\nVERSCHOLLEN", "JULI 1937"), "news2024": ("IST DAS EARHARTS\nFLUGZEUG?", "JANUAR 2024"),
}


def optional(meta):
    """(re)build only the optional user images – fast, no map rendering"""
    for i, (name, src) in enumerate(OPTIONAL.items()):
        path = os.path.join(CUT, src)
        if os.path.exists(path):
            meta[f"st_{name}"] = sticker_file(path, os.path.join(OUT, f"st_{name}.png"), seed=300 + i)
            print("sticker", name)
        elif name in NEWS_FALLBACK:
            hl, d = NEWS_FALLBACK[name]
            arr = g.newspaper(headline=hl, date=d, seed=20 + i)
            Image.fromarray(arr, "RGBA").save(os.path.join(OUT, f"st_{name}.png"))
            meta[f"st_{name}"] = dict(w=arr.shape[1], h=arr.shape[0])
            print("stand-in", name)
        elif name == "satplane":                # no stand-in: the timeline skips it
            meta.pop("st_satplane", None)
            print("missing", name)
        else:                                   # sonar: stand-in = the rock (darkened later in the timeline)
            meta[f"st_{name}"] = dict(meta["st_rock"], file="st_rock")
            print("stand-in", name, "(rock)")


# (lon, lat) – lon given in the copy of the 455°-wide map that the scene uses
PLACES = {
    "atchison": (-95.12, 39.56, "Atchison"), "los_angeles": (-118.24, 34.05, "Los Angeles"),
    "trepassey": (-53.36, 46.74, "Trepassey"), "burry_port": (-4.25, 51.68, "Burry Port"),
    "harbour_grace": (-53.22, 47.70, "Harbour Grace"), "culmore": (-7.29, 55.04, "Londonderry"),
    "oakland_w": (-122.27, 37.80, "Oakland"), "oakland_e": (237.73, 37.80, "Oakland"),
    "honolulu": (202.14, 21.31, "Hawaii"), "miami": (-80.19, 25.76, "Miami"), "natal": (-35.2, -5.8, "Natal"),
    "saint_louis": (-16.5, 16.0, "Saint-Louis"), "karachi": (67.0, 24.9, "Karatschi"),
    "calcutta": (88.4, 22.6, "Kalkutta"), "singapore": (103.8, 1.3, "Singapur"), "darwin": (130.8, -12.5, "Darwin"),
    "lae": (147.0, -6.7, "Lae"), "fiji": (178.44, -18.14, "Fidschi"), "mili": (171.9, 6.1, "Marshallinseln"),
    "saipan": (145.75, 15.18, "Saipan"), "new_jersey": (-74.4, 40.06, "New Jersey"),
    "howland": (183.3832, 0.8047, "Howland"), "nikumaroro": (185.4815, -4.6789, "Nikumaroro"),
}

# landscape zoom tiles (16:9): (name, lon, lat, ppd, w, h)
TILES_16x9 = [
    ("tile_mid", -175.5, -2.0, 120, 3600, 2400),
    ("tile_h1", -176.6168, 0.8047, 600, 2700, 1800),
    ("tile_h2", -176.6168, 0.8047, 3000, 2700, 1800),
    ("tile_h25", -176.6168, 0.8047, 8000, 2700, 1800),
    ("tile_h3", -176.6168, 0.8047, 20000, 2400, 1600),
    ("tile_n1", -174.5185, -4.6789, 600, 2700, 1800),
    ("tile_n2", -174.5185, -4.6789, 3000, 2700, 1800),
    ("tile_n3", -174.5185, -4.6789, 10000, 3000, 2000),
]

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
    # chapter 2
    ("lbl_kap2", "Kapitel 2", "black", 70), ("lbl_t2", "Der Weltflug", "orange", 110),
    ("lbl_47000", "47.000 km", "orange", 110), ("lbl_aequator", "Entlang des Äquators", "petrol", 90),
    ("lbl_electra", "Lockheed Electra", "black", 100), ("lbl_tanks", "Zusatztanks", "orange", 90),
    ("lbl_noonan", "Fred Noonan", "petrol", 100), ("lbl_navigator", "Navigator", "black", 90),
    ("lbl_maerz", "März 1937", "black", 110), ("lbl_versuch1", "1. Versuch", "orange", 100),
    ("lbl_reparatur", "Monatelange Reparatur", "petrol", 90), ("lbl_juni", "Juni 1937", "black", 110),
    ("lbl_osten", "Nach Osten", "orange", 100), ("lbl_dreiviertel", "3/4 geschafft", "petrol", 110),
    ("lbl_pazifik", "Nur noch der Pazifik", "black", 100),
    # chapter 3
    ("lbl_kap3", "Kapitel 3", "black", 70), ("lbl_t3", "Der letzte Flug", "orange", 110),
    ("lbl_flach", "Kaum zu sehen", "orange", 95), ("lbl_fehler", "Kleiner Fehler", "orange", 95),
    ("lbl_vorbei", "Vorbei!", "petrol", 110), ("lbl_itasca", "USCGC Itasca", "petrol", 95),
    ("lbl_problem", "Ein Problem", "black", 110), ("lbl_hoeren", "Hören: Ja", "petrol", 100),
    ("lbl_peilen", "Peilen: Nein", "orange", 100), ("lbl_keine_richtung", "Keine Richtung", "black", 95),
    ("lbl_antenne", "Antenne abgebaut", "orange", 95), ("lbl_morsen", "Morsen?", "petrol", 110),
    ("lbl_742", "7:42 Uhr", "black", 110), ("lbl_843", "8:43 Uhr", "black", 110),
    ("lbl_letzter", "Letzter Funkspruch", "orange", 95), ("lbl_157", "157° / 337°", "petrol", 110),
    ("lbl_nnw", "Nordnordwest", "black", 80), ("lbl_sso", "Südsüdost", "black", 80),
    ("lbl_nichts_mehr", "Nichts mehr.", "petrol", 130),
    # chapter 4
    ("lbl_kap4", "Kapitel 4", "black", 70), ("lbl_t4", "Die Suche", "orange", 110),
    ("lbl_colorado", "USS Colorado", "black", 95), ("lbl_lexington", "USS Lexington", "petrol", 95),
    ("lbl_60", "60+ Flugzeuge", "orange", 95), ("lbl_600k", "600.000 km²", "orange", 110),
    ("lbl_teuer", "Teuerste Suche", "black", 100), ("lbl_1939", "1939", "black", 150),
    ("lbl_tot", "Für tot erklärt", "petrol", 100), ("lbl_4theorien", "4 Theorien", "orange", 120),
    ("lbl_n1", "1", "black", 110), ("lbl_n2", "2", "orange", 110), ("lbl_n3", "3", "petrol", 110), ("lbl_n4", "4", "black", 110),
    # chapter 5
    ("lbl_th1", "Theorie 1", "black", 70), ("lbl_t5", "Absturz ins Meer", "orange", 110),
    ("lbl_verfehlt", "Knapp verfehlt", "orange", 95), ("lbl_5km", "5 km tief", "petrol", 110),
    ("lbl_sonar", "Sonar", "black", 100), ("lbl_2024", "2024", "black", 150),
    ("lbl_sensation", "Sensation?", "orange", 110), ("lbl_160km", "160 km", "petrol", 100),
    ("lbl_felsen", "Ein Felsen.", "orange", 130),
    # chapter 6
    ("lbl_th2", "Theorie 2", "black", 70), ("lbl_t6", "Gestrandet auf Nikumaroro", "orange", 100),
    ("lbl_650km", "650 km", "orange", 100), ("lbl_gardner", "Gardner Island", "black", 90),
    ("lbl_riff", "Landung auf dem Riff?", "petrol", 90), ("lbl_notrufe", "Notrufe", "orange", 110),
    ("lbl_an_land", "An Land?", "black", 100), ("lbl_13", "Nur 13 Knochen", "orange", 100),
    ("lbl_krabbe", "Kokoskrabbe", "petrol", 100), ("lbl_1m", "bis 1 m", "black", 100),
    ("lbl_experiment", "Experiment", "black", 95), ("lbl_jantz", "Richard Jantz", "petrol", 95),
    ("lbl_99", "99 %", "orange", 150), ("lbl_verschwunden", "Verschwunden", "black", 110),
    ("lbl_creme", "Sommersprossencreme?", "petrol", 85), ("lbl_alu", "Flugzeugteil?", "orange", 95),
    ("lbl_baeume", "Baumstämme", "petrol", 110),
    # chapter 7
    ("lbl_th3", "Theorie 3", "black", 70), ("lbl_t7", "Gefangen von Japan", "orange", 110),
    ("lbl_japan", "Japanisches Gebiet", "black", 95), ("lbl_gefangen", "Gefangen?", "orange", 110),
    ("lbl_zeugen", "Augenzeugen", "petrol", 100), ("lbl_2017", "2017", "black", 150),
    ("lbl_beweis", "Der Beweis?", "orange", 110), ("lbl_earhart_q", "Earhart?", "orange", 95),
    ("lbl_noonan_q", "Noonan?", "petrol", 95), ("lbl_blogger", "Ein Blogger", "black", 95),
    ("lbl_30min", "30 Minuten", "orange", 100), ("lbl_1935", "1935", "black", 150),
    # chapter 8
    ("lbl_th4", "Theorie 4", "black", 70), ("lbl_t8", "Ein neues Leben", "orange", 110),
    ("lbl_1970", "1970", "black", 150), ("lbl_bolam", "Irene Bolam?", "orange", 100),
    ("lbl_unsinn", "Unsinn!", "petrol", 120), ("lbl_klage", "Klage", "black", 110),
    # chapter 9
    ("lbl_fazit", "Fazit", "black", 70), ("lbl_t9", "Was ist wirklich passiert?", "orange", 100),
    ("lbl_hinweise", "Viele Hinweise", "petrol", 90), ("lbl_erzaehlungen", "Nur Erzählungen", "black", 90),
    ("lbl_glaubst", "Was glaubst du?", "orange", 130), ("lbl_kommentare", "Schreib es in die Kommentare", "petrol", 85),
    ("lbl_abo", "Abonnieren", "black", 110),
]


def main():
    AB.OUT = OUT                       # build the Short's assets into this project
    AB.DETAIL_TILES = True             # close-up island look (reef, lagoon, vegetation)
    AB.TILES = TILES_16x9              # wider tiles for the landscape frame
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
    for n, t in (("stamp_widerlegt", "WIDERLEGT"), ("stamp_keinbeweis", "KEIN BEWEIS")):
        save(n, g.stamp(t, seed=len(t)))
    proj = meta["map_pacific"]["proj"]

    def mxy(lon, lat):
        if lon < proj["lon_min"]:
            lon += 360
        return [(lon - proj["lon_min"]) * proj["ppd"], (proj["lat_max"] - lat) * proj["ppd"]]
    meta["places"] = {k: mxy(lon, lat) for k, (lon, lat, _) in PLACES.items()}
    for k, (_, _, name) in PLACES.items():
        arr, anc = g.city_label(name)
        save("city_" + k, arr, anchor=anc)
    optional(meta)
    json.dump(meta, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
    print("done ->", OUT)


if __name__ == "__main__":
    if "--optional" in sys.argv:              # only the user images (fast)
        m = json.load(open(os.path.join(OUT, "meta.json")))
        optional(m)
        json.dump(m, open(os.path.join(OUT, "meta.json"), "w"), indent=1)
    else:
        main()
