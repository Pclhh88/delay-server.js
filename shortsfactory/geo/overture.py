"""Lädt einen Kartenausschnitt aus Overture Maps (S3, anonym) als GeoJSON.

Overture enthält die OSM-Gebäude/Straßen/Gewässer (Lizenz ODbL, Quellenangabe:
"© OpenStreetMap-Mitwirkende, Overture Maps Foundation"). OSM selbst ist in der
Umgebung gesperrt, der S3-Bucket nicht.

    python3 -m shortsfactory.geo.overture 9.418 54.775 9.450 54.802 out_dir
"""
import json, os, sys, urllib.parse
import pyarrow.compute as pc
import pyarrow.dataset as ds
import pyarrow.fs as pafs
import shapely.wkb
from shapely.geometry import mapping

RELEASE = "2026-10-21.0"
BUCKET = "overturemaps-us-west-2/release"

LAYERS = {
    "buildings": ("buildings/type=building",
                  ["id", "geometry", "bbox", "height", "num_floors", "class", "subtype",
                   "names", "roof_shape", "roof_color", "facade_color", "roof_height"]),
    "building_parts": ("buildings/type=building_part",
                       ["id", "geometry", "bbox", "height", "min_height", "num_floors",
                        "building_id", "roof_shape", "roof_color", "facade_color", "roof_height"]),
    "segments": ("transportation/type=segment",
                 ["id", "geometry", "bbox", "subtype", "class", "names"]),
    "water": ("base/type=water", ["id", "geometry", "bbox", "subtype", "class", "names"]),
    "land_use": ("base/type=land_use", ["id", "geometry", "bbox", "subtype", "class", "names"]),
    "land": ("base/type=land", ["id", "geometry", "bbox", "subtype", "class"]),
    "infrastructure": ("base/type=infrastructure", ["id", "geometry", "bbox", "subtype", "class", "names"]),
    "places": ("places/type=place", ["id", "geometry", "bbox", "categories", "names"]),
}


def s3fs():
    kw = dict(anonymous=True, region="us-west-2")
    proxy = os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    if proxy:
        p = urllib.parse.urlparse(proxy)
        kw["proxy_options"] = {"scheme": p.scheme or "http", "host": p.hostname, "port": p.port}
    return pafs.S3FileSystem(**kw)


def _clean(v):
    if isinstance(v, dict):
        return {k: _clean(x) for k, x in v.items() if x is not None}
    if isinstance(v, list):
        return [_clean(x) for x in v]
    return v


def fetch(layer, bbox, fs=None, release=RELEASE):
    path, cols = LAYERS[layer]
    fs = fs or s3fs()
    dset = ds.dataset(f"{BUCKET}/{release}/theme={path}", filesystem=fs, format="parquet")
    cols = [c for c in cols if c in dset.schema.names]
    x0, y0, x1, y1 = bbox
    f = lambda k: pc.field(("bbox", k))
    flt = (f("xmin") <= x1) & (f("xmax") >= x0) & (f("ymin") <= y1) & (f("ymax") >= y0)
    table = dset.to_table(columns=cols, filter=flt)
    feats = []
    for row in table.to_pylist():
        geom = shapely.wkb.loads(row.pop("geometry"))
        row.pop("bbox", None)
        feats.append({"type": "Feature", "geometry": mapping(geom), "properties": _clean(row)})
    return {"type": "FeatureCollection", "features": feats}


def main():
    x0, y0, x1, y1 = map(float, sys.argv[1:5])
    out = sys.argv[5]
    layers = sys.argv[6].split(",") if len(sys.argv) > 6 else list(LAYERS)
    os.makedirs(out, exist_ok=True)
    fs = s3fs()
    for layer in layers:
        fc = fetch(layer, (x0, y0, x1, y1), fs)
        with open(os.path.join(out, f"{layer}.geojson"), "w") as f:
            json.dump(fc, f)
        print(layer, len(fc["features"]), flush=True)


if __name__ == "__main__":
    main()
