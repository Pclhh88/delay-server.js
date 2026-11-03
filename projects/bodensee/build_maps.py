"""Karten-Assets für das Bodensee-Video (Stil map_doc), alles in UTM 32N (EPSG:32632, Meter).

  assets/maps/europe.jpg      Europa-Übersicht (aus Höhendaten eingefärbt, satellitenähnlich), 2 km/px
  assets/maps/region.jpg      Region Bodensee (eingefärbt), 100 m/px
  assets/maps/sat.jpg         Sentinel-2 Echtfarbe Bodensee, 10 m/px
  assets/maps/paper_wide.jpg  Papier-Relief Region, 80 m/px
  assets/maps/paper.jpg       Papier-Relief Bodensee, 20 m/px
  assets/maps/vectors.json    See, Länder, Ufer je Land, Grenze Untersee, Mittellinie, Europa-Grenzen, Leitungen

python3 projects/bodensee/build_maps.py
"""
import json
import math
import os
import sys

import cv2
import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)
from shortsfactory.geo import overture, sentinel, terrain  # noqa: E402
from shortsfactory.geo.style import hillshade, paper_relief, rasterize  # noqa: E402

P = os.path.join(ROOT, "projects", "bodensee")
CACHE = os.path.join(P, "cache")
OUT = os.path.join(P, "assets", "maps")
CRS = "EPSG:32632"
BB_EUROPE = (-11.0, 35.0, 30.0, 61.0)
BB_REGION = (7.4, 46.7, 11.2, 48.9)
BB_LAKE = (8.75, 47.38, 9.95, 47.93)
BB_WIDE = (8.15, 47.05, 10.4, 48.3)
TILES = {"32TMT": ["S2B_32TMT_20250811_0_L2A", "S2B_32TMT_20250920_0_L2A"],
         "32TNT": ["S2B_32TNT_20240823_0_L2A"],
         "32UMU": ["S2B_32UMU_20250811_0_L2A", "S2B_32UMU_20250920_0_L2A", "S2B_32UMU_20240823_0_L2A"],
         "32UNU": ["S2B_32UNU_20240823_0_L2A", "S2B_32UNU_20250811_0_L2A", "S2B_32UNU_20250920_0_L2A"]}


def save_raster(name, img, tr, extra=None):
    cv2.imwrite(os.path.join(OUT, name + ".jpg"), img, [cv2.IMWRITE_JPEG_QUALITY, 92])
    meta = {"path": f"assets/maps/{name}.jpg", "crs": CRS,
            "transform": [tr.a, tr.b, tr.c, tr.d, tr.e, tr.f], "w": img.shape[1], "h": img.shape[0]}
    meta.update(extra or {})
    json.dump(meta, open(os.path.join(OUT, name + ".json"), "w"), indent=1)


def grid(bbox, res):
    from rasterio.transform import from_bounds
    from rasterio.warp import transform_bounds
    b = transform_bounds("EPSG:4326", CRS, *bbox)
    W, H = int((b[2] - b[0]) / res), int((b[3] - b[1]) / res)
    return from_bounds(*b, W, H), (H, W)


def sentinel_mosaic(bbox, res):
    """Mehrere Sentinel-Kacheln auf ein gemeinsames Gitter (erste gültige Szene je Pixel)."""
    import rasterio
    from rasterio.warp import Resampling
    tr, shape = grid(bbox, res)
    out = np.zeros(shape + (3,), np.uint8)
    have = np.zeros(shape, bool)
    for tile, scenes in TILES.items():
        for sc in scenes:
            try:
                with rasterio.Env(**sentinel._gdal_env()):
                    with rasterio.open("/vsicurl/" + sentinel.scene_url(sc)) as src:
                        from rasterio.vrt import WarpedVRT
                        with WarpedVRT(src, crs=CRS, transform=tr, width=shape[1], height=shape[0], nodata=0,
                                       resampling=Resampling.bilinear) as vrt:
                            dst = vrt.read([1, 2, 3])
            except Exception as e:  # Szene fehlt
                print("  skip", sc, e)
                continue
            valid = (dst.max(0) > 0) & ~have
            out[valid] = np.moveaxis(dst, 0, -1)[valid]
            have |= valid
            print("  ", sc, "coverage", round(have.mean(), 3))
            if have.all():
                return out, tr
    return out, tr


def tint_relief(elev, water, res, lake_color=(40, 52, 62)):
    """Höhen -> satellitenähnliche Einfärbung (Grünland, Wald, Fels, Schnee), Wasser dunkel. BGR."""
    e = np.clip(elev, -100, 5000)
    stops = [(0, (64, 86, 52)), (400, (70, 92, 58)), (900, (82, 96, 66)), (1600, (118, 116, 100)),
             (2300, (150, 146, 138)), (2900, (225, 228, 232))]  # RGB
    xs = [s[0] for s in stops]
    rgb = np.stack([np.interp(e, xs, [s[1][c] for s in stops]) for c in range(3)], -1)
    hs = hillshade(e, res, exaggerate=2.0 if res > 500 else 2.5, smooth_m=res * 1.5)
    shade = 0.55 + 0.75 * hs
    rgb = rgb * shade[..., None]
    rng = np.random.default_rng(3)
    noise = cv2.GaussianBlur(rng.standard_normal(e.shape).astype(np.float32), (0, 0), 1.2)
    rgb *= (1 + 0.06 * noise)[..., None]
    w = cv2.GaussianBlur(water.astype(np.float32), (0, 0), 0.8)[..., None]
    rgb = rgb * (1 - w) + np.array(lake_color, np.float32) * w
    return np.clip(rgb[..., ::-1], 0, 255).astype(np.uint8)


def midline(lake_poly, axis_deg, step=200):
    """Mittellinie eines länglichen Sees (Mitte zwischen den Ufern quer zur Achse)."""
    import shapely
    a = math.radians(axis_deg)
    ax = np.array([math.cos(a), math.sin(a)])
    nx = np.array([-ax[1], ax[0]])
    c = np.array(lake_poly.centroid.coords[0])
    pts = np.asarray(lake_poly.exterior.coords)
    s = (pts - c) @ ax
    out = []
    for u in np.arange(s.min() + 1500, s.max() - 800, step):
        p0 = c + ax * u
        ln = shapely.LineString([p0 - nx * 30000, p0 + nx * 30000])
        inter = lake_poly.intersection(ln)
        if inter.is_empty:
            continue
        segs = getattr(inter, "geoms", [inter])
        seg = max(segs, key=lambda g: g.length)
        q = np.asarray(seg.coords)
        out.append(q.mean(0))
    out = np.array(out)
    k = np.ones(9) / 9
    return np.stack([np.convolve(np.pad(out[:, i], 4, mode="edge"), k, "valid") for i in range(2)], 1)


def main():
    vec_only = "--vectors-only" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(CACHE, exist_ok=True)
    import pyarrow.compute as pc
    import shapely
    from shapely.ops import unary_union

    # --- Vektoren -----------------------------------------------------------
    cn = overture.fetch("divisions", "division_area", BB_EUROPE, ["id", "geometry", "country", "subtype", "class"],
                        os.path.join(CACHE, "countries.parquet"),
                        (pc.field("subtype") == "country") & (pc.field("class") == "land"))
    cg = overture.geometries(cn, CRS)
    ccode = cn.column("country").to_pylist()
    countries = {c: g.buffer(0) for c, g in zip(ccode, cg)}
    europe_borders = []
    for c, g in countries.items():
        for poly in getattr(g, "geoms", [g]):
            if poly.area < 2e8:
                continue
            europe_borders.append(np.round(np.asarray(poly.exterior.simplify(1500).coords)).astype(int).tolist())

    water = overture.water(BB_REGION, os.path.join(CACHE, "water.parquet"))
    wg = overture.geometries(water, CRS)
    wsub = water.column("subtype").to_pylist()
    wnames = [(n or {}).get("primary") for n in water.column("names").to_pylist()]
    lake_parts = [g for g, n in zip(wg, wnames) if n and any(k in n for k in ("Bodensee", "Obersee", "Untersee",
                                                                               "Überlinger", "Zeller See", "Gnadensee"))
                  and g.geom_type in ("Polygon", "MultiPolygon")]
    lake = unary_union(lake_parts).buffer(5).buffer(-5)
    lake_main = max(getattr(lake, "geoms", [lake]), key=lambda g: g.area)
    lakes_all = [g for g, s in zip(wg, wsub) if s in ("lake", "reservoir", "water", "river")
                 and g.geom_type in ("Polygon", "MultiPolygon") and g.area > 40000]
    rivers = [g for g, s in zip(wg, wsub) if s in ("river", "stream", "canal") and g.geom_type in ("LineString", "MultiLineString")]
    print("lake parts", len(lake_parts), "area km2", round(lake.area / 1e6, 1))

    # Seeteile: Obersee (östlich ~9.15°E), Untersee (westlich von Konstanz)
    from pyproj import Transformer
    T = Transformer.from_crs("EPSG:4326", CRS, always_xy=True)
    kx, _ = T.transform(9.17, 47.66)  # Konstanz
    parts = list(getattr(lake, "geoms", [lake]))
    obersee = unary_union([p for p in parts if p.centroid.x > kx])
    untersee = unary_union([p for p in parts if p.centroid.x <= kx])
    shores = {}
    for c in ("DE", "AT", "CH"):
        b = lake.boundary.intersection(countries[c].buffer(250))
        shores[c] = [np.round(np.asarray(l.coords)).astype(int).tolist() for l in getattr(b, "geoms", [b])
                     if l.geom_type == "LineString" and l.length > 300]
    # Grenze im Untersee: gemeinsame Grenze DE/CH innerhalb des Untersees
    ubox = shapely.box(*T.transform(8.85, 47.64), *T.transform(9.17, 47.72))
    ub = countries["CH"].boundary.intersection(ubox).intersection(lake.buffer(250))
    ulines = [l for l in getattr(ub, "geoms", [ub]) if l.geom_type == "LineString" and not l.is_empty and l.length > 5]
    ulines = shapely.ops.linemerge(ulines) if ulines else None
    ul = max(getattr(ulines, "geoms", [ulines]), key=lambda g: g.length) if ulines is not None else None
    # Obersee-Achse und Mittellinie
    pts = np.asarray(obersee.convex_hull.exterior.coords) if obersee.geom_type != "Polygon" else np.asarray(obersee.exterior.coords)
    cc = pts - pts.mean(0)
    axis = math.degrees(math.atan2(*np.linalg.svd(cc, full_matrices=False)[2][0][::-1]))
    ober_main = max(getattr(obersee, "geoms", [obersee]), key=lambda g: g.area)
    # Mittellinie Obersee (Konstanz -> Bregenzer Bucht), von Hand entlang der Seemitte gelegt
    mid_ll = [(9.205, 47.664), (9.27, 47.645), (9.33, 47.622), (9.40, 47.595), (9.47, 47.567),
              (9.54, 47.540), (9.61, 47.520), (9.67, 47.508), (9.715, 47.505)]
    m0 = np.array([T.transform(*p) for p in mid_ll])
    seg = np.hypot(*np.diff(m0, axis=0).T)
    sd = np.concatenate([[0], np.cumsum(seg)])
    uu = np.arange(0, sd[-1], 150.0)
    mid = np.stack([np.interp(uu, sd, m0[:, 0]), np.interp(uu, sd, m0[:, 1])], 1)
    axis = math.degrees(math.atan2(m0[-1, 1] - m0[0, 1], m0[-1, 0] - m0[0, 0]))
    # Wasserleitungen: von Sipplingen nach Norden (schematisch)
    sx, sy = T.transform(9.096, 47.798)
    pipes = []
    for ang, L in ((78, 105000), (95, 120000), (60, 80000), (115, 90000), (40, 60000)):
        a = math.radians(ang)
        pipes.append([[round(sx), round(sy)], [round(sx + math.cos(a) * L * 0.5 + 3000), round(sy + math.sin(a) * L * 0.5)],
                      [round(sx + math.cos(a) * L), round(sy + math.sin(a) * L)]])
    lake_poly_list = [np.round(np.asarray(p.exterior.simplify(15).coords)).astype(int).tolist()
                      for p in getattr(lake, "geoms", [lake]) if p.area > 2e5]
    vec = {
        "crs": CRS,
        "lake_main": np.round(np.asarray(lake_main.exterior.simplify(15).coords)).astype(int).tolist(),
        "lake_parts": lake_poly_list,
        "obersee": np.round(np.asarray(ober_main.exterior.simplify(15).coords)).astype(int).tolist(),
        "untersee": [np.round(np.asarray(p.exterior.simplify(15).coords)).astype(int).tolist()
                     for p in getattr(untersee, "geoms", [untersee]) if p.area > 1e5],
        "shore_DE": shores["DE"], "shore_AT": shores["AT"], "shore_CH": shores["CH"],
        "border_untersee": np.round(np.asarray(ul.simplify(10).coords)).astype(int).tolist() if ul is not None else [],
        "midline": np.round(mid).astype(int).tolist(),
        "europe_borders": europe_borders,
        "pipes": pipes,
        "axis_deg": axis,
        "attribution": "© OpenStreetMap contributors, Overture Maps Foundation (ODbL)",
    }
    near = lake.buffer(9000)
    for c in ("DE", "AT", "CH"):
        g = countries[c].intersection(near).difference(lake.buffer(30))
        vec["near_" + c] = [np.round(np.asarray(p.exterior.simplify(60).coords)).astype(int).tolist()
                            for p in getattr(g, "geoms", [g]) if p.area > 2e6]
    for c in ("DE", "AT", "CH"):
        g = countries[c].intersection(shapely.box(*shapely.ops.transform(T.transform, shapely.box(*BB_REGION)).bounds))
        vec["country_" + c] = [np.round(np.asarray(p.exterior.simplify(80).coords)).astype(int).tolist()
                               for p in getattr(g, "geoms", [g]) if p.area > 5e6]
    json.dump(vec, open(os.path.join(OUT, "vectors.json"), "w"), separators=(",", ":"))
    print("axis", round(axis, 1), "midline pts", len(mid), "untersee border pts", len(vec["border_untersee"]),
          "shores", {c: len(v) for c, v in shores.items()})

    if vec_only:
        return
    # --- Europa / Region (eingefärbt) --------------------------------------
    for name, bb, z, res in ((("europe", BB_EUROPE, 5, 2500.0), ("region", BB_REGION, 9, 100.0))
                             if "--skip-tint" not in sys.argv else ()):
        elev, etr, _ = terrain.elevation(bb, z, CRS, res, os.path.join(CACHE, "terrain"))
        wat = elev <= 0.5
        if name == "region":
            wat = wat | (rasterize(lakes_all, etr, elev.shape) > 0)
        save_raster(name, tint_relief(elev, wat, res), etr, {"attribution": "Terrain: AWS Terrain Tiles; Gewässer: OSM/Overture"})
        print(name, elev.shape)

    # --- Satellit ----------------------------------------------------------
    rgb, tr = sentinel_mosaic(BB_LAKE, 10.0)
    f = np.clip(cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR).astype(np.float32) / 255 * 1.08, 0, 1) ** 0.85
    sat = (f * 255).astype(np.uint8)
    save_raster("sat", sat, tr, {"attribution": "Contains modified Copernicus Sentinel data 2024/2025"})
    rgbw, trw = sentinel_mosaic(BB_WIDE, 40.0)
    fw = np.clip(cv2.cvtColor(rgbw, cv2.COLOR_RGB2BGR).astype(np.float32) / 255 * 1.08, 0, 1) ** 0.85
    save_raster("sat_wide", (fw * 255).astype(np.uint8), trw, {"attribution": "Contains modified Copernicus Sentinel data 2024/2025"})
    cv2.imwrite(os.path.join(OUT, "sat_wide_valid_mask.png"), ((rgbw.max(2) > 0) * 255).astype(np.uint8))
    cv2.imwrite(os.path.join(OUT, "sat_lake_mask.png"), rasterize([lake], tr, sat.shape[:2]))
    cv2.imwrite(os.path.join(OUT, "sat_valid_mask.png"), ((rgb.max(2) > 0) * 255).astype(np.uint8))

    # --- Papier ------------------------------------------------------------
    for name, bb, z, res in (("paper_wide", BB_REGION, 9, 80.0), ("paper", BB_WIDE, 11, 40.0)):
        elev, etr, _ = terrain.elevation(bb, z, CRS, res, os.path.join(CACHE, "terrain"))
        wat = rasterize(lakes_all, etr, elev.shape) > 0
        sm = rasterize([g.buffer(res * 0.7) for g in rivers if g.length > 3000], etr, elev.shape) > 0
        landm = np.where(wat | sm, 0, 255).astype(np.uint8)
        save_raster(name, paper_relief(elev, landm, res), etr, {"attribution": "Terrain: AWS Terrain Tiles; Gewässer: OSM/Overture"})
        print(name, elev.shape)


if __name__ == "__main__":
    main()
