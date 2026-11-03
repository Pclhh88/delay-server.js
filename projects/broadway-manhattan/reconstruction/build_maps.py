"""Baut alle Karten-Assets für die Broadway-Rekonstruktion aus freien Daten.

Ergebnis (Koordinaten überall: UTM 18N, EPSG:32618, Meter):
  assets/maps/sat.jpg          Sentinel-2 Echtfarbe, 10 m/px          (+ sat.json Geotransform)
  assets/maps/paper_wide.jpg   Papier-Reliefkarte Region, 50 m/px
  assets/maps/paper.jpg        Papier-Reliefkarte Manhattan, 12 m/px
  assets/maps/vectors.json     Broadway-Linie, Manhattan-Umriss, Straßenraster

python3 projects/broadway-manhattan/reconstruction/build_maps.py
"""
import json
import os
import sys

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
from shortsfactory.geo import overture, sentinel, terrain  # noqa: E402
from shortsfactory.geo.style import paper_relief, rasterize  # noqa: E402

P = os.path.join(ROOT, "projects", "broadway-manhattan")
CACHE = os.path.join(P, "cache")
OUT = os.path.join(P, "assets", "maps")
CRS = "EPSG:32618"
SCENE = "S2B_18TWL_20241011_0_L2A"
BBOX_SAT = (-74.16, 40.60, -73.80, 40.93)
BBOX_SAT_WIDE = (-74.75, 40.57, -73.72, 41.15)
BBOX_DETAIL = (-74.14, 40.60, -73.82, 40.92)
BBOX_WIDE = (-74.75, 40.30, -73.35, 41.35)


def save_raster(name, img, tr, extra=None):
    cv2.imwrite(os.path.join(OUT, name + ".jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    meta = {"path": f"assets/maps/{name}.jpg", "crs": CRS,
            "transform": [tr.a, tr.b, tr.c, tr.d, tr.e, tr.f], "w": img.shape[1], "h": img.shape[0]}
    if extra:
        meta.update(extra)
    json.dump(meta, open(os.path.join(OUT, name + ".json"), "w"), indent=1)


def chain_broadway(lines):
    """Broadway-Segmente (Manhattan) -> eine geordnete, geglättete Mittellinie Süd -> Nord."""
    pts = np.vstack([np.asarray(l.coords)[:, :2] for l in lines])
    # Hauptrichtung: Broadway läuft grob SSW -> NNO; sortiere entlang Kette per Nachbarschaft
    start = pts[np.argmin(pts[:, 1])]
    order = [start]
    rest = pts.copy()
    cur = start
    while len(rest):
        d = np.hypot(*(rest - cur).T)
        i = np.argmin(d)
        if d[i] > 900:  # Lücke zu groß -> fertig
            break
        cur = rest[i]
        order.append(cur)
        rest = np.delete(rest, np.where(d < 25)[0], axis=0)  # Nahpunkte (Gegenfahrbahn) verwerfen
    line = np.array(order)
    # gleichmäßig neu abtasten (20 m) und glätten
    seg = np.hypot(*np.diff(line, axis=0).T)
    s = np.concatenate([[0], np.cumsum(seg)])
    ss = np.arange(0, s[-1], 20.0)
    x = np.interp(ss, s, line[:, 0])
    y = np.interp(ss, s, line[:, 1])
    k = np.ones(9) / 9
    xs = np.convolve(np.pad(x, 4, mode="edge"), k, "valid")
    ys = np.convolve(np.pad(y, 4, mode="edge"), k, "valid")
    return np.stack([xs, ys], 1)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    import shapely
    from shapely.ops import unary_union

    # --- Vektoren ---------------------------------------------------------
    land = overture.land(BBOX_WIDE, os.path.join(CACHE, "land.parquet"))
    lg = overture.geometries(land, CRS)
    cls = land.column("class").to_pylist()
    sub = land.column("subtype").to_pylist()
    names = [(n or {}).get("primary") for n in land.column("names").to_pylist()]
    coast = [g for g, s in zip(lg, sub) if s == "land"]
    manhattan = [g for g, n in zip(lg, names) if n == "Manhattan Island"][0]
    manhattan = max(getattr(manhattan, "geoms", [manhattan]), key=lambda g: g.area)
    land_union = unary_union(coast)
    # Binnengewässer (Hudson oberhalb, Flüsse, Seen) sind in Overture eigene Wasserflächen
    water = overture.water(BBOX_WIDE, os.path.join(CACHE, "water.parquet"))
    wg = overture.geometries(water, CRS)
    wsub = water.column("subtype").to_pylist()
    big = [g for g, s in zip(wg, wsub) if s in ("river", "water", "lake", "reservoir", "ocean", "canal")
           and g.geom_type in ("Polygon", "MultiPolygon") and g.area > 20000]
    land_union = land_union.difference(unary_union(big).buffer(0))
    streams = [g for g, s in zip(wg, wsub) if s in ("river", "stream", "canal")
               and g.geom_type in ("LineString", "MultiLineString")]

    roads = overture.roads(BBOX_DETAIL, os.path.join(CACHE, "roads.parquet"))
    rg = overture.geometries(roads, CRS)
    rcls = roads.column("class").to_pylist()
    rnm = [(n or {}).get("primary") for n in roads.column("names").to_pylist()]
    mh = manhattan.buffer(30)
    grid_cls = {"primary", "secondary", "tertiary", "residential", "unclassified", "living_street"}
    grid = [g for g, c in zip(rg, rcls) if c in grid_cls and mh.intersects(g)]
    grid = [mh.intersection(g) for g in grid]
    bw = [g for g, n in zip(rg, rnm) if n == "Broadway" and manhattan.buffer(10).intersects(g)]
    bw_line = chain_broadway(bw)

    def lines_to_list(gs, tol):
        out = []
        for g in gs:
            for l in getattr(g, "geoms", [g]):
                if l.geom_type != "LineString" or l.length < 15:
                    continue
                c = np.asarray(l.simplify(tol).coords)[:, :2]
                out.append(np.round(c).astype(int).tolist())
        return out

    # Straßen außerhalb Manhattans (für die hellen Satelliten-Szenen mit weißem Raster überall)
    bb = shapely.box(*manhattan.bounds).buffer(2500)
    outer = [g for g, c in zip(rg, rcls) if c in grid_cls and bb.intersects(g) and not mh.intersects(g)]
    vec = {
        "crs": CRS,
        "broadway": np.round(bw_line).astype(int).tolist(),
        "manhattan": np.round(np.asarray(manhattan.exterior.simplify(8).coords)).astype(int).tolist(),
        "grid": lines_to_list(grid, 4),
        "grid_outer": lines_to_list(outer, 6),
        "attribution": "© OpenStreetMap contributors, Overture Maps Foundation (ODbL)",
    }
    json.dump(vec, open(os.path.join(OUT, "vectors.json"), "w"), separators=(",", ":"))
    print("broadway pts", len(bw_line), "grid lines", len(vec["grid"]), "outer", len(vec["grid_outer"]))

    # --- Satellit -----------------------------------------------------------
    rgb, tr, _ = sentinel.read_tci(SCENE, BBOX_SAT)
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    # Sentinel ist sehr dunkel/kontrastarm im Wasser: leichte Gamma-Anhebung wie im Original
    f = bgr.astype(np.float32) / 255
    f = np.clip(f * 1.05, 0, 1) ** 0.85
    bgr = (f * 255).astype(np.uint8)
    save_raster("sat", bgr, tr, {"attribution": "Contains modified Copernicus Sentinel data 2024"})
    rgbw, trw, _ = sentinel.read_tci(SCENE, BBOX_SAT_WIDE, 40.0)
    fw = np.clip(cv2.cvtColor(rgbw, cv2.COLOR_RGB2BGR).astype(np.float32) / 255 * 1.05, 0, 1) ** 0.85
    save_raster("sat_wide", (fw * 255).astype(np.uint8), trw, {"attribution": "Contains modified Copernicus Sentinel data 2024"})
    mask = rasterize([manhattan], tr, bgr.shape[:2])
    cv2.imwrite(os.path.join(OUT, "sat_manhattan_mask.png"), mask)

    # --- Papier-Relief ------------------------------------------------------
    for name, bbox, z, res in (("paper_wide", BBOX_WIDE, 10, 50.0), ("paper", BBOX_DETAIL, 12, 12.0)):
        elev, etr, _ = terrain.elevation(bbox, z, CRS, res, os.path.join(CACHE, "terrain"))
        landm = rasterize([land_union], etr, elev.shape)
        sm = rasterize([g.buffer(res * 0.6) for g in streams if g.length > 1500], etr, elev.shape)
        img = paper_relief(elev, np.where(sm > 0, 0, landm), res)
        save_raster(name, img, etr, {"attribution": "Terrain: AWS Terrain Tiles (SRTM/USGS 3DEP); Coast: OSM/Overture"})
        print(name, img.shape)


if __name__ == "__main__":
    main()
