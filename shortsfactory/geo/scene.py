"""GeoJSON (aus overture.py) -> scene.json für den isometrischen Stadtrenderer.

Alle Koordinaten werden in Meter um einen Mittelpunkt umgerechnet ([x=Ost, y=Nord]).
Der Renderer (shortsfactory/city) bekommt nur noch fertige, stilisierte Daten:
Flächen (Wasser, Grün, Plätze, Straßen, Gehwege), Gebäude mit Höhe/Dachform/Farbe,
Baumpositionen, Boots- und Autopfade sowie die Wahrzeichen.

    python3 -m shortsfactory.geo.scene config.json
config: {"geodata": "...", "bbox": [lon0, lat0, lon1, lat1], "out": "scene.json",
         "landmarks": {"nordertor": {"name": "Nordertor"}, ...}}
"""
import hashlib, json, math, os, sys
import shapely
from shapely.geometry import shape, box, Point, LineString, Polygon, MultiPolygon
from shapely.ops import unary_union

ROAD_W = {  # Fahrbahnbreite in m (stilisiert, etwas breiter als echt)
    "motorway": 12, "trunk": 11, "primary": 10, "secondary": 9, "tertiary": 8,
    "residential": 6.5, "unclassified": 6, "living_street": 5.5, "service": 4,
}
PATH_W = {"pedestrian": 6, "footway": 2.2, "path": 2.0, "cycleway": 2.2, "steps": 2.2, "track": 2.5}
SIDEWALK = 2.4
GREEN_LU = {"park", "grass", "recreation_ground", "garden", "meadow", "village_green",
            "cemetery", "allotments", "playground", "golf_course", "dog_park"}
PAVED_LU = {"plaza", "pedestrian", "marina"}
PITCH_LU = {"pitch", "track"}
GREEN_LAND = {"grass", "forest", "shrub", "wetland"}

FACADES = ["#c8644a", "#b8553f", "#d9774f",            # Backstein (Flensburg)
           "#f3dc8f", "#f6c27a", "#f2a77e", "#ec9a8f",  # Gelb, Apricot, Lachs, Rosé
           "#f6efe2", "#efe4cc", "#e8d3b0",             # Weiß, Creme, Sand
           "#bfdbe6", "#cfe3c3", "#e9c6d6", "#d9a7c9"]  # Hellblau, Mint, Rosa, Flieder
ROOFS_PITCHED = ["#c9573c", "#b84a34", "#d66a45", "#a8443a", "#5d6670", "#c25a3f"]
ROOFS_FLAT = ["#d8d3c9", "#cfcac0", "#e0dbd2"]
NAMED_COLORS = {"red": "#b9553f", "brown": "#8a5a44", "white": "#f3efe6", "grey": "#a9a9a9",
                "gray": "#a9a9a9", "yellow": "#e9cf8f", "beige": "#e6d5b0", "black": "#3c3c3c",
                "darkgrey": "#5a5f68", "darkgray": "#5a5f68", "green": "#6d8f6a", "blue": "#6f8fb3"}


def hrand(s, salt=""):
    """deterministische Pseudo-Zufallszahl 0..1 aus einer ID"""
    return int(hashlib.md5((salt + s).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF


def color(v, fallback):
    if not v:
        return fallback
    v = v.strip().lower()
    if v.startswith("#") and len(v) in (4, 7):
        return v if len(v) == 7 else "#" + "".join(c * 2 for c in v[1:])
    return NAMED_COLORS.get(v, fallback)


class Proj:
    def __init__(self, lon0, lat0):
        self.lon0, self.lat0 = lon0, lat0
        self.kx = math.cos(math.radians(lat0)) * 111320.0
        self.ky = 110574.0

    def __call__(self, x, y):
        return ((x - self.lon0) * self.kx, (y - self.lat0) * self.ky)

    def geom(self, g):
        return shapely.transform(g, lambda a: (a - (self.lon0, self.lat0)) * (self.kx, self.ky))


def load(path):
    if not os.path.exists(path):
        return []
    return json.load(open(path))["features"]


def rings(geom, digits=2):
    """Polygon/MultiPolygon -> [[outer, hole, ...], ...] mit gerundeten Koordinaten"""
    out = []
    polys = geom.geoms if hasattr(geom, "geoms") else [geom]
    for p in polys:
        if p.geom_type != "Polygon" or p.is_empty or p.area < 0.5:
            continue
        p = shapely.geometry.polygon.orient(p, 1.0)
        rs = [p.exterior] + list(p.interiors)
        out.append([[[round(x, digits), round(y, digits)] for x, y in r.coords[:-1]] for r in rs])
    return out


def polys_only(g):
    if g.is_empty:
        return g
    if g.geom_type in ("Polygon", "MultiPolygon"):
        return g
    return unary_union([p for p in getattr(g, "geoms", []) if p.geom_type in ("Polygon", "MultiPolygon")])


def est_height(p, area, rid):
    h = p.get("height")
    if h:
        return float(h)
    nf = p.get("num_floors")
    cls = p.get("class") or ""
    if nf:
        return nf * 3.1 + 1.2
    base = {"house": 7.5, "detached": 7.5, "semidetached_house": 7.5, "terrace": 8.5,
            "apartments": 12.5, "residential": 11, "garage": 2.8, "garages": 2.8, "shed": 2.6,
            "carport": 2.6, "roof": 3.5, "industrial": 8, "warehouse": 8, "retail": 8,
            "commercial": 11, "office": 13, "school": 11, "university": 12, "hospital": 15,
            "church": 16, "chapel": 7, "hotel": 14, "parking": 9, "transportation": 6}.get(cls)
    if base is None:
        base = 4 if area < 40 else 8 if area < 120 else 11 if area < 800 else 12
    return base * (0.85 + 0.3 * hrand(rid, "h"))


def oriented_rect(poly):
    r = poly.minimum_rotated_rectangle
    c = list(r.exterior.coords)[:4]
    e0 = math.dist(c[0], c[1]); e1 = math.dist(c[1], c[2])
    return r, c, e0, e1


def building(f, proj, clip):
    p = f["properties"]
    g = proj.geom(shape(f["geometry"]))
    if not g.is_valid:
        g = g.buffer(0)
    g = g.intersection(clip)
    if g.is_empty or g.area < 6:
        return None
    rid = p["id"]
    area = g.area
    h = est_height(p, area, rid)
    cls = p.get("class") or ""
    rs = p.get("roof_shape")
    poly = max(g.geoms, key=lambda q: q.area) if hasattr(g, "geoms") else g
    rect, c, e0, e1 = oriented_rect(poly)
    rectness = poly.area / max(rect.area, 1e-6)
    short = min(e0, e1)
    pitched_shapes = {"gabled", "saltbox", "gambrel", "half_hipped", "hipped", "mansard"}
    small_res = cls in ("", "house", "detached", "semidetached_house", "terrace", "apartments",
                        "residential", "church", "chapel", "farm", "barn", "hotel", "retail")
    pitched = (rs in pitched_shapes) or (rs is None and small_res and area < 700 and h < 20
                                          and short < 22 and hrand(rid, "r") < 0.8)
    pitched = pitched and rectness > 0.82 and short > 3.5 and not hasattr(g, "geoms") and not poly.interiors
    b = {"id": rid, "h": round(h, 2),
         "facade": color(p.get("facade_color"), FACADES[int(hrand(rid, "f") * len(FACADES))])}
    if cls in ("house", "detached", "semidetached_house", "terrace", "bungalow"):
        style = "house"
    elif cls in ("garage", "garages", "shed", "carport", "industrial", "warehouse", "roof",
                 "parking", "transportation", "service") or h < 4:
        style = "plain"
    elif cls in ("commercial", "office", "retail", "school", "university", "hospital", "hotel") or h > 20:
        style = "modern"
    else:
        style = "altbau" if hrand(rid, "st") < 0.65 else "modern"
    b["style"] = style
    if cls in ("garage", "garages", "shed", "carport", "industrial", "warehouse"):
        b["facade"] = color(p.get("facade_color"), ["#d8d4cc", "#c9c4bb", "#b9b4ab"][int(hrand(rid, "g") * 3)])
    if pitched:
        ridge_along_0 = e0 >= e1
        rh = min(short * 0.5 * (0.75 + 0.5 * hrand(rid, "p")), 7.5)
        if rs is None and h > 9:
            h = max(h - rh * 0.6, 5)
        b.update(h=round(h, 2), roof="hipped" if rs == "hipped" else "gabled",
                 rect=[[round(x, 2), round(y, 2)] for x, y in c],
                 ridge=0 if ridge_along_0 else 1, rh=round(rh, 2),
                 roofc=color(p.get("roof_color"), ROOFS_PITCHED[int(hrand(rid, "rc") * len(ROOFS_PITCHED))]))
    else:
        inset = g.buffer(-0.35, join_style="mitre")
        if not inset.is_empty and inset.area > 4:
            b["inset"] = rings(inset)
        b.update(roof="flat", poly=rings(g),
                 roofc=color(p.get("roof_color"), ROOFS_FLAT[int(hrand(rid, "rc") * len(ROOFS_FLAT))]))
        if not b["poly"]:
            return None
    fh = 3.6 if style == "altbau" else 3.1
    b["floors"] = max(1, int(round((b["h"] - 0.3) / fh)))
    return b, g


def front_normal(b, target):
    """Außennormale der Wand, die am nächsten an Straße/Weg liegt (für Tür/Laden/Balkone)"""
    if b["roof"] == "flat":
        ring = b["poly"][0][0]
    else:
        ring = b["rect"]
    if Polygon(ring).exterior.is_ccw is False:
        ring = ring[::-1]
    best, bn = 1e9, None
    for i in range(len(ring)):
        (ax, ay), (bx, by) = ring[i], ring[(i + 1) % len(ring)]
        L = math.hypot(bx - ax, by - ay)
        if L < 2.5:
            continue
        nx, ny = (by - ay) / L, -(bx - ax) / L          # CCW-Ring: rechts = außen
        m = Point((ax + bx) / 2 + nx * 3, (ay + by) / 2 + ny * 3)
        d = target.distance(m) - min(L, 20) * 0.05
        if d < best:
            best, bn = d, [round(nx, 3), round(ny, 3)]
    return bn


SHOP_KIND = {  # basic_category -> (Schild, Markisenfarbe)
    "restaurant": ("RESTAURANT", "#d64545"), "casual_eatery": ("IMBISS", "#e8833a"),
    "cafe": ("CAFÉ", "#2f8f83"), "bar": ("BAR", "#2e6b45"), "dance_club": ("CLUB", "#6b3fa0"),
    "music_venue": ("LIVE", "#6b3fa0"), "food_and_beverage_store": ("MARKT", "#3f9b3f"),
    "fashion_and_apparel_store": ("MODE", "#d9578c"), "pharmacy_and_drug_store": ("APOTHEKE", "#2fa36b"),
    "books_music_and_video_store": ("BÜCHER", "#3d6fb6"), "flowers_and_gifts_store": ("BLUMEN", "#e0609a"),
    "hotel": ("HOTEL", "#2b4f8c"), "lodging": ("PENSION", "#2b4f8c"), "bank_or_credit_union": ("BANK", "#c23b3b"),
    "kiosk": ("KIOSK", "#e0a020"), "electronics_store": ("ELEKTRO", "#3d6fb6"),
    "sporting_goods_store": ("SPORT", "#2f7fc1"), "specialty_store": ("LADEN", "#b05a3c"),
    "shopping": ("LADEN", "#b05a3c"), "second_hand_store": ("SECOND HAND", "#8a5bb5"),
    "personal_care_and_beauty_store": ("BEAUTY", "#d9578c"), "arts_crafts_and_hobby_store": ("HOBBY", "#e0a020"),
    "hardware_home_and_garden_store": ("WOHNEN", "#5f8f3a"), "art_gallery": ("GALERIE", "#333333"),
    "museum": ("MUSEUM", "#7a4a2a"), "personal_or_beauty_service": ("FRISEUR", "#c2477a"),
}


def main(cfg_path):
    cfg = json.load(open(cfg_path))
    base = os.path.dirname(os.path.abspath(cfg_path))
    gd = os.path.join(base, cfg["geodata"])
    lon0, lat0, lon1, lat1 = cfg["bbox"]
    proj = Proj((lon0 + lon1) / 2, (lat0 + lat1) / 2)
    x0, y0 = proj(lon0, lat0); x1, y1 = proj(lon1, lat1)
    clip = box(x0, y0, x1, y1)
    P = lambda f: proj.geom(shape(f["geometry"]))

    # Wasser
    water = []
    for f in load(f"{gd}/water.geojson"):
        if f["geometry"]["type"] in ("Polygon", "MultiPolygon") and f["properties"].get("class") != "swimming_pool":
            water.append(P(f).buffer(0).intersection(clip))
        elif f["properties"].get("subtype") == "stream":
            water.append(P(f).buffer(1.5).intersection(clip))
    water = polys_only(unary_union(water))

    # Grün / Plätze / Sportplätze
    green, paved, pitch = [], [], []
    for f in load(f"{gd}/land_use.geojson"):
        if "Polygon" not in f["geometry"]["type"]:
            continue
        c = f["properties"].get("class")
        g = P(f).buffer(0).intersection(clip)
        if c in GREEN_LU:
            green.append(g)
        elif c in PAVED_LU:
            paved.append(g)
        elif c in PITCH_LU:
            pitch.append(g)
    trees = []
    for f in load(f"{gd}/land.geojson"):
        st = f["properties"].get("subtype")
        if st in GREEN_LAND and "Polygon" in f["geometry"]["type"]:
            g = P(f).buffer(0).intersection(clip)
            green.append(g)
            if st == "forest" and not g.is_empty:
                # Wald: Bäume im Raster mit Jitter
                bx0, by0, bx1, by1 = g.bounds
                step = 9.0
                yy = by0
                while yy < by1:
                    xx = bx0
                    while xx < bx1:
                        k = f"{xx:.0f},{yy:.0f}"
                        pt = Point(xx + (hrand(k, "x") - .5) * 6, yy + (hrand(k, "y") - .5) * 6)
                        if g.contains(pt):
                            trees.append(pt)
                        xx += step
                    yy += step
        elif st == "tree" and f["geometry"]["type"] == "Point":
            pt = P(f)
            if clip.contains(pt):
                trees.append(pt)
        elif st == "tree" and f["geometry"]["type"] == "LineString":
            ln = P(f)
            for d in range(0, int(ln.length), 8):
                trees.append(ln.interpolate(d))

    # Straßen
    roads, paths, rails, car_lines = [], [], [], []
    for f in load(f"{gd}/segments.geojson"):
        pr = f["properties"]
        ln = P(f)
        if not ln.intersects(clip.buffer(50)):
            continue
        if pr.get("subtype") == "rail":
            rails.append(ln)
            continue
        c = pr.get("class")
        if c in ROAD_W:
            roads.append(ln.buffer(ROAD_W[c] / 2, cap_style="round", join_style="round"))
            if c in ("primary", "secondary", "tertiary", "trunk", "residential") and ln.length > 40:
                car_lines.append((ln, ROAD_W[c], c))
        elif c in PATH_W:
            paths.append(ln.buffer(PATH_W[c] / 2, cap_style="flat"))
    road_u = unary_union(roads).intersection(clip)
    sidewalk = unary_union([r.buffer(SIDEWALK) for r in roads]).intersection(clip).difference(road_u)
    path_u = unary_union(paths).intersection(clip).difference(road_u)
    rail_u = unary_union([r.buffer(2.0, cap_style="flat") for r in rails]).intersection(clip) if rails else None

    # Infrastruktur: Stege, Parkplätze
    piers, parking, pier_lines = [], [], []
    for f in load(f"{gd}/infrastructure.geojson"):
        pr = f["properties"]
        c = pr.get("class")
        gt = f["geometry"]["type"]
        if c == "pier":
            g = P(f)
            if gt == "LineString":
                pier_lines.append(g)
                g = g.buffer(1.6, cap_style="flat")
            piers.append(g.buffer(0).intersection(clip))
        elif c == "parking" and "Polygon" in gt:
            parking.append(P(f).buffer(0).intersection(clip))
    pier_u = polys_only(unary_union(piers)) if piers else Polygon()

    # Läden (Erdgeschoss) aus Overture Places
    shops = []
    for f in load(f"{gd}/places.geojson"):
        pr = f["properties"]
        k = SHOP_KIND.get(pr.get("basic_category"))
        if k and f["geometry"]["type"] == "Point" and (pr.get("confidence") or 1) > 0.5:
            pt = P(f)
            if clip.contains(pt):
                shops.append((pt, k))
    # Laternen, Bänke
    props = {"lamp": [], "bench": []}
    for f in load(f"{gd}/infrastructure.geojson"):
        c = f["properties"].get("class")
        kind = {"street_lamp": "lamp", "bench": "bench"}.get(c)
        if kind and f["geometry"]["type"] == "Point":
            pt = P(f)
            if clip.contains(pt):
                props[kind].append([round(pt.x, 1), round(pt.y, 1)])
    front_target = unary_union([road_u, path_u] + ([unary_union(paved)] if paved else []))

    # Gebäude
    lm_cfg = cfg.get("landmarks", {})
    lm_names = {v["name"]: k for k, v in lm_cfg.items()}
    blds, footprints, landmarks, fp_b = [], [], {}, []
    for f in load(f"{gd}/buildings.geojson"):
        name = (f["properties"].get("names") or {}).get("primary")
        r = building(f, proj, clip)
        if not r:
            continue
        b, g = r
        b["front"] = front_normal(b, front_target)
        footprints.append(g)
        fp_b.append(b)
        if name in lm_names:
            key = lm_names[name]
            if key in landmarks:  # mehrere Gebäude gleichen Namens: größtes nehmen
                if g.area <= landmarks[key]["area"]:
                    blds.append(b); continue
                blds.append(landmarks[key]["b"])
            rect, c, e0, e1 = oriented_rect(g if g.geom_type == "Polygon" else max(g.geoms, key=lambda q: q.area))
            ang = math.degrees(math.atan2(c[1][1] - c[0][1], c[1][0] - c[0][0]))
            landmarks[key] = {"name": name, "id": b["id"], "b": b, "area": g.area,
                              "center": [round(g.centroid.x, 2), round(g.centroid.y, 2)],
                              "size": [round(e0, 2), round(e1, 2)], "angle": round(ang, 2),
                              "h": b["h"], "model": lm_cfg[key].get("model")}
            continue
        blds.append(b)
    for k, lm in landmarks.items():
        b = lm.pop("b"); lm.pop("area")
        if not lm.get("model"):
            b["landmark"] = k
            blds.append(b)
    bunion = unary_union(footprints)
    tree_fp = shapely.STRtree(footprints)
    for pt, (sign, col) in shops:
        idx = tree_fp.query_nearest(pt, max_distance=4.0)
        if len(idx):
            b = fp_b[int(idx[0])]
            if "shop" not in b and b.get("style") != "plain":
                b["shop"] = {"sign": sign, "color": col}

    # Bäume nicht in Gebäuden / Wasser / Straßen
    blocked = unary_union([bunion.buffer(1.5), water, road_u])
    tree_pts = shapely.points([(t.x, t.y) for t in trees])
    keep = ~shapely.intersects(blocked, tree_pts) if len(trees) else []
    tree_out = []
    for t, k in zip(trees, keep):
        if k:
            s = f"{t.x:.1f},{t.y:.1f}"
            tree_out.append([round(t.x, 1), round(t.y, 1), round(0.8 + 0.5 * hrand(s, "s"), 2)])

    # Boote: entlang der Stege auf der Wasserseite
    boats = []
    water_free = water.difference(pier_u.buffer(1.0)) if not water.is_empty else water
    for ln in pier_lines:
        if ln.length < 15:
            continue
        for d in range(6, int(ln.length) - 4, 11):
            a = ln.interpolate(d); bpt = ln.interpolate(d + 1)
            dx, dy = bpt.x - a.x, bpt.y - a.y
            n = math.hypot(dx, dy) or 1
            nx, ny = -dy / n, dx / n
            for side in (1, -1):
                k = f"{a.x:.0f},{a.y:.0f},{side}"
                if hrand(k, "boat") > 0.55:
                    continue
                off = 5.5
                pt = Point(a.x + nx * off * side, a.y + ny * off * side)
                if water_free.contains(pt.buffer(2.2)):
                    ang = math.degrees(math.atan2(ny * side, nx * side))
                    boats.append([round(pt.x, 1), round(pt.y, 1), round(ang, 1),
                                  round(hrand(k, "len"), 2), round(hrand(k, "typ"), 2)])

    # Autopfade (rechte Spur)
    cars = []
    for ln, w, c in car_lines:
        ln = ln.intersection(clip)
        if ln.is_empty or ln.geom_type != "LineString" or ln.length < 40:
            continue
        for side in (1, -1):
            off = ln.offset_curve(-side * w / 4)
            if off.is_empty or off.geom_type != "LineString":
                continue
            coords = list(off.coords)
            if side == -1:
                coords = coords[::-1]
            cars.append({"pts": [[round(x, 1), round(y, 1)] for x, y in coords],
                         "len": round(off.length, 1), "cls": c})

    def area(g):
        return rings(polys_only(g)) if g is not None and not g.is_empty else []

    green_u = polys_only(unary_union(green)).difference(water) if green else Polygon()
    scene = {
        "meta": {"center": [proj.lon0, proj.lat0], "bounds": [round(x0, 1), round(y0, 1), round(x1, 1), round(y1, 1)],
                 "attribution": "© OpenStreetMap-Mitwirkende, Overture Maps Foundation (ODbL)"},
        "areas": {
            "water": area(water),
            "green": area(green_u.difference(road_u)),
            "pitch": area(unary_union(pitch).difference(road_u)) if pitch else [],
            "paved": area(unary_union(paved).difference(water).difference(road_u)) if paved else [],
            "parking": area(unary_union(parking).difference(road_u)) if parking else [],
            "sidewalk": area(sidewalk.difference(water)),
            "path": area(path_u.difference(water) if not water.is_empty else path_u),
            "road": area(road_u),
            "road_line": area(road_u.buffer(-0.7).boundary.buffer(0.13).intersection(road_u)),
            "rail": area(rail_u) if rail_u is not None else [],
            "pier": area(pier_u),
        },
        "buildings": blds,
        "trees": tree_out,
        "boats": boats,
        "cars": cars,
        "landmarks": landmarks,
        "props": props,
    }
    out = os.path.join(base, cfg["out"])
    with open(out, "w") as fh:
        json.dump(scene, fh, separators=(",", ":"))
    print(f"{out}: {len(blds)} Gebäude, {len(tree_out)} Bäume, {len(boats)} Boote, "
          f"{len(cars)} Autopfade, {sum('shop' in b for b in blds)} Läden, Wahrzeichen: {list(landmarks)} "
          f"({os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    main(sys.argv[1])
