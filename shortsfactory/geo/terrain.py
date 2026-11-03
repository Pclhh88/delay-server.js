"""Höhenmodell aus den offenen AWS Terrain Tiles (Terrarium-PNG, Mapzen/Tilezen; frei nutzbar,
Quellen u. a. SRTM, USGS 3DEP, GMTED). Liefert ein Höhenraster in einem Ziel-CRS."""
import io
import math
import os
import urllib.request

import numpy as np

URL = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"


def _tile(z, x, y, cache):
    p = os.path.join(cache, f"{z}_{x}_{y}.png")
    if not os.path.exists(p):
        os.makedirs(cache, exist_ok=True)
        with urllib.request.urlopen(URL.format(z=z, x=x, y=y), timeout=60) as r:
            open(p, "wb").write(r.read())
    import cv2
    im = cv2.imread(p, cv2.IMREAD_COLOR)[..., ::-1].astype(np.float32)
    return im[..., 0] * 256 + im[..., 1] + im[..., 2] / 256 - 32768


def _deg2tile(lon, lat, z):
    n = 2 ** z
    x = (lon + 180) / 360 * n
    y = (1 - math.asinh(math.tan(math.radians(lat))) / math.pi) / 2 * n
    return x, y


def elevation(bbox, z, dst_crs, dst_res, cache="models/terrain_cache"):
    """bbox=(lon0,lat0,lon1,lat1) -> (elev float32 HxW, affine transform, crs) im Ziel-CRS."""
    from rasterio.transform import from_bounds
    from rasterio.warp import Resampling, reproject, transform_bounds
    x0, y1 = _deg2tile(bbox[0], bbox[1], z)
    x1, y0 = _deg2tile(bbox[2], bbox[3], z)
    tx = range(int(x0), int(x1) + 1)
    ty = range(int(y0), int(y1) + 1)
    mosaic = np.vstack([np.hstack([_tile(z, x, y, cache) for x in tx]) for y in ty])
    # Web-Mercator-Grenzen des Mosaiks
    R = 6378137.0
    n = 2 ** z
    def merc(t):
        return t / n * 2 * math.pi * R - math.pi * R
    left, right = merc(tx[0]), merc(tx[-1] + 1)
    top, bottom = math.pi * R - ty[0] / n * 2 * math.pi * R, math.pi * R - (ty[-1] + 1) / n * 2 * math.pi * R
    src_tr = from_bounds(left, bottom, right, top, mosaic.shape[1], mosaic.shape[0])
    b = transform_bounds("EPSG:4326", dst_crs, *bbox)
    W = int((b[2] - b[0]) / dst_res)
    H = int((b[3] - b[1]) / dst_res)
    dst_tr = from_bounds(*b, W, H)
    out = np.zeros((H, W), np.float32)
    reproject(mosaic, out, src_transform=src_tr, src_crs="EPSG:3857", dst_transform=dst_tr,
              dst_crs=dst_crs, resampling=Resampling.bilinear)
    return out, dst_tr, dst_crs
