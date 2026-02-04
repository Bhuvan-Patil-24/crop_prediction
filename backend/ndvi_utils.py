import rasterio
from pyproj import Transformer
import numpy as np
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from io import BytesIO

# =========================================================
# PATHS
# =========================================================

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

NDVI_STACK_PATH = os.path.join(
    BASE_DIR,
    "data",
    "images",
    "NDVI_STACK.tif"
)

SEGMENTATION_TIF_PATH = os.path.join(
    BASE_DIR,
    "data",
    "output",
    "segmentation_5classes3.tif"
)

# =========================================================
# 1️⃣ NDVI STACK SAMPLING (FOR ML)
# =========================================================

def extract_ndvi_stack(latitude: float, longitude: float):
    """
    Extract 4-band NDVI values at lat/lon.
    Returns None if outside raster.
    """

    with rasterio.open(NDVI_STACK_PATH) as src:

        transformer = Transformer.from_crs(
            "EPSG:4326", src.crs, always_xy=True
        )

        x, y = transformer.transform(longitude, latitude)

        if not (
            src.bounds.left <= x <= src.bounds.right and
            src.bounds.bottom <= y <= src.bounds.top
        ):
            return None

        if src.count < 4:
            raise ValueError("NDVI stack must have 4 bands")

        values = next(src.sample([(x, y)], indexes=[1, 2, 3, 4]))

        out = []
        for v in values:
            if v is None or np.isnan(v) or v == src.nodata:
                out.append(0.0)
            else:
                out.append(float(v))

        return {
            "NDVI_Nov": out[0],
            "NDVI_Dec": out[1],
            "NDVI_Jan": out[2],
            "NDVI_Feb": out[3],
        }

# =========================================================
# 2️⃣ NDVI STACK → PNG (REFERENCE LOGIC)
# =========================================================

def generate_ndvi_png():
    """
    NDVI stack → RGBA PNG
    Uses original colors
    Removes background via mask
    """

    with rasterio.open(NDVI_STACK_PATH) as src:

        # ---- READ RGB (AS-IS) ----
        rgb = src.read([1, 2, 3]).astype("float32")

        # ---- READ VALID DATA MASK ----
        mask = src.read_masks(1)

        # ---- NORMALIZE (SAFE) ----
        min_val = np.nanmin(rgb)
        max_val = np.nanmax(rgb)
        if max_val > min_val:
            rgb = (rgb - min_val) / (max_val - min_val)

        rgb = (rgb * 255).astype("uint8")

        # ---- TRANSPOSE ----
        rgb = np.transpose(rgb, (1, 2, 0))

        # ---- ALPHA CHANNEL ----
        alpha = np.where(mask > 0, 255, 0).astype("uint8")

        rgba = np.dstack([rgb, alpha])

        # ---- BOUNDS ----
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

    # ---- PLOT (NO BLUR) ----
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(rgba, interpolation="nearest", resample=False)
    ax.axis("off")

    buf = BytesIO()
    plt.savefig(
        buf,
        format="png",
        dpi=300,
        bbox_inches="tight",
        pad_inches=0,
        transparent=True
    )
    plt.close(fig)
    buf.seek(0)

    return buf, leaflet_bounds

# =========================================================
# 3️⃣ SEGMENTATION TIFF → PNG (USING SAME LOGIC)
# =========================================================

def generate_rgb_png():

    with rasterio.open(SEGMENTATION_TIF_PATH) as src:

        # ---- READ RGB (AS-IS) ----
        rgb = src.read([1, 2, 3]).astype("float32")

        # ---- READ MASK ----
        mask = src.read_masks(1)

        # ---- NORMALIZE SAME AS NDVI ----
        min_val = np.nanmin(rgb)
        max_val = np.nanmax(rgb)
        if max_val > min_val:
            rgb = (rgb - min_val) / (max_val - min_val)

        rgb = (rgb * 255).astype("uint8")

        # ---- TRANSPOSE ----
        rgb = np.transpose(rgb, (1, 2, 0))

        # ---- ALPHA (REMOVE BLACK BACKGROUND) ----
        alpha = np.where(mask > 0, 255, 0).astype("uint8")

        rgba = np.dstack([rgb, alpha])

    # ---- PLOT (NO BLUR) ----
    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(rgba, interpolation="nearest", resample=False)
    ax.axis("off")

    buf = BytesIO()
    plt.savefig(
        buf,
        format="png",
        dpi=300,
        bbox_inches="tight",
        pad_inches=0,
        transparent=True
    )
    plt.close(fig)
    buf.seek(0)

    return buf
