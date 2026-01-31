from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

import geopandas as gpd
from shapely.geometry import Point, shape
import json

# ---------------------------------------------------------
# INTERNAL IMPORTS
# ---------------------------------------------------------

# NDVI STACK + ML
from backend.ndvi_utils import (
    extract_ndvi_stack,
    generate_ndvi_png,
    generate_rgb_png
)
from backend.model_utils import predict_crop

# RGB / NDVI MONTHLY VISUALIZATION
from backend.raster_utils import (
    ndvi_tif_to_png,
    load_rgb_png,
    sample_ndvi,
    get_paths
)

import os


# ---------------------------------------------------------
# FASTAPI APP
# ---------------------------------------------------------

app = FastAPI(
    title="Crop Intelligence API",
    description="NDVI visualization + Rabi crop prediction (khasra based)",
    version="1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Bounds"] 
)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
STATIC_DIR = os.path.join(BASE_DIR, "frontend")

app.mount("/frontend", StaticFiles(directory=STATIC_DIR), name="frontend")

# ---------------------------------------------------------
# LOAD SHAPEFILE (ONCE)
# ---------------------------------------------------------

SHP_PATH = os.path.join(
    BASE_DIR,
    "data",
    "shapefiles",
    "rabi",
    "rabi_updated.shp"
)

khasra_gdf = gpd.read_file(SHP_PATH)

if khasra_gdf.crs is None or khasra_gdf.crs.to_string() != "EPSG:4326":
    khasra_gdf = khasra_gdf.to_crs(epsg=4326)

# ---------------------------------------------------------
# REQUEST SCHEMAS
# ---------------------------------------------------------

class PredictRequest(BaseModel):
    latitude: float
    longitude: float

class NDVIRequest(BaseModel):
    latitude: float
    longitude: float
    month: str

# ---------------------------------------------------------
# HEALTH
# ---------------------------------------------------------

@app.get("/")
def serve_index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "rabi-ndvi-gis"
    }

@app.get("/visualize.html")
def serve_visualize():
    return FileResponse(os.path.join(STATIC_DIR, "visualize.html"))

# =========================================================
# 🔹 PART 1: STACK-BASED NDVI + ML PREDICTION
# =========================================================

@app.get("/ndvi-image")
def get_ndvi_image():
    buf, _ = generate_ndvi_png()
    return Response(buf.read(), media_type="image/png")

@app.get("/ndvi-bounds")
def get_ndvi_bounds():
    _, bounds = generate_ndvi_png()
    return {"bounds": bounds}


@app.get("/rgb-image")
def get_rgb_image():
    buf, _ = generate_rgb_png()
    return Response(buf.read(), media_type="image/png")

def find_khasra_from_point(latitude: float, longitude: float):
    point = Point(longitude, latitude)
    match = khasra_gdf[khasra_gdf.geometry.contains(point)]

    if match.empty:
        return None
    
    row = match.iloc[0]
    return {
        "khasra_no": str(row["KHASRA_NO"]),
        "area_ha": float(row["Area_ha"]),
        "geometry": row.geometry.__geo_interface__,
        "Rabi": row.get("Rabi", None),
        "crop_name": row.get("CROP_NAME")
    }
def find_khasra_from_number(khasra_no):
    for _, row in khasra_gdf.iterrows():
        if str(row["KHASRA_NO"]) == khasra_no:
            return {
                "khasra_no": row["KHASRA_NO"],
                "area_ha": row["Area_ha"],
                "geometry": row.geometry.__geo_interface__,
                "Rabi": row.get("Rabi"),
                "crop_name": row.get("CROP_NAME")
            }
    return None


RABI_CLASS_MAP = {
    # -------------------------------
    # No crop / fallow
    # -------------------------------
    "कोई फ़सल नहीं": "कोई फ़सल नहीं",

    # -------------------------------
    # Chana (Gram)
    # -------------------------------
    "चना": "चना",

    # -------------------------------
    # Wheat
    # -------------------------------
    "गेहूँ": "गेहूँ",

    # -------------------------------
    # Mustard
    # -------------------------------
    "सरसों": "सरसों",

    # -------------------------------
    # Other crops → Other Crop
    # -------------------------------
    "रजका": "अन्‍य फसल",
    "मिश्रित फसल": "अन्‍य फसल",
    "जौ": "अन्‍य फसल",
    "मेथी": "अन्‍य फसल",
    "तारामीरा": "अन्‍य फसल",
    "अजवायन": "अन्‍य फसल",
    "मिर्च": "अन्‍य फसल",
    "कासनी": "अन्‍य फसल",
    "रायडा": "अन्‍य फसल",
    "जीरा": "अन्‍य फसल",
    "चरी गाजर": "अन्‍य फसल",
    "मटर": "अन्‍य फसल",
}

def normalize_rabi_crop(raw):
    if raw is None:
        return "कोई फ़सल नहीं"

    raw = raw.strip()

    for key, value in RABI_CLASS_MAP.items():
        if key in raw:
            return value

    return "अन्‍य फसल"


# -----------------------------------------
# PREDICT ENDPOINT
# -----------------------------------------
@app.post("/predict")
def predict(req: PredictRequest):

    khasra = find_khasra_from_point(req.latitude, req.longitude)
    if khasra is None:
        return {
            "predicted_crop": "कोई फ़सल नहीं",
            "actual_crop": "कोई फ़सल नहीं",
            "crop_name": "कोई फ़सल नहीं",
            "outside": True,
            "ndvi": None
        }

    ndvi = extract_ndvi_stack(req.latitude, req.longitude)
    if ndvi is None:
        return {
            "predicted_crop": "कोई फ़सल नहीं",
            "actual_crop": "कोई फ़सल नहीं",
            "crop_name": "कोई फ़सल नहीं",
            "outside": True,
            "ndvi": None
        }

    features = [
        req.latitude,
        req.longitude,
        khasra["area_ha"],
        ndvi["NDVI_Nov"],
        ndvi["NDVI_Dec"],
        ndvi["NDVI_Jan"],
        ndvi["NDVI_Feb"]
    ]

    predicted_crop = predict_crop(features)

    # 🔹 Extract & normalize actual crop
    raw_rabi = khasra.get("Rabi")
    actual_crop = normalize_rabi_crop(raw_rabi)

    return {
        "khasra_no": khasra["khasra_no"],
        "area_ha": khasra["area_ha"],
        "geometry": khasra["geometry"],
        "ndvi": ndvi,
        "predicted_crop": predicted_crop,
        "actual_crop": actual_crop,
        "crop_name": khasra["crop_name"],
        "outside": False
    }
@app.post("/predict-by-khasra")
def predict_by_khasra(req: dict):
    khasra_no = str(req.get("khasra_no")).strip()

    # 1️⃣ Find khasra by number
    khasra = find_khasra_from_number(khasra_no)
    if khasra is None:
        return {
            "outside": True
        }

    # 2️⃣ Use centroid for NDVI + ML
    centroid = shape(khasra["geometry"]).centroid
    lat = centroid.y
    lon = centroid.x

    ndvi = extract_ndvi_stack(lat, lon)
    if ndvi is None:
        return {
            "outside": True
        }

    features = [
        lat,
        lon,
        khasra["area_ha"],
        ndvi["NDVI_Nov"],
        ndvi["NDVI_Dec"],
        ndvi["NDVI_Jan"],
        ndvi["NDVI_Feb"]
    ]

    predicted_crop = predict_crop(features)

    actual_crop = normalize_rabi_crop(khasra.get("Rabi"))

    return {
        "khasra_no": khasra["khasra_no"],
        "area_ha": khasra["area_ha"],
        "geometry": khasra["geometry"],
        "ndvi": ndvi,
        "predicted_crop": predicted_crop,
        "actual_crop": actual_crop,
        "crop_name": khasra["crop_name"],
        "outside": False
    }

# =========================================================
# 🔹 PART 2: MONTH-WISE RGB + NDVI VISUALIZATION (NEW)
# =========================================================

@app.get("/viz/rgb-image")
def viz_rgb_image(month: str = "Nov"):
    rgb_path, _ = get_paths(month)
    buf = load_rgb_png(rgb_path)

    # 🔥 Frontend will set bounds after image load
    return Response(
        buf.read(),
        media_type="image/png"
    )

@app.get("/viz/ndvi-image")
def viz_ndvi_image(month: str = "Nov"):
    _, ndvi_path = get_paths(month)
    buf, bounds = ndvi_tif_to_png(ndvi_path)

    return Response(
        buf.read(),
        media_type="image/png",
        headers={"X-Bounds": json.dumps(bounds)}
    )

@app.post("/viz/ndvi-value")
def viz_ndvi_value(req: NDVIRequest):
    value = sample_ndvi(req.latitude, req.longitude, req.month)
    return {
        "month": req.month,
        "ndvi": value
    }

@app.get("/khasra-geojson")
def get_khasra_geojson():
    """
    Send all khasra boundaries for map overlay
    """
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "geometry": row.geometry.__geo_interface__,
                "properties": {
                    "khasra_no": row["KHASRA_NO"],
                    "area_ha": float(row["Area_ha"])
                }
            }
            for _, row in khasra_gdf.iterrows()
        ]
    }
