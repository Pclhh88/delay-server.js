"""Extract the country polygons we need from aourednik/historical-basemaps (GPL-3.0).
    python3 -I extract_geo.py <historical-basemaps/geojson dir> <out dir>
Countries are picked by a point inside them (names differ between years)."""
import json
import sys

import numpy as np

SRC, OUT = sys.argv[1], sys.argv[2]
PICK = {
    "1715": {"prussia": (20.5, 54.7), "brandenburg": (13.4, 52.5), "russia": (37.6, 55.75), "russia2": (30.3, 59.9),
             "sweden": (18.0, 59.3), "sweden_fin": (25.0, 61.0), "poland": (21.0, 52.2), "denmark": (12.5, 55.7)},
    "2010": {"poland": (19.0, 52.0), "germany": (10.0, 51.0), "russia_k": (20.5, 54.7), "russia": (37.6, 55.75),
             "lithuania": (24.0, 55.3), "sweden": (16.0, 60.0), "denmark": (9.5, 56.0), "belarus": (28.0, 53.5),
             "latvia": (25.0, 57.0), "estonia": (25.5, 58.7), "finland": (26.0, 62.0), "ukraine": (31.0, 49.0)},
    "1938": {"germany": (10.0, 51.0), "germany_ep": (20.5, 54.7), "ussr": (37.6, 55.75), "ussr2": (30.3, 59.9),
             "poland": (19.0, 52.0), "sweden": (16.0, 60.0), "finland": (26.0, 62.0), "lithuania": (24.0, 55.3),
             "latvia": (25.0, 57.0), "estonia": (25.5, 58.7), "denmark": (9.5, 56.0)},
}


def inside(pt, ring):
    x, y = pt
    r = np.asarray(ring)
    xi, yi = r[:, 0], r[:, 1]
    xj, yj = np.roll(xi, 1), np.roll(yi, 1)
    c = ((yi > y) != (yj > y)) & (x < (xj - xi) * (y - yi) / (yj - yi + 1e-12) + xi)
    return c.sum() % 2 == 1


for year, picks in PICK.items():
    d = json.load(open(f"{SRC}/world_{year}.geojson"))
    out = {"type": "FeatureCollection", "features": []}
    for key, pt in picks.items():
        for f in d["features"]:
            g = f["geometry"]
            if not g:
                continue
            polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
            if any(inside(pt, p[0]) for p in polys):
                out["features"].append({"type": "Feature", "properties": {"key": key, "NAME": f["properties"].get("NAME")},
                                        "geometry": g})
                print(year, key, "->", f["properties"].get("NAME"))
                break
        else:
            print(year, key, "-> NOT FOUND")
    json.dump(out, open(f"{OUT}/countries_{year}.geojson", "w"))
