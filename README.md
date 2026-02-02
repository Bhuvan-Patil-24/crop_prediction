---
title: Rabi Ndvi Gis
emoji: 🌖
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
short_description: This project is linked with Micronet Solutions
---

# 🌾 Rabi Crop Prediction & NDVI Visualization  
### *(GIS + Remote Sensing + Web Mapping)*

A **GIS-correct, production-ready web application** for **Rabi season crop analysis** using **NDVI time-series**, **cadastral (khasra) boundaries**, and **interactive web maps**.

This project is designed for **research, academic, and government-grade use cases**, with strict adherence to **GIS standards** (CRS correctness, raster–vector alignment, and spatial accuracy).

---

## 🚀 Features

### 🗺️ Main Prediction Page
- OpenStreetMap basemap (**EPSG:3857**)
- NDVI stack overlay (**GeoTIFF → PNG**)
- Always-visible cadastral (**khasra**) polygons
- Optional khasra number labels (zoom-aware toggle)
- Click on map to:
  - Identify khasra
  - Show **predicted Rabi crop**
  - Show **actual crop** (from shapefile)
  - Display **NDVI trend (Nov–Feb)**

---

### 🛰️ NDVI & RGB Visualization Page
- Side-by-side **RGB and NDVI maps**
- Month selector: **Nov, Dec, Jan, Feb**
- Pixel-level NDVI value extraction
- Crop / No-crop legend
- Same cadastral overlay as main page

---

## 📊 Data & GIS Correctness
- NDVI GeoTIFFs in **EPSG:32643 (UTM)**
- Cadastral shapefile in **EPSG:4326**
- Proper CRS transformations (**no CRS.Simple hacks**)
- Raster sampling via **Rasterio**
- Vector operations via **GeoPandas / Shapely**

---

## 🧱 Tech Stack

### Backend
- **FastAPI**
- **Rasterio** (NDVI sampling)
- **GeoPandas + Shapely** (khasra polygons)
- **PyProj** (CRS transforms)
- **Matplotlib** (TIFF → PNG, server-side)

### Frontend
- Vanilla **HTML / CSS / JavaScript**
- **Leaflet.js**
- **Chart.js**
- **OpenStreetMap** tiles

### Deployment
- **Docker**
- **Hugging Face Spaces**
- **Python 3.9 compatible**

---

## 📁 Project Structure

```bash
rabi-ndvi-gis/
│
├── backend/
│ ├── models/
│ ├── app.py # FastAPI app
│ ├── model_utils.py
│ ├── raster_utils.py # NDVI handling
│ └── ndvi_utils.py # Khasra logic
│
├── frontend/
│ ├── index.html
│ ├── visualize.html
│ ├── style.css
│ ├── visualize.css
│ ├── script.js
│ └── visualize.js
│
├── data/
│ ├── images/
│ │ └── NDVI_STACK.tif
│ └── shapefiles/
│   └── rabi_updated.shp
│
├── requirements.txt
├── Dockerfile
├── .dockerignore
└── README.md
```

---

## ⚙️ Installation (Local Development)

### 1️⃣ Create virtual environment (Python 3.9)

```bash
python -m venv venv
source venv/bin/activate   # Linux / Mac
venv\Scripts\activate # Windows
```

### 2️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### ▶️ Run Locally
```bash
uvicorn backend.app:app --host 0.0.0.0 --port 8000
```

### Open in browser:
```bash
http://127.0.0.1:8000
```

---

### 🧠 Crop Classes

The system works with 5 standardized Rabi crop classes:

- कोई फ़सल नहीं (No Crop)
- चना (Gram)
- गेहूँ (Wheat)
- सरसों (Mustard)
- अन्य फसल (Other Crop)

Actual crop names from the shapefile are mapped internally to these classes.

---

### 📜 License
This project is intended for educational, research, and demonstration purposes.
For government or commercial deployment, ensure proper data licensing.

---

### 👤 Author

**Bhuvan Patil**

GIS • Remote Sensing • Machine Learning • Web Mapping