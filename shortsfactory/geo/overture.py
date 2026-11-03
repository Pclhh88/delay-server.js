"""Overture-Maps-Daten (OpenStreetMap-basiert, ODbL) für eine Bounding-Box aus dem offenen S3-Bucket.

Nennung bei Veröffentlichung: "© OpenStreetMap contributors, Overture Maps Foundation".
"""
import os

RELEASE = "2026-10-21.0"


def fetch(theme, typ, bbox, columns, out_path, extra_filter=None, release=RELEASE):
    """Liest alle Features von theme/type, deren bbox die bbox=(lon0,lat0,lon1,lat1) schneidet,
    und speichert sie als Parquet (Cache: existiert die Datei, wird nichts geladen)."""
    import pyarrow.compute as pc
    import pyarrow.dataset as ds
    import pyarrow.fs as pfs
    import pyarrow.parquet as pq
    if os.path.exists(out_path):
        return pq.read_table(out_path)
    fs = pfs.S3FileSystem(anonymous=True, region="us-west-2")
    d = ds.dataset(f"overturemaps-us-west-2/release/{release}/theme={theme}/type={typ}/",
                   filesystem=fs, format="parquet")
    x0, y0, x1, y1 = bbox
    f = ((pc.field("bbox", "xmin") < x1) & (pc.field("bbox", "xmax") > x0)
         & (pc.field("bbox", "ymin") < y1) & (pc.field("bbox", "ymax") > y0))
    if extra_filter is not None:
        f = f & extra_filter
    tb = d.to_table(columns=columns, filter=f)
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    pq.write_table(tb, out_path)
    return tb


def roads(bbox, out_path):
    import pyarrow.compute as pc
    return fetch("transportation", "segment", bbox, ["id", "geometry", "class", "names"], out_path,
                 pc.field("subtype") == "road")


def land(bbox, out_path):
    return fetch("base", "land", bbox, ["id", "geometry", "subtype", "class", "names"], out_path)


def water(bbox, out_path):
    return fetch("base", "water", bbox, ["id", "geometry", "subtype", "class", "names"], out_path)


def geometries(table, crs_to=None):
    """WKB-Spalte -> Liste shapely-Geometrien (optional in Ziel-CRS projiziert)."""
    import shapely
    import shapely.ops
    geoms = shapely.from_wkb(table.column("geometry").to_pylist())
    if crs_to:
        from pyproj import Transformer
        tr = Transformer.from_crs("EPSG:4326", crs_to, always_xy=True)
        geoms = [shapely.ops.transform(tr.transform, g) for g in geoms]
    return geoms
