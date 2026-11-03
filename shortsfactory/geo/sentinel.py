"""Sentinel-2-Echtfarbbild (TCI, 10 m) für eine Bounding-Box, aus dem offenen AWS-Bucket.

Lizenz: Copernicus Sentinel data (frei, Nennung: "Contains modified Copernicus Sentinel data <Jahr>").
"""
import os

import numpy as np

BUCKET = "https://sentinel-cogs.s3.us-west-2.amazonaws.com/sentinel-s2-l2a-cogs"


def _gdal_env():
    ca = "/root/.ccr/ca-bundle.crt"
    env = {"GDAL_DISABLE_READDIR_ON_OPEN": "EMPTY_DIR", "CPL_VSIL_CURL_ALLOWED_EXTENSIONS": ".tif"}
    if os.path.exists(ca):
        env["CURL_CA_BUNDLE"] = ca
    return env


def scene_url(scene_id):
    """scene_id z. B. 'S2B_18TWL_20241011_0_L2A'."""
    _, tile, date, _, _ = scene_id.split("_")
    zone, band, sq = tile[:2], tile[2], tile[3:]
    return f"{BUCKET}/{int(zone)}/{band}/{sq}/{date[:4]}/{int(date[4:6])}/{scene_id}/TCI.tif"


def read_tci(scene_id, bbox_lonlat, out_res=10.0):
    """Liest den Ausschnitt bbox=(lon0, lat0, lon1, lat1) mit Auflösung out_res (Meter, >= 10;
    gröber wird aus den COG-Übersichten gelesen). Gibt (rgb uint8 HxWx3, transform, crs) in UTM zurück."""
    import rasterio
    from rasterio.warp import transform_bounds
    from rasterio.windows import from_bounds
    with rasterio.Env(**_gdal_env()):
        with rasterio.open("/vsicurl/" + scene_url(scene_id)) as src:
            b = transform_bounds("EPSG:4326", src.crs, *bbox_lonlat)
            win = from_bounds(*b, transform=src.transform).round_offsets().round_lengths()
            f = max(1.0, out_res / 10.0)
            shape = (3, int(win.height / f), int(win.width / f))
            rgb = src.read([1, 2, 3], window=win, out_shape=shape)
            from affine import Affine
            tr = src.window_transform(win) * Affine.scale(win.width / shape[2], win.height / shape[1])
            return np.moveaxis(rgb, 0, -1), tr, src.crs
