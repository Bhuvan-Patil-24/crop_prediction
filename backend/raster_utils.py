import rasterio
from pyproj import Transformer
import numpy as np
import os
from io import BytesIO
import matplotlib

# 🔥 Prevent Tkinter crash
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

RGB_PNG_DIR = os.path.join(
    BASE_DIR,
    "data",
    "Rabbi",
    "images"
)

NDVI_TIF_DIR = os.path.join(
    BASE_DIR,
    "data",
    "images"
)


MONTH_MAP = {
    "Nov": (
        os.path.join(RGB_PNG_DIR, "RGB_Nov.png"),
        os.path.join(NDVI_TIF_DIR, "NDVI_Nov.tif")
    ),
    "Dec": (
        os.path.join(RGB_PNG_DIR, "RGB_Dec.png"),
        os.path.join(NDVI_TIF_DIR, "NDVI_Dec.tif")
    ),
    "Jan": (
        os.path.join(RGB_PNG_DIR, "RGB_Jan.png"),
        os.path.join(NDVI_TIF_DIR, "NDVI_Jan.tif")
    ),
    "Feb": (
        os.path.join(RGB_PNG_DIR, "RGB_Feb.png"),
        os.path.join(NDVI_TIF_DIR, "NDVI_Feb.tif")
    ),
}

# --------------------------------------------------
# PATH HELPER
# --------------------------------------------------

def get_paths(month):
    rgb_png, ndvi_tif = MONTH_MAP[month]
    return (
        os.path.join(RGB_PNG_DIR, rgb_png),
        os.path.join(NDVI_TIF_DIR, ndvi_tif)
    )

# --------------------------------------------------
# RGB PNG LOADER (NO PROCESSING)
# --------------------------------------------------

def load_rgb_png(png_path):
    with open(png_path, "rb") as f:
        buf = BytesIO(f.read())
        buf.seek(0)

    # 🔥 Fake pixel bounds (CRS.Simple)
    # These will be overridden by frontend using image size
    return buf

# --------------------------------------------------
# NDVI TIF → PNG (PIXEL BOUNDS)
# --------------------------------------------------

def ndvi_tif_to_png(tif_path):
    """
    Convert NDVI GeoTIFF to sharp PNG with transparency.
    Uses raster mask for alpha channel.
    Keeps NDVI colormap (RdYlGn).
    """

    with rasterio.open(tif_path) as src:
        # ---- READ NDVI BAND ----
        ndvi = src.read(1).astype("float32")

        # ---- READ VALID DATA MASK ----
        mask = src.read_masks(1)  # 0 = nodata, 255 = valid

        # ---- MASK INVALID NDVI VALUES ----
        ndvi = np.where((ndvi < -1) | (ndvi > 1), np.nan, ndvi)

        height, width = ndvi.shape

    # -------------------------------------------------
    # 🔥 APPLY MASK PROPERLY (THIS WAS MISSING)
    # -------------------------------------------------
    ndvi_masked = np.ma.array(
        ndvi,
        mask=(mask == 0) | np.isnan(ndvi)
    )

    # ---- PLOT NDVI (NO BLUR, NO RESAMPLING) ----
    fig, ax = plt.subplots(figsize=(6, 6))

    ax.imshow(
        ndvi_masked,
        cmap="RdYlGn",           # unchanged
        vmin=-0.2,
        vmax=0.9,
        interpolation="nearest",
        resample=False
    )

    ax.axis("off")

    # ---- SAVE WITH TRANSPARENCY ----
    buf = BytesIO()
    plt.savefig(
        buf,
        format="png",
        dpi=300,
        bbox_inches="tight",
        pad_inches=0,
        transparent=True        # now ACTUALLY works
    )
    plt.close(fig)
    buf.seek(0)

    # ---- PIXEL BOUNDS FOR CRS.Simple ----
    pixel_bounds = [[0, 0], [height, width]]

    return buf, pixel_bounds

# --------------------------------------------------
# NDVI SAMPLING (PIXEL SPACE)
# --------------------------------------------------

# Create transformer ONCE (global / cached)
wgs84_to_utm = Transformer.from_crs(
    "EPSG:4326",
    "EPSG:32643",
    always_xy=True
)
def sample_ndvi(lat, lon, month):
    """
    lat, lon are geographic coordinates (EPSG:4326)
    """

    _, ndvi_tif = get_paths(month)

    # Convert lat/lon → UTM
    x_utm, y_utm = wgs84_to_utm.transform(lon, lat)

    with rasterio.open(ndvi_tif) as src:
        # Check if point is inside raster bounds
        if not (
            src.bounds.left <= x_utm <= src.bounds.right and
            src.bounds.bottom <= y_utm <= src.bounds.top
        ):
            return None

        # Sample using rasterio (correct way)
        sample = list(src.sample([(x_utm, y_utm)], masked=True))[0]
        if sample.mask[0]:
            return None

        value = float(sample[0])

        if np.isnan(value):
            return None

        return value