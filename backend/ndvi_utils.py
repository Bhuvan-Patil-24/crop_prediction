import rasterio
from pyproj import Transformer
import numpy as np
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from io import BytesIO

# =========================================================
# PATH
# =========================================================
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

NDVI_STACK_PATH = os.path.join(
    BASE_DIR,
    "data",
    "images",
    "NDVI_STACK.tif"
)

# =========================================================
# 1️⃣ NDVI STACK SAMPLING (FOR ML PREDICTION)
# =========================================================

def extract_ndvi_stack(latitude: float, longitude: float):
    """
    Extract 4-month NDVI values from stacked NDVI raster.
    Returns dict OR None if point is outside raster.
    """

    with rasterio.open(NDVI_STACK_PATH) as src:

        # ---- CRS transform (lat/lon → raster CRS) ----
        transformer = Transformer.from_crs(
            "EPSG:4326",
            src.crs,
            always_xy=True
        )
        x, y = transformer.transform(longitude, latitude)

        # ---- Bounds check ----
        if not (
            src.bounds.left <= x <= src.bounds.right
            and src.bounds.bottom <= y <= src.bounds.top
        ):
            return None   # outside raster

        # ---- Ensure 4-band stack ----
        if src.count < 4:
            raise ValueError("NDVI_STACK.tif must contain at least 4 bands")

        # ---- Sample NDVI values (all 4 bands at once) ----
        sampled = next(
            src.sample([(x, y)], indexes=[1, 2, 3, 4])
        )

        ndvi_values = []
        for v in sampled:
            if v is None or np.isnan(v) or v == src.nodata:
                ndvi_values.append(0.0)
            else:
                ndvi_values.append(float(v))

        return {
            "NDVI_Nov": ndvi_values[0],
            "NDVI_Dec": ndvi_values[1],
            "NDVI_Jan": ndvi_values[2],
            "NDVI_Feb": ndvi_values[3]
        }

# =========================================================
# 2️⃣ NDVI → PNG CONVERSION (FOR FRONTEND DISPLAY)
# =========================================================

def generate_ndvi_png():
    """
    Convert NDVI RGB raster to transparent PNG (in-memory).
    Outside raster area becomes transparent.
    """

    with rasterio.open(NDVI_STACK_PATH) as src:

        # ---- READ RGB ----
        rgb = src.read([1, 2, 3]).astype("float32")

        # ---- READ MASK (valid data mask) ----
        mask = src.read_masks(1)  # 0 = nodata, 255 = valid

        # ---- NORMALIZE RGB (prevent black image) ----
        min_val = rgb.min()
        max_val = rgb.max()
        if max_val > min_val:
            rgb = (rgb - min_val) / (max_val - min_val)
        rgb = (rgb * 255).astype("uint8")

        # ---- TRANSPOSE TO H,W,C ----
        rgb = np.transpose(rgb, (1, 2, 0))

        # ---- CREATE ALPHA CHANNEL ----
        alpha = np.where(mask > 0, 255, 0).astype("uint8")

        # ---- STACK RGBA ----
        rgba = np.dstack((rgb, alpha))

        # ---- GET BOUNDS ----
        bounds = src.bounds
        transformer = Transformer.from_crs(
            src.crs, "EPSG:4326", always_xy=True
        )

        min_lon, min_lat = transformer.transform(bounds.left, bounds.bottom)
        max_lon, max_lat = transformer.transform(bounds.right, bounds.top)

        leaflet_bounds = [
            [min_lat, min_lon],
            [max_lat, max_lon]
        ]

    # ---- PLOT RGBA (SHARP / NO SMOOTHING) ----
    fig, ax = plt.subplots(figsize=(6, 6))

    ax.imshow(
        rgba,
        interpolation="nearest",   # 🔥 KEY FIX (NO BLUR)
        resample=False             # 🔥 disable resampling
    )

    ax.axis("off")

    buf = BytesIO()
    plt.savefig(
        buf,
        format="png",
        dpi=300,                   # 🔥 higher DPI = sharper
        bbox_inches="tight",
        pad_inches=0,
        transparent=True
    )
    plt.close(fig)
    buf.seek(0)

    return buf, leaflet_bounds


def generate_rgb_png():
    """
    Convert original multispectral TIF to RGB PNG (in-memory)
    """
    RGB_TIF_PATH = os.path.join(
    BASE_DIR,
    "data",
    "Rabbi",
    "23_Feb2025_psscene_analytic_sr_udm2",
    "PSScene",
    "20250223_055317_82_251c_3b_analyticms_sr_mosaic.tif"
    )

    with rasterio.open(RGB_TIF_PATH) as src:
        # Adjust band numbers if needed (PlanetScope example: 3,2,1)
        red = src.read(3)
        green = src.read(2)
        blue = src.read(1)

        bounds = src.bounds

        rgb = np.dstack([red, green, blue]).astype("float32")
        rgb /= np.percentile(rgb, 98)  # contrast stretch
        rgb = np.clip(rgb, 0, 1)

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(rgb)
    ax.axis("off")

    buf = BytesIO()
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)

    # Convert bounds to Leaflet format
    leaflet_bounds = [
        [bounds.bottom, bounds.left],
        [bounds.top, bounds.right]
    ]

    return buf, leaflet_bounds
