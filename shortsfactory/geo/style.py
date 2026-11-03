"""Kartenstile: Rasterisieren von Geometrien und der 'Papier-Relief'-Look (Referenz 3)."""
import cv2
import numpy as np

# gemessen am Original (Referenz 3, 15-20 s), RGB
PAPER_LAND = (186, 160, 140)
PAPER_WATER = (129, 137, 142)


def rasterize(geoms, transform, shape, value=255):
    """Shapely-Geometrien (im CRS des Transforms) -> uint8-Maske."""
    from rasterio.features import rasterize as rz
    return rz([(g, value) for g in geoms], out_shape=shape, transform=transform, fill=0, dtype="uint8")


def hillshade(elev, res, az=315, alt=45, exaggerate=3.0, smooth_m=110.0):
    e = cv2.GaussianBlur(np.clip(elev, -50, 3000), (0, 0), max(1.0, smooth_m / res)) * exaggerate
    gy, gx = np.gradient(e, res)
    slope = np.arctan(np.hypot(gx, gy))
    aspect = np.arctan2(-gx, gy)
    a, z = np.radians(az), np.radians(90 - alt)
    hs = np.cos(z) * np.cos(slope) + np.sin(z) * np.sin(slope) * np.cos(a - aspect)
    return np.clip(hs, 0, 1)


def paper_noise(shape, seed=7):
    rng = np.random.default_rng(seed)
    n = np.zeros(shape, np.float32)
    for s, w in ((2, 0.5), (8, 0.3), (40, 0.2)):
        small = rng.standard_normal((shape[0] // s + 2, shape[1] // s + 2)).astype(np.float32)
        n += w * cv2.resize(small, (shape[1], shape[0]), interpolation=cv2.INTER_CUBIC)
    return n


def paper_relief(elev, land_mask, res):
    """Höhen + Landmaske -> BGR-Bild im Papierkarten-Look."""
    h, w = elev.shape
    land = (land_mask > 0).astype(np.float32)
    land = cv2.GaussianBlur(land, (0, 0), 0.6)
    hs = hillshade(np.where(land > 0.5, elev, 0), res)
    flat = np.cos(np.radians(45))
    shade = 1.0 + (hs - flat) * 0.55            # 1 = flach
    noise = paper_noise((h, w))
    land_rgb = np.array(PAPER_LAND, np.float32)[None, None] * shade[..., None]
    land_rgb *= (1 + 0.025 * noise)[..., None]
    # Wasser: Grundton, an der Küste etwas dunkler (weicher Innenschatten)
    dist = cv2.distanceTransform((land < 0.5).astype(np.uint8), cv2.DIST_L2, 5) * res
    edge = np.exp(-dist / 250.0)
    water_rgb = np.array(PAPER_WATER, np.float32)[None, None] * (1 - 0.10 * edge)[..., None]
    water_rgb *= (1 + 0.02 * noise)[..., None]
    rgb = land_rgb * land[..., None] + water_rgb * (1 - land[..., None])
    return np.clip(rgb[..., ::-1], 0, 255).astype(np.uint8)
